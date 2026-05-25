---
title: "LLM 做 Join Order：从 Databricks 的实验,看 Apache Spark 视角下的三层落地阶梯"
date: 2026-05-25
tags: ["spark", "query-optimizer", "llm", "join-order", "performance"]
categories: ["Apache Spark"]
summary: "Databricks 与 UPenn 把 LLM agent 当成离线 join-order 调优师,在 JOB 113 条查询上拿到 P90 -41% / 几何均值 1.288× 的提速,甚至超过\"完美基数估计\"。从 Apache Spark 一线视角看,这件事说明了什么、又没说明什么。"
showToc: true
---

2026 年 4 月,Databricks 工程博客发了一篇与 UPenn 合作的研究:[*Are LLM agents good at join order optimization?*](https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization) 给的结论很扎眼——在 [Join Order Benchmark (JOB)](https://www.vldb.org/pvldb/vol9/p204-leis.pdf) 的 113 条查询上,LLM agent 选出的 join 顺序让 Databricks Runtime 的 P90 latency 下降 41%、几何均值提速 1.288×,**超过给 optimizer 喂"完美基数估计"得到的下界**,也超过了 [BayesQO](https://rm.cab/bayesqo) 这类离线优化器。

作为长期做查询引擎的人,看到这种数字第一反应是怀疑。读完原文 + UPenn 的[后续 blog](https://ucbskyadrs.github.io/blog/databricks/),怀疑没了大半,但有几个观察值得拎出来——尤其是放在 Apache Spark 这种开源引擎的语境里。

## 这篇研究到底做了什么

抛开 marketing 措辞,核心设定其实很朴素:

- **角色定位**: agent **不进 hot path**。它不替代 cost-based optimizer,也不在 ms 级查询编译期介入。它做的是**离线反复试探**——人类 DBA 几十年来一直在做、却从未被自动化打通的那件事。
- **工具最小化**: agent 只有 **一个** tool: `execute(plan)`,返回真实运行时与各子树的真实 cardinality。
- **结构化输出**: 用 grammar 强制 agent 输出合法的 join order,跳过任何 LLM 输出校验代码。
- **预算可调**: anytime algorithm,15 rollouts/query 报数,最高跑到 50 iterations 还能继续涨。

数据集是 IMDb 放大 10× 到约 20GB。Baseline 包括 DBR 默认 optimizer、注入完美基数估计的 DBR、小模型 agent、BayesQO。结果是开头那串数字。

文章里有个 case study (`q5b`) 很说明问题: 一个 5-way join,DBR 默认从"American VHS company"(12 行,看起来最有选择性) 开始;agent 反过来,先过滤"VHS releases referencing 1994"——因为 `LIKE` predicate 让 CBO 把这一步的基数估错了一个数量级以上。

## 为什么"超过完美基数估计"听起来玄,其实不玄

这是全文最容易被误读的一点。

"完美基数估计 (perfect cardinality estimates)" 听起来像数学下界——既然每一步的真实行数都给了,optimizer 怎么还会输给 LLM?

答案是: **cost model 本身并不完美**。

任何 CBO 都是两次近似:

```
cardinality   →   cost (CPU + I/O + 网络 + shuffle)   →   wall-clock time
        ^近似 1                              ^近似 2
```

第一道近似(基数估计)被这篇论文用"完美基数"消掉了,但第二道近似——cost 到实际时间的映射——还在。Cost model 里那些系数: shuffle 单价、broadcast 阈值、spill 损耗,在现代硬件 (NVMe / 大内存 / 列存 / 向量化执行) 上早就不是 80 年代教科书的样子了。

agent 之所以能赢,是因为它**绕过了这两层近似**: 直接观察 `execute(plan)` 返回的 wall-clock,以试错代价换掉模型偏差。

这不是 LLM 超越数学最优,这是**试错优于建模**——在 cost model 不完美这件事被坐实之前,你听不到这句话的份量。

## LLM × Query Optimizer 的三层落地阶梯

把所有"LLM + 查询优化"的提议拍扁,大致可以分到这三层:

| 层 | 角色 | 时延预算 | 工程难度 | 当前可落地度 |
|---|---|---|---|---|
| **L1 Hot-path replace** | 在编译期生成最终 plan | ms 级 | 极高(LLM 太慢、太贵、不确定性大) | ❌ 现阶段不现实 |
| **L2 Hint generation (online)** | 编译期给优化器一些提示(join 顺序、broadcast 选择) | 几十 ms ~ s | 高(还是要跟 ms 级编译期共存) | ⚠️ 部分可行,需异步 |
| **L3 Offline tuning + 写回 hint** | 离线挑 query、agent 调优、把结果固化成 hint/物化视图/统计信息 | 分钟 ~ 小时 | 中(完全离线,不卡 SLA) | ✅ 已被本文证实 |

Databricks 选择了 **L3**。这是个工程上极其务实的选择,值得展开说几句:

1. **不卡查询路径**。 任何在线 LLM 调用都要面对 100+ms 的 TTFB,光这一项就把 OLAP 的交互体验毁了。L3 完全避开。
2. **失败可回退**。 agent 选错了一次?把 hint 丢掉,下次重跑,代价等于一次额外的 query 执行。L1 / L2 失败的代价是污染生产 traffic。
3. **可量化的 ROI**。 "这条 query 一天跑 200 次,agent 一次性优化省 30%"——这种账好算,容易给老板批预算。
4. **天然 anytime**。 SLA 严的 query 给 5 rollouts,报表/ETL 给 50 rollouts。报表查询的"调优 1 小时换每日节省 30 分钟"模型成立。

**L3 是 2026-2027 LLM × QO 最现实的产品形态。** 等 LLM 推理价格再降一个数量级,L2 才会进入射程;L1 还要再等。

## 这件事对 Apache Spark 生态意味着什么

Spark 的 join reorder 走 `JoinReorderDP` (DPhyp 算法) + cost-based estimation,弱点跟 DBR 完全一样——`LIKE` / range / string predicate 的基数估计,以及 cost model 里那些过时的硬件系数。Databricks 这条路在 OSS Spark 上同样能走,而且开源生态有它自己的优势:

- **统计信息是开放的**。 `DESCRIBE EXTENDED`、`ANALYZE TABLE`、列直方图——agent 需要的所有"真实 cardinality"反馈,Spark 本来就有 API 暴露。
- **plan history 是开放的**。 Spark UI / Spark History Server / SQL execution event log,都能拿到历史 plan + 真实 metrics。这是构造 agent 训练 / 调用样本的现成材料。
- **hint 机制是成熟的**。 Spark 早就有 `/*+ BROADCAST(t) */`、`/*+ MERGE(t1, t2) */`、`/*+ SHUFFLE_HASH */`、`/*+ JOIN_REORDER */` 这类 hint。agent 选定的 plan 不需要侵入 Catalyst,直接生成 hint 写回就行。

如果有人要在 OSS Spark 上把 L3 走通,大概的最短路径是:

1. **从 SQL execution event log 里挑慢 query**——重复执行、长 wall-clock、宽 join 树。
2. **构造 agent 的 single tool**: 一个能接受 join order + 执行 EXPLAIN ANALYZE、返回每个 child 的真实 cardinality 和耗时的接口。
3. **跑 N rollouts** (15 起步,SLA 宽的 query 给到 50)。
4. **把最优 plan 反编译成 Spark hint**,写回到一个查询重写中间层 (任何能在解析后、optimizer 之前拦截 SQL 的地方都行——gateway、JDBC proxy、SQL view、catalog hint 表)。
5. **持续监控**:统计信息变了或表分布漂移,需要重新触发调优。这件事开源做能比 Databricks 做得更好,因为社区可以共建一个跨引擎的 hint catalog 规范。

至于 vectorized execution 那条线(Gluten / Velox / Photon / Comet): join reorder 几乎都还卡在 Spark Catalyst 这一层,native 执行只看 plan、不重写 plan。也就是说,**这件事是 Catalyst 之上的事,在 vectorized 引擎落地之前,先在传统 Spark 上跑通就已经能拿走 80% 的红利。**

## 几个原文没回答的问题

读得越细,越觉得这篇 blog 有些数字必须保留怀疑:

1. **Token 成本是多少?** 50 rollouts × N tokens × frontier-model 单价,可能比省下来的查询时间还贵。这是 L3 能否落地的核心问题,blog 没正面回答。
2. **frontier model 是哪个?** 整篇只说"frontier model",不写 GPT-5 / Claude / Gemini,也不给版本。这意味着结果对模型敏感、不可复现。
3. **数据集规模偏小**。 20GB 的 IMDb 不能代表 TPC-DS 1TB 的世界。长查询、宽 fact 表、大维度表的可推广性,目前是开放问题。
4. **DBR 版本未指明**。 Spark 3.5? DBR 15? 在底座没说清楚的情况下,1.288× 的提速包含多少 DBR runtime 自身改进,无法拆分。
5. **未开源**。 没有 repo,只能信原文的数。我个人希望 UPenn 那边后续会放出一个能在 PostgreSQL/Spark 上跑的最小实现——那才是社区真能复现的起点。

## 一个 PMC 视角的小结

L3 路线最有意思的一点是: 它**把过去几十年 DBA 手调 join 顺序的工艺,第一次变成了可自动化的循环**。

这件事**不需要赌"LLM 替换 query optimizer"这种大事件**。它只需要 LLM 在"反复试探 + 提交最优解"这一件可验证、可回退的任务上,做得比启发式好一点。这个 bar 已经被 Databricks + UPenn 这篇文章迈过去了。

对开源引擎社区,信号是清楚的: **L3 是个低风险、可量化、有真 benchmark 背书的方向**。下一步该有人去 Spark / Trino / DuckDB 上做开源复现,把那 5 个未解问题里至少一两个回答掉。

如果你正在做这件事,欢迎在评论或 [@yaooqinn](https://github.com/yaooqinn) 找我聊。

---

**参考资料**

- Databricks Engineering · [*Are LLM agents good at join order optimization?*](https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization) · 2026-04-22
- UPenn Sky-ADRs · [*How do LLM agents think through SQL join orders?*](https://ucbskyadrs.github.io/blog/databricks/)
- Leis et al. · [*How Good Are Query Optimizers, Really?*](https://www.vldb.org/pvldb/vol9/p204-leis.pdf) · VLDB 2015 (JOB benchmark 原始论文)
- [BayesQO](https://rm.cab/bayesqo) — 离线 Bayesian 优化器,本文 baseline 之一
