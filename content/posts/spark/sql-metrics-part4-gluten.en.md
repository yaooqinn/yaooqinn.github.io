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

## How Gluten's Native Engine Produces Metrics

Apache Gluten replaces the JVM execution engine with a native C++ engine — either [Velox](https://github.com/facebookincubator/velox) or [ClickHouse](https://github.com/ClickHouse/ClickHouse). Because native operators execute independently (not fused by JVM codegen), each C++ operator is a separate function call with its own timing infrastructure. As a natural consequence, Gluten surfaces **60+ metrics** per operator, including wall clock time, per-phase join metrics, native spill tracking, dynamic filter statistics, and I/O breakdowns by storage tier.

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

| Metric | Display Name | Type | What It Measures |
|--------|-------------|------|-----------------|
| `wallNanos` | time of *{operator}* | nsTiming | Wall clock time per operator |
| `cpuCount` | cpu wall time count | sum | Number of `getOutput()` invocations (batch count) |
| `peakMemoryBytes` | peak memory bytes | size | Peak memory usage |
| `numMemoryAllocations` | number of memory allocations | sum | Memory allocation count |
| `outputRows` | number of output rows | sum | Output row count |
| `outputVectors` | number of output vectors | sum | Output vector (batch) count |
| `outputBytes` | number of output bytes | size | Output data volume in columnar format |
| `loadLazyVectorTime` | time to load lazy vectors | timing | Time loading lazy-evaluated vectors |

Note: `wallNanos` uses an operator-specific display name — "time of filter", "time of sort", "time of scan and filter", "time of project", etc.

Having `wallNanos` on every operator makes it straightforward to identify bottleneck operators in native execution.

### Understanding wallNanos and cpuCount

These two metrics deserve special attention because they are the most important for performance analysis.

Both originate from Velox's `CpuWallTiming` structure, which is collected via RAII timers (`DeltaCpuWallTimer`) wrapping each operator's `getOutput()` call:

```cpp
struct CpuWallTiming {
  uint64_t count;      // Number of getOutput() invocations (batch count)
  uint64_t wallNanos;  // Total wall-clock time (steady_clock, nanoseconds)
  uint64_t cpuNanos;   // Total CPU time (CLOCK_THREAD_CPUTIME_ID, nanoseconds)
};
```

**wallNanos** — measured with `std::chrono::steady_clock`. Captures total real elapsed time, **including** any time the operator spends blocked waiting for its child to produce data, I/O waits, or thread scheduling delays.

**cpuCount** — despite the name, this is actually the **invocation count** (number of `getOutput()` calls = number of batches processed), not CPU time. The Gluten JNI bridge maps `CpuWallTiming.count` to the `cpuCount` metric.

**How to interpret:**

| Scenario | wallNanos | cpuCount | What It Means |
|----------|:---------:|:--------:|---------------|
| Large data, even work | High | High | Many batches processed, expected |
| Few batches, each slow | High | Low | Possible skew or complex per-batch work |
| Leaf operator (scan) | High | — | Mostly I/O time (check `ioWaitTime` separately) |
| Middle operator (filter) | High | — | Includes wait for child — compare with child's wallNanos |

**Important caveat — wallNanos includes child waiting:**

Because `wallNanos` wraps the entire `getOutput()` call, a parent operator's wallNanos includes time spent blocked waiting for its child to produce data. This means:

- For a **leaf operator** (scan): wallNanos ≈ I/O + compute time
- For a **middle operator** (filter above a scan): wallNanos = own compute + child's scan time
- **You cannot simply sum wallNanos across all operators** — that would double-count

To isolate an operator's own contribution, compare its wallNanos with its child's wallNanos. The difference is the operator's own processing time. Velox also tracks some I/O-specific metrics separately (`ioWaitTime`, `dataSourceReadTime`) to help separate pure I/O from compute.

### Scan-Specific Metrics

Vanilla Spark's scan operators have `scanTime` and `numFiles`. Gluten goes much deeper:

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `skippedSplits` / `processedSplits` | number of skipped/processed splits | File split pruning effectiveness |
| `skippedStrides` / `processedStrides` | number of skipped/processed row groups | Row group/stripe pruning within files |
| `ioWaitTime` | io wait time | Time waiting for I/O operations |
| `storageReadBytes` | storage read bytes | Bytes read from remote storage |
| `localReadBytes` | Bytes read from local SSD cache |
| `ramReadBytes` | Bytes read from in-memory cache |
| `preloadSplits` | Pre-loaded splits (prefetching) |
| `dataSourceAddSplitTime` | Time managing split assignments |
| `dataSourceReadTime` | Time reading data from the source |

The `storageReadBytes` / `localReadBytes` / `ramReadBytes` breakdown is particularly valuable for cloud environments. If you see most reads coming from `storageReadBytes`, your cache isn't warm. If `ioWaitTime` dominates `wallNanos`, the bottleneck is network I/O, not CPU.

### Spill Metrics

Vanilla Spark tracks spill at the stage level. Gluten tracks it per operator, per phase:

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `spilledBytes` | bytes written for spilling | Volume of data spilled to disk |
| `spilledRows` | total rows written for spilling | Number of rows spilled |
| `spilledPartitions` | total spilled partitions | Number of partitions involved in spill |
| `spilledFiles` | total spilled files | Number of spill files created |

For join operators, spill is tracked separately for the build and probe phases (see next section), so you can pinpoint exactly which phase is under memory pressure.

### Dynamic Filter Metrics

Dynamic filters (also called runtime filters) are generated by join operators to prune scan results at runtime. Vanilla Spark has no metrics for this. Gluten tracks the full lifecycle:

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `numDynamicFiltersProduced` | number of dynamic filters produced | Runtime filters generated by join build sides |
| `numDynamicFiltersAccepted` | number of dynamic filters accepted | Runtime filters applied to scan operators |
| `numReplacedWithDynamicFilterRows` | number of replaced with dynamic filter rows | Rows eliminated before reaching the join |

If `numDynamicFiltersProduced` > 0 but `numDynamicFiltersAccepted` = 0, the filters were generated but not applied — a sign that the scan and join aren't connected in the way the optimizer expected. If `numReplacedWithDynamicFilterRows` is a large number, runtime filters are saving significant work.

### Join Phase Separation — 20+ Metrics per Join

This is arguably Gluten's most powerful metric enhancement. Vanilla Spark's join operators report a single `buildTime` and `numOutputRows`. Gluten splits every join into its constituent phases with separate metrics for each:

**Build phase:**

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `hashBuildInputRows` | number of hash build input rows | Rows consumed by the build side |
| `hashBuildOutputRows` | number of hash build output rows | Rows in the hash table |
| `hashBuildWallNanos` | time of hash build | Wall clock time for building |
| `hashBuildPeakMemoryBytes` | hash build peak memory bytes | Peak memory during build |
| `hashBuildSpilledBytes` | hash build spilled bytes | Data spilled during build |
| `hashBuildSpilledRows` | hash build spilled rows | Rows spilled during build |
| `hashBuildSpilledPartitions` | hash build spilled partitions | Partitions spilled during build |
| `hashBuildSpilledFiles` | hash build spilled files | Spill files created during build |

**Probe phase:**

| Metric | What It Measures |
| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `hashProbeInputRows` | number of hash probe input rows | Rows consumed by the probe side |
| `hashProbeOutputRows` | number of hash probe output rows | Rows output after probing |
| `hashProbeWallNanos` | time of hash probe | Wall clock time for probing |
| `hashProbePeakMemoryBytes` | hash probe peak memory bytes | Peak memory during probe |
| `hashProbeSpilledBytes` | hash probe spilled bytes | Data spilled during probe |
| `hashProbeSpilledRows` | hash probe spilled rows | Rows spilled during probe |
| `hashProbeSpilledPartitions` | hash probe spilled partitions | Partitions spilled during probe |
| `hashProbeSpilledFiles` | hash probe spilled files | Spill files created during probe |

**Pre/post projection:**

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `streamPreProjectionWallNanos` | time of stream preProjection | Expression evaluation time on the stream (probe) side before join |
| `streamPreProjectionCpuCount` | stream preProject cpu wall time count | Batch count for stream pre-projection |
| `buildPreProjectionWallNanos` | time to build preProjection | Expression evaluation time on the build side before join |
| `buildPreProjectionCpuCount` | preProject cpu wall time count | Batch count for build pre-projection |
| `postProjectionWallNanos` | time of postProjection | Expression evaluation time after join |
| `postProjectionCpuCount` | postProject cpu wall time count | Batch count for post-projection |

In vanilla Spark, a slow join gives you almost nothing to work with — you know it's slow, but not why. With Gluten, you can immediately see: is the build phase slow (maybe the build side is too large)? Is the probe phase slow (maybe hash collisions are causing excessive probing)? Is the build phase spilling (memory pressure)? This level of detail changes how you diagnose join performance.

### Write Metrics

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `physicalWrittenBytes` | number of written bytes | Actual bytes written to storage |
| `writeIOTime` / `writeIONanos` | time of write IO | I/O time during writes |
| `numWrittenFiles` | number of written files | Number of files produced |

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

**Engine replacement provides comprehensive metrics naturally.** When the engine controls every operator's execution, it can measure every boundary. Each C++ operator is a separate function call with its own start and end timestamps — per-operator timing on every operator is achievable without any workarounds.

**The MetricsUpdater pattern is reusable.** Any native backend can adopt this pattern: define a tree of lightweight, serializable updater objects that mirror the plan, transfer bulk metric arrays via JNI, and walk the tree to update `SQLMetric` accumulators.

**JNI array-based transfer minimizes overhead.** Instead of calling back into the JVM for every metric update, Gluten batches all metrics into `long[]` arrays — one bulk JNI transfer per task. This keeps the metrics overhead negligible even with 60+ metrics per operator.

**Backend-agnostic design through MetricsApi.** The `MetricsApi` abstraction means the Velox backend and ClickHouse backend can define completely different metrics for the same operator type. Adding a new backend (say, DataFusion) would only require implementing the `MetricsApi` interface — no changes to the core bridging code.

---

*In [Part 1](/posts/spark/understanding-sql-metrics/), we covered the five metric types and the complete reference. In [Part 2](/posts/spark/sql-metrics-part2-internals/), we traced the internal lifecycle and AQE's use of shuffle statistics. In [Part 3](/posts/spark/sql-metrics-part3-extension-api/), we explored extension APIs, UI rendering, and the REST API. This bonus Part 4 examined how Apache Gluten extends the metrics system by bridging native engine metrics back to Spark's framework.*
