---
title: "Spark vs Hive: Operators"
date: 2024-01-04
tags: ["spark", "hive", "sql", "operators"]
categories: ["Apache Spark"]
summary: "Comparison of operator behavior differences between Spark SQL and Hive SQL."
showToc: true
---

The differences between Spark and Hive operators can be categorized into several types.

**Compatibility Legend:**
- **\<-\>**: Bi-directional compatibility
- **-\>**: A Spark workload can run the same way in Hive, but not vice versa
- **\<-**: A Hive workload can run the same way in Spark, but not vice versa
- **!=**: Non-compatible

## Supported Operators

| Operator | Spark | Hive | Compatible | Description | Differences |
|:---------|:-----:|:----:|:----------:|:------------|:------------|
| `+` | Y | Y | \<- | Addition | See [Handle Arithmetic Overflow](/posts/spark/spark-vs-hive-functions/#handle-arithmetic-overflow), [Allows Interval Input](/posts/spark/spark-vs-hive-functions/#allows-interval-input) |
