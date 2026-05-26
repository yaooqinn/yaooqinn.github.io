---
title: "只让 LLM 改 SQL,几乎什么都不会发生"
date: 2026-05-26
tags: ["query-optimizer", "llm", "sql-rewrite", "performance", "fine-tuning"]
categories: ["Query Engines"]
summary: "在 TPC-H 10GB 上,直接让 GPT-4o 改写 SQL,平均执行时间从 78.81s 降到 74.92s——几乎等于没改。换一个开源 14B 模型,喂 plan、加 reward、训一遍,同样的工作量降到 29.67s。LLM 在 SQL rewrite 上能不能工作,不取决于 LLM 多强,取决于你愿不愿意给它真正能改 SQL 的信号。"
cover:
  image: /images/posts/llm-only-rewrite-cover.png
  relative: false
showToc: true
---

我上一篇博客写了 Databricks 与 UPenn 的 [LLM × join order 实验](/posts/spark/llm-for-join-order-an-apache-spark-perspective/),论点是:LLM agent 在离线 join-order 调优上是能工作的,因为它**绕过了 cost model 的两道近似**——直接观察 `execute(plan)` 的真实 wall-clock,以试错代价换掉模型偏差。

那篇博客的潜台词是:**"喂对信号、给够反馈,LLM 才能在查询引擎里发挥价值。"** 这一篇写它的反面——**当你不喂、不训、不反馈,只是直接调一个商业 LLM 的 API 让它改 SQL,会发生什么。**

答案有点尴尬。

## 一个让人尴尬的数字

最近读到一篇 2025 年 8 月放出来的论文 [E³-Rewrite](https://arxiv.org/abs/2508.09023)(arXiv:2508.09023),做的是用 LLM 改写 SQL,目标三联——**Executable / Equivalent / Efficient**。论文的核心贡献是一套基于 GRPO 的 RL 微调流程,我下面会展开。但真正让我停下来盯了一会儿的,是它的 Table 1 里"baseline"那一行:

| 方法 | TPC-H 10GB avg latency (s) | TPC-H p90 latency (s) |
|---|---|---|
| Original (不改写) | 78.81 | 300.00 |
| **LLM-only (GPT-4o)** | **74.92** | **300.00** |
| LearnedRewrite (SIGMOD'22) | 41.34 | 103.41 |
| LLM-R² | 54.76 | 300.00 |
| R-Bot | 39.89 | 84.27 |
| **E³-Rewrite (Qwen3-32B, 训练后)** | **29.67** | **51.37** |

(数据来源:E³-Rewrite 论文 Table 1,PostgreSQL,TPC-H SF=10,~2000 条 query,每条跑 5 次去掉极值取均值。)

把视线锁在第二行:**直接拿一个公认最强的商业大模型(GPT-4o)写 prompt 让它改 SQL,平均执行时间从 78.81s 降到 74.92s。**

几乎等于没改。在统计意义上,这个数字和"什么都不做"区分不开。

而最后一行是同一篇论文里他们自己的方法:**同一个 PostgreSQL、同一个 workload,把模型换成 14B/32B 的开源 Qwen,喂上 plan 信号、用 RL 训一遍,平均时间从 74.92 干到 29.67——降到原始查询的 38%。**

差距不是 LLM 的差距(GPT-4o 本身比 Qwen3-32B 在大多数任务上更强),是**信号的差距**。

## 为什么 LLM 知道 SQL,却改不动 SQL

这件事乍看反直觉:LLM 训练语料里 SQL 多得是,改一个 query 改成等价的高效形式听起来不算难。但仔细想就明白了。

让一个人改写 SQL,他改之前会做什么?

- 用 `EXPLAIN` 看一眼当前 plan 长什么样
- 看哪一步是 full table scan、哪个 join 走了 nested loop
- 看哪个 filter 把行数从一亿砍到一千
- 然后才决定:这个子查询能不能拍平、这个 `OR` 能不能拆成 `UNION ALL`、这个 `EXISTS` 能不能改成 `IN`

人拿到的不只是 SQL 字符串,还有**引擎对这串 SQL 的解读**——什么慢、为什么慢、瓶颈在哪。

而 prompt 里只塞一段 SQL 让 LLM 改写,等于让人**只看 SQL 字符串、不看 EXPLAIN** 去优化。LLM 知道一万种 rewrite 套路,但它不知道**这一条 query 在这个数据库上当下哪里慢**,于是它要么照着 schema 名瞎猜应用一些"通用"改写,要么干脆原样输出。

74.92 vs 78.81——这个数字其实在告诉你,**它要么原样输出,要么改完跟没改差不多;真正改对的比例,低到在平均值上看不出来**。

## 第一步:把 EXPLAIN 喂给它

E³-Rewrite 论文里第一件做的事就是这个——他们叫 **Execution Hint Injection**:在把 SQL 喂给模型之前,先跑一次 `EXPLAIN`(训练阶段用 `EXPLAIN ANALYZE`),拿到执行计划,**把这棵树线性化成带缩进的文本**,prepend 到 SQL 前面。

这样 prompt 里多了一段类似:

```
Seq Scan on lineitem  (cost=0.00..172800 rows=6000000)
  Filter: l_shipdate < '1998-12-01'::date
  Rows Removed by Filter: 4500000   ← 瓶颈
->  Hash Join  (cost=...)
    Hash Cond: (l_orderkey = o_orderkey)
    ...
```

模型看到这段就知道:**`lineitem` 上那个 filter 把 75% 的行扔了,而且是在 join 之前过滤,这是个全表扫**。它现在有了一个具体的优化目标——把 filter 下推、或者建议加索引、或者改写谓词形式。

效果立竿见影。同一篇论文 Table 4 的消融实验:

| E³-Rewrite 变体 | avg latency (s) | improved queries | equivalence ratio |
|---|---|---|---|
| 完整版 | 29.67 | 210 | 99.6% |
| **去掉 execution hint** | **39.56** | **163** | 100% |
| 去掉 RL | 32.29 | 194 | 90.1% |
| 去掉 demonstration retrieval | 35.39 | 177 | 96.5% |
| 不微调 vanilla | 56.71 | 125 | 84.8% |

(同上,TPC-H 10GB。)

把 execution hint 去掉,latency 从 29.67 涨到 39.56——**单这一项贡献了 25% 的退化**。一个本来什么都不会改的 LLM,只是因为多看了一段 EXPLAIN,就知道该往哪里使劲。

这件事的一般化结论是:**模型不是没能力,是没视野。** LLM × 查询引擎的任何严肃工作,prompt 里都得有 plan 的某种表示——不一定是文本 EXPLAIN(JSON、protobuf、operator graph 都行),但必须有。光给 SQL 字符串,等于让人闭眼优化。

## 第二步:用 reward 训它

光有 plan 还不够。把 EXPLAIN 喂给 GPT-4o,会不会就工作了?会更好,但还差很远。

回到 Table 4 第三行,**"去掉 RL"这个变体——意思是保留 plan hint、保留 demonstration,但不做 RL 微调,直接用基础模型推理。结果是 32.29s 和 90.1% 等价率。**

90.1% 是什么概念?每改 100 条 query,**有 10 条改写完跟原 query 不等价**——执行出来结果不一样,或者直接报错。在生产环境里这意味着什么不用我多说。

E³-Rewrite 的训练目标设计得很直白,三个 reward 分量:

1. **Executability**:改写出来的 SQL 能不能在 DBMS 里跑起来(语法 + schema 检查)
2. **Equivalence**:跑起来的结果和原 query 是不是一样
3. **Efficiency**:能跑起来、又等价的前提下,比原 query 快多少(用 cost model 估或者实际跑一次)

三个分量加权打分,GRPO 算法在多个候选 rewrite 之间做组内归一更新。**Curriculum** 设计得也克制:**第一阶段强调 executability + equivalence(先逼它改对),第二阶段才把 efficiency reward 加进来**——避免一开始就追快导致模型为了快牺牲等价。

训练完,等价率从 90.1% 涨到 **99.6%**,latency 从 32.29 降到 29.67。这一步不是锦上添花,是把"能用"和"不能用"分开。

## 第三步:训练用真实数据,推理用估算

这是 E³-Rewrite 里一个我觉得被低估的工程细节——他们在论文里只写了短短一段,但值得拎出来说。

`EXPLAIN ANALYZE` 在 PostgreSQL 里会**实际执行 query**,然后给你每个算子的真实行数和真实耗时。`EXPLAIN`(不带 ANALYZE)只给优化器估算出来的 cost,不跑 query。

E³-Rewrite 的做法是:**训练阶段用 `EXPLAIN ANALYZE` 拿真实 plan(因为训练慢一点没关系,样本质量更重要),推理/部署阶段用 `EXPLAIN`(因为线上要快,不能为了改写 SQL 先跑一遍原 query)**。

这是一个朴素但通用的工程模式:**训练时给模型 oracle 信号,推理时给它 proxy 信号,让模型学到从 proxy 推断 oracle 的能力**。说白了就是 distillation 的一种变体,但用在 systems × LLM 上很自然——几乎所有 query optimization 相关的任务都符合这个 oracle/proxy 不对称:

- cost model:训练能跑真实 wall-clock,推理只能估
- cardinality estimation:训练能跑真实 row count,推理只能查统计
- index recommendation:训练能跑 what-if,推理不能

值得记的一个 pattern。

## 三个还没答案的问题

写到这里,论点已经清楚了——"LLM 改 SQL"这件事的瓶颈不在 LLM,在信号通路。但论文给的方案离能在开源引擎里落地还有距离,我留三个问题:

**1. 把 plan 喂给 LLM,有没有一个标准化的接口?**

EXPLAIN 文本只是最朴素的方案。它有版本问题(不同引擎、不同版本输出格式都不一样)、有信息丢失(很多内部 state 不在 EXPLAIN 里)、还有 token 浪费(一棵深 plan 文本化下来很长)。如果未来 LLM × query engine 真的要工业化,**这一层很可能需要一个引擎中立的 plan 表示**——protobuf? Substrait? 还是某种 LLM 友好的中间格式?现在还没共识。

**2. 等价性验证这件事,工业界还没有共识的工具。**

E³-Rewrite 的 reward 函数里写了"equivalence verification",但论文没说具体怎么做的——是 [SPES](https://dl.acm.org/doi/10.1145/3318464.3389761)? [SQLancer](https://github.com/sqlancer/sqlancer)? 还是用 LLM 自己判?三种路径各有限制:SPES 精确但只支持子集 SQL;SQLancer 强但是 differential testing,只能找反例不能证等价;LLM judge 灵活但本身可能幻觉。**没有靠谱的等价验证工具,任何 LLM rewrite 方案在落到生产前都过不了 review**。这一层基础设施缺得很明显。

**3. 10GB benchmark 上的结论,到 TB 级、到真实多租户负载,会不会反转?**

E³-Rewrite 跑的是 TPC-H SF=10(10GB),这在学术界已经算偏大,但离生产环境 TB 级还差两到三个数量级。规模上去之后两件事会变:一是 rewrite 带来的绝对收益变大(慢 query 慢得更多,优化空间更大),二是某些 rewrite 的副作用也被放大(比如改写后 shuffle 数据量变化、内存压力变化)。**在小数据上看起来 -62% 的改写,放到 TB 级数据上是 -80% 还是 +10%,目前没有公开数据能回答**。

---

我没有 actionable 的结论想留给你。这篇博客的全部意图,是想把那个 74.92 的数字摆在所有"用 LLM 改 SQL"项目的入口处:

**如果你的方案没有给 LLM 看 plan,没有用某种反馈训它或筛它,那不管你用的是 GPT-4o、Claude 4 还是 Gemini 3,你做出来的东西大概率跟"什么都不做"区分不开。**

LLM 能不能改 SQL,是个信号通路问题,不是模型能力问题。
