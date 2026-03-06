---
title: "Spark vs Hive: Data Types"
date: 2024-01-02
tags: ["spark", "hive", "sql", "data-types"]
categories: ["Apache Spark"]
summary: "A comprehensive comparison of data types supported by Spark SQL and Hive SQL, including compatibility notes."
showToc: true
---

This document provides a comparison of the differences between Spark SQL Data Types and Hive SQL Data Types.

## Supported Data Types

| KEYWORD | Spark | Hive | Compatible | Description | Differences |
|:--------|:-----:|:----:|:----------:|:------------|:------------|
| BOOLEAN | Y | Y | Y | A boolean type. | |
| TINYINT | Y | Y | Y | 1-byte signed integer numbers, [-128, 127]. | |
| BYTE | Y | **N** | **N** | Alias for TINYINT | Hive does not support BYTE |
| SMALLINT | Y | Y | Y | 2-byte signed integer numbers, [-32768,32767]. | |
| SHORT | Y | **N** | **N** | Alias for SMALLINT | |
| INT / INTEGER | Y | Y | Y | 4-byte signed integer numbers, [-2147483648, 2147483647]. | |
| BIGINT | Y | Y | Y | 8-byte signed integer numbers. | |
| LONG | Y | **N** | **N** | Alias for BIGINT | |
| FLOAT / REAL | Y | Y | Y | 4-byte single precision floating point numbers. | |
| DOUBLE | Y | Y | Y | 8-byte double precision floating point numbers. | |
| DOUBLE PRECISION | **N** | Y | **N** | Alias for DOUBLE | |
| DECIMAL / DEC / NUMERIC | Y | Y | Y | Arbitrary precision decimal numbers. | NUMERIC added in Hive since 3.0.0 and Spark since 3.0.0 |
| STRING | Y | Y | Y | Variable-length character string. | |
| CHAR(n) | Y | Y | **N** | Fixed-length character string. | `n` is allowed [1, 255] in Hive, while [1, 2147483647] in Spark |
| CHARACTER(n) | Y | **N** | **N** | Alias for CHAR(n) | Hive does not support CHARACTER(n) |
| VARCHAR(n) | Y | Y | **N** | Variable-length character string. | `n` is allowed [1, 65535] in Hive, while [1, 2147483647] in Spark |
| BINARY | Y | Y | Y | Variable-length binary string. | |
| DATE | Y | Y | Y | A date type. | |
| TIMESTAMP | Y | Y | **N** | A timestamp type. | In Hive, it's `TIMESTAMP WITHOUT TIME ZONE`; in Spark, it's `TIMESTAMP WITH LOCAL TIME ZONE` |
| TIMESTAMP WITH LOCAL TIME ZONE | **N** | Y | **N** | A timestamp with local time zone type | In Spark, `TIMESTAMP` represents this but the keyword is not available |
| TIMESTAMP_LTZ | Y | **N** | **N** | A timestamp with local time zone type | |
| TIMESTAMP_NTZ | Y | **N** | **N** | A timestamp without time zone type | |
| ARRAY\<element_type\> | Y | Y | Y | A collection of elements. | |
| MAP\<key_type, value_type\> | Y | Y | **N** | A collection of key-value pairs. | In Hive, key type is limited to primitive types; in Spark, it can be any type |
| STRUCT\<...\> | Y | Y | Y | A structure of named fields. | |
| UNIONTYPE\<...\> | **N** | Y | **N** | A collection of types. | |
| INTERVAL YEAR TO MONTH / YEAR / MONTH | Y | Y | **N** | Year to month intervals. | |
| INTERVAL DAY / DAY TO HOUR / etc. | Y | Y | **N** | Day to second intervals. | |
| VOID | Y | Y | Y | Null Type | |

> **⚠️ Important:** Hive 3.1 added support for `TIMESTAMP WITH LOCAL TIME ZONE`, and Spark 3.4 added support for `TIMESTAMP_NTZ`. The `TIMESTAMP` type exists in both with **different semantics**. BE CAREFUL when using `TIMESTAMP` in Spark and Hive with a shared Hive Metastore. Another pain point is that Spark supports interoperating with different versions of Hive Metastore, and not all of them support `TIMESTAMP WITH LOCAL TIME ZONE`.

## Type Conversions

### Implicit Type Conversion

*(Work in progress)*

### Explicit Type Conversion

*(Work in progress)*
