---
title: "Spark Declarative Pipelines：数据管道的声明式革命"
date: 2026-03-28
tags: ["spark", "pipelines", "sdp", "streaming", "etl"]
categories: ["Apache Spark"]
summary: "Apache Spark 4.1 引入了 Spark Declarative Pipelines（SDP），一个全新的声明式数据管道框架。作为 Spark PMC 成员，我来解读这个框架的设计哲学、核心概念，以及它如何改变数据工程的开发方式。"
showToc: true
---

## 从 DAG 到声明式：一场范式转变

数据工程师最熟悉的工作模式是什么？写一个 DAG。定义任务 A、任务 B、任务 C，然后画出它们之间的依赖关系。Airflow 是这样，Dagster 是这样，大多数编排工具都是这样。

但问题来了：**你真正关心的是数据本身，还是执行 DAG？**

Apache Spark 4.1 给出了一个新答案：**Spark Declarative Pipelines（SDP）**。你只需要声明"我要什么表、表的内容怎么来"，剩下的——依赖推断、执行顺序、并行化、错误处理、增量更新——全部交给框架。

这不是一个小功能。这是 Spark 生态对数据管道开发方式的根本性重新思考。

## 三分钟快速体验

安装只需一行：

```bash
pip install pyspark[pipelines]
```

写一个最简单的管道：

```python
from pyspark import pipelines as dp

@dp.materialized_view
def daily_sales():
    return spark.table("orders").groupBy("date").agg({"amount": "sum"})
```

运行：

```bash
spark-pipelines run
```

没有 `saveAsTable()`。没有 `start()`。没有 `awaitTermination()`。你只是描述了"我想要一个按日期汇总的销售表"，SDP 负责让它存在。

## 核心概念

### Flow：数据流动的最小单元

Flow 是 SDP 的基本构建块。每个 Flow 描述了一个完整的数据流动过程：从哪里读、怎么转换、写到哪里。

SDP 有两种 Flow 语义：

- **Streaming Flow** → 输出到 Streaming Table（增量处理）
- **Batch Flow** → 输出到 Materialized View 或 Temporary View

### Dataset：你真正关心的东西

Dataset 是 Flow 的输出，也是管道中可查询的对象。SDP 提供三种 Dataset 类型：

**Streaming Table** —— 持续增量更新的表，适合从 Kafka 等消息系统摄入数据：

```python
@dp.table
def raw_events():
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "localhost:9092")
        .option("subscribe", "events")
        .load()
    )
```

**Materialized View** —— 预计算的批处理表，完整刷新：

```python
@dp.materialized_view
def hourly_metrics():
    return (
        spark.table("raw_events")
        .groupBy(window("timestamp", "1 hour"))
        .agg(count("*").alias("event_count"))
    )
```

**Temporary View** —— 管道执行期间的中间结果，不持久化，但让依赖图更清晰：

```python
@dp.temporary_view
def cleaned_events():
    return spark.table("raw_events").filter("event_type IS NOT NULL")
```

### 依赖自动推断

这是 SDP 最优雅的设计之一。你不需要显式声明 "hourly_metrics 依赖 raw_events"——SDP 分析你的查询逻辑，发现 `spark.table("raw_events")` 的调用，自动构建依赖图。

```
raw_events (Streaming Table)
    ↓
cleaned_events (Temporary View)
    ↓
hourly_metrics (Materialized View)
```

## SQL 原生支持

SDP 不仅支持 Python，还原生支持 SQL。同样的管道可以这样写：

```sql
CREATE STREAMING TABLE raw_events
AS SELECT * FROM STREAM kafka_source;

CREATE TEMPORARY VIEW cleaned_events
AS SELECT * FROM raw_events WHERE event_type IS NOT NULL;

CREATE MATERIALIZED VIEW hourly_metrics
AS SELECT window(timestamp, '1 hour'), count(*) AS event_count
FROM cleaned_events
GROUP BY 1;
```

对于以 SQL 为主的团队，这意味着零学习成本。

## 批流混合：一个图搞定

传统做法中，批处理和流处理是两套独立的管道。SDP 允许你在同一个依赖图中混合使用：

```python
# 流式摄入
@dp.table
def orders():
    return spark.readStream.format("kafka")...

# 批处理聚合（读取上面的流表）
@dp.materialized_view
def daily_summary():
    return spark.table("orders").groupBy("date").count()
```

SDP 自动管理触发器、调度和检查点，你不需要关心底层的 Structured Streaming 机制。

## 多 Flow 写入同一目标

一个常见场景：你有多个数据源需要写入同一张表。SDP 通过 `append_flow` 优雅地解决：

```python
dp.create_streaming_table("all_orders")

@dp.append_flow(target="all_orders")
def us_orders():
    return spark.readStream.table("orders_us")

@dp.append_flow(target="all_orders")
def eu_orders():
    return spark.readStream.table("orders_eu")
```

## 工程化：项目结构和 CLI

SDP 提供了完整的项目结构和命令行工具：

```bash
# 初始化项目
spark-pipelines init --name my_pipeline

# 验证管道（不读写数据）
spark-pipelines dry-run

# 执行管道
spark-pipelines run
```

项目通过 `spark-pipeline.yml` 配置：

```yaml
name: my_pipeline
libraries:
  - glob:
      include: transformations/**
catalog: my_catalog
database: my_db
configuration:
  spark.sql.shuffle.partitions: "1000"
```

`dry-run` 特别值得一提——它能在不读写任何数据的情况下捕获语法错误、分析错误和循环依赖，这对 CI/CD 集成非常友好。

## 与编排工具的关系

SDP 不是要替代 Airflow 或 Dagster。它专注于 Spark 层面的数据转换和依赖管理。在实际生产中，一个典型的架构是：

```
Airflow/Dagster（顶层编排）
    ├── 触发 SDP 管道（数据转换）
    ├── 调用外部 API
    ├── 发送通知
    └── 其他非 Spark 任务
```

SDP 处理数据转换的重活，编排工具处理端到端的工作流。

## 我的看法

作为 Spark PMC 成员，我认为 SDP 解决了几个长期存在的痛点：

1. **降低入门门槛**。新手不需要理解 Structured Streaming 的 checkpoint、trigger、outputMode 等概念就能写出可靠的流式管道。

2. **减少样板代码**。不再需要 `writeStream.format().option().start().awaitTermination()` 这样的仪式性代码。

3. **统一批流**。同一套声明式 API，同一个依赖图，batch 和 streaming 不再是两个世界。

4. **AI 友好**。声明式的 Flow 本质上是函数，可以被测试、被调用、被 AI 编程助手理解和生成。这对 AI 辅助数据工程意义重大。

SDP 的设计思路源自 Databricks 在生产环境中验证过的 Delta Live Tables（DLT）模式，现在被带入了开源 Spark。这意味着整个社区都能受益于这些经过大规模验证的最佳实践。

## 上手试试

```bash
pip install pyspark[pipelines]
spark-pipelines init --name hello_sdp
cd hello_sdp
spark-pipelines run
```

更多内容请参阅官方编程指南：[Spark Declarative Pipelines Programming Guide](https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html)

---

*Spark Declarative Pipelines 在 Apache Spark 4.1 中引入，相关设计文档见 [SPARK-51727](https://issues.apache.org/jira/browse/SPARK-51727)。*
