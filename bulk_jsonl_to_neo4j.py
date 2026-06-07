import argparse
import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from typing import Dict, List, Tuple, Set

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

Triple = Tuple[str, str, str]


def clean_text(val) -> str:
    if val is None:
        return ""
    s = str(val)
    s = re.sub(r"\s+", " ", s.strip())
    return s


def record_to_text(rec: Dict) -> str:
    keys_priority = [
        "服务事项", "事项", "title",
        "实施依据", "法律依据", "依据",
        "责任事项", "职责", "责任",
        "权力类型", "类型",
        "行使主体", "行驶主体", "主管部门",
        "承办机构", "承办部门",
        "监管电话", "联系电话",
        "统一发布平台unid", "unid", "id",
    ]
    seen: Set[str] = set()
    parts: List[str] = []

    for k in keys_priority:
        if k in rec:
            v = clean_text(rec.get(k))
            if v and v not in seen:
                parts.append(f"{k}: {v}")
                seen.add(v)

    for k, v in rec.items():
        if k in keys_priority:
            continue
        vv = clean_text(v)
        if vv and vv not in seen:
            parts.append(f"{k}: {vv}")
            seen.add(vv)

    return "\n".join(parts)


def write_tsv_line(fh, triples: List[Triple]) -> None:
    for h, r, t in triples:
        fh.write(f"{h}\t{r}\t{t}\n")


def escape_quote(s: str) -> str:
    return str(s).replace("'", "\\'")


def rel_to_type(r: str) -> str:
    return ''.join(c if str(c).isalnum() else '_' for c in str(r)).upper() or 'RELATED_TO'


def write_cypher_lines(fh, triples: List[Triple]) -> None:
    for h, r, t in triples:
        h_e = escape_quote(h)
        t_e = escape_quote(t)
        r_t = rel_to_type(r)
        # 单条语句内定义并使用变量，避免变量作用域问题
        fh.write(
            f"MERGE (h:Entity {{name: '{h_e}'}}) "
            f"MERGE (t:Entity {{name: '{t_e}'}}) "
            f"MERGE (h)-[:`{r_t}`]->(t);\n"
        )


async def run_bulk(jsonl_path: str, out_base: str, server_cmd: str = "python", server_args: List[str] = None):
    server_args = server_args or ["kg_server.py"]
    load_dotenv()

    params = StdioServerParameters(command=server_cmd, args=server_args, env=os.environ)

    tsv_path = f"{out_base}_triples.tsv"
    cypher_path = f"{out_base}.cypher"

    os.makedirs(os.path.dirname(tsv_path) or ".", exist_ok=True)
    # 初始化文件（覆盖重建）
    with open(tsv_path, "w", encoding="utf-8") as tf:
        tf.write("")
    with open(cypher_path, "w", encoding="utf-8") as cf:
        cf.write("// Neo4j import script (incremental)\n")
        cf.write("CREATE INDEX IF NOT EXISTS FOR (n:Entity) ON (n.name);\n\n")

    seen_triples: Set[Triple] = set()

    async with AsyncExitStack() as stack:
        stdio_transport = await stack.enter_async_context(stdio_client(params))
        stdio, write = stdio_transport
        session = await stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        prefer_tool = "build_and_analyze_kg" if "build_and_analyze_kg" in tool_names else "build_knowledge_graph"

        with open(jsonl_path, "r", encoding="utf-8") as f, \
             open(tsv_path, "a", encoding="utf-8") as tsv_fh, \
             open(cypher_path, "a", encoding="utf-8") as cyp_fh:

            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    print(f"跳过第{line_no}行（JSON解析失败）")
                    continue

                text = record_to_text(rec)
                if not text:
                    continue

                args = {"text": text, "output_file": f"{out_base}_tmp.html", "enable_analysis": True, "auto_enhance": True}
                try:
                    result = await session.call_tool(prefer_tool, args)
                    payload = json.loads(result.content[0].text)
                except Exception as e:
                    print(f"第{line_no}行处理失败: {e}")
                    continue

                triples: List[Triple] = []
                summary = payload.get("summary", {})
                if isinstance(summary.get("final_triples"), list):
                    for t in summary["final_triples"]:
                        if isinstance(t, dict):
                            h, r, ta = t.get("head"), t.get("relation"), t.get("tail")
                            if h and r and ta:
                                triples.append((h, r, ta))
                if not triples:
                    kg = payload.get("stages", {}).get("original_knowledge_graph", {})
                    for t in kg.get("triples", []):
                        if isinstance(t, dict):
                            h, r, ta = t.get("head"), t.get("relation"), t.get("tail")
                            if h and r and ta:
                                triples.append((h, r, ta))

                # 去重后增量写入
                new_triples = [tr for tr in triples if tr not in seen_triples]
                if not new_triples:
                    continue
                for tr in new_triples:
                    seen_triples.add(tr)

                write_tsv_line(tsv_fh, new_triples)
                write_cypher_lines(cyp_fh, new_triples)
                tsv_fh.flush(); cyp_fh.flush()
                print(f"已写入第{line_no}行的 {len(new_triples)} 条三元组（累计 {len(seen_triples)}）")

    print("✅ 流式写入完成：")
    print(" - TSV:", os.path.abspath(tsv_path))
    print(" - Cypher:", os.path.abspath(cypher_path))
    print(f"共输出三元组 {len(seen_triples)} 条")


def main():
    parser = argparse.ArgumentParser(description="通过增强流程流式将 JSONL 转为 Neo4j 三元组（边处理边写入）")
    parser.add_argument("input", help="输入 JSONL 文件路径（每行一个 JSON 对象）")
    parser.add_argument("--out-base", default=None, help="输出文件前缀（默认与输入同名去后缀）")
    parser.add_argument("--server-cmd", default="python", help="服务器启动命令（默认 python）")
    parser.add_argument("--server-args", nargs='*', default=["kg_server_enhanced.py"], help="服务器启动参数（默认 kg_server_enhanced.py）")
    args = parser.parse_args()

    in_path = args.input
    if not os.path.exists(in_path):
        raise FileNotFoundError(f"输入文件不存在: {in_path}")

    out_base = args.out_base or os.path.splitext(in_path)[0]
    asyncio.run(run_bulk(in_path, out_base, server_cmd=args.server_cmd, server_args=args.server_args))


if __name__ == "__main__":
    main()
