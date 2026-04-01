---
title: "Deep Dive into Spark SQL Metrics (Part 2): Internals and How AQE Uses Them"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "aqe", "internals"]
categories: ["Apache Spark"]
summary: "Part 2 of the SQL Metrics deep dive. How metrics flow from tasks to driver, and how Adaptive Query Execution uses shuffle statistics to rewrite plans at runtime."
showToc: true
---

This is Part 2 of a 3-part series on Spark SQL Metrics:

- [Part 1: Metric types, complete reference, and what they mean](/posts/spark/understanding-sql-metrics/)
- **Part 2 (this post)**: How metrics work internally, and how AQE uses them for runtime decisions
- Part 3: Extension APIs, UI rendering, and REST API

## The AccumulatorV2 Lifecycle

In [Part 1](/posts/spark/understanding-sql-metrics/), we looked at SQL metrics from the outside — what they measure and how to read the numbers. Now let's trace how those numbers get from executor tasks to the Spark UI.

### From Task to Driver

Every SQL metric is a `SQLMetric`, which extends `AccumulatorV2[Long, Long]`. When a physical operator defines a metric like `numOutputRows`, Spark creates an accumulator on the driver and registers it with the SparkContext.

When a task runs on an executor, it works with a **local copy** of the accumulator. The operator code calls `metric += value` or `metric.add(value)` as it processes rows. These updates are purely local — no network traffic during execution.

The interesting part happens when the task finishes:

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

On task completion, the driver receives the accumulator updates through `SparkListener` events. The `SQLAppStatusListener` handles `onTaskEnd()` — it takes the metric values from the completed task and stores them in `LiveStageMetrics`, an in-memory structure that tracks per-task values for each stage.

### Aggregation and Storage

For **completed** executions, metrics go through `aggregateMetrics()`, which computes the `total (min, med, max)` distribution you see in the UI. These aggregated values are formatted into human-readable strings by `MetricUtils.stringValue()` and persisted to the KVStore as part of `SQLExecutionUIData`. Once stored, the original per-task values are discarded.

For **live** (still-running) executions, the aggregation happens on-the-fly. Each time you refresh the SQL tab, the listener computes the distribution from whatever task values are currently in memory. This is why metrics update in near-real-time while a query is running.

### Driver-Side Metrics

Not all metrics come from tasks. Some originate on the driver itself:

- **Subquery execution time** — when a scalar subquery runs, the driver times it and posts the result
- **Broadcast time** — the time the driver spends broadcasting a table to executors
- **AQE-related timing** — time spent in adaptive optimization

These driver-side metrics use `SQLMetrics.postDriverMetricUpdates()`, which directly updates the accumulator on the driver without going through the task lifecycle. They bypass `onTaskEnd()` entirely.

## How AQE Uses Statistics for Runtime Decisions

This is where things get subtle — and where many people get confused. Adaptive Query Execution (AQE) makes smart decisions at runtime based on **actual data sizes**. But it doesn't use SQL Metrics to do this. It uses a completely separate data source: **MapOutputStatistics**.

### The Data Flow

When AQE is enabled, Spark doesn't execute the entire query plan at once. Instead, it executes stage by stage:

1. `ShuffleExchangeExec` submits a shuffle map stage via `sparkContext.submitMapStage()`
2. The map stage runs — tasks write shuffle data to local disk
3. After all map tasks complete, the `MapOutputTracker` knows exactly how many bytes each reducer partition will receive
4. This information is packaged as `MapOutputStatistics`, which contains `bytesByPartitionId: Array[Long]` — the exact byte size of each shuffle partition
5. `ShuffleQueryStageExec` exposes this via its `mapStats` property
6. `AdaptiveSparkPlanExec` runs optimization rules **after** the stage materializes, using these real statistics instead of estimates

The key insight: AQE waits for shuffle stages to finish, then uses the **actual output sizes** to decide what to do next.

### CoalesceShufflePartitions — Merging Small Partitions

The most common AQE optimization. After a shuffle, you might have 200 partitions (the default `spark.sql.shuffle.partitions`) where most contain very little data.

CoalesceShufflePartitions reads `bytesByPartitionId` and merges adjacent small partitions until each merged partition reaches approximately `spark.sql.adaptive.advisoryPartitionSizeInBytes` (default 64 MB).

**Key configuration:**

| Config | Default | Purpose |
|--------|---------|---------|
| `spark.sql.adaptive.advisoryPartitionSizeInBytes` | 64 MB | Target size for coalesced partitions |
| `spark.sql.adaptive.coalescePartitions.minPartitionNum` | (none) | Minimum number of partitions to keep |
| `spark.sql.adaptive.coalescePartitions.minPartitionSize` | 1 MB | Won't create partitions smaller than this |

**Example:** If you have 200 partitions averaging 1 MB each, AQE might coalesce them into ~3 partitions of ~64 MB each. Instead of 200 tasks reading tiny amounts of data, you get 3 tasks doing real work.

### OptimizeSkewedJoin — Splitting Skewed Partitions

Data skew is one of the most common performance problems in Spark. One partition has 10 GB while the rest have 100 MB each — the skewed partition becomes a bottleneck.

OptimizeSkewedJoin reads `bytesByPartitionId` for **both sides** of a shuffle join. It calculates the median partition size, then flags a partition as "skewed" if:

```
size > max(skewThreshold, median × skewFactor)
```

**Key configuration:**

| Config | Default | Purpose |
|--------|---------|---------|
| `spark.sql.adaptive.skewJoin.skewedPartitionThresholdInBytes` | 256 MB | Absolute minimum to be considered skewed |
| `spark.sql.adaptive.skewJoin.skewedPartitionFactor` | 5.0 | Must be this many times the median |

Both conditions must be met: the partition must be at least 256 MB **and** at least 5× the median size.

Once a skewed partition is identified, AQE splits it into smaller sub-partitions, each targeting `advisoryPartitionSizeInBytes` (64 MB). The non-skewed side of the join is duplicated to match — each sub-partition on the skewed side gets a full copy of the corresponding partition from the other side.

### OptimizeLocalShuffleReader — Eliminating Shuffle Network I/O

When AQE determines that the shuffle data is already on the same executor that will read it (co-located), it can replace the standard `ShuffleExchangeExec` with `AQEShuffleReadExec` configured for local reading. This eliminates network transfer entirely — the reducer reads shuffle files directly from the local disk.

This optimization typically applies after broadcast hash joins, where all the data is already local.

### The Distinction: SQL Metrics vs AQE Statistics

This is the most important conceptual distinction in this post:

| | SQL Metrics | AQE Statistics |
|--|-------------|----------------|
| **What** | `SQLMetric` accumulators | `MapOutputStatistics` |
| **Purpose** | Observability (what you see in the UI) | Runtime plan optimization |
| **Data format** | Formatted strings (`"512.0 MiB"`) | Raw `Long[]` arrays (byte counts) |
| **Code path** | `AccumulatorV2` → `SparkListener` → KVStore | `MapOutputTracker` → `ShuffleQueryStageExec.mapStats` |
| **When computed** | After each task completes | After all map tasks in a stage complete |
| **Who consumes** | Spark UI, REST API, you | AQE optimizer rules |

They often measure **similar things** — both care about data sizes — but through completely different code paths. SQL Metrics tell you what happened. AQE Statistics determine what happens next.

That said, AQE's actions **do** show up in SQL Metrics. When AQE coalesces or splits partitions, the resulting `AQEShuffleReadExec` operator reports its own metrics that tell you exactly what AQE decided to do.

## Metrics That Tell You What AQE Did

The `AQEShuffleReadExec` operator (covered in [Part 1](/posts/spark/understanding-sql-metrics/)) is your window into AQE's decisions. Here's what each metric tells you:

| Metric | What It Means |
|--------|--------------|
| `numCoalescedPartitions` > 0 | AQE merged small partitions together |
| `numSkewedPartitions` > 0 | AQE detected skewed partitions |
| `numSkewedSplits` | How many sub-partitions were created from skewed ones |
| `numEmptyPartitions` | Empty partitions that were detected |
| `partitionDataSize` | Actual data size after AQE optimization |

**Practical example:** If you see `numSkewedPartitions: 3` and `numSkewedSplits: 12`, it means AQE found 3 partitions that exceeded the skew threshold and split them into 12 sub-partitions. Those 3 bottleneck tasks became 12 parallel tasks, dramatically reducing wall-clock time.

If you see `numCoalescedPartitions: 180` with the original `numPartitions: 200`, AQE merged 180 tiny partitions together — your 200 reducer tasks likely became around 20.

These metrics are **the** way to confirm whether AQE is actually helping your query. If `numCoalescedPartitions` and `numSkewedPartitions` are both zero, AQE is active but didn't find anything to optimize.

## Using SQL Plans to Understand AQE

The SQL execution plan is another powerful tool for understanding what AQE did. When AQE is active, the plan shows `AdaptiveSparkPlan` at the top with `isFinalPlan=true` (for completed executions).

You can compare the **initial** plan (what the optimizer originally planned) with the **final** plan (what actually executed after AQE's changes):

```bash
# See the initial plan (before AQE)
spark-history-cli -a <app-id> sql-plan <execution-id> --view initial

# See the final plan (after AQE)
spark-history-cli -a <app-id> sql-plan <execution-id> --view final
```

By comparing these two plans, you can see exactly where AQE intervened:

- `ShuffleExchangeExec` nodes replaced by `AQEShuffleReadExec` — shuffle optimizations applied
- Join strategy changes — e.g., sort-merge join converted to broadcast hash join because one side turned out to be small
- Different partition counts in the final plan — coalescing or splitting happened

This comparison is invaluable when debugging performance issues: you can see whether AQE's decisions helped or whether further tuning is needed.

---

*In [Part 1](/posts/spark/understanding-sql-metrics/), we covered the five metric types and the complete reference. In Part 3, we'll cover the DataSource V2 `CustomMetric` extension API, how the UI renders metrics, and how to query them programmatically via the REST API.*
