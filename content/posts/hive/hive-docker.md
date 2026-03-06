---
title: "Using Hive with Docker"
date: 2023-01-01
tags: ["hive", "docker"]
categories: ["Apache Hive"]
summary: "Quick reference for running Apache Hive 4.0.0 with Docker — start HiveServer2, connect with beeline, and clean up."
showToc: true
---

A quick guide to running Apache Hive using Docker.

## Start HiveServer2

```shell
docker run -d -p 10000:10000 -p 10002:10002 \
  --env SERVICE_NAME=hiveserver2 \
  --name hiveserver2 \
  apache/hive:4.0.0
```

## Stop HiveServer2

```shell
docker rm hiveserver2
```

## Start Beeline

```shell
docker exec -it hiveserver2 beeline -u 'jdbc:hive2://localhost:10000/'
```
