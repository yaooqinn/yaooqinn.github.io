---
title: "Unconventional Usages of Apache Spark"
date: 2024-01-05
tags: ["spark", "tips"]
categories: ["Apache Spark"]
summary: "Creative and unconventional ways to use Apache Spark tooling, including using spark-class as a shorthand for java -cp."
showToc: true
---

## Shorthand for `java -cp`

### Compress Tool

The `bin/spark-class` wrapper can be used as a convenient shorthand for `java -cp`, leveraging Spark's classpath:

```shell {linenos=true,hl_lines=[3]}
# java -cp jars/compress-lzf-1.1.2.jar com.ning.compress.lzf.LZF -c README.md

bin/spark-class com.ning.compress.lzf.LZF -c README.md
```
