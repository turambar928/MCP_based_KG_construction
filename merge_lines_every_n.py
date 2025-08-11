import argparse
import os
from typing import List

PUNCTUATION_ENDINGS = ("。", "！", "?", "？", ".", "!")


def read_texts_from_file(input_path: str) -> List[str]:
    texts: List[str] = []
    with open(input_path, "r", encoding="utf-8") as fin:
        for raw in fin:
            line = raw.strip()
            if not line:
                continue
            # 支持“编号\t文本”或“纯文本”两种输入
            parts = line.split("\t", 1)
            text = parts[-1].strip()
            if text:
                texts.append(text)
    return texts


def ensure_trailing_punctuation(text: str) -> str:
    if not text:
        return text
    return text if text.endswith(PUNCTUATION_ENDINGS) else text + "。"


def merge_every_n(texts: List[str], n: int, sep: str, ensure_period: bool) -> List[str]:
    merged_lines: List[str] = []
    for i in range(0, len(texts), n):
        chunk = texts[i : i + n]
        merged = sep.join(chunk)
        if ensure_period:
            merged = ensure_trailing_punctuation(merged)
        merged_lines.append(merged)
    return merged_lines


def write_output(output_path: str, merged_lines: List[str]) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fout:
        for idx, line in enumerate(merged_lines, 1):
            fout.write(f"{idx}\t{line}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将输入文本每N条合并为一行（使用分隔符连接），输出仍为 编号\t文本 格式"
    )
    parser.add_argument("input", help="输入 txt 文件路径（支持 编号\\t文本 或 纯文本）")
    parser.add_argument(
        "--output",
        help="输出文件路径（默认自动在输入文件名后加 _merge{N}.txt）",
        default=None,
    )
    parser.add_argument(
        "--n", type=int, default=10, help="每多少条合并为一行（默认 10）"
    )
    parser.add_argument(
        "--sep", default="；", help="合并时的分隔符（默认 '；'）"
    )
    parser.add_argument(
        "--no-ensure-period",
        action="store_true",
        help="不强制在合并后的行末追加句号",
    )

    args = parser.parse_args()
    input_path: str = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    n: int = max(1, int(args.n))
    sep: str = args.sep
    ensure_period: bool = not args.no_ensure_period

    default_out = f"{os.path.splitext(input_path)[0]}_merge{n}.txt"
    output_path: str = args.output or default_out

    texts = read_texts_from_file(input_path)
    if not texts:
        raise ValueError("输入文件没有可用文本")

    merged_lines = merge_every_n(texts, n=n, sep=sep, ensure_period=ensure_period)
    write_output(output_path, merged_lines)

    print(
        f"✅ 已生成 {output_path}（共 {len(merged_lines)} 行，每行 {n} 条；分隔符='{sep}'；"
        f"末尾{'已' if ensure_period else '未'}追加句号）"
    )


if __name__ == "__main__":
    main()
