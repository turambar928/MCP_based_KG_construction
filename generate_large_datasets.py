import os
import json
import random
import argparse
from typing import List, Dict, Any
from datetime import datetime, timedelta

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def save_jsonl(data: List[Dict], filepath: str):
    """保存数据为JSONL格式"""
    ensure_dir(os.path.dirname(filepath) if os.path.dirname(filepath) else ".")
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ 已保存 {len(data)} 条记录到 {filepath}")

def generate_dates(start_year=2020, end_year=2024, count=2000):
    """生成随机日期"""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    dates = []
    for _ in range(count):
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        random_date = start_date + timedelta(days=random_days)
        dates.append(random_date.strftime("%Y-%m-%d"))
    
    return dates

def generate_case_numbers(prefix_list, count=2000):
    """生成案件编号"""
    case_numbers = []
    for i in range(count):
        prefix = random.choice(prefix_list)
        year = random.choice([2020, 2021, 2022, 2023, 2024])
        number = str(i + 1).zfill(3)
        case_number = f"{prefix}[{year}]{number}号"
        case_numbers.append(case_number)
    return case_numbers

def generate_large_financial_dataset(target_count=2000):
    """生成大规模金融数据集"""
    print(f"🏦 开始生成 {target_count} 条金融领域数据...")
    
    # 金融机构类型
    institution_types = [
        "银行", "证券公司", "保险公司", "基金管理公司", "信托公司", 
        "期货公司", "小额贷款公司", "融资租赁公司", "财务公司", "消费金融公司",
        "村镇银行", "农村信用社", "城市商业银行", "股份制银行", "政策性银行"
    ]
    
    # 违法行为类型
    violation_types = [
        "未按规定履行客户身份识别义务", "内幕交易行为", "销售误导行为", 
        "未按规定进行信息披露", "高利放贷违规行为", "违规放贷", "挪用客户资金",
        "操纵市场价格", "虚假陈述", "欺诈发行", "违规担保", "资金池业务违规",
        "同业业务违规", "理财业务违规", "信贷资金违规流入股市", "违规收费",
        "风险管理缺失", "内控制度不健全", "数据治理不规范", "消费者权益保护不到位",
        "反洗钱工作不力", "征信业务违规", "支付业务违规", "外汇业务违规",
        "保险资金运用违规", "偿付能力不足", "准备金提取不足", "违规关联交易"
    ]
    
    # 处罚类型
    penalty_types = [
        "罚款", "警告", "责令改正", "没收违法所得", "责令停业整顿", 
        "取消任职资格", "禁止从业", "撤销许可证", "责令关闭", "限制业务范围"
    ]
    
    # 监管机构
    regulatory_bodies = [
        "中国人民银行", "银保监会", "证监会", "外汇管理局",
        "中国人民银行某分行", "银保监会某监管局", "证监会某监管局",
        "省地方金融监管局", "市地方金融监管局", "县金融办"
    ]
    
    # 法律依据
    legal_bases = [
        "《中华人民共和国银行业监督管理法》",
        "《中华人民共和国商业银行法》", 
        "《中华人民共和国保险法》",
        "《中华人民共和国证券法》",
        "《中华人民共和国反洗钱法》",
        "《证券投资基金法》",
        "《期货交易管理条例》",
        "《信托公司管理办法》",
        "《小额贷款公司监督管理条例》",
        "《融资租赁企业监督管理暂行办法》",
        "《关于规范民间借贷行为的通知》",
        "《银行业金融机构反洗钱和反恐怖主义融资管理办法》"
    ]
    
    # 生成数据
    financial_data = []
    dates = generate_dates(count=target_count)
    case_numbers = generate_case_numbers([
        "银罚字", "证监罚字", "银保监罚字", "保监罚字", "金监罚字", "央行罚字"
    ], count=target_count)
    
    for i in range(target_count):
        institution_type = random.choice(institution_types)
        institution_name = f"某{institution_type}"
        if random.random() < 0.3:  # 30%概率使用具体名称
            institution_name = f"{random.choice(['华夏', '招商', '中信', '光大', '平安', '兴业', '浦发', '民生', '交通', '建设', '工商', '农业', '中国', '邮储'])}{institution_type}"
        
        violation = random.choice(violation_types)
        penalty_type = random.choice(penalty_types)
        regulatory_body = random.choice(regulatory_bodies)
        legal_basis = random.choice(legal_bases)
        
        # 生成处罚金额
        penalty_amounts = ["5万元", "10万元", "20万元", "30万元", "50万元", "80万元", "100万元", "150万元", "200万元", "300万元", "500万元"]
        penalty_amount = random.choice(penalty_amounts)
        
        record = {
            "统一发布平台unid": f"fin_{i+1}_{case_numbers[i]}",
            "服务事项": f"金融监管处罚：{violation}",
            "权力类型": "行政处罚",
            "行驶主体": regulatory_body,
            "承办机构": regulatory_body,
            "实施依据": legal_basis,
            "责任事项": f"违法主体：{institution_name}\n违法行为：{violation}\n处罚类型：{penalty_type}\n处罚金额：{penalty_amount}\n处罚日期：{dates[i]}\n案件编号：{case_numbers[i]}",
            "监管电话": "12363"
        }
        financial_data.append(record)
        
        # 每生成100条打印进度
        if (i + 1) % 100 == 0:
            print(f"  已生成 {i+1}/{target_count} 条金融数据...")
    
    # 添加金融服务类数据
    service_types = [
        "银行开户服务", "信用卡申请服务", "贷款申请服务", "理财产品销售",
        "保险产品销售", "证券开户服务", "基金投资服务", "期货开户服务",
        "信托产品销售", "外汇兑换服务", "支付结算服务", "征信查询服务"
    ]
    
    # 添加500条服务类数据
    for i in range(500):
        service_type = random.choice(service_types)
        institution = random.choice(["中国工商银行", "招商银行", "平安银行", "中信证券", "华泰证券", "中国人寿", "平安保险"])
        
        record = {
            "统一发布平台unid": f"fin_service_{target_count + i + 1}",
            "服务事项": service_type,
            "权力类型": "公共服务",
            "行驶主体": institution,
            "承办机构": institution,
            "实施依据": random.choice(legal_bases),
            "责任事项": f"服务内容：{service_type}\n办理机构：{institution}\n业务流程：申请→审核→办理→完成\n办理时限：1-15个工作日\n收费标准：按相关规定执行",
            "监管电话": random.choice(["95588", "400-820-5555", "95511", "400-888-8888"])
        }
        financial_data.append(record)
    
    return financial_data

def generate_large_environmental_dataset(target_count=2000):
    """生成大规模环境数据集"""
    print(f"🌱 开始生成 {target_count} 条环境领域数据...")
    
    # 企业类型
    enterprise_types = [
        "化工厂", "钢铁公司", "造纸厂", "印刷企业", "养殖场", "电力公司",
        "水泥厂", "纺织厂", "制药厂", "食品厂", "石化企业", "有色金属公司",
        "建材厂", "玻璃厂", "陶瓷厂", "涂料厂", "橡胶厂", "塑料厂",
        "电镀厂", "皮革厂", "制浆厂", "焦化厂", "炼油厂", "煤矿",
        "采石场", "砂石厂", "垃圾处理厂", "污水处理厂", "危废处置中心"
    ]
    
    # 违法行为类型
    violation_types = [
        "超标排放废水", "超标排放废气", "危险废物未按规定贮存", 
        "未按规定安装污染物排放自动监测设备", "VOCs治理设施未正常运行",
        "畜禽粪污直排入河", "未取得排污许可证排污", "环评手续不全擅自开工",
        "未验先投违法生产", "污染防治设施未正常运行", "偷排偷放污染物",
        "篡改伪造监测数据", "拒绝环境执法检查", "土壤污染未修复",
        "噪声污染超标", "恶臭污染扰民", "固体废物乱堆乱放",
        "危险化学品泄漏", "辐射安全管理不规范", "生态破坏未恢复",
        "环境应急预案未备案", "环境信息未公开", "建设项目未批先建",
        "违法占用湿地", "破坏自然保护区", "非法采砂采石",
        "水土流失治理不力", "扬尘污染防治不到位"
    ]
    
    # 处罚类型
    penalty_types = [
        "罚款", "责令停产整治", "责令改正", "没收违法所得", "限制生产",
        "停业整顿", "责令关闭", "查封扣押", "移送司法机关", "行政拘留"
    ]
    
    # 监管机构
    regulatory_bodies = [
        "生态环境部", "省生态环境厅", "市生态环境局", "县生态环境局", 
        "区生态环境分局", "镇环保所", "环境监察支队", "环境应急中心",
        "环境监测站", "生态环境综合执法支队", "自然资源局", "水利局",
        "农业农村局", "林业局", "应急管理局"
    ]
    
    # 法律依据
    legal_bases = [
        "《中华人民共和国环境保护法》",
        "《中华人民共和国水污染防治法》",
        "《中华人民共和国大气污染防治法》",
        "《中华人民共和国固体废物污染环境防治法》",
        "《中华人民共和国土壤污染防治法》",
        "《中华人民共和国环境噪声污染防治法》",
        "《中华人民共和国环境影响评价法》",
        "《建设项目环境保护管理条例》",
        "《排污许可管理条例》",
        "《畜禽规模养殖污染防治条例》",
        "《危险废物经营许可证管理办法》",
        "《环境监测管理办法》"
    ]
    
    # 污染物类型
    pollutants = [
        "化学需氧量、氨氮", "二氧化硫、氮氧化物、颗粒物", "挥发性有机化合物",
        "重金属污染物", "含重金属污泥", "畜禽粪便、尿液", "有机溶剂",
        "酸性废水", "含油废水", "电镀废水", "印染废水", "制药废水",
        "苯系物、甲苯", "甲醛、苯酚", "氰化物", "铬、镉、铅、汞",
        "放射性物质", "医疗废物", "农药残留", "化工废料"
    ]
    
    # 生成数据
    environmental_data = []
    dates = generate_dates(count=target_count)
    case_numbers = generate_case_numbers([
        "环罚字", "环监罚字", "生态罚字", "环执罚字", "环保罚字"
    ], count=target_count)
    
    for i in range(target_count):
        enterprise_type = random.choice(enterprise_types)
        enterprise_name = f"某{enterprise_type}"
        if random.random() < 0.2:  # 20%概率使用具体名称
            enterprise_name = f"{random.choice(['华能', '中石化', '中石油', '宝钢', '首钢', '华润', '中铝', '紫金', '五粮液', '茅台'])}{enterprise_type}"
        
        violation = random.choice(violation_types)
        penalty_type = random.choice(penalty_types)
        regulatory_body = random.choice(regulatory_bodies)
        legal_basis = random.choice(legal_bases)
        pollutant = random.choice(pollutants)
        
        # 生成处罚金额
        penalty_amounts = ["3万元", "5万元", "10万元", "15万元", "20万元", "30万元", "50万元", "80万元", "100万元", "150万元", "200万元", "300万元"]
        penalty_amount = random.choice(penalty_amounts)
        
        record = {
            "统一发布平台unid": f"env_{i+1}_{case_numbers[i]}",
            "服务事项": f"环境执法处罚：{violation}",
            "权力类型": "行政处罚",
            "行驶主体": regulatory_body,
            "承办机构": regulatory_body,
            "实施依据": legal_basis,
            "责任事项": f"违法主体：{enterprise_name}\n违法行为：{violation}\n处罚类型：{penalty_type}\n处罚金额：{penalty_amount}\n污染物：{pollutant}\n处罚日期：{dates[i]}\n案件编号：{case_numbers[i]}",
            "监管电话": "12369"
        }
        environmental_data.append(record)
        
        # 每生成100条打印进度
        if (i + 1) % 100 == 0:
            print(f"  已生成 {i+1}/{target_count} 条环境数据...")
    
    # 添加环境许可服务类数据
    permit_types = [
        "排污许可证申请", "环境影响评价审批", "危险废物经营许可", 
        "辐射安全许可证申请", "建设项目环保审批", "环境监测资质认定",
        "清洁生产审核", "环境应急预案备案", "固体废物跨省转移审批",
        "夜间施工许可", "河道采砂许可", "林地使用许可"
    ]
    
    # 添加500条许可服务类数据
    for i in range(500):
        permit_type = random.choice(permit_types)
        
        record = {
            "统一发布平台unid": f"env_permit_{target_count + i + 1}",
            "服务事项": permit_type,
            "权力类型": "行政许可",
            "行驶主体": random.choice(regulatory_bodies),
            "承办机构": random.choice(regulatory_bodies),
            "实施依据": random.choice(legal_bases),
            "责任事项": f"许可事项：{permit_type}\n适用对象：相关企业和个人\n办理流程：申请→受理→审查→决定→发证\n办理时限：20-60个工作日\n收费标准：按国家规定执行\n有效期：3-5年",
            "监管电话": "12369"
        }
        environmental_data.append(record)
    
    return environmental_data

def main():
    parser = argparse.ArgumentParser(description="生成大规模金融和环境数据集")
    parser.add_argument("--finance-count", type=int, default=2000, help="金融数据集大小")
    parser.add_argument("--env-count", type=int, default=2000, help="环境数据集大小")
    parser.add_argument("--output-dir", default="data", help="输出目录")
    
    args = parser.parse_args()
    
    ensure_dir(args.output_dir)
    
    print(f"🚀 开始生成大规模数据集...")
    print(f"🏦 金融数据目标：{args.finance_count} 条")
    print(f"🌱 环境数据目标：{args.env_count} 条")
    print("-" * 50)
    
    # 生成金融数据集
    financial_data = generate_large_financial_dataset(args.finance_count)
    save_jsonl(financial_data, os.path.join(args.output_dir, "金融_大规模.jsonl"))
    save_jsonl(financial_data[:20], os.path.join(args.output_dir, "金融_大规模_test.jsonl"))
    
    print("-" * 50)
    
    # 生成环境数据集
    environmental_data = generate_large_environmental_dataset(args.env_count)
    save_jsonl(environmental_data, os.path.join(args.output_dir, "环境_大规模.jsonl"))
    save_jsonl(environmental_data[:20], os.path.join(args.output_dir, "环境_大规模_test.jsonl"))
    
    print("-" * 50)
    
    # 生成混合数据集
    mixed_data = financial_data + environmental_data
    save_jsonl(mixed_data, os.path.join(args.output_dir, "混合_大规模.jsonl"))
    save_jsonl(mixed_data[:40], os.path.join(args.output_dir, "混合_大规模_test.jsonl"))
    
    print("\n📊 大规模数据集生成完成！")
    print(f"🏦 金融数据：{len(financial_data)} 条")
    print(f"🌱 环境数据：{len(environmental_data)} 条") 
    print(f"🔄 混合数据：{len(mixed_data)} 条")
    print("\n🎯 现在你可以进行大规模实验了！")
    print("💡 建议先用test文件验证，再用完整数据集进行实验")

if __name__ == "__main__":
    main()
