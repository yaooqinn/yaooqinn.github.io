---
title: "深入 Spark SQL Metrics（第二部分）：内部机制与 AQE 的运行时决策"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "aqe", "internals"]
categories: ["Apache Spark"]
summary: "SQL Metrics 三部曲的第二部分。指标如何从任务流向驱动端，以及自适应查询执行（AQE）如何利用 Shuffle 统计信息在运行时重写查询计划。"
showToc: true
---

这是 Spark SQL Metrics 深度解析的三部曲：

- [第一部分：指标类型、完整参考和含义](/zh/posts/spark/understanding-sql-metrics/)
- **第二部分（本文）**：内部实现机制，以及 AQE 如何利用指标做出运行时决策
- [第三部分：扩展 API、UI 渲染和 REST API](/zh/posts/spark/sql-metrics-part3-extension-api/)
- [第四部分：Gluten 如何扩展指标系统](/zh/posts/spark/sql-metrics-part4-gluten/)

## AccumulatorV2 生命周期

在[第一部分](/zh/posts/spark/understanding-sql-metrics/)中，我们从外部视角了解了 SQL Metrics——它们测量什么、如何解读数字。现在让我们追踪这些数字是如何从 Executor 端的任务传递到 Spark UI 的。

### 从任务到驱动端

每个 SQL 指标都是一个 `SQLMetric`，它继承自 `AccumulatorV2[Long, Long]`。当物理算子定义一个如 `numOutputRows` 的指标时，Spark 会在驱动端创建一个累加器并注册到 SparkContext。

任务在 Executor 上运行时，使用的是累加器的**本地副本**。算子代码通过 `metric += value` 或 `metric.add(value)` 来更新指标。这些更新完全在本地进行——执行过程中不产生任何网络通信。

关键在于任务完成时发生的事情：

```
Task (Executor)           Driver
─────────────           ──────
metric.add(value)        
    ↓                    
Task completes →────→ onTaskEnd()
                         ↓
                    Store in LiveStageMetrics
                         ↓
                    aggregateMetrics()
                         ↓
                    MetricUtils.stringValue()
                         ↓
                    Map[accId → "512.0 MiB (min, med, max)"]
                         ↓
                    Persist to KVStore (SQLExecutionUIData)
```

任务完成后，驱动端通过 `SparkListener` 事件接收累加器更新。`SQLAppStatusListener` 处理 `onTaskEnd()` 事件——它从已完成的任务中提取指标值，并存储到 `LiveStageMetrics` 中，这是一个在内存中追踪每个 Stage 各任务指标值的数据结构。

### 聚合与存储

对于**已完成**的执行，指标会经过 `aggregateMetrics()` 处理，计算出你在 UI 中看到的 `total (min, med, max)` 分布。这些聚合值由 `MetricUtils.stringValue()` 格式化为可读字符串，然后作为 `SQLExecutionUIData` 的一部分持久化到 KVStore。一旦存储完成，原始的每任务值会被丢弃。

对于**正在运行**的执行，聚合是实时计算的。每次你刷新 SQL 标签页，监听器都会从内存中当前可用的任务值重新计算分布。这就是为什么查询运行时指标能近实时更新。

### 驱动端指标

并非所有指标都来自任务。有些直接在驱动端产生：

- **子查询执行时间** ——标量子查询运行时，驱动端计时并上报结果
- **广播时间** ——驱动端将表广播到各 Executor 花费的时间

这些驱动端指标使用 `SQLMetrics.postDriverMetricUpdates()`，直接在驱动端更新累加器，无需经过任务生命周期，完全绕过了 `onTaskEnd()` 路径。

## AQE 如何利用统计信息做出运行时决策

这部分非常关键，也是很多人容易混淆的地方。自适应查询执行（AQE）在运行时基于**实际数据大小**做出优化决策。但它并不使用 SQL Metrics，而是使用一个完全独立的数据源：**MapOutputStatistics**。

### 数据流转过程

当 AQE 启用时，Spark 不会一次执行整个查询计划，而是逐 Stage 执行：

1. `ShuffleExchangeExec` 通过 `sparkContext.submitMapStage()` 提交 Shuffle Map Stage
2. Map Stage 运行——各任务将 Shuffle 数据写入本地磁盘
3. 所有 Map 任务完成后，`MapOutputTracker` 精确知道每个 Reducer 分区将接收多少字节
4. 这些信息被封装为 `MapOutputStatistics`，其中包含 `bytesByPartitionId: Array[Long]`——每个 Shuffle 分区的精确字节大小
5. `ShuffleQueryStageExec` 通过 `mapStats` 属性暴露这些统计信息
6. `AdaptiveSparkPlanExec` 在 Stage 物化**之后**运行优化规则，使用真实统计信息而非估算值

核心要点：AQE 等待 Shuffle Stage 完成，然后利用**实际输出大小**决定下一步操作。

### CoalesceShufflePartitions——合并小分区

这是最常见的 AQE 优化。Shuffle 之后，你可能有 200 个分区（`spark.sql.shuffle.partitions` 的默认值），其中大部分只包含很少的数据。

CoalesceShufflePartitions 读取 `bytesByPartitionId`，将相邻的小分区合并，直到每个合并后的分区大约达到 `spark.sql.adaptive.advisoryPartitionSizeInBytes`（默认 64 MB）。

**关键配置：**

| 配置项 | 默认值 | 用途 |
|-------|-------|------|
| `spark.sql.adaptive.advisoryPartitionSizeInBytes` | 64 MB | 合并后分区的目标大小 |
| `spark.sql.adaptive.coalescePartitions.minPartitionNum` | （无） | 保留的最小分区数 |
| `spark.sql.adaptive.coalescePartitions.minPartitionSize` | 1 MB | 不会创建小于此值的分区 |

**示例：** 如果你有 200 个分区，每个平均 1 MB，AQE 可能将它们合并为大约 3 个 64 MB 的分区。原来 200 个任务各读取少量数据，变成 3 个任务处理有意义的工作量。

### OptimizeSkewedJoin——拆分倾斜分区

数据倾斜是 Spark 中最常见的性能问题之一。一个分区有 10 GB 而其余分区只有 100 MB——倾斜分区成为整个查询的瓶颈。

OptimizeSkewedJoin 读取 Shuffle Join **两侧**的 `bytesByPartitionId`，计算中位数分区大小，然后将满足以下条件的分区标记为"倾斜"：

```
size > max(skewThreshold, median × skewFactor)
```

**关键配置：**

| 配置项 | 默认值 | 用途 |
|-------|-------|------|
| `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` | 256 MB | 被认定为倾斜的绝对最小值 |
| `spark.sql.adaptive.skewJoin.skewedPartitionFactor` | 5.0 | 必须达到中位数的这个倍数 |

两个条件必须同时满足：分区大小至少达到 256 MB **且**至少是中位数的 5 倍。

一旦识别出倾斜分区，AQE 会将其拆分为较小的子分区，每个子分区目标大小为 `advisoryPartitionSizeInBytes`（64 MB）。Join 的非倾斜侧会被复制以匹配——倾斜侧的每个子分区都会获得来自另一侧对应分区的完整副本。

### OptimizeShuffleWithLocalRead——消除 Shuffle 网络 I/O

当 AQE 判断 Shuffle 数据可以在本地读取（位于同一 Executor 上）时，它会用配置为本地读取的 `AQEShuffleReadExec` 替换标准的 Shuffle 读取。这完全消除了网络传输——Reducer 直接从本地磁盘读取 Shuffle 文件。

这种优化最常见于广播哈希 Join 之后（此时所有数据已在本地），但也可以应用于其他分区方式允许本地读取的 Shuffle。

当 AQE 判断 Shuffle 数据已经在将要读取它的同一个 Executor 上（共置）时，可以将标准的 `ShuffleExchangeExec` 替换为配置了本地读取的 `AQEShuffleReadExec`。这完全消除了网络传输——Reducer 直接从本地磁盘读取 Shuffle 文件。

此优化通常发生在广播哈希 Join 之后，因为此时所有数据已经在本地。

### 核心区别：SQL Metrics 与 AQE 统计信息

这是本文最重要的概念区分：

| | SQL Metrics | AQE 统计信息 |
|--|-------------|-------------|
| **是什么** | `SQLMetric` 累加器 | `MapOutputStatistics` |
| **目的** | 可观测性（UI 中显示的内容） | 运行时计划优化 |
| **数据格式** | 格式化字符串（`"512.0 MiB"`） | 原始 `Long[]` 数组（字节数） |
| **代码路径** | `AccumulatorV2` → `SparkListener` → KVStore | `MapOutputTracker` → `ShuffleQueryStageExec.mapStats` |
| **计算时机** | 每个任务完成后 | Stage 中所有 Map 任务完成后 |
| **消费者** | Spark UI、REST API、用户 | AQE 优化器规则 |

它们经常测量**相似的内容**——都关注数据大小——但通过完全不同的代码路径。SQL Metrics 告诉你发生了什么，AQE 统计信息决定接下来会发生什么。

需要注意的是，AQE 的操作**确实会**反映在 SQL Metrics 中。当 AQE 合并或拆分分区时，产生的 `AQEShuffleReadExec` 算子会上报自己的指标，告诉你 AQE 做了什么决策。

## 从指标中读取 AQE 的决策

`AQEShuffleReadExec` 算子（[第一部分](/zh/posts/spark/understanding-sql-metrics/)中有介绍）是你了解 AQE 决策的窗口。每个指标的含义如下：

| 指标 | 含义 |
|-----|------|
| `numCoalescedPartitions` > 0 | AQE 合并了小分区 |
| `numSkewedPartitions` > 0 | AQE 检测到了倾斜分区 |
| `numSkewedSplits` | 从倾斜分区创建了多少个子分区 |
| `numEmptyPartitions` | 检测到的空分区数 |
| `partitionDataSize` | AQE 优化后的实际数据大小 |

**实际示例：** 如果你看到 `numSkewedPartitions: 3` 和 `numSkewedSplits: 12`，这意味着 AQE 发现了 3 个超过倾斜阈值的分区，并将它们拆分为 12 个子分区。原来的 3 个瓶颈任务变成了 12 个并行任务，显著减少了总执行时间。

如果你看到 `numCoalescedPartitions: 180`，原始 `numPartitions: 200`，说明 AQE 将 180 个微小分区合并在一起——你的 200 个 Reducer 任务可能变成了大约 20 个。

这些指标是确认 AQE 是否真正帮助了你的查询的**唯一方式**。如果 `numCoalescedPartitions` 和 `numSkewedPartitions` 都为零，说明 AQE 虽然启用了，但没有找到需要优化的内容。

## 通过 SQL 执行计划理解 AQE

SQL 执行计划是理解 AQE 行为的另一个强大工具。当 AQE 启用时，计划顶部会显示 `AdaptiveSparkPlan`，对于已完成的执行会标注 `isFinalPlan=true`。

你可以对比**初始**计划（优化器最初的规划）和**最终**计划（AQE 修改后实际执行的计划）：

```bash
# 查看初始计划（AQE 之前）
spark-history-cli -a <app-id> sql-plan <execution-id> --view initial

# 查看最终计划（AQE 之后）
spark-history-cli -a <app-id> sql-plan <execution-id> --view final
```

通过对比这两个计划，你可以准确看到 AQE 在哪里进行了干预：

- `ShuffleExchangeExec` 节点被替换为 `AQEShuffleReadExec`——应用了 Shuffle 优化
- Join 策略改变——例如 Sort Merge Join 转换为 Broadcast Hash Join，因为某一侧的数据量实际上很小
- 最终计划中分区数不同——发生了合并或拆分

这种对比在调试性能问题时非常有价值：你可以看到 AQE 的决策是否有帮助，或者是否需要进一步调优。

---

*在[第一部分](/zh/posts/spark/understanding-sql-metrics/)中，我们介绍了五种指标类型和完整参考。[第三部分](/zh/posts/spark/sql-metrics-part3-extension-api/)将涵盖 DataSource V2 `CustomMetric` 扩展 API、UI 如何渲染指标，以及如何通过 REST API 编程查询指标。*
