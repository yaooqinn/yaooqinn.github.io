---
title: "LLM 不该替代查询优化器,该接在它后面做 plan-tuner"
date: 2026-05-27
tags: ["llm", "query-optimization", "spark", "datafusion", "physical-plan"]
categories: ["query-engines"]
summary: "把 LLM 放在 optimizer 之后,以 JSON Patch 方式做局部计划微调,这条路比让 LLM 替代优化器更经得起工程治理的考验。"
cover:
  image: "/images/posts/llm-as-plan-tuner-cover.png"
  alt: "LLM 接在 optimizer 之后做 plan-tuner"
  relative: false
showToc: true
---

![LLM 不该替代优化器,该接在它后面做 plan-tuner](/images/posts/llm-as-plan-tuner-cover.png)

我前三篇博客 ([LLM × join order](/zh/posts/query-engines/llm-only-rewrite-doesnt-work/) · [rule-rewrite 的盲区](/zh/posts/query-engines/rule-rewrite-blindspot-dsb/) · [120 行 prompt 的解剖](/zh/posts/query-engines/prompt-anatomy-for-plan-generation/)) 都在回答一个问题:**LLM 该怎么参与查询优化**。前三篇拆的是"怎么改"——改 SQL 文本、改 plan、写 prompt 让它改。这一篇换个问题:**LLM 在 optimizer 流水线里该站哪一层**。

我的判断是:**把它放在 optimizer 之后**,以局部 patch 的方式微调,而不是替代 cost-based optimizer。这不是技术新颖度的问题,是工程治理的问题。

## 三条路线,先把分类摆出来

近半年我读到的 LLM × QO 工作,落地路径大致是三条:

| 路线 | 代表工作 | LLM 输出什么 | 输出粒度 |
|---|---|---|---|
| **A. 改 SQL 文本** | (SQL → SQL 改写,前几篇已展开) | 重写后的 SQL 字符串 | 整段 |
| **B. LLM 直接做 plan 决策** | Databricks 2026-04 blog: LLM agent 选 join order[^1] | 一个具体决策(如 join 顺序) | 整张 plan 维度 |
| **C. LLM 输出 patch,改 optimizer 给的 plan** | DBPlanBench (arXiv 2602.10387)[^2] | RFC 6902 风格 JSON Patch | 局部小改 |

A 已经讨论过,它的麻烦是 SQL 文本层信息量不够,改不动只有看物理计划才能发现的问题(join 顺序、projection 列序、算子选择)。B 和 C 的差别更细,也是这一篇的主角。

## 为什么 patch 路线值得讨论

DBPlanBench 是路线 C 最完整的开源实现。它的做法是:让 DataFusion 先按自己的 optimizer 把 SQL 编译成 physical plan,再把这份 plan 扁平化成 JSON 喂给 GPT-5,**让 LLM 输出 RFC 6902[^3] 风格的 JSON Patch**(比如把某个 hash join 的 build/probe 边互换),最后把 patch 应用回 DataFusion 真跑。

在 TPC-H 和 TPC-DS(SF=3/10)上,论文报告**单 query 最高 4.78× speedup**[^2]——这个数字本身不是这篇博客的重点,我反而想先说它的 caveat:

- baseline 是 DataFusion 自家 optimizer,没有跟 Bao/Balsa 这类 learned optimizer 或 Photon/Spark CBO 做 head-to-head
- 实验只到 SF=10(<10 GB 量级),没有 TB
- "transfer 到大规模"靠的是从 SF3 → SF10 的一段 deterministic 脚本,严格说不算 transfer 到 TB

所以 4.78× 这个数字,我倾向于把它读作 **"DataFusion 现有 physical optimizer 在这批 query 上的可改进空间"**,而不是"LLM 比 cost-based optimizer 强"。这一点要先讲清楚,后面才好谈架构选择,而不是比谁更准。

真正让 C 路线相对 B 路线有优势的,是三个**和准确率无关**的工程性质。

## 论据一 · Patch 是可 review 的最小单位

Spark Catalyst 里大家熟悉的 rewrite rule(`PushDownPredicates`、`ColumnPruning` 这些)是直接在 `LogicalPlan` 上改 tree。如果你写过 Catalyst rule,你知道一个常见的 review 难题:**rule 改 plan 之后,plan diff 是结构性的,review 时很难一眼看出"它到底动了哪根筋"**。

JSON Patch 给了一个更小的单位:

```json
[
  { "op": "replace", "path": "/nodes/3/build_side", "value": "left" },
  { "op": "remove", "path": "/nodes/5" }
]
```

每一条 patch 是原子的、可以单独 revert、可以单独写测试用例。从工程治理角度,**我认为这比"我们写了一条新 rule"或"agent 直接选了这个 join 顺序"更可控**——尤其是在 B 路线里,LLM agent 直接吐出"用这个 join 顺序",输出本身没有 diff,你只能信或不信。

这不是说 patch 路线一定正确,而是它**犯错之后,你能精确说出错在哪一条 patch**。

## 论据二 · OLAP 反复运行,API 成本可摊销

LLM 的 per-query 调用费用,是任何"LLM 进优化器"提案的第一个工程异议。

DBPlanBench 论文称单 query 优化通常"a few cents"[^2]。这个数字我没法独立复现,但它给了一个有用的框架:**OLAP 场景的特征是同一个 query 模板每天反复跑**。一条 dashboard 查询、一条报表 ETL,跑一千次是日常。如果一次几美分的 LLM 调用换来一个能复用一千次的 patch,经济账就成立。

论文里还有一个细节支持这个论证:他们在 SF=3 上 LLM 找到的优化,通过一段一次性生成的 deterministic 重写脚本,**可以在 SF=10 上保持加速**[^2]。这个机制本身的可扩展性需要更大数据集验证(论文没给 SF=100/1000),但它指向一个工程模式:**LLM 一次性发现 + 长期规则化复用**,不是每次执行都现场调用。

相比之下,B 路线里 LLM agent 每次跑都要走一遍 reasoning,摊销路径不天然。

要诚实地说一句:论文也没给"几次复用之后才回本"的实测数据。在有人给出复用次数对回本的实测曲线之前,"可摊销"只是一个假设,不是结论。

## 论据三 · Patch 缓存可以做成基础设施

如果接受"一次发现、多次复用"的模式,那 patch 不只是一次性的优化结果,**是一份可以入库、可以按 query signature 索引的资产**。

这给了几个工程上很自然的扩展:

1. **按 query 签名 dedup**:同一个 query 模板换 literal 参数,patch 大概率仍然适用
2. **A/B 灰度**:patch 可以挂在 query plan 上做 shadow execution,不直接生效
3. **审计 trail**:每条 patch 落到日志里,后续可以回查"哪条 query 被谁的 patch 改过"

这一套机制和 SQL gateway 类组件已有的工程实践(签名索引的 plan 缓存、计划级审计日志)是合拍的。LLM 在这里的角色更像"补丁生成器",不是 runtime 上的在线决策者。

## 落到 Spark 上,挂点其实已经存在

如果想在 Spark 上把这条路线走通,API 层是现成的。`SparkSessionExtensions` 提供了 `injectPlannerStrategy`、`injectOptimizerRule`、`injectPostHocResolutionRule` 等扩展点[^4],其中 `injectPlannerStrategy` 注入的 `SparkStrategy` 会在 logical → physical 转换时介入——**正好是"optimizer 已经做完它的工作"之后、"执行真正开始"之前**的位置。一个 patch applier 自然可以挂在这里。

真正的工程瓶颈不在 API,在 **`SparkPlan` 和 JSON 之间的序列化/反序列化**。Catalyst 的 plan tree 节点没有官方的 JSON codec。

就我目前看到的情况,patch 路线要落地的前置依赖就是这块。DBPlanBench 在 DataFusion 上写了一份扁平 node-id schema(节点 id + input/left/right 引用)可以作为参考。

## LLM-PM:一条独立路线,而不是更便宜的 C

写到这里有一个明显的质疑要正面回答:**既然要让 LLM 帮 query 选 plan,training-free 的 plan 检索是不是更便宜?**

有一篇工作就在做这件事:**LLM-PM** (arXiv 2506.05853)[^5] 用 `text-embedding-3-large` 把 EXPLAIN plan 文本编码成向量,新 query 来时去历史 plan 库里做 KNN 检索,套用最相似那条历史 plan 的形状。完全 training-free。论文报告在 OpenGauss + JOB-CEB 上**均值 -21% latency**。

仔细看分布:**约 20% 的 query 反而被减速,60% 不变**[^5]。均值 -21% 是少数大幅加速 query 把均值拉低的结果——这是 LLM × QO 这个领域目前普遍存在的报告纪律问题,任何"我们均值 +N%"的论文都该被追问"加速 / 减速 / 不变三分布"。

但分布问题不是关键。关键是 **LLM-PM 和 DBPlanBench 解决的不是同一类问题**:

- **LLM-PM** = 检索 + 套用已有 plan,**不创造新结构**。受历史库覆盖度限制,query 形状没见过就退化到 baseline。
- **DBPlanBench** = 生成新的 plan 变体,**能创造原 optimizer 没产生的结构**。代价是要付 GPT-5 调用费。

所以这不是"更便宜 vs 更贵"的选择,而是两条不同的路线:**检索能复用的、生成能补齐的**。一个完整的方案大概率是两层叠用——先 KNN 命中已知模式,miss 再调 LLM 生 patch——而不是二选一。

## 收束 — 下一步具体该测什么

LLM 进查询优化器的讨论,过去常常停留在"它能不能替代 cost-based optimizer"。这个问题本身可能就问错了。

**把 LLM 放在 optimizer 之后,以 patch 形式做最后一公里微调**,在三件事上比另两条路线更好谈:输出粒度小、review 友好;摊销模型清晰,OLAP 反复运行天然契合;落地路径短,Spark 这类引擎里挂点已经存在(`SparkSessionExtensions.injectPlannerStrategy`)。

但要把这条路线从"工程上合理"推到"benchmark 上证明",真正缺的不是更多 framing,而是一组具体的实验。如果让我列下一步该看到什么,我会要这几个数:

1. **Spark CBO + AQE 作 baseline,TPC-DS SF≥100,patch 路线能榨出多少头部 query 的进一步 speedup**——4.78× 是在 DataFusion + SF=10 上的数字,在成熟 CBO 上头条空间多大,这是核心问题
2. **patch 缓存的命中率曲线**:同模板换 literal,patch 仍适用的比例;不适用时 selectivity 漂移幅度
3. **回本曲线**:一条 patch 平均要被复用多少次才覆盖 LLM 调用成本,在生产 dashboard 流量上的实测
4. **regression rate**:对应 LLM-PM 那 20% 减速比例,patch 路线在同样基准上是多少;有没有自动检测 + 自动 revert 的机制

在这些数出来之前,这一篇也只是个工程方向上的判断,不是结论。如果让我自己起这个实验,我会先把 `SparkPlan ↔ JSON` 这一层做出来——LLM、规则化、缓存都是接得上去的,但 codec 没有,这条路一步都走不动。

---

[^1]: Databricks Blog. "Are LLM agents good at join order optimization?" 2026-04-22. <https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization>
[^2]: Erol M.H., Hao X., Bianchi F., Greco C., Tagliabue J., Zou J. "Making Databases Faster with LLM Evolutionary Sampling." arXiv:2602.10387. <https://arxiv.org/abs/2602.10387> · Code (MIT): <https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling>
[^3]: IETF RFC 6902: JavaScript Object Notation (JSON) Patch. <https://datatracker.ietf.org/doc/html/rfc6902>
[^4]: Apache Spark API: `org.apache.spark.sql.SparkSessionExtensions` — `injectOptimizerRule` / `injectPlannerStrategy` / `injectPostHocResolutionRule`. <https://spark.apache.org/docs/latest/api/java/org/apache/spark/sql/SparkSessionExtensions.html>
[^5]: arXiv:2506.05853, "Training-Free Query Optimization via LLM-Based Plan Similarity." <https://arxiv.org/abs/2506.05853>
