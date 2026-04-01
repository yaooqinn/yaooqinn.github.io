---
title: "Deep Dive into Spark SQL Metrics (Part 1): Types, Full Reference, and What They Mean"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "performance", "debugging"]
categories: ["Apache Spark"]
summary: "Part 1 of a 3-part deep dive into Apache Spark's SQL metrics system. Covers the 5 metric types, a complete reference of 100+ metrics across all operators, and how to read the numbers in the Spark UI."
showToc: true
---

This is Part 1 of a 3-part series on Spark SQL Metrics:

- **Part 1 (this post)**: Metric types, complete reference, and what they mean
- Part 2: How metrics work internally, and how AQE uses them for runtime decisions
- Part 3: Extension APIs, UI rendering, and REST API

## What Are SQL Metrics?

Every physical operator in Spark SQL can define **metrics** — counters that track what happened during query execution. When you click on a query in the Spark SQL tab and see numbers like "number of output rows: 5,000" or "peak memory: 512.0 MiB", those are SQL metrics.

They are built on Spark's `AccumulatorV2` framework: each task updates its local copy, and the driver aggregates them after task completion.

## The Five Metric Types

Spark defines five metric types, each with different aggregation and display semantics:

### 1. Sum (`createMetric`)

The simplest type. Values from all tasks are summed into a single total.

**Display format:** `1,234,567`

**Typical usage:** Row counts, file counts, partition counts.

```scala
"numOutputRows" -> SQLMetrics.createMetric(sparkContext, "number of output rows")
```

### 2. Size (`createSizeMetric`)

For byte-based measurements. Shows the total plus per-task distribution.

**Display format:** `total (min, med, max): 512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB)`

**Typical usage:** Peak memory, spill size, data size, shuffle bytes.

```scala
"peakMemory" -> SQLMetrics.createSizeMetric(sparkContext, "peak memory")
```

The `(min, med, max)` breakdown reveals per-task distribution — essential for detecting skew. If `max` is 10x the `median`, one task is doing most of the work.

### 3. Timing (`createTimingMetric`)

For millisecond durations. Shows total plus per-task distribution.

**Display format:** `total (min, med, max): 5.0 s (100 ms, 1.2 s, 2.0 s)`

**Typical usage:** Aggregation time, sort time, broadcast time, hash map build time.

```scala
"aggTime" -> SQLMetrics.createTimingMetric(sparkContext, "time in aggregation build")
```

### 4. Nanosecond Timing (`createNanoTimingMetric`)

Same as timing but accepts nanosecond values, converted to milliseconds for display.

**Display format:** Same as timing.

**Typical usage:** Shuffle write time (measured in nanoseconds for precision).

```scala
"shuffleWriteTime" -> SQLMetrics.createNanoTimingMetric(sc, "shuffle write time")
```

### 5. Average (`createAverageMetric`)

For per-task averages. Shows distribution of the average values across tasks.

**Display format:** `avg (min, med, max): (1.2, 2.5, 6.3)`

**Typical usage:** Hash probe efficiency.

```scala
"avgHashProbe" -> SQLMetrics.createAverageMetric(sparkContext, "avg hash probes per key")
```

## Reading the "total (min, med, max)" Format

This is the most important format to understand:

```
peak memory
total (min, med, max)
512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB (stage 3.0: task 36))
```

| Field | Meaning |
|-------|---------|
| **total** | Sum across all tasks |
| **min** | Smallest task value |
| **med** | Median (50th percentile) |
| **max** | Largest task value, annotated with `(stage X: task Y)` |

**Balanced workload:** min ≈ med ≈ max

**Skewed workload:** max >> med — investigate the annotated task

## Complete SQL Metrics Reference

### Scan Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numOutputRows` | number of output rows | sum | `DataSourceScanExec`, `DataSourceV2ScanExecBase`, `InMemoryTableScanExec`, `LocalTableScanExec` |
| `numFiles` | number of files read | sum | `DataSourceScanExec` |
| `filesSize` | size of files read | size | `DataSourceScanExec` |
| `numPartitions` | number of partitions read | sum | `DataSourceScanExec` |
| `staticFilesNum` | static number of files read | sum | `DataSourceScanExec` |
| `staticFilesSize` | static size of files read | size | `DataSourceScanExec` |
| `metadataTime` | metadata time | timing | `DataSourceScanExec` |
| `scanTime` | scan time | timing | `DataSourceScanExec` |
| `pruningTime` | dynamic partition pruning time | timing | `DataSourceScanExec` |

### Aggregation Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numOutputRows` | number of output rows | sum | All aggregate operators |
| `aggTime` | time in aggregation build | timing | `HashAggregateExec`, `ObjectHashAggregateExec`, `SortAggregateExec` |
| `peakMemory` | peak memory | size | `HashAggregateExec` |
| `spillSize` | spill size | size | `HashAggregateExec`, `ObjectHashAggregateExec` |
| `avgHashProbe` | avg hash probes per key | average | `HashAggregateExec` |
| `numTasksFallBacked` | number of sort fallback tasks | sum | `HashAggregateExec`, `ObjectHashAggregateExec` |

### Join Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numOutputRows` | number of output rows | sum | All join operators |
| `buildDataSize` | data size of build side | size | `ShuffledHashJoinExec` |
| `buildTime` | time to build hash map | timing | `ShuffledHashJoinExec` |
| `spillSize` | spill size | size | `SortMergeJoinExec` |

### Sort Operator

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `sortTime` | sort time | timing | `SortExec` |
| `peakMemory` | peak memory | size | `SortExec` |
| `spillSize` | spill size | size | `SortExec` |

### Shuffle Exchange

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `dataSize` | data size | size | `ShuffleExchangeExec` |
| `numPartitions` | number of partitions | sum | `ShuffleExchangeExec` |
| `shuffleBytesWritten` | shuffle bytes written | size | Shuffle write |
| `shuffleRecordsWritten` | shuffle records written | sum | Shuffle write |
| `shuffleWriteTime` | shuffle write time | nsTiming | Shuffle write |

### Shuffle Read (via `AQEShuffleReadExec`)

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numPartitions` | number of partitions | sum | `AQEShuffleReadExec` |
| `partitionDataSize` | partition data size | size | `AQEShuffleReadExec` |
| `numCoalescedPartitions` | number of coalesced partitions | sum | `AQEShuffleReadExec` |
| `numSkewedPartitions` | number of skewed partitions | sum | `AQEShuffleReadExec` |
| `numSkewedSplits` | number of skewed partition splits | sum | `AQEShuffleReadExec` |
| `numEmptyPartitions` | number of empty partitions | sum | `AQEShuffleReadExec` |
| `remoteBlocksFetched` | remote blocks read | sum | Shuffle read |
| `localBlocksFetched` | local blocks read | sum | Shuffle read |
| `remoteBytesRead` | remote bytes read | size | Shuffle read |
| `remoteBytesReadToDisk` | remote bytes read to disk | size | Shuffle read |
| `localBytesRead` | local bytes read | size | Shuffle read |
| `fetchWaitTime` | fetch wait time | timing | Shuffle read |
| `recordsRead` | records read | sum | Shuffle read |
| `remoteReqsDuration` | remote reqs duration | timing | Shuffle read |
| `remoteMergedReqsDuration` | remote merged reqs duration | timing | Shuffle read |

### Broadcast Exchange

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `dataSize` | data size | size | `BroadcastExchangeExec` |
| `numOutputRows` | number of output rows | sum | `BroadcastExchangeExec` |
| `collectTime` | time to collect | timing | `BroadcastExchangeExec` |
| `buildTime` | time to build | timing | `BroadcastExchangeExec` |
| `broadcastTime` | time to broadcast | timing | `BroadcastExchangeExec` |

### Python UDF Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `pythonDataSent` | data sent to Python workers | size | All Python operators |
| `pythonDataReceived` | data returned from Python workers | size | All Python operators |
| `pythonBootTime` | time to start Python workers | timing | All Python operators |
| `pythonInitTime` | time to initialize Python workers | timing | All Python operators |
| `pythonTotalTime` | time to run Python workers | timing | All Python operators |
| `pythonProcessingTime` | time to execute Python code | timing | All Python operators |
| `pythonNumRowsReceived` | number of output rows | sum | All Python operators |

### Window Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `spillSize` | spill size | size | `WindowExec`, `ArrowWindowPythonExec` |

### Write Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numFiles` | number of written files | sum | File writes |
| `numOutputBytes` | written output | size | File writes |
| `numOutputRows` | number of output rows | sum | File writes |
| `numParts` | number of dynamic part | sum | File writes |
| `taskCommitTime` | task commit time | timing | File writes |
| `jobCommitTime` | job commit time | timing | File writes |

### MERGE INTO Operator

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numTargetRowsCopied` | target rows copied unmodified | sum | `MergeRowsExec` |
| `numTargetRowsInserted` | target rows inserted | sum | `MergeRowsExec` |
| `numTargetRowsUpdated` | target rows updated | sum | `MergeRowsExec` |
| `numTargetRowsDeleted` | target rows deleted | sum | `MergeRowsExec` |
| `numTargetRowsMatchedUpdated` | target rows updated by matched clause | sum | `MergeRowsExec` |
| `numTargetRowsMatchedDeleted` | target rows deleted by matched clause | sum | `MergeRowsExec` |
| `numTargetRowsNotMatchedBySourceUpdated` | target rows updated by not matched by source | sum | `MergeRowsExec` |
| `numTargetRowsNotMatchedBySourceDeleted` | target rows deleted by not matched by source | sum | `MergeRowsExec` |

### Stateful Streaming Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numOutputRows` | number of output rows | sum | Stateful operators |
| `numTotalStateRows` | number of total state rows | sum | Stateful operators |
| `numRowsDroppedByWatermark` | rows dropped by watermark | sum | Stateful operators |
| `stateMemory` | memory used by state | size | Stateful operators |
| `allUpdatesTimeMs` | time to update | timing | Stateful operators |
| `allRemovalsTimeMs` | time to remove | timing | Stateful operators |
| `commitTimeMs` | time to commit changes | timing | Stateful operators |

### Other Operators

| Metric | Display Name | Type | Operators |
|--------|-------------|------|-----------|
| `numOutputRows` | number of output rows | sum | `FilterExec`, `ProjectExec`, `ExpandExec`, `GenerateExec`, `CommandResultExec`, `WindowGroupLimitExec`, `UnionLoopExec`, `PythonWorkerLogsExec` |
| `numAnchorOutputRows` | number of anchor output rows | sum | `UnionLoopExec` |
| `numIterations` | number of recursive iterations | sum | `UnionLoopExec` |
| `dataSize` | data size | size | `SubqueryBroadcastExec` |
| `collectTime` | time to collect | timing | `SubqueryBroadcastExec` |

## WholeStageCodegen and Metric Scope

Most operators (`FilterExec`, `ProjectExec`, `HashAggregateExec`, joins) are fused by WholeStageCodegen into a single JVM method. Their row count metrics (`numOutputRows`) are individually accurate, but they don't have individual timing because they execute as one compiled function.

Operators that execute **outside** codegen and have their own timing:
- `SortExec` (sort time)
- Aggregations (aggregation build time)
- `ShuffledHashJoinExec` (hash map build time)
- `BroadcastExchangeExec` (collect/build/broadcast time)
- `ShuffleExchangeExec` (shuffle write time)
- Python UDF operators (Python worker time)
- Stateful streaming operators (update/remove/commit time)

---

*In Part 2, we'll cover how SQL metrics are implemented internally (the `AccumulatorV2` lifecycle), and how AQE uses shuffle statistics at runtime to rewrite query plans. In Part 3, we'll cover the DataSource V2 `CustomMetric` extension API, UI rendering, and the REST API.*
