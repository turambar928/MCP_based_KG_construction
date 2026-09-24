# Paper2：方法、数学、实现与证据对应审计

本轮保留题目与 RL 协同优化 / 双策略规则生成的主线。下表区分概念框架、
已执行代码和结果，避免正文把分开的证据链写成已验证的完整闭环。

| 位置 / 问题 | 本轮修订 | 可核查证据 | 仍有的边界 |
|---|---|---|---|
| 联合优化对象 | 保留图谱 G 与规则 R 的预算化序列决策 | 原环境 `Paper2CoOptimizationEnv` | 当前 R 来自固定 registry，未动态执行 LLM 候选 |
| MDP / 状态 | 区分完整环境状态与 14 维压缩观测 | `state()`、私有修复记录、mask | 14 维观测没有证明充分 Markov 性，不作该保证 |
| 图质量 | 四个结构缺陷率、固定 0.2/0.2/0.3/0.3 权重 | `q_graph()` | 结构质量不是事实正确率；删除可提高得分但损失事实 |
| 规则质量 | 固定 180-case 库上 precision/recall/family coverage | 原环境的校准模块 | 这些预测行为由环境预设，不是自然缺陷抽样估计 |
| 动作 | 四种图编辑、两种单族 acquisition、mixed acquisition、prune | `step()`、`available_action_mask()` | acquisition 是注册模块激活；call 为成本单位 |
| 原始关系恢复 | 检出 invalid 后使用环境私有 corruption record | `_repair_graph()` | 不把已知源记录恢复写成无监督语义推断 |
| 奖励 | 质量差分 − 调用成本 − 编辑成本 − 新违反惩罚 | `step()` | 算子固定返回新违反数 0；该奖励项并非编辑后独立检查，未验证安全性 |
| DDQN target | online 选动作、target 估值、terminal/empty mask 不 bootstrap | 原训练器与新训练器 | 功能特征消融后 mask 仍可传递间接信息 |
| 探索与 target sync | 250 episodes 训练，260 episodes 线性衰减；100 environment steps 同步 | `AgentConfig`、`epsilon_for_episode`、training histories | 最末 epsilon 约 0.0902，不是 0.05 |
| 消融 | 图特征、规则特征、action mask、训练调用惩罚各十个模型 | `training/`、`policy_results.json` | 同十个已用场景，非新 held-out evaluation |
| 策略优势 | 增加可行基线与 acquire-then-deficit | `policy_comparisons.csv` | 强启发式略优于 DDQN；不能再笼统声称 RL 优于简单策略 |
| Lookahead | 单步 transition-model reference | probes / transition logs | 单步 greedy 不构成长期性能上界 |
| AUC | 统一 18 步梯形积分、终止后补最终质量 | 每条 `curve18` 共 19 个点 | 旧的可变长度 AUC 留在历史目录，不能混用 |
| 删除算法 | 短字符跨度；original、masked、removed 全部入 prompt；一调用 | 当前 builder 导出的 `prompts/` | 原始文本可见，是对照式 elicitation，不是盲补全 |
| augmentation 算法 | 一响应内输出 ≤3 条补充条款与候选 | 当前 builder | 不是多个图谱 extractor 调用，也不是独立真实样本 |
| 规则聚合 | 分类 canonical 去重，声明与约束分列 | `budget_summary.csv` | 没有运行 DBSCAN / PMI / 0.95 precision floor |
| 同文档 vs 同成本 | 保留旧同文档 union；新增 450 个等调用样本 | `budget_per_sample.csv` | 双策略覆盖 B/2 文档，单策略覆盖 B；不把数量解释为质量 |
| 规则执行 | 仅 exact typed allowed/forbidden；冲突 abstain；不推断别名 | `rule_lineage.jsonl.gz`、case predictions | 18,143 个 pattern 仅两个命中，需独立验证 vocabulary mapping |
| RuleTest labels | 使用存储的 expected_detection，specialist_miss 为正类 | `family_label_check.csv`、`test_rules.py` | 设计标签非独立双人标注 |
| family union | 手工 detector 的覆盖与 generated execution 单列 | 两套 confusion matrices | 64/64 不等于实际候选能检出 64 个，直接执行为 10/64 |
| SHACL | 改为已选 shapes 的覆盖有限 | 原 SHACL baseline | 不能据此推断 SHACL 语言不支持范围、逻辑或更复杂检查 |
| 45-title API 结果 | 保留历史 no-op 与弱标签指标 | 原 API archived outputs | 本轮无 API，未增强其 gold semantic evidence |
| 模型元数据 | script defaults 与历史调用确认值分开 | prompt builder 与 archived fields | 旧日志缺 exact prompts / full decoding config，不补造 |
| 引用 | 修正 MINERVA/DeepPath 与 Lin 的已有准确元数据 | `paper2/references.bib`、既有 Paper1 条目（只读） | 未开展全库在线出版页核验；待核验条目单独留档 |

## 统计解释

十项 planned contrasts（heuristic + 四个消融，各 final quality/AUC）用同一 Holm family。
双侧符号随机化枚举 1,024 种翻转，bootstrap 10,000 次重采样整个场景对。
区间为 pointwise，不是 simultaneous intervals。图上的 95% CI 不跨零，与经过
多重比较校正的 p 值不显著可以同时成立。十个样本同时包含训练种子和场景变化，
不能用它分解二者各自方差。

无规则特征两项指标经校正显著；无 mask 的 final quality 显著，AUC 不显著。
图特征和调用惩罚的单独增益未被校正后的检验确证。强启发式优于完整模型，
意味着下一阶段应考察更复杂、未见的规则可用性与修复效果，而非忽略简单对照。

## 代码修正与核查

- 原环境、旧 checkpoints、旧实验输出保持不变；frozen manifest 做 SHA 核查。
- toy 全阳性样本触发 specificity 分母为零，改为 undefined 返回 null；原始
  RuleTest-94 分析文件 SHA 与修正前完全一致，见 correction manifest。
- 40 个新 checkpoint、10,000 episodes、110 次评估、1,974 transitions、450 个
  budget samples 均有完整性核查；7 个有意义的行为测试通过。
- 公开/匿名 artifact URL 尚待真正配置；本地路径不冒充已公开链接。

## 本轮不宣称完成的内容

实际 generated-rule → validation → RL action → repair 的动态闭环；自然错误独立标注；
未见领域泛化；外部 repair / rule-mining 方法的公平实验；真实 API latency/token 成本。
这些事项列在 `paper2/TODO.md`，不会因为离线消融完成而被自动勾选。
