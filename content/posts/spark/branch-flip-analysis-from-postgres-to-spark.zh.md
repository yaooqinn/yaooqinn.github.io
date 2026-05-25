---
title: "翻转分支找性能 bug：ETH 的 BFA 方法，以及它对 Spark 意味着什么"
date: 2026-05-26
tags: ["spark", "query-optimizer", "performance", "testing", "catalyst"]
categories: ["Apache Spark"]
summary: "ETH 的一篇新论文用「把优化分支翻一下，看谁更快」这一招，在 PostgreSQL、MySQL、CockroachDB、MariaDB 上挖出 21 个此前未知的性能 bug。方法概念简单，Spark 这边的落地接口意外地齐整 —— `spark.sql.optimizer.excludedRules` 几乎就是现成的翻转开关。"
showToc: true
---

上周 arXiv 上有一篇值得查询引擎从业者再读一遍的论文：[*Finding Performance Issues in Database Systems by Exploiting Dormant Code Paths*](https://arxiv.org/abs/2605.22992)，作者是 ETH Zürich 的 Jinsheng Ba 和 Zhendong Su，arXiv:2605.22992，2026 年 5 月 21 日提交。

结论非常具体：在 **PostgreSQL、MySQL、CockroachDB、MariaDB** 四个成熟数据库上，用 TPC-H 和 TPC-DS 工作负载，发现了 21 个**此前未公开**的、独立的性能问题。背后的方法 —— Branch Flip Analysis，BFA —— 概念上很简单；放在 Apache Spark 的语境里看，落地接口意外地齐整。这篇博客梳理一下论文做了什么，为什么有效，以及把它老老实实搬到 Spark 上会长什么样。

## BFA 到底是什么

方法一句话：**把源代码里所有「为某个优化开/关」的 `if` 分支挨个翻转，看翻完之后是否显著更快**。如果翻完反而显著更快，那就是一个性能 bug —— 这个优化按定义就不应该让查询变慢。

作者把这个方法实现成一个叫 **QueryZen** 的原型，跑在四个成熟的开源 DBMS 上。三个细节决定了它是「实际可用」而不是「输出一堆假阳性」：

1. **用 differential testing 保 soundness**：翻转后的分支必须保持查询结果不变。QueryZen 在原版和翻转版二进制上跑同一组语料，只要结果不一致就丢弃；论文还对样本做了人工检查，论证幸存下来的分支确实是「优化-only」（日志、缓存、执行计划选择），而不是功能性逻辑。
2. **统计显著性过滤噪声**：只有当翻转后的运行时在多轮重复测试里显著快于原版，才被记为发现。这把 wall-clock 基准本身的噪声筛掉。
3. **报告 triage 友好**：每条发现都是「(commit, 分支, 查询)」三元组，开发者用一个开关就能复现，不必反推工作负载。

论文也坦诚承认两条限制：在某台机器上看起来稳定的现象，换硬件或换内存配置可能就变了；论文把「真阳性」定义为「上游开发者确认」—— 门槛很高，所以 21 这个数字是个下界。

## 它和「A/B 切一下配置开关」不是一回事

数据库引擎一直有「关掉某个优化」的配置：PostgreSQL 的 `enable_hashjoin = off`、MySQL 的 `optimizer_switch`、Spark 一堆 `spark.sql.*` 开关。从业者几十年来一直靠这些 flag 调试性能回归。

BFA 多出来的是**广度和覆盖**：它不依赖「碰巧被暴露出来的那些开关」。它的目标是源代码里所有可以分类为「优化分支」的 `if`，包括没有任何用户可见 flag 控制的那些。论文里 21 个 issue 大多数都藏在**没有 flag** 的分支里 —— 这一点才是引擎维护者真正应该警觉的地方：那些有名有姓的开关已经被反复 A/B 过了，而埋在 planner/executor 深处、没有 flag 的优化分支没有。

## 在 Spark 上的着力点

接下来对 Spark 社区来说有意思的部分。BFA 需要的两块原料，主干 Spark 已经现成提供：

- **能单独禁用某条 optimizer rule 的接口**：[`spark.sql.optimizer.excludedRules`](https://spark.apache.org/docs/latest/configuration.html#runtime-sql-configuration) 接受一个逗号分隔的全限定类名列表，把对应规则从 Catalyst optimizer batch 中剔除。这就是 BFA 想要的「分支翻转开关」—— 粒度合适、声明式、且是社区长期维护的稳定 API。
- **现成的基准工作负载**：[`sql/core` 目录下的 TPC-DS 生成器](https://github.com/apache/spark/tree/master/sql/core/src/test/scala/org/apache/spark/sql)在项目内部就被用于性能回归相关工作；TPC-DS 99 条查询在 Spark 性能讨论里也是公认的对照基线。

把 BFA 搬到 Spark 的做法因此并不玄乎：

1. 枚举给定构建里 `Optimizer.batches` 中的所有 rule，以及通过 SparkSessionExtensions API 注册进来的 rule。
2. 对每条 rule，跑同一份 TPC-H 或 TPC-DS 工作负载两遍：一遍启用（默认），一遍把它列进 `spark.sql.optimizer.excludedRules`。多次重复取中位数。
3. 校验两轮的查询结果一致；不一致就丢掉这对。
4. 报告「禁用后显著更快」的 rule × query 组合。

坦白讲，复杂之处也有几个。Catalyst 里的 rule 并非全部是 order-independent ——禁用 rule A 可能让 rule B 的 pattern 命中情况发生变化，所以「只翻一条」的局部语义会泄漏。AQE 的部分决策依赖运行时统计，要做确定性翻转就需要确定性的输入。再加上「每条 rule 各跑一次 TPC-DS」乘以现代 Catalyst 的规则数量，机器成本不低。这些都不会让实验不可行，只是说明它是工程活。

## BFA 不是什么

把方法的边界讲清楚同样重要：

- **不是最优性证明**。在四个成熟系统里挖出 21 个 bug 已经很有分量，但 BFA 没法告诉你它「没标」的地方就一定是对的。
- **不是 cost-based 推理的替代品**。「翻转后某条查询更快」是在特定查询、特定配置下的一个事实。修复方式可能是调整 cost model 或某个启发式的阈值，不见得就该把整条优化逻辑拔掉。论文讨论的两类假阳性正是这种情况 —— 作者本来就在做某种取舍，BFA 看不出来。
- **不是 workload-free**。TPC-H 和 TPC-DS 偏向分析型负载。在 Spark 上跑一遍 BFA，很可能漏掉只在 streaming、structured streaming、或重度依赖 DSv2 连接器的场景下才暴露的问题。

## 一个克制的建议，以问题的形式抛出

这是个人观察。但我觉得这个问题值得在开源社区里公开问一句：开源查询引擎社区 —— Spark、Trino、DuckDB、Velox 系列、ClickHouse —— 是否应该把「per-rule 性能回归测试」纳入新优化工作的 CI 契约，就像大家已经把「正确性回归测试」纳入了那样？

材料其实都在了。Spark 的 `excludedRules` 已经有了。Trino 给很多 optimizer 提供了 [`optimizer.<rule>.disabled`](https://trino.io/docs/current/admin/properties-optimizer.html) flag。DuckDB 暴露了 [`SET disabled_optimizers`](https://duckdb.org/docs/configuration/overview.html)。多数大项目本来就在夜跑 TPC-H 或 TPC-DS。缺的只是那一层 harness：枚举、翻转、diff、报告。

代价是真实的 —— 机器时间，以及把「真回归」从「故意的取舍」里分拣出来的人力。不做的代价就是 BFA 这篇论文刚刚演示过的：21 个 bug，安安静静地待在被反复 review 过的成熟代码库里，藏在没人有理由专门去看的分支中。

## 延伸阅读

- 论文：[arXiv:2605.22992](https://arxiv.org/abs/2605.22992)（PDF / HTML 版本入口在 abs 页面）。
- Spark 单 rule 禁用接口：[`spark.sql.optimizer.excludedRules`](https://spark.apache.org/docs/latest/configuration.html#runtime-sql-configuration)，Spark 3.5+ 配置参考。
- 自动化 DBMS 性能测试的前期工作 —— APOLLO（[Jung et al., 2019](https://doi.org/10.1145/3338906.3338937)）、AMOEBA（[Liu et al., 2022](https://doi.org/10.1145/3510003.3510123)）、CERT（[Ba et al., 2024](https://doi.org/10.1145/3641939)）—— 论文 related work 章节是张紧凑的地图。

文中是个人观察，不代表任何项目立场。引用材料就是一手来源，欢迎读者自己读完再下判断。
