---
title: "深入 Spark SQL Metrics（第三部分）：扩展 API、UI 渲染与 REST API"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "api", "datasource-v2"]
categories: ["Apache Spark"]
summary: "SQL Metrics 三部曲的第三部分。如何通过 DataSource V2 API 扩展自定义指标、UI 如何渲染指标、以及如何通过 REST API 编程查询指标。"
showToc: true
---

这是 Spark SQL Metrics 深度解析的三部曲：

- [第一部分：指标类型、完整参考和含义](/zh/posts/spark/understanding-sql-metrics/)
- [第二部分：内部实现机制，以及 AQE 如何利用指标做出运行时决策](/zh/posts/spark/sql-metrics-part2-internals/)
- **第三部分（本文）**：扩展 API、UI 渲染和 REST API

## DataSource V2 CustomMetric API

在[第一部分](/zh/posts/spark/understanding-sql-metrics/)和[第二部分](/zh/posts/spark/sql-metrics-part2-internals/)中，我们探索了 Spark 内置指标及其内部机制。但如果你正在构建自定义连接器，需要暴露连接器特有的数据——例如从专有格式读取的字节数、缓存命中率或限流次数，该怎么办？从 Spark 3.2 开始，DataSource V2 API 提供了一个干净的扩展点来满足这一需求。

### 接口层次结构

核心是 `org.apache.spark.sql.connector.metric` 包中的两个接口：

**`CustomMetric`** —— 在连接器中定义一次，描述*指标是什么*：

- `name()` —— 指标名称（必须与 `CustomTaskMetric` 匹配）
- `description()` —— 人类可读的描述，在 UI 中显示
- `aggregateTaskMetrics(long[] taskMetrics)` —— 由你决定如何将各任务的值合并为一个显示字符串。连接器在此拥有完全的控制权：你可以计算总和、平均值、百分位数或任何其他聚合方式。
- 必须有一个**无参构造函数** —— Spark 在驱动端聚合时通过反射实例化它。

**`CustomTaskMetric`** —— 由每个 `PartitionReader` 在 Executor 上报告：

- `name()` —— 必须与对应 `CustomMetric.name()` 匹配
- `value()` —— 返回一个 `long`，表示该任务的当前指标值

Spark 提供了两个便利的基类，让你无需从头实现 `aggregateTaskMetrics`：

| 类 | 聚合逻辑 | 输出格式 |
|---|---------|---------|
| `CustomSumMetric` | 求所有任务值的和 | `String.valueOf(sum)` |
| `CustomAvgMetric` | 计算任务值的平均值 | `DecimalFormat("#0.000").format(avg)` |

### 如何实现自定义指标

**第一步：定义指标类。**

继承内置基类或直接实现 `CustomMetric` 接口：

```java
public class MyBytesReadMetric extends CustomSumMetric {
    @Override
    public String name() { return "myBytesRead"; }

    @Override
    public String description() { return "bytes read from my source"; }
}
```

**第二步：在 `Scan` 中注册指标。**

你的 `Scan` 实现告诉 Spark 连接器支持哪些自定义指标：

```java
@Override
public CustomMetric[] supportedCustomMetrics() {
    return new CustomMetric[] { new MyBytesReadMetric() };
}
```

**第三步：在 `PartitionReader` 中报告值。**

每个 `PartitionReader` 在 Spark 调用 `currentMetricsValues()` 时报告当前指标值。此方法在任务执行期间被周期性调用，以及在任务完成时调用：

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

就是这样——你的自定义指标现在将在 Spark UI 中与内置指标一起显示。

### Spark 内部如何处理自定义指标

在幕后，多个组件协同工作，使自定义指标通过与内置指标相同的管道流转：

1. **注册**：`DataSourceV2ScanExecBase` 在规划阶段调用 `scan.supportedCustomMetrics()` 并通过 `SQLMetrics.createV2CustomMetric()` 创建 `SQLMetric` 包装器。每个包装器都有一个特殊的类型字符串。

2. **类型编码**：指标类型存储为 `"v2Custom_<完整类名>"` —— 例如 `"v2Custom_com.mycompany.MyBytesReadMetric"`。这个编码由 `CustomMetrics.buildV2CustomMetricTypeName()` 构造。

3. **聚合**：当 `SQLAppStatusListener` 在聚合时接收到任务指标时，它解析 `v2Custom_` 前缀，提取类名，通过反射加载类，并调用 `aggregateTaskMetrics(long[])`。这就是为什么需要无参构造函数。

4. **特殊指标名**：如果你的 `CustomTaskMetric` 使用 `"bytesWritten"` 或 `"recordsWritten"` 作为名称，Spark 还会将这些值传播到内部的 `TaskOutputMetrics`。这意味着它们不仅会出现在 SQL 标签页，还会出现在 Executors 标签页和阶段级 I/O 摘要中。

### 驱动端自定义指标

自定义指标不仅限于 Executor 端报告。你的 `Scan` 还可以从驱动端报告指标：

- `Scan.reportDriverMetrics()` 从驱动端返回 `CustomTaskMetric[]` 数组
- `DataSourceV2ScanExecBase.postDriverMetrics()` 通过 `SQLMetrics.postDriverMetricUpdates()` 将它们发送到指标系统

这对于"列出的文件数"、"裁剪的分区数"或"元数据缓存命中次数"等指标非常有用——这些事情发生在驱动端的规划阶段，而非 Executor 上的数据读取阶段。

## UI 中的指标渲染

指标在驱动端被收集和聚合后，需要被渲染。Spark UI 的 SQL 标签页已经有了显著的演进，理解渲染管道有助于你解读所看到的内容。

### 计划可视化管道

从存储的指标到视觉渲染的路径如下：

```
SQLAppStatusStore.executionMetrics(id)
    → Map[accumulatorId → formatted String]

ExecutionPage.planVisualization()
    → graph.makeDotFile(metrics)        # 紧凑的 DOT 标签
    → graph.makeNodeDetailsJson(metrics) # 完整指标 JSON

spark-sql-viz.js
    → renderPlanViz()                    # dagre-d3 图形
    → getNodeDetails()                   # 解析 JSON
    → updateDetailsPanel()              # 点击后的侧边面板
    → rerenderWithDetailedLabels()       # 可选的内联模式
```

服务端准备两种表示：用于图形布局的 **DOT 文件**（使用紧凑的节点标签）和包含完整指标详情的 **JSON 数据**。JavaScript 前端使用 dagre-d3 渲染 DAG 并提供交互式指标探索。

### 紧凑模式与详细模式

SQL 计划可视化支持两种显示模式：

- **紧凑模式**（自 SPARK-55785 起默认）：节点标签仅显示算子名称。点击节点可打开侧边面板，查看完整的指标表。即使对于包含数十个算子的复杂计划，图形也保持可读性。

- **详细模式**（通过复选框切换）：指标以 10px 字号内联渲染在图形节点内。当你需要一个包含所有数字的完整计划的可打印快照时很有用，但对于指标较多的算子可能会使图形变得很宽。

- **阶段/任务切换**：启用后，会在最大值旁添加 `(stage X: task Y)` 标注，帮助你定位产生极端值的具体任务——这对调试数据倾斜非常有价值。

### 侧边面板

在紧凑模式下点击节点时，侧边面板显示：

- 清晰的表格布局中的**指标名称 + 格式化后的值**
- **WholeStageCodegen 集群**：点击集群节点会显示所有子算子的指标分组，让你看到单个代码生成单元内发生的全貌
- **搜索过滤器**：对于指标众多的计划，文本过滤器帮助你快速找到关心的指标
- **描述提示信息**：将鼠标悬停在面板标题中的算子名称上可看到提示信息，当计划中出现多个相同类型的算子时有助于区分

## REST API

Spark UI 非常适合可视化探索，但对于自动化——监控仪表板、性能回归测试或事后分析脚本——你需要编程访问。

### 端点

SQL 执行指标的主要端点是：

```
GET /api/v1/applications/{appId}/sql/{executionId}
```

查询参数：

| 参数 | 默认值 | 描述 |
|-----|-------|------|
| `details` | `true` | 包含节点级详情和指标 |
| `planDescription` | `true` | 包含物理计划文本 |

### 响应结构

典型的响应如下：

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

### 关键要点

- **`Metric` 仅仅是 `{name: String, value: String}`** —— REST API 返回的是格式化后的显示字符串，而非原始数值或指标类型。如果你需要对指标值做算术运算，必须自行解析格式化字符串。

- **`wholeStageCodegenId`** 表示算子所属的代码生成集群。具有相同 ID 的算子被融合到同一个生成的 Java 类中。

- **`edges`** 以父→子算子关系定义 DAG 结构。结合 `nodeId` 值，你可以编程重建完整的计划树。

- **列表端点**：获取应用程序的所有 SQL 执行：
  ```
  GET /api/v1/applications/{appId}/sql?offset=0&length=100
  ```
  通过 `offset` 和 `length` 参数支持分页。

### 通过 spark-history-cli 访问

对于交互式探索，`spark-history-cli` 封装了 REST API，提供便捷的命令：

```bash
# 结构化 JSON 输出
spark-history-cli --json -a <app> sql          # 列出所有 SQL 执行
spark-history-cli --json -a <app> sql <id>     # 单次执行及其指标

# 计划文本
spark-history-cli -a <app> sql-plan <id>           # 完整计划
spark-history-cli -a <app> sql-plan <id> --view final  # AQE 后的最终计划
```

## 实用示例

### 使用 Spark Listener 编程捕获指标

如果你想实时响应指标——例如记录慢查询或触发告警——可以注册一个 `QueryExecutionListener`：

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

这个监听器在每次成功的查询执行后触发，让你可以访问已执行的物理计划，遍历算子并直接读取它们的指标值。

### 从 DataFrame 执行中访问指标

对于临时调试或 REPL 交互式探索，你可以在执行查询后通过状态存储访问指标：

```scala
val df = spark.sql("SELECT count(*) FROM my_table")
df.collect()

// 访问最近一次执行的指标
val lastExec = spark.sharedState.statusStore.executionsList().last
val metrics = spark.sharedState.statusStore.executionMetrics(lastExec.executionId)
metrics.foreach { case (accId, value) => println(s"$accId: $value") }
```

这种方式对于集成测试中断言特定优化是否生效（例如"裁剪的文件数" > 0）或在 Notebook 中不切换 UI 即可检查性能非常有用。

## 系列总结

本文是 Spark SQL Metrics 三部曲深度解析的最终篇：

- 在**[第一部分](/zh/posts/spark/understanding-sql-metrics/)**中，我们建立了基础：五种指标类型（`sum`、`size`、`timing`、`nanoTiming`、`average`）、`total (min, med, max)` 聚合格式，以及覆盖所有算子的 100+ 指标的完整参考。

- 在**[第二部分](/zh/posts/spark/sql-metrics-part2-internals/)**中，我们追踪了内部生命周期——`AccumulatorV2` 值如何从 Executor 任务流向驱动端，`SQLAppStatusListener` 如何聚合它们，以及自适应查询执行（AQE）如何利用 Shuffle 统计信息（而非 SQL 指标）做出运行时决策，包括分区合并、倾斜 Join 优化和本地 Shuffle 读取。

- 在**第三部分（本文）**中，我们介绍了扩展点：连接器开发者如何通过 DataSource V2 API 定义自定义指标，UI 如何通过 DOT/JSON/dagre-d3 管道渲染计划和指标，以及如何通过 REST API 和 Spark Listener 编程查询指标。

这三个视角——**指标测量什么**、**内部如何工作**、**如何扩展和访问它们**——共同构成了有效使用 SQL 指标进行性能调试、监控和连接器开发所需的完整知识体系。

*在[第一部分](/zh/posts/spark/understanding-sql-metrics/)中，我们介绍了五种指标类型和完整参考。在[第二部分](/zh/posts/spark/sql-metrics-part2-internals/)中，我们追踪了内部生命周期和 AQE 对 Shuffle 统计信息的使用。本文为系列的终章。*
