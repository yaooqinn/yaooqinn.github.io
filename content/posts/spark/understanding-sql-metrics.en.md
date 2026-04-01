---
title: "Understanding SQL Metrics in Apache Spark: What the Numbers Actually Mean"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "performance", "debugging"]
categories: ["Apache Spark"]
summary: "Spark SQL metrics are the first thing you look at when debugging a slow query — but do you know what they actually measure, which operators have them, and where precision is lost? As a Spark PMC Member, here's what I found when I traced the numbers from source to screen."
showToc: true
---

You open the Spark SQL tab. You click on a slow query. You see numbers next to every operator: "number of output rows", "peak memory", "time in aggregation build". You make decisions based on these numbers.

But have you ever wondered: **what do these numbers actually represent?** How are they collected? Are they precise? Why do some operators have timing metrics and others don't?

I traced the entire SQL metrics pipeline from source code to the Web UI. Here's what I found — and what every Spark user should know.

## The Five Metric Types

Not all metrics are created equal. Spark has five distinct metric types, each with different aggregation semantics:

| Type | What It Measures | Display Format | Example |
|------|-----------------|---------------|---------|
| **sum** | Counts | `1,234,567` | number of output rows |
| **size** | Byte sizes | `total (min, med, max): 512.0 MiB (...)` | peak memory, spill size |
| **timing** | Millisecond durations | `total (min, med, max): 5.0 s (...)` | time in aggregation build |
| **nsTiming** | Nanosecond durations | Same as timing (converted) | shuffle write time |
| **average** | Per-task averages | `avg (min, med, max): (1.2, 2.5, 6.3)` | avg hash probes per key |

The key insight: **`sum` shows a single total, but all other types show per-task distribution** (total, min, median, max). This is critical for spotting skew — if `max` is 10x the `median`, you have a straggler task.

## The "total (min, med, max)" Format

When you see this in the SQL plan:

```
peak memory
total (min, med, max)
512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB)
```

Here's what each number means:

- **total** — sum across ALL tasks that ran this operator
- **min** — the task that used the LEAST memory
- **med** — the median task (50th percentile)
- **max** — the task that used the MOST memory, with a stage/task annotation like `(stage 3.0: task 36)`

When all three are equal, your workload is perfectly balanced. When `max >> med`, you have skew.

## Which Operators Have Timing Metrics?

Out of 100+ physical operators in Spark, **only 7 have any timing metric**:

| Operator | Timing Metric |
|----------|--------------|
| `HashAggregateExec` | time in aggregation build |
| `ObjectHashAggregateExec` | time in aggregation build |
| `SortAggregateExec` | time in aggregation build |
| `SortExec` | sort time |
| `ShuffledHashJoinExec` | time to build hash map |
| `BroadcastExchangeExec` | time to collect, time to build, time to broadcast |
| `ShuffleExchangeExec` | shuffle write time |

**Without any timing:** `FilterExec`, `ProjectExec`, `SortMergeJoinExec`, `BroadcastHashJoinExec`, `WindowExec`, all Python UDF operators, all scan operators.

### Why Most Operators Don't Need Timing

This isn't a bug — it's WholeStageCodegen. Spark compiles `Filter` → `Project` → `HashAggregate` into a single JVM method. They share CPU instructions, so individual operator timing inside a codegen pipeline is meaningless.

Operators WITH timing execute **outside** the codegen boundary: aggregations (hash map build), sorts (external sorter), shuffles (network I/O).

Operators **missing** timing that probably should have it are the ones that **break codegen**: `WindowExec`, Python UDF operators, `CartesianProductExec`, `BroadcastNestedLoopJoinExec`. [DataFlint](https://github.com/dataflint/spark) fills this gap by adding `duration` to these operators.

## Practical Takeaways

1. **Look at min/med/max, not just total.** "10 GiB peak memory" might be even (100 MiB × 100 tasks) or skewed (one task at 9 GiB).

2. **Missing timing ≠ fast.** Python UDFs and window functions are often the slowest but have no timing by default.

3. **Web UI and REST API are identical.** Same `Map[Long, String]`. No hidden detail view.

4. **WholeStageCodegen changes what's measurable.** Individual operator timing inside codegen is not available — only the cluster's stage duration.

---

*Based on Apache Spark master branch, April 2026. Key files: `SQLMetrics.scala`, `MetricUtils.scala`, `SQLAppStatusListener.scala`, `SqlResource.scala`, `Utils.scala`.*
