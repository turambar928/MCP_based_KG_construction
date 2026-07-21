#!/usr/bin/env python3
"""
测试增强版与普通版服务器的对比脚本
使用 政务_test.jsonl 进行测试
"""

import asyncio
import json
import os
from typing import Dict, List, Set
from dotenv import load_dotenv
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession


def extract_text_from_json(data: Dict) -> str:
    """从政务 JSON 数据中提取文本"""
    parts = []
    if '服务事项' in data:
        parts.append(f"服务事项：{data['服务事项']}")
    if '权力类型' in data:
        parts.append(f"权力类型：{data['权力类型']}")
    if '行驶主体' in data:
        parts.append(f"行驶主体：{data['行驶主体']}")
    if '承办机构' in data:
        parts.append(f"承办机构：{data['承办机构']}")
    if '实施依据' in data and len(data['实施依据']) < 300:
        parts.append(f"实施依据：{data['实施依据'][:300]}")
    
    return "。".join(parts) if parts else ""


async def test_server(server_script: str, texts: List[str], output_prefix: str):
    """测试指定的服务器"""
    print(f"\n🔧 测试服务器: {server_script}")
    
    server_params = StdioServerParameters(
        command="python", 
        args=[server_script], 
        env=os.environ
    )
    
    all_results = []
    
    async with stdio_client(server_params) as (stdio, write):
        async with ClientSession(stdio, write) as session:
            print("📡 连接到服务器...")
            await session.initialize()
            
            # 选择合适的工具
            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            
            if "build_and_analyze_kg" in tool_names:
                tool_name = "build_and_analyze_kg"
                print("✅ 使用增强版工具: build_and_analyze_kg")
            elif "build_knowledge_graph" in tool_names:
                tool_name = "build_knowledge_graph"
                print("✅ 使用普通版工具: build_knowledge_graph")
            else:
                print(f"❌ 未找到合适的工具，可用工具: {tool_names}")
                return []
            
            print(f"⚙️ 开始处理 {len(texts)} 条文本...")
            
            for i, text in enumerate(texts, 1):
                print(f"  处理第 {i}/{len(texts)} 条...", end='\r')
                
                try:
                    if tool_name == "build_and_analyze_kg":
                        result = await session.call_tool(tool_name, {
                            "text": text,
                            "output_file": "off",
                            "enable_analysis": True,
                            "auto_enhance": True
                        })
                    else:
                        result = await session.call_tool(tool_name, {
                            "text": text,
                            "output_file": "off"
                        })
                    
                    if result.content and len(result.content) > 0:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            parsed_result = json.loads(content.text)
                            all_results.append(parsed_result)
                        
                except Exception as e:
                    print(f"\n处理第 {i} 条时出错: {e}")
                    all_results.append({"success": False, "error": str(e)})
    
    print(f"\n✅ {server_script} 处理完成")
    
    # 统计结果
    successful = sum(1 for r in all_results if r.get("success", False))
    print(f"📊 成功: {successful}/{len(texts)}")
    
    # 提取三元组统计
    total_triples = 0
    total_enhanced = 0
    
    for result in all_results:
        if result.get("success", False):
            # 尝试从不同位置提取三元组
            summary = result.get("summary", {})
            final_triples = summary.get("final_triples", [])
            
            if not final_triples:
                # 尝试从data字段获取
                data = result.get("data", {})
                final_triples = data.get("triples", [])
            
            total_triples += len(final_triples)
            
            # 检查是否有增强
            stages = result.get("stages", {})
            enhancement_res = stages.get("enhancement_results", {})
            if enhancement_res.get("enhancement_applied", False):
                total_enhanced += 1
    
    print(f"📈 统计:")
    print(f"  - 总三元组: {total_triples}")
    if server_script == "kg_server_enhanced.py":
        print(f"  - 增强条数: {total_enhanced}/{len(texts)}")
    
    return all_results


async def main():
    """主测试函数"""
    load_dotenv()
    
    # 读取测试数据
    jsonl_path = "data/政务_test.jsonl"
    
    if not os.path.exists(jsonl_path):
        print(f"❌ 测试文件不存在: {jsonl_path}")
        return
    
    texts = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    text = extract_text_from_json(data)
                    if text:
                        texts.append(text)
                except json.JSONDecodeError:
                    continue
    
    print(f"📖 从测试文件读取了 {len(texts)} 条文本")
    
    # 测试普通版服务器
    print("\n" + "="*60)
    print("🔍 测试普通版服务器 (kg_server.py)")
    print("="*60)
    normal_results = await test_server("kg_server.py", texts, "normal")
    
    # 测试增强版服务器
    print("\n" + "="*60)
    print("🔍 测试增强版服务器 (kg_server_enhanced.py)")
    print("="*60)
    enhanced_results = await test_server("kg_server_enhanced.py", texts, "enhanced")
    
    # 对比结果
    print("\n" + "="*60)
    print("📊 对比结果")
    print("="*60)
    
    normal_success = sum(1 for r in normal_results if r.get("success", False))
    enhanced_success = sum(1 for r in enhanced_results if r.get("success", False))
    


    print(f"成功率对比:")
    print(f"  普通版: {normal_success}/{len(texts)} ({normal_success/len(texts)*100:.1f}%)")
    print(f"  增强版: {enhanced_success}/{len(texts)} ({enhanced_success/len(texts)*100:.1f}%)")
    
    # 计算三元组数量对比
    normal_triples = 0
    enhanced_triples = 0
    
    for result in normal_results:
        if result.get("success", False):
            data = result.get("data", {})
            normal_triples += len(data.get("triples", []))
    
    for result in enhanced_results:
        if result.get("success", False):
            summary = result.get("summary", {})
            enhanced_triples += len(summary.get("final_triples", []))
    
    print(f"\n三元组数量对比:")
    print(f"  普通版: {normal_triples} 个三元组")
    print(f"  增强版: {enhanced_triples} 个三元组")
    print(f"  增强效果: {enhanced_triples - normal_triples:+d} 个三元组")
    
    # 统计增强应用情况
    enhanced_applied = 0
    for result in enhanced_results:
        if result.get("success", False):
            stages = result.get("stages", {})
            enhancement_res = stages.get("enhancement_results", {})
            if enhancement_res.get("enhancement_applied", False):
                enhanced_applied += 1
    
    print(f"\n质量增强统计:")
    print(f"  应用增强: {enhanced_applied}/{len(texts)} 条")
    print(f"  增强率: {enhanced_applied/len(texts)*100:.1f}%")
    
    print(f"\n🎯 测试结论:")
    if enhanced_triples > normal_triples:
        print(f"✅ 增强版成功提取了更多三元组 (+{enhanced_triples - normal_triples})")
    elif enhanced_triples == normal_triples:
        print(f"⚠️ 增强版与普通版提取的三元组数量相同")
    else:
        print(f"❌ 增强版提取的三元组反而更少 ({enhanced_triples - normal_triples})")
    
    if enhanced_applied > 0:
        print(f"✅ 质量增强功能正常工作，对 {enhanced_applied} 条文本应用了增强")
    else:
        print(f"❌ 质量增强功能未生效，没有应用任何增强")


if __name__ == "__main__":
    asyncio.run(main())
