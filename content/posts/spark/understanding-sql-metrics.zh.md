---
title: "深入 Spark SQL Metrics（第一部分）：类型、完整参考和含义"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "performance", "debugging"]
categories: ["Apache Spark"]
summary: "Spark SQL Metrics 三部曲的第一部分。涵盖 5 种指标类型、100+ 指标的完整参考，以及如何正确解读 Spark UI 中的指标数字。"
showToc: true
---

这是 Spark SQL Metrics 深度解析的三部曲：

- **第一部分（本文）**：指标类型、完整参考和含义
- 第二部分：内部实现机制，以及 AQE 如何利用指标做出运行时决策
- [第三部分：扩展 API、UI 渲染和 REST API](/zh/posts/spark/sql-metrics-part3-extension-api/)
- [第四部分：Gluten 如何扩展指标系统](/zh/posts/spark/sql-metrics-part4-gluten/)

## 什么是 SQL Metrics？

Spark SQL 的每个物理算子都可以定义 **metrics**——在查询执行过程中跟踪各种计数的指标。当你在 SQL 标签页点击一个查询，看到 "number of output rows: 5,000" 或 "peak memory: 512.0 MiB"，那些就是 SQL Metrics。

它们基于 Spark 的 `AccumulatorV2` 框架：每个任务更新自己的本地副本，任务完成后 Driver 进行聚合。

## 五种指标类型

### 1. Sum（`createMetric`）

最简单的类型。所有任务的值求和为单一总计。

**显示格式：** `1,234,567`

**典型用途：** 行数、文件数、分区数。

### 2. Size（`createSizeMetric`）

用于字节量度。显示总计加上每任务的分布。

**显示格式：** `total (min, med, max): 512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB)`

**典型用途：** 峰值内存、Spill 大小、数据大小、Shuffle 字节数。

`(min, med, max)` 分布对于检测数据倾斜至关重要——如果 `max` 是 `median` 的 10 倍，说明有掉队任务。

### 3. Timing（`createTimingMetric`）

用于毫秒级耗时。显示总计加上每任务分布。

**显示格式：** `total (min, med, max): 5.0 s (100 ms, 1.2 s, 2.0 s)`

**典型用途：** 聚合时间、排序时间、广播时间。

### 4. NsTiming（`createNanoTimingMetric`）

与 Timing 相同但接受纳秒值，显示时自动转换为毫秒。

**典型用途：** Shuffle 写入时间。

### 5. Average（`createAverageMetric`）

用于每任务平均值，显示平均值在各任务间的分布。

**显示格式：** `avg (min, med, max): (1.2, 2.5, 6.3)`

**典型用途：** 哈希探测效率。

## 如何解读 "total (min, med, max)" 格式

```
peak memory
total (min, med, max)
512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB (stage 3.0: task 36))
```

| 字段 | 含义 |
|------|------|
| **total** | 所有任务的总和 |
| **min** | 最小的任务值 |
| **med** | 中位数（第 50 百分位） |
| **max** | 最大的任务值，标注 `(stage X: task Y)` |

**负载均衡时：** min ≈ med ≈ max

**数据倾斜时：** max >> med——检查标注的那个任务

## 完整 SQL Metrics 参考

### Scan 算子

| 指标 | 显示名称 | 类型 | 算子 |
|------|---------|------|------|
| `numOutputRows` | number of output rows | sum | 所有 Scan 算子 |
| `numFiles` | number of files read | sum | `DataSourceScanExec` |
| `filesSize` | size of files read | size | `DataSourceScanExec` |
| `scanTime` | scan time | timing | `DataSourceScanExec` |
| `metadataTime` | metadata time | timing | `DataSourceScanExec` |
| `pruningTime` | dynamic partition pruning time | timing | `DataSourceScanExec` |

### 聚合算子

| 指标 | 显示名称 | 类型 | 算子 |
|------|---------|------|------|
| `numOutputRows` | number of output rows | sum | 所有聚合算子 |
| `aggTime` | time in aggregation build | timing | `HashAggregateExec`, `ObjectHashAggregateExec`, `SortAggregateExec` |
| `peakMemory` | peak memory | size | `HashAggregateExec` |
| `spillSize` | spill size | size | `HashAggregateExec`, `ObjectHashAggregateExec` |
| `avgHashProbe` | avg hash probes per key | average | `HashAggregateExec` |

### Join 算子

| 指标 | 显示名称 | 类型 | 算子 |
|------|---------|------|------|
| `numOutputRows` | number of output rows | sum | 所有 Join 算子 |
| `buildDataSize` | data size of build side | size | `ShuffledHashJoinExec` |
| `buildTime` | time to build hash map | timing | `ShuffledHashJoinExec` |
| `spillSize` | spill size | size | `SortMergeJoinExec` |

### Sort 算子

| 指标 | 显示名称 | 类型 | 算子 |
|------|---------|------|------|
| `sortTime` | sort time | timing | `SortExec` |
| `peakMemory` | peak memory | size | `SortExec` |
| `spillSize` | spill size | size | `SortExec` |

### Shuffle 写入

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `dataSize` | data size | size |
| `shuffleBytesWritten` | shuffle bytes written | size |
| `shuffleRecordsWritten` | shuffle records written | sum |
| `shuffleWriteTime` | shuffle write time | nsTiming |

### Shuffle 读取（`AQEShuffleReadExec`）

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `partitionDataSize` | partition data size | size |
| `numCoalescedPartitions` | number of coalesced partitions | sum |
| `numSkewedPartitions` | number of skewed partitions | sum |
| `numSkewedSplits` | number of skewed partition splits | sum |
| `fetchWaitTime` | fetch wait time | timing |
| `remoteBytesRead` | remote bytes read | size |
| `localBytesRead` | local bytes read | size |

### Broadcast Exchange

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `dataSize` | data size | size |
| `collectTime` | time to collect | timing |
| `buildTime` | time to build | timing |
| `broadcastTime` | time to broadcast | timing |

### Python UDF 算子

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `pythonDataSent` | data sent to Python workers | size |
| `pythonDataReceived` | data returned from Python workers | size |
| `pythonBootTime` | time to start Python workers | timing |
| `pythonInitTime` | time to initialize Python workers | timing |
| `pythonTotalTime` | time to run Python workers | timing |
| `pythonProcessingTime` | time to execute Python code | timing |

### 写入算子

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `numFiles` | number of written files | sum |
| `numOutputBytes` | written output | size |
| `taskCommitTime` | task commit time | timing |
| `jobCommitTime` | job commit time | timing |

### MERGE INTO 算子

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `numTargetRowsInserted` | target rows inserted | sum |
| `numTargetRowsUpdated` | target rows updated | sum |
| `numTargetRowsDeleted` | target rows deleted | sum |
| `numTargetRowsCopied` | target rows copied unmodified | sum |

### 有状态流处理算子

| 指标 | 显示名称 | 类型 |
|------|---------|------|
| `numTotalStateRows` | number of total state rows | sum |
| `stateMemory` | memory used by state | size |
| `allUpdatesTimeMs` | time to update | timing |
| `allRemovalsTimeMs` | time to remove | timing |
| `commitTimeMs` | time to commit changes | timing |

## WholeStageCodegen 与指标范围

大多数算子被 WholeStageCodegen 融合成单一 JVM 方法。它们的行数指标（`numOutputRows`）各自准确，但没有各自的计时——因为它们作为一个编译函数执行。

在**代码生成管道之外**有独立执行阶段并具有独立计时的算子：
- `SortExec`（排序时间）
- 聚合算子（聚合构建时间）
- `ShuffledHashJoinExec`（Hash Table 构建时间）
- `BroadcastExchangeExec`（收集/构建/广播时间）
- `ShuffleExchangeExec`（Shuffle 写入时间）
- Python UDF 算子（Python 工作器时间）
- 有状态流处理算子（更新/删除/提交时间）

---

*第二部分将深入 SQL Metrics 的内部实现机制（`AccumulatorV2` 生命周期），以及 AQE 如何利用 Shuffle 统计信息在运行时重写查询计划。[第三部分](/zh/posts/spark/sql-metrics-part3-extension-api/)将介绍 DataSource V2 `CustomMetric` 扩展 API、UI 渲染和 REST API。*
