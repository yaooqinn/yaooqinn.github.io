---
title: "Deep Dive into Spark SQL Metrics (Part 3): Extension APIs, UI, and REST API"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "api", "datasource-v2"]
categories: ["Apache Spark"]
summary: "Part 3 of the SQL Metrics deep dive. How to extend Spark with custom metrics via the DataSource V2 API, how the UI renders them, and how to query metrics programmatically."
showToc: true
---

This is Part 3 of a 3-part series on Spark SQL Metrics:

- [Part 1: Metric types, complete reference, and what they mean](/posts/spark/understanding-sql-metrics/)
- [Part 2: How metrics work internally, and how AQE uses them for runtime decisions](/posts/spark/sql-metrics-part2-internals/)
- **Part 3 (this post)**: Extension APIs, UI rendering, and REST API

## The DataSource V2 CustomMetric API

In [Part 1](/posts/spark/understanding-sql-metrics/) and [Part 2](/posts/spark/sql-metrics-part2-internals/), we explored Spark's built-in metrics and their internal machinery. But what if you're building a custom connector and need to expose connector-specific numbers — bytes read from your proprietary format, cache hit rates, or throttling counts? Since Spark 3.2, the DataSource V2 API provides a clean extension point for exactly this.

### The Interface Hierarchy

At the core are two interfaces in `org.apache.spark.sql.connector.metric`:

**`CustomMetric`** — defined once in your connector, describes *what* the metric is:

- `name()` — the metric name (must match between `CustomMetric` and `CustomTaskMetric`)
- `description()` — human-readable description shown in the UI
- `aggregateTaskMetrics(long[] taskMetrics)` — you decide how to combine per-task values into a single display string. This is where the connector has full control: you could compute a sum, average, percentile, or anything else.
- Must have a **zero-argument constructor** — Spark instantiates it via reflection on the driver when aggregating.

**`CustomTaskMetric`** — reported by each `PartitionReader` on executors:

- `name()` — must match the corresponding `CustomMetric.name()`
- `value()` — returns a `long` representing the current metric value for this task

Spark ships two convenient base classes so you don't need to implement `aggregateTaskMetrics` from scratch:

| Class | Aggregation Logic | Output Format |
|-------|-------------------|---------------|
| `CustomSumMetric` | Sums all task values | `String.valueOf(sum)` |
| `CustomAvgMetric` | Computes average of task values | `DecimalFormat("#0.000").format(avg)` |

### How to Implement Custom Metrics

**Step 1: Define your metric class.**

Extend one of the built-in base classes or implement `CustomMetric` directly:

```java
public class MyBytesReadMetric extends CustomSumMetric {
    @Override
    public String name() { return "myBytesRead"; }

    @Override
    public String description() { return "bytes read from my source"; }
}
```

**Step 2: Register the metric in your `Scan`.**

Your `Scan` implementation tells Spark which custom metrics your connector supports:

```java
@Override
public CustomMetric[] supportedCustomMetrics() {
    return new CustomMetric[] { new MyBytesReadMetric() };
}
```

**Step 3: Report values from your `PartitionReader`.**

Each `PartitionReader` reports its current metric values whenever Spark calls `currentMetricsValues()`. This is called periodically during task execution and at task completion:

```java
@Override
public CustomTaskMetric[] currentMetricsValues() {
    return new CustomTaskMetric[] {
        new CustomTaskMetric() {
            @Override public String name() { return "myBytesRead"; }
            @Override public long value() { return bytesReadSoFar; }
        }
    };
}
```

That's it — your custom metric will now appear in the Spark UI alongside the built-in ones.

### How Spark Processes Custom Metrics Internally

Behind the scenes, several components work together to make custom metrics flow through the same pipeline as built-in metrics:

1. **Registration**: `DataSourceV2ScanExecBase` calls `scan.supportedCustomMetrics()` during planning and creates `SQLMetric` wrappers via `SQLMetrics.createV2CustomMetric()`. Each wrapper gets a special type string.

2. **Type encoding**: The metric type is stored as `"v2Custom_<fully.qualified.ClassName>"` — for example, `"v2Custom_com.mycompany.MyBytesReadMetric"`. This encoding is constructed by `CustomMetrics.buildV2CustomMetricTypeName()`.

3. **Aggregation**: When `SQLAppStatusListener` receives task metrics during aggregation, it parses the `v2Custom_` prefix, extracts the class name, loads it via reflection, and calls `aggregateTaskMetrics(long[])` on the instantiated object. This is why the zero-arg constructor is required.

4. **Special metric names**: If your `CustomTaskMetric` uses the names `"bytesWritten"` or `"recordsWritten"`, Spark also propagates the values to its internal `TaskOutputMetrics`. This means they will appear in the Executors tab and stage-level I/O summaries, not just in the SQL tab.

### Driver-Side Custom Metrics

Custom metrics aren't limited to executor-side reporting. Your `Scan` can also report metrics from the driver:

- `Scan.reportDriverMetrics()` returns a `CustomTaskMetric[]` array from the driver side
- `DataSourceV2ScanExecBase.postDriverMetrics()` posts them to the metrics system via `SQLMetrics.postDriverMetricUpdates()`

This is useful for metrics like "number of files listed", "partitions pruned", or "metadata cache hits" — things that happen during planning on the driver rather than during data reading on executors.

## How Metrics Are Rendered in the UI

Once metrics are collected and aggregated on the driver, they need to be rendered. The Spark UI's SQL tab has evolved significantly, and understanding the rendering pipeline helps you interpret what you see.

### The Plan Visualization Pipeline

The journey from stored metrics to visual rendering follows this path:

```
SQLAppStatusStore.executionMetrics(id)
    → Map[accumulatorId → formatted String]

ExecutionPage.planVisualization()
    → graph.makeDotFile(metrics)        # compact DOT labels
    → graph.makeNodeDetailsJson(metrics) # full metrics JSON

spark-sql-viz.js
    → renderPlanViz()                    # dagre-d3 graph
    → getNodeDetails()                   # parse JSON
    → updateDetailsPanel()              # side panel on click
    → rerenderWithDetailedLabels()       # optional inline mode
```

The server side prepares two representations: a **DOT file** for the graph layout (with compact node labels) and a **JSON payload** with full metric details. The JavaScript frontend renders the DAG using dagre-d3 and provides interactive metric exploration.

### Compact vs Detailed Mode

The SQL plan visualization supports two display modes:

- **Compact mode** (default since SPARK-55785): Node labels show only operator names. Metrics are available through clicking a node, which opens a side panel with the full metric table. This keeps the graph readable even for complex plans with dozens of operators.

- **Detailed mode** (toggle via checkbox): Metrics are rendered inline inside graph nodes in a 10px font. Useful when you want a printable snapshot of the full plan with all numbers, but can make the graph very wide for operators with many metrics.

- **Stage/Task toggle**: When enabled, adds `(stage X: task Y)` annotations to max values, helping you identify which specific task produced the extreme value — invaluable for debugging skew.

### The Side Panel

When you click a node in compact mode, the side panel shows:

- **Metric name + formatted value** in a clean table layout
- **WholeStageCodegen clusters**: Clicking a cluster node shows all child operator metrics grouped together, so you can see the full picture of what happened inside a single codegen unit
- **Search filter**: For plans with many metrics, a text filter helps you quickly find the metric you care about
- **Description tooltip**: Hover over the operator name in the panel title to see a tooltip that helps disambiguate operators when the same operator type appears multiple times in a plan

## The REST API

The Spark UI is great for visual exploration, but for automation — monitoring dashboards, performance regression tests, or post-hoc analysis scripts — you need programmatic access.

### Endpoint

The primary endpoint for SQL execution metrics is:

```
GET /api/v1/applications/{appId}/sql/{executionId}
```

Query parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `details` | `true` | Include node-level details with metrics |
| `planDescription` | `true` | Include the physical plan text |

### Response Structure

A typical response looks like:

```json
{
  "id": 0,
  "status": "COMPLETED",
  "description": "count at ...",
  "planDescription": "*(1) HashAggregate ...",
  "submissionTime": "2026-04-01T12:00:00Z",
  "duration": 5432,
  "runningJobIds": [],
  "successJobIds": [0, 1],
  "failedJobIds": [],
  "nodes": [
    {
      "nodeId": 0,
      "nodeName": "HashAggregate",
      "wholeStageCodegenId": 1,
      "metrics": [
        {"name": "number of output rows", "value": "5,000"},
        {"name": "peak memory", "value": "total (min, med, max)\n512.0 MiB (128.0 MiB, 128.0 MiB, 128.0 MiB)"},
        {"name": "spill size", "value": "0.0 B"}
      ]
    }
  ],
  "edges": [
    {"fromId": 1, "toId": 0}
  ]
}
```

### Key Things to Note

- **`Metric` is just `{name: String, value: String}`** — the REST API returns the formatted display string, not raw numeric values or metric types. If you need to do arithmetic on metric values, you'll need to parse the formatted strings yourself.

- **`wholeStageCodegenId`** tells you which codegen cluster an operator belongs to. Operators with the same ID were fused into a single generated Java class.

- **`edges`** define the DAG structure as parent→child operator relationships. Combined with `nodeId` values, you can reconstruct the full plan tree programmatically.

- **Listing endpoint**: To get all SQL executions for an application:
  ```
  GET /api/v1/applications/{appId}/sql?offset=0&length=100
  ```
  Supports pagination via `offset` and `length` parameters.

### Accessing via spark-history-cli

For interactive exploration, `spark-history-cli` wraps the REST API with convenient commands:

```bash
# Structured JSON output
spark-history-cli --json -a <app> sql          # list all SQL executions
spark-history-cli --json -a <app> sql <id>     # single execution with metrics

# Plan text
spark-history-cli -a <app> sql-plan <id>           # full plan
spark-history-cli -a <app> sql-plan <id> --view final  # post-AQE plan
```

## Practical Examples

### Using Spark Listener to Capture Metrics Programmatically

If you want to react to metrics in real time — for example, logging slow queries or triggering alerts — you can register a `QueryExecutionListener`:

```scala
spark.listenerManager.register(new QueryExecutionListener {
  override def onSuccess(funcName: String, qe: QueryExecution, durationNs: Long): Unit = {
    val metrics = qe.executedPlan.collectLeaves().flatMap(_.metrics)
    metrics.foreach { case (name, metric) =>
      println(s"$name: ${metric.value}")
    }
  }

  override def onFailure(funcName: String, qe: QueryExecution, exception: Exception): Unit = {}
})
```

This listener fires after every successful query execution and gives you access to the executed physical plan, where you can traverse operators and read their metric values directly.

### Accessing Metrics from DataFrame Execution

For ad-hoc debugging or REPL-based exploration, you can access metrics after executing a query through the status store:

```scala
val df = spark.sql("SELECT count(*) FROM my_table")
df.collect()

// Access the last execution's metrics
val lastExec = spark.sharedState.statusStore.executionsList().last
val metrics = spark.sharedState.statusStore.executionMetrics(lastExec.executionId)
metrics.foreach { case (accId, value) => println(s"$accId: $value") }
```

This approach is useful for integration tests where you want to assert that a specific optimization was applied (e.g., "number of files pruned" > 0) or for notebooks where you want to inspect performance without switching to the UI.

## Series Conclusion

This concludes our 3-part deep dive into Spark SQL Metrics:

- In **[Part 1](/posts/spark/understanding-sql-metrics/)**, we established the foundation: the five metric types (`sum`, `size`, `timing`, `nanoTiming`, `average`), the `total (min, med, max)` aggregation format, and a comprehensive reference of 100+ metrics across all operators.

- In **[Part 2](/posts/spark/sql-metrics-part2-internals/)**, we traced the internal lifecycle — how `AccumulatorV2` values flow from executor tasks to the driver, how `SQLAppStatusListener` aggregates them, and how Adaptive Query Execution uses shuffle statistics (not SQL metrics) to make runtime decisions like partition coalescing, skew join optimization, and local shuffle reads.

- In **Part 3 (this post)**, we covered the extension points: how connector developers can define custom metrics via the DataSource V2 API, how the UI renders plans and metrics through the DOT/JSON/dagre-d3 pipeline, and how to query metrics programmatically via the REST API and Spark listeners.

Together, these three perspectives — **what metrics measure**, **how they work internally**, and **how to extend and access them** — give you the complete picture needed to effectively use SQL metrics for performance debugging, monitoring, and connector development.

*In [Part 1](/posts/spark/understanding-sql-metrics/), we covered the five metric types and the complete reference. In [Part 2](/posts/spark/sql-metrics-part2-internals/), we traced the internal lifecycle and AQE's use of shuffle statistics. This concludes the series.*
