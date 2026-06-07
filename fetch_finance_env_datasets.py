import os
import json
import argparse
from typing import List, Dict, Any

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def save_jsonl(data: List[Dict], filepath: str):
    """保存数据为JSONL格式"""
    ensure_dir(os.path.dirname(filepath) if os.path.dirname(filepath) else ".")
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ 已保存 {len(data)} 条记录到 {filepath}")

def fetch_financial_data():
    """获取金融领域数据并转换为政务.jsonl格式"""
    print("🏦 开始获取金融领域数据...")
    
    financial_data = []
    
    # 模拟金融监管处罚数据
    sample_financial_cases = [
        {
            "机构名称": "某银行股份有限公司",
            "违法行为": "未按规定履行客户身份识别义务",
            "处罚类型": "罚款",
            "处罚金额": "50万元",
            "处罚依据": "《中华人民共和国反洗钱法》第三十二条",
            "处罚机关": "中国人民银行某分行",
            "处罚日期": "2024-01-15",
            "案件编号": "银罚字[2024]001号"
        },
        {
            "机构名称": "某证券公司",
            "违法行为": "内幕交易行为",
            "处罚类型": "罚款并没收违法所得",
            "处罚金额": "100万元",
            "处罚依据": "《证券法》第一百九十一条",
            "处罚机关": "中国证监会",
            "处罚日期": "2024-02-10",
            "案件编号": "证监罚字[2024]002号"
        },
        {
            "机构名称": "某保险公司",
            "违法行为": "销售误导行为",
            "处罚类型": "责令改正并罚款",
            "处罚金额": "30万元",
            "处罚依据": "《保险法》第一百六十一条",
            "处罚机关": "银保监会某监管局",
            "处罚日期": "2024-03-05",
            "案件编号": "银保监罚字[2024]003号"
        },
        {
            "机构名称": "某基金管理公司",
            "违法行为": "未按规定进行信息披露",
            "处罚类型": "警告并罚款",
            "处罚金额": "20万元",
            "处罚依据": "《证券投资基金法》第一百二十八条",
            "处罚机关": "中国证监会",
            "处罚日期": "2024-04-12",
            "案件编号": "证监罚字[2024]004号"
        },
        {
            "机构名称": "某小额贷款公司",
            "违法行为": "高利放贷违规行为",
            "处罚类型": "停业整顿并罚款",
            "处罚金额": "80万元",
            "处罚依据": "《关于规范民间借贷行为的通知》",
            "处罚机关": "地方金融监管局",
            "处罚日期": "2024-05-20",
            "案件编号": "金监罚字[2024]005号"
        }
    ]
    
    # 转换为政务.jsonl格式
    for i, case in enumerate(sample_financial_cases, 1):
        record = {
            "统一发布平台unid": f"fin_{i}_{case['案件编号']}",
            "服务事项": f"金融监管处罚：{case['违法行为']}",
            "权力类型": "行政处罚",
            "行驶主体": case["处罚机关"],
            "承办机构": case["处罚机关"],
            "实施依据": case["处罚依据"],
            "责任事项": f"违法主体：{case['机构名称']}\n违法行为：{case['违法行为']}\n处罚类型：{case['处罚类型']}\n处罚金额：{case['处罚金额']}\n处罚日期：{case['处罚日期']}\n案件编号：{case['案件编号']}",
            "监管电话": "12363"  # 银保监会投诉电话
        }
        financial_data.append(record)
    
    # 添加更多金融业务场景
    financial_business_cases = [
        {
            "业务类型": "银行开户服务",
            "服务内容": "个人银行账户开立业务",
            "办理机构": "中国工商银行",
            "业务流程": "身份验证→填写申请表→提交材料→审核→开户成功",
            "所需材料": "身份证、手机号、初始存款",
            "办理时限": "当日办结",
            "收费标准": "免费",
            "咨询电话": "95588"
        },
        {
            "业务类型": "信用卡申请服务",
            "服务内容": "个人信用卡申请办理",
            "办理机构": "招商银行",
            "业务流程": "在线申请→资料审核→征信查询→审批决策→制卡邮寄",
            "所需材料": "身份证、收入证明、工作证明",
            "办理时限": "7-15个工作日",
            "收费标准": "年费根据卡种而定",
            "咨询电话": "400-820-5555"
        }
    ]
    
    for i, case in enumerate(financial_business_cases, len(sample_financial_cases)+1):
        record = {
            "统一发布平台unid": f"fin_service_{i}",
            "服务事项": case["服务内容"],
            "权力类型": "公共服务",
            "行驶主体": case["办理机构"],
            "承办机构": case["办理机构"],
            "实施依据": "《中华人民共和国银行业监督管理法》、《个人银行账户管理办法》",
            "责任事项": f"业务流程：{case['业务流程']}\n所需材料：{case['所需材料']}\n办理时限：{case['办理时限']}\n收费标准：{case['收费标准']}",
            "监管电话": case["咨询电话"]
        }
        financial_data.append(record)
    
    return financial_data

def fetch_environmental_data():
    """获取环境领域数据并转换为政务.jsonl格式"""
    print("🌱 开始获取环境领域数据...")
    
    environmental_data = []
    
    # 模拟环境执法处罚数据
    sample_env_cases = [
        {
            "企业名称": "某化工厂",
            "违法行为": "超标排放废水",
            "处罚类型": "罚款并责令停产整治",
            "处罚金额": "200万元",
            "处罚依据": "《中华人民共和国水污染防治法》第八十三条",
            "处罚机关": "市生态环境局",
            "处罚日期": "2024-01-20",
            "案件编号": "环罚字[2024]001号",
            "污染物": "化学需氧量、氨氮"
        },
        {
            "企业名称": "某钢铁公司",
            "违法行为": "未按规定安装大气污染物排放自动监测设备",
            "处罚类型": "罚款并责令改正",
            "处罚金额": "50万元",
            "处罚依据": "《中华人民共和国大气污染防治法》第一百条",
            "处罚机关": "省生态环境厅",
            "处罚日期": "2024-02-15",
            "案件编号": "环罚字[2024]002号",
            "污染物": "二氧化硫、氮氧化物、颗粒物"
        },
        {
            "企业名称": "某造纸厂",
            "违法行为": "危险废物未按规定贮存",
            "处罚类型": "罚款并没收违法所得",
            "处罚金额": "120万元",
            "处罚依据": "《中华人民共和国固体废物污染环境防治法》第一百一十二条",
            "处罚机关": "县生态环境局",
            "处罚日期": "2024-03-10",
            "案件编号": "环罚字[2024]003号",
            "污染物": "含重金属污泥"
        },
        {
            "企业名称": "某印刷企业",
            "违法行为": "VOCs治理设施未正常运行",
            "处罚类型": "责令停止违法行为并罚款",
            "处罚金额": "15万元",
            "处罚依据": "《中华人民共和国大气污染防治法》第九十九条",
            "处罚机关": "区生态环境分局",
            "处罚日期": "2024-04-05",
            "案件编号": "环罚字[2024]004号",
            "污染物": "挥发性有机化合物"
        },
        {
            "企业名称": "某养殖场",
            "违法行为": "畜禽粪污直排入河",
            "处罚类型": "罚款并责令治理",
            "处罚金额": "30万元",
            "处罚依据": "《畜禽规模养殖污染防治条例》第三十九条",
            "处罚机关": "镇环保所",
            "处罚日期": "2024-05-12",
            "案件编号": "环罚字[2024]005号",
            "污染物": "畜禽粪便、尿液"
        }
    ]
    
    # 转换为政务.jsonl格式
    for i, case in enumerate(sample_env_cases, 1):
        record = {
            "统一发布平台unid": f"env_{i}_{case['案件编号']}",
            "服务事项": f"环境执法处罚：{case['违法行为']}",
            "权力类型": "行政处罚",
            "行驶主体": case["处罚机关"],
            "承办机构": case["处罚机关"],
            "实施依据": case["处罚依据"],
            "责任事项": f"违法主体：{case['企业名称']}\n违法行为：{case['违法行为']}\n处罚类型：{case['处罚类型']}\n处罚金额：{case['处罚金额']}\n污染物：{case['污染物']}\n处罚日期：{case['处罚日期']}\n案件编号：{case['案件编号']}",
            "监管电话": "12369"  # 环保举报热线
        }
        environmental_data.append(record)
    
    # 添加环境许可业务
    env_permit_cases = [
        {
            "许可类型": "排污许可证申请",
            "适用对象": "工业企业排污许可",
            "办理机构": "生态环境局",
            "办理流程": "网上申报→材料审核→现场核查→技术评估→许可决定",
            "所需材料": "申请表、环评文件、监测报告、企业基本信息",
            "办理时限": "30个工作日",
            "收费标准": "不收费",
            "有效期": "5年"
        },
        {
            "许可类型": "环境影响评价审批",
            "适用对象": "建设项目环评审批",
            "办理机构": "生态环境局",
            "办理流程": "提交环评文件→技术审查→公众参与→审批决定→批复下达",
            "所需材料": "环评报告书/表、公众参与说明、专家评审意见",
            "办理时限": "60个工作日",
            "收费标准": "不收费",
            "有效期": "5年"
        }
    ]
    
    for i, case in enumerate(env_permit_cases, len(sample_env_cases)+1):
        record = {
            "统一发布平台unid": f"env_permit_{i}",
            "服务事项": case["许可类型"],
            "权力类型": "行政许可",
            "行驶主体": case["办理机构"],
            "承办机构": case["办理机构"],
            "实施依据": "《中华人民共和国环境保护法》、《环境影响评价法》、《排污许可管理条例》",
            "责任事项": f"适用对象：{case['适用对象']}\n办理流程：{case['办理流程']}\n所需材料：{case['所需材料']}\n办理时限：{case['办理时限']}\n收费标准：{case['收费标准']}\n有效期：{case['有效期']}",
            "监管电话": "12369"
        }
        environmental_data.append(record)
    
    return environmental_data

def create_mixed_dataset():
    """创建混合领域数据集用于对比实验"""
    print("🔄 创建混合领域数据集...")
    
    # 获取各领域数据
    financial_data = fetch_financial_data()
    environmental_data = fetch_environmental_data()
    
    # 保存各领域单独数据集
    save_jsonl(financial_data, "data/金融.jsonl")
    save_jsonl(environmental_data, "data/环境.jsonl")
    
    # 创建混合数据集
    mixed_data = financial_data + environmental_data
    save_jsonl(mixed_data, "data/混合_金融_环境.jsonl")
    
    # 创建小规模测试集
    financial_test = financial_data[:3]
    environmental_test = environmental_data[:3]
    mixed_test = financial_test + environmental_test
    
    save_jsonl(financial_test, "data/金融_test.jsonl")
    save_jsonl(environmental_test, "data/环境_test.jsonl")
    save_jsonl(mixed_test, "data/混合_test.jsonl")
    
    return {
        "financial": financial_data,
        "environmental": environmental_data,
        "mixed": mixed_data
    }

def main():
    parser = argparse.ArgumentParser(description="获取金融和环境领域数据集，转换为政务.jsonl格式")
    parser.add_argument("--domain", choices=["financial", "environmental", "both"], 
                       default="both", help="选择获取的领域数据")
    parser.add_argument("--output-dir", default="data", help="输出目录")
    
    args = parser.parse_args()
    
    ensure_dir(args.output_dir)
    
    if args.domain in ["financial", "both"]:
        financial_data = fetch_financial_data()
        save_jsonl(financial_data, os.path.join(args.output_dir, "金融.jsonl"))
        save_jsonl(financial_data[:5], os.path.join(args.output_dir, "金融_test.jsonl"))
    
    if args.domain in ["environmental", "both"]:
        environmental_data = fetch_environmental_data()
        save_jsonl(environmental_data, os.path.join(args.output_dir, "环境.jsonl"))
        save_jsonl(environmental_data[:5], os.path.join(args.output_dir, "环境_test.jsonl"))
    
    if args.domain == "both":
        # 创建混合数据集
        financial_data = fetch_financial_data()
        environmental_data = fetch_environmental_data()
        mixed_data = financial_data + environmental_data
        save_jsonl(mixed_data, os.path.join(args.output_dir, "混合_金融_环境.jsonl"))
        save_jsonl(mixed_data[:8], os.path.join(args.output_dir, "混合_test.jsonl"))
    
    print("\n📊 数据集生成完成！")
    print("🔥 现在你可以用这些数据集测试你的规则生成方法:")
    print("   python generate_rules_from_gov_texts.py --input data/金融_test.jsonl")
    print("   python generate_rules_from_gov_texts.py --input data/环境_test.jsonl")
    print("   python generate_rules_from_gov_texts.py --input data/混合_test.jsonl")

if __name__ == "__main__":
    main()
