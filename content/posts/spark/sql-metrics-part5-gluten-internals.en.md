---
title: "Deep Dive into Spark SQL Metrics (Part 5): Gluten Metrics Internals"
date: 2026-04-02
tags: ["spark", "sql", "metrics", "gluten", "velox", "internals"]
categories: ["Apache Spark"]
summary: "Part 5 of the SQL Metrics deep dive. How Gluten maps Substrait plan nodes to Velox operators, aggregates metrics across pipelines, walks the MetricsUpdaterTree, and handles aggregation sub-phases and shuffle metrics."
showToc: true
---

This is Part 5 of the Spark SQL Metrics deep-dive series:

- [Part 1: Metric types, complete reference, and what they mean](/posts/spark/understanding-sql-metrics/)
- [Part 2: How metrics work internally, and how AQE uses them for runtime decisions](/posts/spark/sql-metrics-part2-internals/)
- [Part 3: Extension APIs, UI rendering, and REST API](/posts/spark/sql-metrics-part3-extension-api/)
- [Part 4: How Gluten extends the metrics system](/posts/spark/sql-metrics-part4-gluten/)
- **Part 5 (this post)**: Gluten metrics internals — node mapping, pipeline aggregation, MetricsUpdaterTree, aggregation sub-phases, and shuffle metrics

In [Part 4](/posts/spark/sql-metrics-part4-gluten/), we saw *what* Gluten's metrics look like from the outside — the 60+ counters that appear in the Spark UI. Now we go deeper: *how* those numbers actually get from native Velox operators back to the JVM. If you've ever stared at a confusing Gluten metrics value and wondered where it came from — or if you're contributing to Gluten and need to add new metrics — this post is for you.

## Substrait Node ID → Velox Operator Mapping

When Gluten converts a Spark plan to a Velox plan via Substrait, every operator in the plan receives a **plan node ID**. This ID is the bridge between the JVM world (where Spark lives) and the C++ world (where Velox executes). The C++ side needs to map these IDs back to metrics arrays so that each native metric value ends up attached to the right Spark operator.

### How `getOrderedNodeIds()` Works

The key function is `getOrderedNodeIds()`. It performs a **post-order traversal** of the Velox plan tree, building an `orderedNodeIds_` vector. The traversal order is critical — it determines which index in the flat metrics arrays corresponds to which operator.

```
Spark Plan → Substrait Plan → Velox PlanNode tree
                                      ↓
                              getOrderedNodeIds() (post-order)
                                      ↓
                              orderedNodeIds_[0] = leaf operator
                              orderedNodeIds_[1] = next operator
                              ...
                              orderedNodeIds_[N] = root operator
```

Why post-order? Because the JVM-side `MetricsUpdaterTree` also walks children before parents. Using the same traversal order on both sides ensures indices stay synchronized without needing an explicit lookup table.

### Special Case: Filter–Project Fusion

Velox fuses `FilterNode → ProjectNode` into a single `FilterProject` operator for better performance. When this happens, the Filter node has no separate runtime metrics — it's been absorbed into the fused operator. Gluten handles this by adding the Filter's plan node ID to `omittedNodeIds_` and emitting **zeros** for its metrics slot. The JVM side sees the zero-filled slot and knows to skip it.

This is important to understand when debugging: if you see a `FilterExecTransformer` with all-zero metrics, it doesn't mean the filter wasn't evaluated — it means Velox fused it with its adjacent Project.

### Special Case: Union

Velox represents a Union as `LocalPartitionNode + LocalExchangeNode + fake ProjectNodes`. This internal representation doesn't map cleanly to a single Spark `UnionExec`. Gluten unwraps this structure to find the real children, ensuring the metrics arrays line up with the Spark plan's structure rather than Velox's internal representation.

## Velox Pipeline Model and Metrics Aggregation

Here's a subtlety that catches many developers off guard: Velox doesn't execute a plan as a single pipeline. It splits the plan into **multiple pipelines** at exchange boundaries (and sometimes at other points like hash join build sides). A single logical operator can have instances running in different pipelines, and each instance collects its own metrics.

### How `toPlanStats()` Aggregates

`toPlanStats(taskStats)` gathers metrics from all pipeline instances and returns a `Map[PlanNodeId → PlanStats]`. Each `PlanStats` contains:

- `operatorStats`: a `Map[SequenceId → OperatorStats]`, where each entry represents one pipeline instance of the operator

When Gluten's `collectMetrics()` iterates through these entries, it writes each pipeline instance into a separate metrics index:

```cpp
for (const auto& entry : stats.operatorStats) {
    // Each entry is one pipeline instance of this operator
    metrics_->get(Metrics::kWallNanos)[metricIndex] = entry.second->cpuWallTiming.wallNanos;
    metricIndex++;
}
```

This means a single Spark operator might map to **multiple metrics indices** in the arrays. For example, a `HashAggregateExec` that appears in both a pre-shuffle partial aggregation pipeline and a post-shuffle final aggregation pipeline will have two separate metrics entries.

### JVM-Side Merging

The JVM-side `MetricsUpdater` handles multi-pipeline entries by fetching all entries from the `relMap` for a given operator and calling `mergeMetrics()`. For timing metrics, this typically sums them. For peak memory, it takes the maximum. The merged result is what you see in the Spark UI — a single set of numbers that represents the operator's total work across all pipelines.

## MetricsUpdaterTree Walking

On the JVM side, `MetricsUtil.scala` orchestrates the entire metrics dispatch with two key methods.

### Building the Tree: `treeifyMetricsUpdaters()`

`treeifyMetricsUpdaters(plan)` builds a `MetricsUpdaterTree` from the SparkPlan. This isn't a simple recursive copy — there are several adjustments:

- **HashJoin handling**: The tree separates build and stream children, since Velox executes them in different pipelines with different metrics
- **SortMergeJoin handling**: Similarly separates buffer and stream children
- **`MetricsUpdater.None` operators**: These are skipped entirely — their child is linked directly to their parent. This happens for operators that Gluten replaces with no-ops (e.g., certain adapter nodes)
- **Children are reversed**: This is crucial. The children list is reversed to match the post-order traversal used by `getOrderedNodeIds()` on the C++ side

### Walking the Tree: `updateTransformerMetricsInternal()`

`updateTransformerMetricsInternal()` walks the `MetricsUpdaterTree` and dispatches metrics to type-specific updaters:

| Updater | Operator | Special Handling |
|---------|----------|-----------------|
| `HashAggregateMetricsUpdater` | HashAggregate | 3-phase sub-metrics (see next section) |
| `JoinMetricsUpdaterBase` | HashJoin | Extra metrics entry for build phase |
| `SortMergeJoinMetricsUpdater` | SortMergeJoin | Buffer/stream phase separation |
| `LimitMetricsUpdater` | Limit over Sort | Skips Limit's own metrics (Velox TopN handles both) |
| Default | Everything else | `mergeMetrics()` → `updateNativeMetrics()` |

For joins, there's an important detail: Velox reports build-phase metrics as an **extra entry** beyond what the `relMap` directly provides. The join updater knows to extract this extra entry and attach it to the build-side metrics, which is why you'll sometimes see accurate build-side timing even though the build and probe happen in different pipelines.

For Limit over Sort, Gluten skips the Limit's own metrics entirely. Velox implements this as a TopN operator that handles both the sorting and the limit in one fused operation, so there's only one set of metrics to report.

After dispatching, the walker recursively processes children with updated operator and metrics indices, ensuring each child picks up from where the parent left off in the flat metrics arrays.

## Aggregation Sub-Phase Metrics

Hash aggregation in Velox is more nuanced than in vanilla Spark. It can execute in up to **three phases**, controlled by `AggregationParams`. Understanding this split is essential for diagnosing aggregation performance.

### Phase 1: Extraction (`extractionNeeded = true`)

Pre-aggregation column extraction — for example, extracting fields from nested structs before they can be grouped and aggregated.

**Metrics:**
- `extractionCpuCount` — CPU time for extraction
- `extractionWallNanos` — Wall clock time for extraction

If extraction time is high relative to total aggregation time, your schema might benefit from flattening nested columns before aggregation.

### Phase 2: Aggregation (always present)

The main hash aggregation work — hashing group keys, looking up or creating groups, and accumulating values.

**Metrics:**
- `aggOutputRows` — Number of output rows (i.e., distinct groups)
- `aggWallNanos` — Wall clock time for aggregation
- `aggPeakMemoryBytes` — Peak memory used by the hash table
- `aggSpilledBytes` — Bytes spilled when memory pressure triggers spilling
- `flushRowCount` — Intermediate rows flushed when the hash table gets too large
- `loadedToValueHook` — Pushdown aggregation count (an optimization where aggregation is pushed into the scan operator)

`flushRowCount` is particularly useful for debugging: a high flush count means the hash table keeps exceeding its memory budget, causing intermediate results to be flushed and re-aggregated. This leads to extra work and slower queries.

### Phase 3: Row Construction (`rowConstructionNeeded = true`)

Post-aggregation row assembly — for example, constructing output struct columns from the aggregated results.

**Metrics:**
- `rowConstructionCpuCount` — CPU time for row construction
- `rowConstructionWallNanos` — Wall clock time for row construction

### How the Phases Map to Metrics Entries

The updater walks the `aggregationMetrics` list in order, consuming one entry per phase:

```
aggregationMetrics[0] → extraction phase (if needed)
aggregationMetrics[1] → aggregation phase
aggregationMetrics[2] → row construction phase (if needed)
```

This three-phase split is unique to Gluten/Velox — vanilla Spark's `HashAggregateExec` reports a single `aggTime` that lumps everything together. With Gluten, you can pinpoint *where* in the aggregation pipeline the time is being spent.

## Shuffle Metrics

Gluten's columnar shuffle has its own metrics layer, and the available metrics vary by **shuffle writer type**. Understanding which writer is in use tells you which metrics to look at — and which tuning knobs are relevant.

### Base Metrics (All Writers)

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `dataSize` | data size | Total shuffle data size |
| `bytesSpilled` | shuffle bytes spilled | Bytes spilled during shuffle |
| `spillTime` | time to spill | Time spent spilling |
| `compressTime` | time to compress | Compression time |
| `decompressTime` | time to decompress | Decompression time |
| `deserializeTime` | time to deserialize | Deserialization time |
| `shuffleWallTime` | shuffle wall time | Total shuffle wall clock time |
| `peakBytes` | peak bytes allocated | Peak memory for shuffle buffers |

### Hash Shuffle Writer Adds

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `splitTime` | time to split | Time splitting rows into partitions |
| `dictionarySize` | dictionary size | Size of dictionary-encoded columns |

### Sort Shuffle Writer Adds

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `sortTime` | time to shuffle sort | Time sorting rows by partition |
| `c2rTime` | time to shuffle c2r | Time converting columnar→row format for sorting |

### RSS (Remote Shuffle Service) Writer Adds

| Metric | Display Name | What It Measures |
|--------|-------------|-----------------|
| `sortTime` | time to shuffle sort | Time sorting rows by partition |

### Diagnosing Shuffle Bottlenecks

The `c2rTime` metric deserves special attention. It represents the overhead of converting columnar batches to row format inside the sort-based shuffle writer. In columnar engines like Velox, data naturally lives in columnar format — converting it to rows for sorting is pure overhead.

If `c2rTime` dominates `shuffleWallTime`, the columnar-to-row conversion is your bottleneck. In this case, switching to hash-based shuffle (which can operate directly on columnar batches) might yield a significant speedup. This is one of the key decisions Gluten users face: hash shuffle is faster for wide tables with many columns, while sort shuffle uses less memory for high-cardinality partition keys.

## Wrapping Up

Gluten's metrics machinery is complex because it bridges two very different execution models — Spark's row-at-a-time Volcano iterator model and Velox's pipeline-parallel vectorized model. The key concepts to remember:

1. **Node ID mapping** via post-order traversal keeps the C++ and JVM sides synchronized
2. **Multi-pipeline aggregation** means a single Spark operator's metrics may come from multiple Velox pipeline instances
3. **MetricsUpdaterTree** dispatches metrics to type-specific updaters that understand each operator's internal structure
4. **Aggregation sub-phases** give you visibility into extraction, aggregation, and row construction separately
5. **Shuffle writer type** determines which metrics are available and which tuning strategies apply

---

*In [Part 1](/posts/spark/understanding-sql-metrics/), we covered the five metric types and the complete reference. In [Part 2](/posts/spark/sql-metrics-part2-internals/), we traced the internal lifecycle and AQE's use of shuffle statistics. In [Part 3](/posts/spark/sql-metrics-part3-extension-api/), we explored extension APIs, UI rendering, and the REST API. In [Part 4](/posts/spark/sql-metrics-part4-gluten/), we examined how Gluten extends the metrics system. In Part 5 (this post), we went deep into the internals — from Substrait-to-Velox node mapping to pipeline aggregation, MetricsUpdaterTree walking, aggregation sub-phases, and shuffle metrics. This concludes the series.*
