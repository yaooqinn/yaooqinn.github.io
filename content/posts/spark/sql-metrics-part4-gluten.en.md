---
title: "Deep Dive into Spark SQL Metrics (Part 4): How Gluten Extends the Metrics System"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "gluten", "velox", "native"]
categories: ["Apache Spark"]
summary: "Part 4 of the SQL Metrics deep dive. How Apache Gluten bridges native Velox/ClickHouse metrics back to Spark's SQL Metrics framework, adding 60+ metrics that vanilla Spark doesn't have."
showToc: true
---

This is a bonus Part 4 of the Spark SQL Metrics series:

- [Part 1: Metric types, complete reference, and what they mean](/posts/spark/understanding-sql-metrics/)
- [Part 2: How metrics work internally, and how AQE uses them for runtime decisions](/posts/spark/sql-metrics-part2-internals/)
- [Part 3: Extension APIs, UI rendering, and REST API](/posts/spark/sql-metrics-part3-extension-api/)
- **Part 4 (this post)**: How Gluten extends the metrics system

## The Problem Gluten Solves for Metrics

In [Part 1](/posts/spark/understanding-sql-metrics/), we noted that vanilla Spark has only **7 operators** with timing metrics: `HashAggregateExec`, `SortExec`, `SortMergeJoinExec`, `ShuffledHashJoinExec`, `BroadcastExchangeExec`, `ShuffleExchangeExec`, and `DataSourceScanExec`. Most operators that live inside a `WholeStageCodegen` cluster can't have individual timing because they are fused into a single JVM method — once the JVM compiles them together, there's no boundary left to measure.

Apache Gluten takes a fundamentally different approach: it replaces the JVM execution engine entirely with a native C++ engine — either [Velox](https://github.com/facebookincubator/velox) or [ClickHouse](https://github.com/ClickHouse/ClickHouse). Because native operators execute independently (they are not fused by JVM codegen), **every operator can have individual timing**. This is not a workaround like DataFlint, which wraps existing Spark operators with extra measurement code. It is a natural consequence of replacing the engine entirely — each C++ operator is a separate function call with its own start and end timestamps.

The result: Gluten surfaces **60+ metrics** that vanilla Spark simply does not have, including per-operator wall clock time, per-phase join metrics, native spill tracking, dynamic filter statistics, and I/O breakdowns by storage tier.

## The 3-Layer Architecture

Gluten's metrics system bridges two worlds: Spark's JVM-based `SQLMetric` framework and the native C++ execution engine. The architecture has three layers:

```
Spark SQLMetric (JVM)     ←── MetricsUpdater (bridge)  ←── Velox/CH (C++)
Map[String, SQLMetric]        updateNativeMetrics()         long[] arrays via JNI
```

### Layer 1: Spark SQLMetric (unchanged)

Each `*ExecTransformer` — Gluten's replacement for vanilla Spark's `*Exec` operators — overrides `lazy val metrics` using the same pattern as vanilla Spark. But instead of hardcoding the metric set, it delegates to the backend:

```scala
BackendsApiManager.getMetricsApiInstance
  .genFilterTransformerMetrics(sparkContext)
```

This means the Velox backend and the ClickHouse backend can define completely different metrics for the same logical operator. A `FilterExecTransformer` running on Velox might expose `wallNanos` and `peakMemoryBytes`, while the same operator running on ClickHouse could expose different internal counters. The metric definitions are backend-specific, but they all end up as standard `SQLMetric` objects that Spark's UI and REST API can display.

### Layer 2: MetricsUpdater (Gluten's bridge abstraction)

The `MetricsUpdater` trait is Gluten's central bridging abstraction. It defines a single method:

```scala
trait MetricsUpdater extends Serializable {
  def updateNativeMetrics(opMetrics: IOperatorMetrics): Unit
}
```

Each operator has a corresponding `MetricsUpdater` implementation. These updaters are organized into a `MetricsUpdaterTree` that mirrors the plan DAG — one updater per operator, connected in the same parent-child structure as the physical plan.

Why a separate tree? Because the `MetricsUpdaterTree` is `Serializable` — it can be sent to executors without serializing the full `SparkPlan` (which contains non-serializable objects like `SparkContext`). On the executor, after native execution completes, the tree walks the native metrics and updates the `SQLMetric` accumulators.

Three special sentinel instances handle edge cases:

- `MetricsUpdater.None` — operator has no metrics to update
- `MetricsUpdater.Todo` — metrics support not yet implemented for this operator
- `MetricsUpdater.Terminate` — the branch ends here (no children to recurse into)

Here's a concrete example — the `FilterMetricsUpdater`:

```scala
class FilterMetricsUpdater(val metrics: Map[String, SQLMetric]) extends MetricsUpdater {
  override def updateNativeMetrics(opMetrics: IOperatorMetrics): Unit = {
    val m = opMetrics.asInstanceOf[OperatorMetrics]
    metrics("numOutputRows") += m.outputRows
    metrics("outputVectors") += m.outputVectors
    metrics("outputBytes") += m.outputBytes
    metrics("cpuCount") += m.cpuCount
    metrics("wallNanos") += m.wallNanos
    metrics("peakMemoryBytes") += m.peakMemoryBytes
    metrics("numMemoryAllocations") += m.numMemoryAllocations
  }
}
```

Notice how each native metric field (e.g., `m.wallNanos`) maps directly to a `SQLMetric` key. The updater is the translation layer between native C++ naming and Spark's metric namespace.

### Layer 3: Native metrics via JNI

On the C++ side, the Velox engine collects metrics in arrays during execution — one entry per operator index. When a task completes, Gluten transfers these metrics across the JNI boundary as a `Metrics` object containing `long[]` arrays:

```
inputRows[]       — rows consumed by each operator
outputRows[]      — rows produced by each operator
wallNanos[]       — wall clock nanoseconds per operator
cpuCount[]        — CPU time per operator
peakMemoryBytes[] — peak memory per operator
...               — 20+ more arrays
```

The `MetricsUpdatingFunction` walks the `MetricsUpdaterTree`, extracting per-operator values from the arrays by operator index. This is a bulk transfer — one JNI call per task, not per row — keeping overhead minimal.

## What Gluten Adds — 60+ Metrics

Let's look at the specific metrics Gluten introduces, organized by category.

### Per-Operator Execution Metrics

In vanilla Spark, most operators report only `numOutputRows`. In Gluten, **every operator** gets these:

| Metric | Type | What It Measures |
|--------|------|-----------------|
| `wallNanos` | nsTiming | Wall clock time per operator |
| `cpuCount` | timing | CPU time count |
| `peakMemoryBytes` | size | Peak memory usage |
| `numMemoryAllocations` | sum | Memory allocation count |
| `outputRows` | sum | Output row count |
| `outputVectors` | sum | Output vector (batch) count |
| `outputBytes` | size | Output data volume in columnar format |
| `loadLazyVectorTime` | timing | Time loading lazy-evaluated vectors |

Having `wallNanos` on every operator is transformative. In vanilla Spark, if a query is slow and the bottleneck is inside a `WholeStageCodegen` cluster, you have no way to tell which operator is responsible. With Gluten, you can immediately see that `FilterExecTransformer` took 200 ms while the adjacent `ProjectExecTransformer` took 5 ms.

### Scan-Specific Metrics

Vanilla Spark's scan operators have `scanTime` and `numFiles`. Gluten goes much deeper:

| Metric | What It Measures |
|--------|-----------------|
| `skippedSplits` / `processedSplits` | File split pruning effectiveness |
| `skippedStrides` / `processedStrides` | Row group/stripe pruning within files |
| `ioWaitTime` | Time waiting for I/O operations |
| `storageReadBytes` | Bytes read from remote storage |
| `localReadBytes` | Bytes read from local SSD cache |
| `ramReadBytes` | Bytes read from in-memory cache |
| `preloadSplits` | Pre-loaded splits (prefetching) |
| `dataSourceAddSplitTime` | Time managing split assignments |
| `dataSourceReadTime` | Time reading data from the source |

The `storageReadBytes` / `localReadBytes` / `ramReadBytes` breakdown is particularly valuable for cloud environments. If you see most reads coming from `storageReadBytes`, your cache isn't warm. If `ioWaitTime` dominates `wallNanos`, the bottleneck is network I/O, not CPU.

### Spill Metrics

Vanilla Spark tracks spill at the stage level. Gluten tracks it per operator, per phase:

| Metric | What It Measures |
|--------|-----------------|
| `spilledBytes` | Volume of data spilled to disk |
| `spilledRows` | Number of rows spilled |
| `spilledPartitions` | Number of partitions involved in spill |
| `spilledFiles` | Number of spill files created |

For join operators, spill is tracked separately for the build and probe phases (see next section), so you can pinpoint exactly which phase is under memory pressure.

### Dynamic Filter Metrics

Dynamic filters (also called runtime filters) are generated by join operators to prune scan results at runtime. Vanilla Spark has no metrics for this. Gluten tracks the full lifecycle:

| Metric | What It Measures |
|--------|-----------------|
| `numDynamicFiltersProduced` | Runtime filters generated by join build sides |
| `numDynamicFiltersAccepted` | Runtime filters applied to scan operators |
| `numReplacedWithDynamicFilterRows` | Rows eliminated before reaching the join |

If `numDynamicFiltersProduced` > 0 but `numDynamicFiltersAccepted` = 0, the filters were generated but not applied — a sign that the scan and join aren't connected in the way the optimizer expected. If `numReplacedWithDynamicFilterRows` is a large number, runtime filters are saving significant work.

### Join Phase Separation — 20+ Metrics per Join

This is arguably Gluten's most powerful metric enhancement. Vanilla Spark's join operators report a single `buildTime` and `numOutputRows`. Gluten splits every join into its constituent phases with separate metrics for each:

**Build phase:**

| Metric | What It Measures |
|--------|-----------------|
| `hashBuildInputRows` | Rows consumed by the build side |
| `hashBuildOutputRows` | Rows in the hash table |
| `hashBuildWallNanos` | Wall clock time for building |
| `hashBuildPeakMemoryBytes` | Peak memory during build |
| `hashBuildSpilledBytes` | Data spilled during build |
| `hashBuildSpilledRows` | Rows spilled during build |
| `hashBuildSpilledPartitions` | Partitions spilled during build |
| `hashBuildSpilledFiles` | Spill files created during build |

**Probe phase:**

| Metric | What It Measures |
|--------|-----------------|
| `hashProbeInputRows` | Rows consumed by the probe side |
| `hashProbeOutputRows` | Rows output after probing |
| `hashProbeWallNanos` | Wall clock time for probing |
| `hashProbePeakMemoryBytes` | Peak memory during probe |
| `hashProbeSpilledBytes` | Data spilled during probe |
| `hashProbeSpilledRows` | Rows spilled during probe |
| `hashProbeSpilledPartitions` | Partitions spilled during probe |
| `hashProbeSpilledFiles` | Spill files created during probe |

**Pre/post projection:**

| Metric | What It Measures |
|--------|-----------------|
| Pre-projection timing | Expression evaluation time before join |
| Post-projection timing | Expression evaluation time after join |

In vanilla Spark, a slow join gives you almost nothing to work with — you know it's slow, but not why. With Gluten, you can immediately see: is the build phase slow (maybe the build side is too large)? Is the probe phase slow (maybe hash collisions are causing excessive probing)? Is the build phase spilling (memory pressure)? This level of detail changes how you diagnose join performance.

### Write Metrics

| Metric | What It Measures |
|--------|-----------------|
| `physicalWrittenBytes` | Actual bytes written to storage |
| `writeIOTime` | I/O time during writes |
| `numWrittenFiles` | Number of files produced |

## Gluten vs Vanilla Spark vs DataFlint

To put Gluten's metrics in perspective, here's a comparison with vanilla Spark and [DataFlint](https://www.dataflinttool.com/) (a third-party monitoring plugin that wraps Spark operators to add timing):

| Aspect | Vanilla Spark | DataFlint | Gluten |
|--------|--------------|-----------|--------|
| Per-operator timing | 7 operators only | Adds to ~10 more (Python UDF, Window) | **Every operator** |
| Implementation | Built-in SQLMetric | SparkSessionExtensions wrapping | Native C++ engine replacement |
| Spill detail | Per-stage only | Same as Spark | Per-operator, per-phase (build/probe) |
| Dynamic filters | Not tracked | Not tracked | Produced/accepted/rows eliminated |
| Scan I/O detail | `scanTime` only | Same as Spark | `ioWaitTime`, storage/local/RAM breakdown |
| Memory per operator | HashAggregate + Sort only | Same as Spark | Every operator |
| Columnar metrics | Basic (ColumnarToRow) | Same as Spark | `outputVectors`, `outputBytes` per operator |
| Join phase breakdown | None | None | Separate build/probe metrics (20+ each) |

DataFlint and Gluten are not competing approaches — they solve different problems. DataFlint adds observability to an existing JVM-based Spark deployment. Gluten replaces the execution engine entirely, and comprehensive metrics are a byproduct of that architectural choice. If you're already using Gluten for native acceleration, you get the metrics for free.

## Reading Gluten Metrics in the Spark UI

Gluten metrics appear in the same Spark SQL tab because they use the same `SQLMetric` framework. The operator names change (e.g., `HashAggregateExecTransformer` instead of `HashAggregateExec`) but metrics appear in the same side panel when you click on an operator node.

### What to Look For

Here are the key patterns to watch for when reading Gluten metrics:

**Identify the bottleneck operator:**

Look at `wallNanos` on each operator. In a healthy query, scan and join operators dominate. If a `FilterExecTransformer` or `ProjectExecTransformer` has high `wallNanos`, the filter or projection expression itself is expensive — consider simplifying it.

**Diagnose slow joins:**

Compare `hashBuildWallNanos` vs `hashProbeWallNanos`. If the build side dominates, the build input is too large — consider changing the join order or adding a filter to reduce the build side. If the probe side dominates, look at `hashProbeInputRows` — too many probe rows or hash collisions could be the cause.

**Check native predicate pushdown:**

If `skippedSplits` > 0, native file-level pruning is working. If `skippedStrides` > 0, row group or stripe-level pruning within files is working. If both are zero, your predicate isn't being pushed down into the native scan — check if the column type supports pushdown.

**Verify runtime filter effectiveness:**

If `numDynamicFiltersAccepted` > 0, runtime filters from join build sides are being applied to scans. Check `numReplacedWithDynamicFilterRows` to see how many rows were eliminated — a large number means significant I/O savings.

**Detect memory pressure in native engine:**

If `spilledBytes` > 0 on any operator, the native engine is spilling to disk. For joins, check whether the build phase or probe phase is spilling. For aggregations, spill means the grouping cardinality is high. Consider increasing native memory allocation or reducing data volume.

**I/O tier analysis:**

Compare `storageReadBytes`, `localReadBytes`, and `ramReadBytes` on scan operators. In a well-cached environment, you want most reads from `ramReadBytes` or `localReadBytes`. High `storageReadBytes` means you're reading from remote storage (S3, HDFS) — check if your caching layer is configured correctly.

### Accessing via spark-history-cli

Gluten metrics are also available through the REST API and `spark-history-cli`, since they're stored as standard `SQLMetric` values:

```bash
spark-history-cli --json -a <app> sql <id>  # includes Gluten metrics
```

The JSON output will contain all the Gluten-specific metrics alongside vanilla Spark metrics, using the same `{name, value}` format described in [Part 3](/posts/spark/sql-metrics-part3-extension-api/).

## Architectural Implications

Gluten's metrics system offers several insights about extending Spark's observability:

**Engine replacement > wrapping for comprehensive metrics.** Wrapping existing operators (like DataFlint does) can only measure what happens outside the wrapped boundary. Replacing the engine means you control every measurement point inside the execution pipeline. Gluten proves that per-operator timing on every operator is achievable — you just need an engine architecture that doesn't fuse operators together at the JVM level.

**The MetricsUpdater pattern is reusable.** Any native backend can adopt this pattern: define a tree of lightweight, serializable updater objects that mirror the plan, transfer bulk metric arrays via JNI, and walk the tree to update `SQLMetric` accumulators. This pattern cleanly separates the three concerns: metric definition (Layer 1), metric bridging (Layer 2), and metric collection (Layer 3).

**JNI array-based transfer minimizes overhead.** Instead of calling back into the JVM for every metric update, Gluten batches all metrics into `long[]` arrays — one bulk JNI transfer per task. This keeps the metrics overhead negligible even with 60+ metrics per operator.

**Backend-agnostic design through MetricsApi.** The `MetricsApi` abstraction means the Velox backend and ClickHouse backend can define completely different metrics for the same operator type. Adding a new backend (say, DataFusion) would only require implementing the `MetricsApi` interface — no changes to the core bridging code.

---

*In [Part 1](/posts/spark/understanding-sql-metrics/), we covered the five metric types and the complete reference. In [Part 2](/posts/spark/sql-metrics-part2-internals/), we traced the internal lifecycle and AQE's use of shuffle statistics. In [Part 3](/posts/spark/sql-metrics-part3-extension-api/), we explored extension APIs, UI rendering, and the REST API. This bonus Part 4 examined how Apache Gluten extends the metrics system by bridging native engine metrics back to Spark's framework.*
