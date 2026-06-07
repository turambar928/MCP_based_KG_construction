# 人工标注操作手册（paper1 §4.3 语义可靠性 · tab:sem_reliability 第二行）

## 0. 这件事是干什么的
论文 §4.3 要证明"自动语义评分 S_sem(Qwen 打的分)是可靠的、不是自我偏袒"。
第一行已用独立模型 Gemma 做了交叉验证(r=0.62)。**这一步是补"人工 vs 机器"的一致性**:
让真人对同一批三元组独立打分,再算 人工分 与 Qwen 分 的相关性,以及 标注者之间的一致性。

全程约 1.5–2.5 小时/人(180 条),纯人工 + 一条命令。

---

## 1. 需要的文件(都在 `exps/semantic_reliability/`)
| 文件 | 作用 |
|---|---|
| `human_annotation_sheet.csv` | **要填的表**:180 行三元组 + 3 个空打分列 |
| `human_annotation_README.md` | 本说明 |
| `answer_key.csv` | 隐藏的机器分(**别给标注者看**,算分时脚本自动用) |
| `score_human.py` | 填完后跑它自动算 r 和 κ |

表格列:`id, domain(政务/金融/环境), triple, annotator1_score, annotator2_score, annotator3_score`
（表里**故意不显示机器分**,保证盲评。）

---

## 2. 找标注者
- **2–3 人**,各自**独立**打分,**不要互相商量**(独立性是这步的关键)。
- 最好是懂一点政务/金融/环境业务常识的人;不需要是 NLP 专家。
- 用 2 人也行(填 annotator1、annotator2,annotator3 留空即可;脚本自动跳过空列)。

## 3. 怎么打分(0–1,步长 0.2,六档)
| 分 | 含义 |
|---|---|
| 1.0 | 完全符合该领域常识与逻辑,关系表述准确 |
| 0.8 | 基本合理,仅轻微表述不准 |
| 0.6 | 部分合理但有歧义或不够准确 |
| 0.4 | 存在明显逻辑问题或术语错误 |
| 0.2 | 严重违背常识/逻辑 |
| 0.0 | 完全不合理、荒谬 |

**重点看**:主谓宾有没有颠倒/错位;层级对不对(下级不能管理上级);术语准不准;信息自不自洽。
**只看三元组本身**,不参考任何模型输出。

**示例**(三元组 → 合理打分):
- `养老保险处 --[隶属于]-> 西安市人力资源和社会保障局` → **1.0**(层级、关系都对)
- `销售...电子产品 --[违法行为]-> 市场监督管理部门` → **0.2**(主客体颠倒,监管部门成了违法对象)
- `服务事项 --[涉及]-> 传染病疫情` → **0.6**(关系笼统,但不算错)

## 4. 具体操作步骤
1. 用 Excel / WPS / 任意表格软件打开 `human_annotation_sheet.csv`(注意 UTF-8 编码,避免中文乱码;WPS/Excel 一般自动识别)。
2. 每位标注者在**自己那一列**(annotator1_score 等)逐行填 0/0.2/0.4/0.6/0.8/1.0 之一。
   - 多人可各存一份再合并,或同一文件不同列分别填。
3. 全部填完后**保存为 CSV**(保持原文件名 `human_annotation_sheet.csv`,仍是 UTF-8)。
4. 跑算分脚本:
   ```bash
   cd /home/taozifu2025/MCP_based_KG_construction && source .venv/bin/activate
   python3 exps/semantic_reliability/score_human.py
   ```
5. 结果打印在屏幕并写入 `exps/semantic_reliability/human_agreement.txt`,形如:
   ```
   Human vs Qwen S_sem : Pearson r=0.71 (p=...)
   Human vs Gemma judge: Pearson r=0.69 (p=...)
   Inter-annotator Cohen's kappa (pairwise mean): 0.58
   ```

## 5. 把结果填进论文
打开 `paper1/sections/experiments.tex`,找到 `tab:sem_reliability` 的这一行:
```latex
Human annotators & TBD (Pearson $r$) & TBD (Cohen's $\kappa$) \\
```
把两个 TBD 换成脚本算出的数,例如:
```latex
Human annotators & $r=0.71$ (Pearson) & $\kappa=0.58$ \\
```
然后在 §4.3 结尾那句 `% TODO(human)` 注释处,补一句解读(例:
"人工评分与 $S_{sem}$ 强相关、标注者间一致性中等偏上,进一步佐证自动评分反映真实质量")。

---

## 6. 注意事项 / 排错
- 脚本依赖 `scipy` 和 `scikit-learn`(本仓库 .venv 已装好)。
- 每列至少要填 **≥3 个**有效分脚本才会采用该标注者(否则视为未填)。
- 分数只填 0/0.2/0.4/0.6/0.8/1.0;填了别的数值脚本会按数值处理但建议守这六档。
- 不要改 `id`、`triple`、`domain` 列,也不要打乱行序(脚本靠 id 对齐机器分)。
- 预期:r 大概率 0.6–0.8,κ 0.5 左右 → 足以支撑"S_sem 可靠"的结论。
