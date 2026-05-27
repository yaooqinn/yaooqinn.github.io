---
title: "解剖一份让 LLM 改物理计划的 120 行 prompt"
date: 2026-05-27
tags: ["query-optimizer", "llm", "prompt-engineering", "datafusion", "json-patch"]
categories: ["Query Engines"]
summary: "DBPlanBench 让 GPT-5 在 TPC-H SF10 上把 DataFusion 几何平均加速 4.78×。我对着它的 sql_optimization_prompts.py 数了一遍——120 行,方法论 30 行,剩下 90 行全在给 LLM 立合同。这个比例本身就是这条路线最值得抄走的东西。"
cover:
  image: /images/posts/prompt-anatomy-cover.png
  relative: false
showToc: true
---

![解剖一份 120 行 prompt](/images/posts/prompt-anatomy-cover.png)

我前两篇博客 ([LLM × join order](/posts/query-engines/llm-only-rewrite-doesnt-work/) 和 [rule-rewrite 的盲区](/posts/query-engines/rule-rewrite-blindspot-dsb/)) 写的都是**让 LLM 改 SQL 文本**——输入字符串,输出字符串,执行引擎照常处理。这条路线的好处是上手快,坏处是 LLM 改不动那些只有看物理计划才能发现的问题:join 顺序、projection 列序、physical operator 选择。

那如果让 LLM 直接改物理计划呢?

最近读了一篇 2026 年 2 月的论文 [Making Databases Faster with LLM Evolutionary Sampling](https://arxiv.org/abs/2602.10387)(arXiv:2602.10387),配套开源 [BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling](https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling),做的就是这个。在 DataFusion 上,他们让 GPT-5 直接对物理 plan 做结构变换,TPC-H SF10 上几何平均加速 **4.78×**。

数字漂亮,但更值得抄走的不是数字,是 prompt。我对着仓库里的 [`sql_optimization_prompts.py`](https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling/blob/main/src/sampling/sql_optimization_prompts.py) 数了一遍——**120 行整**。

## 120 行 prompt 怎么分配

按内容拆,这 120 行大致是这样:

| 层 | 内容 | 占比 |
|---|---|---|
| **L1 · 输入 schema** | 讲清楚 `structure` / `succinct_table_info` / `query` 三个输入,给一个三节点的样例 JSON | ~20% |
| **L2 · 方法论** | Step 1 cardinality 估计;Step 2 用估计结果做 join-side selection 和 join reordering | ~30% |
| **L3 · invariant 合同 + 输出 schema** | 3 条 invariant、projection index 计算规则带完整算例、输出必须是 `<patch>[...]</patch>` 包住的 RFC 6902 JSON Patch 数组 | ~50% |

让我盯了一会儿的是这个比例。**方法论只占 30%,剩下 70% 全在"定义合法输出"。**

这是反直觉的。我之前默认的假设是,让 LLM 做查询优化,prompt 的大头应该是"教 LLM 怎么优化"——什么是好 plan、什么是坏 plan、什么时候 broadcast、什么时候 shuffle。但 DBPlanBench 的作者把这块压到 30%,把剩下 70% 全花在**让 LLM 的输出可以被自动验证**。

回头看一下结果——4.78× 几何平均加速,**大约一半 LLM 输出能过 validator**(论文 Section 4)——这个比例就讲得通了。如果 prompt 写松了,LLM 会输出一堆"看起来合理但 compile 不过"的 plan,5 个里过不了 1 个,evolutionary loop 根本搜不动。

## 三个值得抄走的设计

### ① "Be not lazy":显式禁止空响应

prompt 里有这么一段:

```
You should assume that the current plan can almost always be improved
and must not be lazy: actively search for semantics-preserving structural
changes instead of defaulting to making no changes.

By default, the JSON patch array you output should contain at least one
operation that changes the plan structure. Returning an empty array []
... is acceptable only in critical cases ...
```

我读到这段笑了一下。LLM 面对"无法改进"的判断时确实倾向于偷懒返回空数组——这是工程上的常识,但很少有人愿意把它写进 prompt。作者把"积极尝试"写成默认行为,把"返回空"写成 escape hatch。

这种"反惰性 prompt"模式跟查询优化没什么关系,**任何 agent-style 工具调用都通用**。PR 评审、性能诊断、错误归因,只要你不希望 LLM 在"没把握"时一句"看起来没问题"打发掉,就该这么写。

### ② "用语义而不是默认值":把 cardinality 估计交给世界知识

prompt 的 Step 1 里有这么一段:

```
CRITICAL: Do not use defaultFilterSelectivity or other default values.
Instead, perform semantic analysis of column names, table contexts, and
filter predicates to make intelligent cardinality estimates based on
real-world knowledge.
```

这是整套方法的核心赌注。传统 cost-based optimizer 在缺统计信息时退化为常数(PostgreSQL 等值过滤默认 selectivity `DEFAULT_EQ_SEL = 0.005`,见源码 `selfuncs.h`);DBPlanBench 赌 LLM 能从"列名 `order_status` + 过滤值 `'completed'`"推出选择性大致 0.7。

这一点也是这套方法**最大的局限**,后面会展开。

### ③ Projection index 计算规则:invariant 合同的硬核例子

这是 L3 里我觉得最有意思的一段:

```
When you swap the left and right inputs of a HashJoin, you MUST update
the projection indexes to reflect the new schema order. The projection
calculation follows this rule:
- If projection references a left field: use the index as-is
- If projection references a right field: offset by len(left_schema),
  i.e., len(left_schema) + right_projection[i]
```

后面跟着 4 段完整算例:`A[name, id] × B[dept_name, budget]`,原 projection `[0, 3]`,swap 之后应该变 `[2, 1]`,逐字算给你看。

这是 prompt 工程里我很少见到的写法——**把执行引擎的物理 invariant 当成代码注释写给 LLM 看**。一般人写 prompt 给 LLM 改 plan,会写"注意 swap 之后保持语义正确",然后 LLM 改出一个 compile 通过但跑起来列错位的方案。作者直接把"哪个 index 怎么算"列出来,LLM 不需要"理解",只需要"复读"。

## 为什么 4.78× 不能直接套到别家

读完 prompt 我的第一反应是想抄,第二反应是慢一点。这套方法在 DataFusion 上跑出 4.78×,有相当一部分是 DataFusion 自身的红利,跟 LLM 多强其实关系不大。

**DataFusion 的 physical optimizer 是出名的朴素**。statistics propagation 在过去半年才补上,histogram 还在 RFC 阶段,filter selectivity 在大量场景下确实就是 0.005 那一档。当你让 LLM 用"`order_status = 'completed'`"语义推出 0.7,对比基线是 0.005——**这个 100× 的差距其实是 DataFusion 缺统计而不是 LLM 比 cost model 聪明**。

把同样的方法搬到 Spark CBO + histogram 上,或者 Photon、Trino 这种已经有完整 cost model 的引擎上,headroom 会小很多。我不是说没空间,而是**4.78× 不能直接外推**。

Projection index 那部分也是。DataFusion 的 schema 是扁平的 `Vec<Field>`,index 算术很干净;Spark 的 Catalyst 用 `StructType` + `ExprId` + `AttributeReference`,"swap join 之后 projection 怎么走"这件事在 Catalyst 里散落在 `ResolveReferences` / `BindReferences` 那一坨 transform 里,不存在一条能直接"复读给 LLM"的规则。要做的工作是先把这些规则**显式提取出来**——这本身就是个不小的工程。

## 那这份 prompt 究竟可以抄走什么

剥掉数字之后,我觉得真正可以借鉴的是这三件:

1. **三层 prompt 结构**(schema / 方法 / invariant)和它们的比例——70% 用来定义合法输出。这个不止对查询优化适用,对所有"让 LLM 输出结构化 artifact + 自动验证"的任务都适用。
2. **JSON Patch (RFC 6902) 作为输出格式**。工业标准,有现成的 applier,跟 LLM 的"diff 思维"也对得上,不需要重新发明。
3. **"反惰性"指令**。当你不希望 LLM 输出"等于没改"的结果时,这种 prompt 模式是值得抄走的通用 trick。

至于"用 LLM 估 cardinality"——这一条在 DataFusion 上是 4.78× 的来源,在 Spark 上更可能是个累赘。**应该反过来:把 Spark 的真实统计注入 prompt,让 LLM 不用猜**。

## 一个未解的问题

这篇博客我没回答的事:**~50% 的 validator 通过率到底够不够支撑生产**。

DBPlanBench 是离线 evolutionary sampling,跑一晚上、采几百个 plan、挑最快的——50% 通过率没问题。如果是在线的 plan tuner,每个 query 等 LLM 改 10 次才有 5 个 compile 过,延迟和 token 成本两边都不划算。

这条路线要不要走、走多远,我自己也没想清楚。先把这份 prompt 拆开看一遍,至少知道下次有人拿"LLM 改 plan"这件事来卖给我时,该看哪几个地方。

---

**附:文中数字的出处**

- 4.78× 几何平均加速:[arXiv:2602.10387](https://arxiv.org/abs/2602.10387),TPC-H SF10
- 120 行 prompt:仓库源码 `wc -l sql_optimization_prompts.py`,2026-05-26 commit
- ~50% validator 通过率:论文 Section 4
- PostgreSQL 默认 filter selectivity 0.005:[PG 源码 `selfuncs.c` `DEFAULT_INEQ_SEL`](https://github.com/postgres/postgres/blob/master/src/include/utils/selfuncs.h)
- JSON Patch:[RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902)
