---
title: "深入理解 Apache Spark SQL Metrics：那些数字到底在说什么"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "performance", "debugging"]
categories: ["Apache Spark"]
summary: "Spark SQL 指标是调试慢查询时第一个看的东西——但你知道它们实际测量的是什么、哪些算子有、哪些没有、以及精度在哪里丢失吗？作为 Spark PMC 成员，我追踪了数字从源码到屏幕的全过程。"
showToc: true
---

你打开 Spark SQL 标签页，点击一个慢查询，看到每个算子旁边的数字："number of output rows"、"peak memory"、"time in aggregation build"。你基于这些数字做出判断。

但你有没有想过：**这些数字到底代表什么？** 它们是怎么收集的？精确吗？为什么有些算子有计时指标而其他的没有？

## 五种指标类型

Spark 有五种不同的指标类型，每种有不同的聚合语义：

| 类型 | 测量内容 | 显示格式 | 示例 |
|------|---------|---------|------|
| **sum** | 计数 | `1,234,567` | number of output rows |
| **size** | 字节大小 | `total (min, med, max): 512.0 MiB (...)` | peak memory |
| **timing** | 毫秒耗时 | `total (min, med, max): 5.0 s (...)` | time in aggregation build |
| **nsTiming** | 纳秒耗时 | 同 timing（自动转换） | shuffle write time |
| **average** | 每任务平均值 | `avg (min, med, max): (1.2, 2.5, 6.3)` | avg hash probes per key |

关键洞察：**`sum` 显示单一总计，但其他所有类型都显示每任务的分布**。这对发现倾斜至关重要——如果 `max` 是 `med` 的 10 倍，你就有掉队任务了。

## "total (min, med, max)" 格式详解

```
peak memory
total (min, med, max)
512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB)
```

- **total** — 所有任务的总和
- **min** — 使用最少的任务
- **med** — 中位数任务（第 50 百分位）
- **max** — 使用最多的任务，带 `(stage 3.0: task 36)` 标注

三个值相等 = 负载均衡。`max >> med` = 数据倾斜。

## 只有 7 个算子有计时指标

在 100+ 物理算子中：

| 算子 | 计时指标 |
|------|---------|
| `HashAggregateExec` | time in aggregation build |
| `ObjectHashAggregateExec` | time in aggregation build |
| `SortAggregateExec` | time in aggregation build |
| `SortExec` | sort time |
| `ShuffledHashJoinExec` | time to build hash map |
| `BroadcastExchangeExec` | collect / build / broadcast 三个计时 |
| `ShuffleExchangeExec` | shuffle write time |

**没有计时的：** `FilterExec`、`ProjectExec`、`SortMergeJoinExec`、`BroadcastHashJoinExec`、`WindowExec`、所有 Python UDF、所有扫描算子。

### 原因：WholeStageCodegen

Spark 将 `Filter → Project → HashAggregate` 编译成单一 JVM 方法，共享 CPU 指令。在代码生成管道内测量单个算子耗时没有意义。

有计时的算子在**代码生成边界之外**执行：聚合（构建哈希表）、排序（外部排序器）、Shuffle（网络 I/O）。

缺少计时但应该有的是**打断代码生成管道**的算子：`WindowExec`、Python UDF、`CartesianProductExec`。[DataFlint](https://github.com/dataflint/spark) 为这些算子添加了 `duration` 指标。

## 实用建议

1. **看 min/med/max，不只是 total。** 分布才能揭示倾斜。
2. **没有计时 ≠ 很快。** Python UDF 和 Window 通常最慢但无默认计时。
3. **Web UI 和 REST API 数据完全一致。** 同一数据源，无隐藏详情。
4. **WholeStageCodegen 改变可测量范围。** 代码生成管道内无法获得单算子执行时间。

---

*基于 2026 年 4 月 Apache Spark master 分支。关键源文件：`SQLMetrics.scala`、`MetricUtils.scala`、`SQLAppStatusListener.scala`、`SqlResource.scala`、`Utils.scala`。*
