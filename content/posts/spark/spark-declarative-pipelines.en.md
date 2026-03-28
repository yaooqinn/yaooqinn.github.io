---
title: "Spark Declarative Pipelines: A Paradigm Shift for Data Engineering"
date: 2026-03-28
tags: ["spark", "pipelines", "sdp", "streaming", "etl"]
categories: ["Apache Spark"]
summary: "Apache Spark 4.1 introduces Spark Declarative Pipelines (SDP) — a declarative framework that lets you define what your data should look like, not how to compute it. As a Spark PMC Member, here's my take on what this means for data engineering."
showToc: true
---

## From DAGs to Declarations

Every data engineer knows the drill: define Task A, Task B, Task C, draw the arrows, manage the DAG. Airflow does it. Dagster does it. Every orchestrator does it.

But here's the thing: **do you actually care about the DAG, or do you care about your data?**

Apache Spark 4.1 offers a new answer: **Spark Declarative Pipelines (SDP)**. You declare what tables you want and how their contents are derived. The framework handles dependency resolution, execution order, parallelization, error handling, and incremental updates.

This isn't a small feature. It's a fundamental rethinking of how data pipelines should be built.

## Three-Minute Quick Start

Install:

```bash
pip install pyspark[pipelines]
```

Write a pipeline:

```python
from pyspark import pipelines as dp

@dp.materialized_view
def daily_sales():
    return spark.table("orders").groupBy("date").agg({"amount": "sum"})
```

Run it:

```bash
spark-pipelines run
```

No `saveAsTable()`. No `start()`. No `awaitTermination()`. You described "I want a daily sales summary table" and SDP makes it exist.

## Core Concepts

### Flows: The Atomic Unit

A flow describes a complete data movement: where to read, how to transform, where to write.

- **Streaming Flow** → outputs to a Streaming Table (incremental)
- **Batch Flow** → outputs to a Materialized View or Temporary View

### Datasets: What You Actually Care About

**Streaming Table** — continuously updated from sources like Kafka:

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

**Materialized View** — precomputed batch table, fully refreshed:

```python
@dp.materialized_view
def hourly_metrics():
    return (
        spark.table("raw_events")
        .groupBy(window("timestamp", "1 hour"))
        .agg(count("*").alias("event_count"))
    )
```

**Temporary View** — intermediate results scoped to one pipeline run:

```python
@dp.temporary_view
def cleaned_events():
    return spark.table("raw_events").filter("event_type IS NOT NULL")
```

### Automatic Dependency Inference

You don't declare dependencies. SDP analyzes your queries, discovers `spark.table("raw_events")` calls, and builds the dependency graph automatically:

```
raw_events (Streaming Table)
    ↓
cleaned_events (Temporary View)
    ↓
hourly_metrics (Materialized View)
```

## SQL-Native Support

The same pipeline in pure SQL:

```sql
CREATE STREAMING TABLE raw_events
AS SELECT * FROM STREAM kafka_source;

CREATE TEMPORARY VIEW cleaned_events
AS SELECT * FROM raw_events WHERE event_type IS NOT NULL;

CREATE MATERIALIZED VIEW hourly_metrics
AS SELECT window(timestamp, '1 hour'), count(*) AS event_count
FROM cleaned_events GROUP BY 1;
```

Zero learning curve for SQL-first teams.

## Mixed Batch and Streaming

Traditionally, batch and streaming are separate pipelines. SDP lets you mix them in one graph:

```python
@dp.table
def orders():
    return spark.readStream.format("kafka")...

@dp.materialized_view
def daily_summary():
    return spark.table("orders").groupBy("date").count()
```

SDP manages triggers, scheduling, and checkpoints automatically.

## Engineering: Project Structure and CLI

```bash
spark-pipelines init --name my_pipeline   # scaffold
spark-pipelines dry-run                    # validate without I/O
spark-pipelines run                        # execute
```

Configure via `spark-pipeline.yml`:

```yaml
name: my_pipeline
libraries:
  - glob:
      include: transformations/**
catalog: my_catalog
database: my_db
```

The `dry-run` command catches syntax errors, analysis errors, and cyclic dependencies without touching any data — perfect for CI/CD.

## Relationship with Orchestrators

SDP doesn't replace Airflow or Dagster. It handles Spark-level data transformations and dependency management. In production:

```
Airflow/Dagster (top-level orchestration)
    ├── Trigger SDP pipeline (data transformations)
    ├── Call external APIs
    ├── Send notifications
    └── Non-Spark tasks
```

## My Take as a Spark PMC Member

SDP solves several long-standing pain points:

1. **Lower barrier to entry.** No need to understand checkpoint, trigger, outputMode to build reliable streaming pipelines.

2. **Less boilerplate.** No more `writeStream.format().option().start().awaitTermination()` ceremony.

3. **Unified batch and streaming.** Same declarative API, same dependency graph, no more two worlds.

4. **AI-friendly.** Declarative flows are essentially functions — testable, callable, and easy for AI assistants to understand and generate.

SDP's design originates from Databricks' production-proven Delta Live Tables pattern, now brought to open-source Spark. The entire community benefits from best practices validated at massive scale.

## Try It

```bash
pip install pyspark[pipelines]
spark-pipelines init --name hello_sdp
cd hello_sdp
spark-pipelines run
```

Full guide: [Spark Declarative Pipelines Programming Guide](https://spark.apache.org/docs/latest/declarative-pipelines-programming-guide.html)

---

*Spark Declarative Pipelines was introduced in Apache Spark 4.1. Design doc: [SPARK-51727](https://issues.apache.org/jira/browse/SPARK-51727).*
