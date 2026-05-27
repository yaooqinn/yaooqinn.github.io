---
title: "-46% 还是 -2%?规则改写器只在自己家有效"
date: 2026-05-27
tags: ["query-optimizer", "sql-rewrite", "performance", "benchmark", "llm"]
categories: ["Query Engines"]
summary: "在 TPC-H 10GB 上,一个学界 SOTA 的规则改写器把平均执行时间从 69.84s 砍到 37.57s,-46%。换到 DSB 10GB,同一个改写器把 32.62s 砍到 31.93s——只有 -2.1%。差距不在 query 难度,而在 benchmark 是不是它的训练集。\"规则系统稳定可靠\"很多时候是基准过拟合,不是工程事实。"
cover:
  image: /images/posts/rule-rewrite-blindspot-cover.png
  relative: false
showToc: true
---

上一篇博客写了 [只让 LLM 改 SQL,几乎什么都不会发生](/posts/query-engines/llm-only-rewrite-doesnt-work/),论点是:不给 plan、不给反馈、直接 prompt 一个商业 LLM 改 SQL,在 TPC-H 10GB 上把 78.81s 干到 74.92s——和\"什么都不做\"区分不开。

那篇博客有个潜在反问:那不用 LLM、走传统路线呢?学界几十年研究的基于规则的改写器、近几年的学习型改写器,这些\"久经考验\"的路径,是不是更稳?

读完 [QUITE](https://arxiv.org/abs/2506.07675) 这篇论文(arXiv:2506.07675, 2025 年 6 月)的 Table 3,我对这个反问的答案变了:**它们也不稳。它们只是在自己被训练过的那个 benchmark 上看起来稳。**

## 一个换了 schema 就崩塌的数字

QUITE 论文用了三个 benchmark 比较各种改写方法。我把其中一行——**LearnedRewrite**(SIGMOD'22,以下简称 LR)——单独拎出来看:

| Benchmark | Original 平均执行时间 | LR 改写后 | 提升 |
|---|---|---|---|
| **TPC-H** (SF=10) | 69.84s | **37.57s** | **−46.2%** |
| **DSB** (SF=10) | 32.62s | **31.93s** | **−2.1%** |
| Calcite | 23.88s | 22.88s | −4.2% |

(数据来源:QUITE 论文 Table 3。所有 benchmark 都是 SF=10,PostgreSQL,三次执行平均,300 秒截断。)

LR 在 TPC-H 上的成绩单非常体面——几乎砍掉一半执行时间。如果你只看 TPC-H,你会觉得这是一个能打的改写器。

但**同一个 LR、同一份代码,换到 DSB 上,32.62 改到 31.93,只快了 2.1%**。在 benchmark 噪声范围内,基本可以说"什么都没改"。

DSB 不是什么冷门数据集,它是微软 2021 年发的决策支持 benchmark,query 结构比 TPC-H 复杂(更深的嵌套子查询、更多的 CTE、更现实的过滤条件)。**改写空间客观存在**——同一篇论文里 QUITE 在 DSB 上把 31.93 干到了 5.85,等价改写空间显然有,只是 LR 没看见。

## 论文自己承认了

最戳穿这件事的是 QUITE 作者自己写在 Section 7.2 里的一句话:

> "The LR we use is trained on the TPC-H, LR can proficiently identify effective rewrite rules and navigate their constrained search spaces."

—— LR 在 TPC-H 上能打,**是因为它就是在 TPC-H 上训出来的**。

这句话看起来温和,其实把 30 年的规则改写器研究的一个隐性问题挑明了。它们的"训练集",不一定是学习意义上的训练集,但**规则集本身是按 benchmark 演化出来的**:

- 哪条规则被收进 Calcite/Orca 的 rule library? 通常是因为某个 paper 在某个 benchmark 上证明了它有用。
- 哪条规则被反复打磨? 通常是因为它在 TPC-H/TPC-DS/JOB 这些基准上有显著效果。
- 哪条规则被剪掉? 因为它在主流 benchmark 上没贡献甚至带来 regression。

整套规则库不是按"真实世界 query 分布"演化的,而是**按学界共识 benchmark 的分布演化的**。规则系统的本质是 pattern matching,pattern 没在训练集里见过——它就识别不出来。这话不是我说的,是 QUITE 论文引用 Leis et al. (VLDB'15) 那篇经典 join 顺序基准论文里的原文:

> "fixed rewrite rules rely on pattern matching and therefore are fundamentally unable to optimize unseen or complex query patterns"

## "规则系统稳定可靠"的真实含义

回到那两个数字,−46% 和 −2.1%。

如果你之前对"规则改写器"的印象是\"经典、成熟、稳定\",那是因为你看到的几乎所有评测,都在 TPC-H/TPC-DS/JOB 上做。**这些 benchmark 是规则系统的训练集**,在训练集上表现好,本身不构成"稳定可靠"。

DSB 不是规则库的训练集——它出现在 LR 那篇论文发表之后,规则库还没来得及"长出"它需要的模式——结果就是 −2.1%。

这件事的一般化:**"规则系统在生产环境的真实有效性"几乎没有公开数据**。一个公司的生产 SQL 长什么样? 嵌套深度、predicate 形状、join 模式、UDF 使用——绝大部分都和 TPC-H 不像。当你把"在 TPC-H 上 −46%"的规则系统部署到真实负载,你拿到的可能是−5%,可能是 0,也可能某些 query 反而变慢(规则触发但收益负)。

这就是 LLM 路线在改写问题上仍然有戏的原因。规则系统的搜索空间是**封闭的、人工编辑的、滞后于真实负载演化的**;LLM 的模式空间是**开放的、可外推到未见 schema 形状的**。前者在自己的训练集里上限明确,跳不出去;后者上限不清楚,但至少不会因为没见过 DSB 就一动不动。

QUITE 自己的方案——用有限状态机框住 agent 的搜索路径,加上 Calcite 做等价校验——在三个 benchmark 上的提升比例分别是 −46→−63%、−2→−82%、−4→−58%。**TPC-H 上的相对收益小,DSB 上的相对收益大**,这正是规则系统盲区的形状:训练集里改不动的少,陌生 schema 上改不动的多。

## 三个还没答案的问题

写到这里,论点是清楚的:**规则改写器不是不行,是在 benchmark 之外没人测过。**但论文给的方案离结论扎实还差几步,我留三个问题:

**1. 怎么衡量一个改写器的"覆盖泛化能力"?**

目前所有 benchmark 都是单点的——TPC-H 一个值、DSB 一个值、Calcite 一个值。但泛化能力的关键不是任意单点的高低,而是**点之间的方差**。一个 −46% / −2% / −4% 的系统,和一个 −20% / −15% / −18% 的系统,平均看起来差不多,但后者显然更稳。学界需要一个跨 schema 的稳定性指标,不是又多加一个 benchmark 数据点。

**2. 改写器的训练分布和生产分布的差距,有公开数据吗?**

Databricks/Snowflake/阿里这些有海量生产 SQL 的厂商,如果能放出一份"真实 query 形状统计 vs TPC-H 形状统计"的对比——子查询深度分布、predicate 个数分布、join 类型分布——整个行业对"规则系统能不能落地"的判断会立刻清晰一档。现在大家都凭直觉。

**3. 自由生成 vs 框定搜索 vs 规则枚举,三者的边界在哪里?**

LLM 自由生成改写有等价性风险(上一篇博客提到 E³-Rewrite 不微调时等价率只有 84.8%);规则枚举有覆盖盲区(本篇);QUITE 这类\"FSM 框 + LLM 生成 + Calcite 验等价\"是折中。但三者各自的 cost(token 消耗、调用延迟、运维成本)、quality(等价率、改写命中率、平均加速)、coverage(在多少种 schema 上稳定有效)的实际曲线——没有公开对比。这是真正的工业化前置工作。

---

我没有 actionable 的结论想留给你。这篇博客只想留下两个数字——**−46% 和 −2.1%**——和一句要警惕的话:

**任何一个改写器在某个 benchmark 上的成绩,只能证明它在那个 benchmark 上工作。** 工业界讨论\"用不用 LLM 改 SQL\"之前,值得先问的是:我们现在的规则改写器,在我们自己的 query 上,到底是 −46% 还是 −2%?

如果是后者——那这场讨论的真正问题不是 LLM 行不行,是**我们这些年评估改写器的方法,可能本身就有问题**。
