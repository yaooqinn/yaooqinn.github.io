---
title: "Spark vs Hive: Functions"
date: 2024-01-03
tags: ["spark", "hive", "sql", "functions"]
categories: ["Apache Spark"]
summary: "Detailed comparison of function behavior differences between Spark SQL and Hive SQL, including overflow handling and NULL semantics."
showToc: true
---

The differences between Spark and Hive functions can be categorized into several types.

**Compatibility Legend:**
- **\<-\>**: Bi-directional compatibility
- **-\>**: A Spark workload can run the same way in Hive, but not vice versa
- **\<-**: A Hive workload can run the same way in Spark, but not vice versa
- **!=**: Non-compatible

## Compatibility Details

| Function | Spark | Hive | Compatible | Description | Differences |
|:---------|:-----:|:----:|:----------:|:------------|:------------|
| [ABS](https://spark.apache.org/docs/latest/api/sql/index.html#abs)(expr) | Y | Y | \<- | Returns the absolute value of the numeric value | See [Handle Arithmetic Overflow](#handle-arithmetic-overflow), [Allows Interval Input](#allows-interval-input) |
| [BIN](https://spark.apache.org/docs/latest/api/sql/index.html#bin)(expr) | Y | Y | \<-\> | Returns the number in binary format | |
| [DECODE](https://spark.apache.org/docs/latest/api/sql/index.html#decode)(bin, charset) | Y | Y | != | Decodes the first argument using the second argument character set | **bin**: Spark supports both string and binary values, Hive supports only binary. **charset**: limited to 'US-ASCII', 'ISO-8859-1', 'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-16' since Spark 4.0. **Malformed input**: Spark produces mojibake, Hive raises an error. |
| [DECODE](https://spark.apache.org/docs/latest/api/sql/index.html#decode)(expr, search, result [, ...] [, default]) | Y | **N** | != | Compares expr to each search value in order | Derived from [Oracle DECODE](https://docs.oracle.com/en/database/oracle/oracle-database/23/sqlrf/DECODE.html); Hive does not have it. |
| [E](https://spark.apache.org/docs/latest/api/sql/index.html#e)() | Y | Y | \<-\> | Returns the value of the base of the natural logarithm | |
| [ENCODE](https://spark.apache.org/docs/latest/api/sql/index.html#encode)(str, charset) | Y | Y | != | Encode the first argument using the second argument character set | **str**: Spark supports implicit conversion to string, Hive supports only string. **charset**: limited since Spark 4.0. **Malformed input**: Spark produces mojibake, Hive raises an error. |
| [FACTORIAL](https://spark.apache.org/docs/latest/api/sql/index.html#factorial)(expr) | Y | Y | != | Returns the factorial of expr. expr is [0..20], otherwise null. | Spark supports integral and fractional types; Hive supports only integral types. |
| [GREATEST](https://spark.apache.org/docs/latest/api/sql/index.html#greatest)(expr, ...) | Y | Y | != | Returns the greatest value of all parameters | Spark and Hive(\<2.0.0) skip NULLs; Hive(\>2.0.0) returns NULL if any parameter is NULL. |
| [HASH](https://spark.apache.org/docs/latest/api/sql/index.html#hash)(expr, ...) | Y | Y | != | Returns a hash value of the arguments | Different hash algorithms produce different results. |
| [LEAST](https://spark.apache.org/docs/latest/api/sql/index.html#least)(expr, ...) | Y | Y | != | Returns the least value of all parameters | Same differences as GREATEST. |
| [NEGATIVE](https://spark.apache.org/docs/latest/api/sql/index.html#negative)(expr) | Y | Y | N | Returns the negated value of expr. | See [Handle Arithmetic Overflow](#handle-arithmetic-overflow), [Allows Interval Input](#allows-interval-input) |
| [POSITIVE](https://spark.apache.org/docs/latest/api/sql/index.html#positive)(expr) | Y | Y | \<- | Returns the value of the argument | See [Allows Interval Input](#allows-interval-input) |
| [PI](https://spark.apache.org/docs/latest/api/sql/index.html#pi)() | Y | Y | \<-\> | Returns the value of PI | |

---

## Generic Differences

### Handle Arithmetic Overflow

An arithmetic overflow occurs when a calculation exceeds the maximum size that can be stored in the data type being used.

#### Produces Overflowed Values

When `spark.sql.ansi.enabled` is set to `false` (default before Spark 4.0.0, `true` since 4.0.0), Spark uses this semantics to handle overflow in most arithmetic operations:

```sql
> SELECT 127Y + 1Y
-128
```

#### Produces NULL

Spark provides `try_` prefixed variants to handle overflow with NULL output:

```sql
> SELECT try_add(127Y, 1Y)
NULL
```

#### Throws Errors

When `spark.sql.ansi.enabled` is set to `true` (default since Spark 4.0.0):

```sql
> SELECT 127Y + 1Y
org.apache.spark.SparkArithmeticException: [BINARY_ARITHMETIC_OVERFLOW]
127S + 1S caused overflow. SQLSTATE: 22003
```

#### Widens Data Type

Hive uses this semantics — the result type is promoted:

```sql
> SELECT 127Y + 1Y
-- The result type is promoted from tinyint to smallint
128
```

### Handle NULL Input

*(Work in progress)*

### Allows Interval Input

Spark allows interval types as input to most arithmetic operations (e.g. `ABS`, `POSITIVE`, `NEGATIVE`), while Hive does not.

```sql
> SELECT ABS(- INTERVAL 1-1 YEAR TO MONTH)
INTERVAL 1-1 YEAR TO MONTH
```
