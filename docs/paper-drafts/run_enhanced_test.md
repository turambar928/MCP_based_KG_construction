# 增强版服务器测试指南

## 🎯 测试目标

使用 `data/政务_test.jsonl` 中的10条测试数据，对比普通版和增强版服务器的处理效果，验证质量增强逻辑是否正常工作。

## 🚀 测试步骤

### 1. 运行对比测试脚本

```bash
# 确保在项目根目录且虚拟环境已激活
source .venv/bin/activate

# 运行对比测试
python test_enhanced_vs_normal.py
```

这个脚本会：
- 自动启动普通版服务器 (`kg_server.py`) 处理测试数据
- 自动启动增强版服务器 (`kg_server_enhanced.py`) 处理相同数据
- 对比两者的处理结果
- 显示增强效果统计

### 2. 如果需要生成CSV文件进行详细分析

```bash
# 使用增强版服务器生成CSV文件
python bulk_jsonl_to_csv_enhanced.py data/政务_test.jsonl -o data/政务_test_enhanced

# 使用普通版服务器生成CSV文件（对照组）
python bulk_jsonl_to_csv_nodes_rels.py data/政务_test.jsonl -o data/政务_test_normal
```

### 3. 质量评估对比

```bash
cd data

# 评估普通版结果
python evaluate.py \
    --node-files 政务_test_normal_nodes.csv \
    --rel-files 政务_test_normal_relationships.csv \
    --output-dir 普通版_评估报告 \
    --no-semantic

# 评估增强版结果
python evaluate.py \
    --node-files 政务_test_enhanced_nodes.csv \
    --rel-files 政务_test_enhanced_relationships.csv \
    --output-dir 增强版_评估报告 \
    --no-semantic
```

## 📊 预期测试结果

### 成功指标
- ✅ **三元组数量增加**：增强版应该提取到更多或质量更高的三元组
- ✅ **增强应用率**：至少有部分文本应用了质量增强逻辑
- ✅ **质量评分提升**：增强版的质量评估分数应该更高

### 关键观察点
1. **增强应用情况**：多少条文本被判定为需要增强并成功应用了增强
2. **三元组质量**：增强后的三元组是否更准确、更完整
3. **逻辑一致性**：增强版是否修正了逻辑错误（如地理关系、层级关系等）
4. **处理时间**：增强版的处理时间（应该比普通版长，但要在合理范围内）

## 🔧 故障排除

### 如果增强功能未生效
1. 检查 `.env` 文件中的 API 配置是否正确
2. 查看服务器启动日志，确认"高级分析功能: ✅ 可用"
3. 检查测试文本是否被判定为"低质量"需要增强

### 如果处理速度太慢
1. 减少测试数据量（使用前5条数据）
2. 检查网络连接和 API 响应时间
3. 考虑调整并发参数

### 如果出现错误
1. 确保所有依赖包已安装
2. 检查服务器是否正常启动
3. 查看详细错误信息进行调试

## 📝 测试记录模板

```
测试时间: ____
测试数据: data/政务_test.jsonl (10条)

普通版结果:
- 成功率: __/__
- 三元组数: __
- 处理时间: __ 秒

增强版结果:
- 成功率: __/__
- 三元组数: __
- 增强应用: __/__
- 处理时间: __ 秒

结论:
- 增强效果: ____
- 质量提升: ____
- 建议: ____
```

开始测试吧！🎉
