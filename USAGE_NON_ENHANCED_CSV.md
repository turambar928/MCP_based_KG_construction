# 非增强模式批量处理使用说明

本文档说明如何使用非增强模式（`kg_server.py`）批量处理 JSONL 文件，并输出符合 `evaluate_kg` 文件夹格式要求的分离 CSV 文件。

## 输出格式

处理后会生成两个 CSV 文件：

1. **nodes.csv** - 节点信息
   - `id`: 节点唯一标识（数字）
   - `name`: 节点名称
   - `node_type`: 节点类型（从实体类型中获取，默认为 "Unknown"）

2. **relationships.csv** - 关系信息
   - `start_id`: 起始节点 ID
   - `end_id`: 终止节点 ID
   - `relation_type`: 关系类型
   - `source`: 数据来源（默认为 "extraction"）

## 使用方法

### 1. 基本用法

对于政务数据（使用修改后的脚本）：
```bash
python bulk_jsonl_to_csv_nodes_rels.py data/政务.jsonl
```

或使用灵活版本（推荐）：
```bash
python bulk_jsonl_to_csv_flexible.py data/政务.jsonl \
    --fields "服务事项:服务事项" "权力类型:权力类型" "行驶主体:行驶主体" "承办机构:承办机构"
```

这将生成：
- `data/政务_nodes.csv`
- `data/政务_relationships.csv`

### 2. 指定输出文件名

```bash
python bulk_jsonl_to_csv_nodes_rels.py data/政务.jsonl -o output/政务_知识图谱
```

这将生成：
- `output/政务_知识图谱_nodes.csv`
- `output/政务_知识图谱_relationships.csv`

### 3. 处理流程

1. 脚本会自动启动 `kg_server.py`（非增强模式）
2. 逐行读取 JSONL 文件，提取文本内容
3. **实时增量处理**：
   - 每批处理 10 条数据
   - 处理完一批立即写入 CSV 文件
   - 你可以实时查看文件增长
   - 即使中途中断也不会丢失已处理的数据
4. 自动去重节点，分配唯一 ID
5. 输出分离的 CSV 文件

### 4. JSONL 文件格式支持

#### 标准格式
脚本支持标准文本字段：
- `text`
- `sentence` 
- `content`

例如：
```json
{"text": "张三是阿里巴巴的CEO"}
{"sentence": "李四在北京大学学习计算机科学"}
{"content": "王五创立了创新科技公司"}
```

#### 政务数据格式
修改后的脚本也支持政务数据格式：
```json
{
  "服务事项": "对擅自停用、拆除消防设施、器材的处罚",
  "权力类型": "行政处罚",
  "行驶主体": "市公安局",
  "承办机构": "消防支队、大队",
  "实施依据": "《中华人民共和国消防法》..."
}
```

#### 使用灵活版本处理自定义格式
```bash
# 处理包含 title 和 content 的新闻数据
python bulk_jsonl_to_csv_flexible.py news.jsonl \
    --fields "title:标题" "content:内容" "author:作者"

# 只提取字段值，不带标签，用空格分隔
python bulk_jsonl_to_csv_flexible.py data.jsonl \
    --fields title content --sep " "
```

### 5. 实时监控功能

#### 方法1：查看处理进度输出
脚本运行时会显示实时进度：
```
📦 处理批次 1 (第 1-10 条)...
  ✅ 本批次: +15 节点, +12 关系
  📊 累计: 15 节点, 12 关系

📦 处理批次 2 (第 11-20 条)...
  ✅ 本批次: +8 节点, +6 关系
  📊 累计: 23 节点, 18 关系
```

#### 方法2：实时监控文件增长
在另一个终端窗口运行监控脚本：
```bash
python monitor_progress.py data/政务
```

这将实时显示文件增长情况：
```
[14:30:15] 📈 更新: +15 节点, +12 关系 (总计: 15 节点, 12 关系)
[14:30:17] 📈 更新: +8 节点, +6 关系 (总计: 23 节点, 18 关系)
```

#### 方法3：直接查看文件
你可以随时用 `wc -l` 或 `tail` 命令查看文件：
```bash
# 查看文件行数（减1得到实际数据行数）
wc -l data/政务_nodes.csv data/政务_relationships.csv

# 查看最新添加的数据
tail -n 5 data/政务_nodes.csv
tail -n 5 data/政务_relationships.csv
```

### 6. 注意事项

- 服务器使用的是 `kg_server.py`（非增强模式），处理速度较快
- CSV 文件中包含逗号的字段会自动用引号包裹
- **实时增量写入**：每批处理完立即写入，不会丢失数据
- 重复运行会覆盖已有的输出文件
- 节点自动去重，每个节点只会有一个唯一ID

### 7. 与质量评估集成

生成的 CSV 文件可以直接用于质量评估：

```bash
# 1. 先生成 CSV 文件
python bulk_jsonl_to_csv_nodes_rels.py data/政务.jsonl

# 2. 运行质量评估
cd evaluate_kg
python evaluate.py --node-files ../data/政务_nodes.csv --rel-files ../data/政务_relationships.csv
```

### 8. 调试选项

如果需要自定义服务器启动参数：

```bash
python bulk_jsonl_to_csv_nodes_rels.py data/政务.jsonl \
    --server-cmd python \
    --server-args kg_server.py --debug
```
