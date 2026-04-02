---
title: "深入 Spark SQL Metrics（第五部分）：Gluten 指标收集的内部机制"
date: 2026-04-02
tags: ["spark", "sql", "metrics", "gluten", "velox", "internals"]
categories: ["Apache Spark"]
summary: "SQL Metrics 系列第五部分。Gluten 如何将 Substrait 计划节点映射到 Velox 算子、跨管道聚合指标、遍历 MetricsUpdaterTree，以及聚合子阶段和 Shuffle 指标的内部机制。"
showToc: true
---

这是 Spark SQL Metrics 深度解析系列的第五部分：

- [第一部分：指标类型、完整参考和含义](/zh/posts/spark/understanding-sql-metrics/)
- [第二部分：内部实现机制，以及 AQE 如何利用指标做出运行时决策](/zh/posts/spark/sql-metrics-part2-internals/)
- [第三部分：扩展 API、UI 渲染和 REST API](/zh/posts/spark/sql-metrics-part3-extension-api/)
- [第四部分：Gluten 如何扩展指标系统](/zh/posts/spark/sql-metrics-part4-gluten/)
- **第五部分（本文）**：Gluten 指标内部机制 — 节点映射、管道聚合、MetricsUpdaterTree、聚合子阶段和 Shuffle 指标

在[第四部分](/zh/posts/spark/sql-metrics-part4-gluten/)中，我们从外部视角了解了 Gluten 的指标体系 — 那些出现在 Spark UI 中的 60 多个计数器。现在我们要深入内部：这些数字究竟是*如何*从原生 Velox 算子传回 JVM 的。如果你曾经盯着一个令人困惑的 Gluten 指标值想弄清它的来源，或者你正在为 Gluten 贡献代码需要添加新指标，这篇文章就是为你写的。

## Substrait 节点 ID → Velox 算子映射

当 Gluten 通过 Substrait 将 Spark 计划转换为 Velox 计划时，计划中的每个算子都会获得一个**计划节点 ID**。这个 ID 是 JVM 世界（Spark 所在之处）和 C++ 世界（Velox 执行之处）之间的桥梁。C++ 侧需要将这些 ID 映射回指标数组，使每个原生指标值都能关联到正确的 Spark 算子。

### `getOrderedNodeIds()` 的工作原理

关键函数是 `getOrderedNodeIds()`。它对 Velox 计划树执行**后序遍历**，构建 `orderedNodeIds_` 向量。遍历顺序至关重要 — 它决定了扁平指标数组中的哪个索引对应哪个算子。

```
Spark Plan → Substrait Plan → Velox PlanNode tree
                                      ↓
                              getOrderedNodeIds()（后序遍历）
                                      ↓
                              orderedNodeIds_[0] = 叶子算子
                              orderedNodeIds_[1] = 下一个算子
                              ...
                              orderedNodeIds_[N] = 根算子
```

为什么使用后序遍历？因为 JVM 侧的 `MetricsUpdaterTree` 也是先遍历子节点再遍历父节点。两侧使用相同的遍历顺序确保索引保持同步，无需显式查找表。

### 特殊情况：Filter–Project 融合

Velox 将 `FilterNode → ProjectNode` 融合为单个 `FilterProject` 算子以提升性能。当这种情况发生时，Filter 节点没有独立的运行时指标 — 它已被吸收到融合算子中。Gluten 通过将 Filter 的计划节点 ID 添加到 `omittedNodeIds_` 并为其指标槽位填充**零值**来处理这种情况。JVM 侧看到零值槽位后知道应该跳过它。

理解这一点对调试很重要：如果你看到一个 `FilterExecTransformer` 的所有指标都是零，这并不意味着过滤器没有被执行 — 而是 Velox 将它与相邻的 Project 融合了。

### 特殊情况：Union

Velox 将 Union 表示为 `LocalPartitionNode + LocalExchangeNode + 虚拟 ProjectNode`。这种内部表示不能干净地映射到单个 Spark `UnionExec`。Gluten 会解开这个结构以找到真正的子节点，确保指标数组与 Spark 计划的结构对齐，而非 Velox 的内部表示。

## Velox 管道模型与指标聚合

这里有一个让很多开发者始料未及的微妙之处：Velox 不会将计划作为单个管道执行。它在交换边界（有时也在其他点，如 Hash Join 的构建侧）将计划拆分为**多个管道**。单个逻辑算子可以有在不同管道中运行的实例，每个实例收集各自的指标。

### `toPlanStats()` 如何聚合

`toPlanStats(taskStats)` 从所有管道实例收集指标，返回 `Map[PlanNodeId → PlanStats]`。每个 `PlanStats` 包含：

- `operatorStats`：一个 `Map[SequenceId → OperatorStats]`，其中每个条目代表该算子的一个管道实例

当 Gluten 的 `collectMetrics()` 遍历这些条目时，它将每个管道实例写入单独的指标索引：

```cpp
for (const auto& entry : stats.operatorStats) {
    // 每个 entry 是该算子的一个管道实例
    metrics_->get(Metrics::kWallNanos)[metricIndex] = entry.second->cpuWallTiming.wallNanos;
    metricIndex++;
}
```

这意味着单个 Spark 算子可能映射到指标数组中的**多个指标索引**。例如，一个 `HashAggregateExec` 如果同时出现在 Shuffle 前的局部聚合管道和 Shuffle 后的最终聚合管道中，就会有两个独立的指标条目。

### JVM 侧的合并

JVM 侧的 `MetricsUpdater` 通过从 `relMap` 获取给定算子的所有条目并调用 `mergeMetrics()` 来处理多管道条目。对于时间指标，通常是求和；对于峰值内存，取最大值。合并后的结果就是你在 Spark UI 中看到的 — 一组代表算子在所有管道中总工作量的数字。

## MetricsUpdaterTree 遍历

在 JVM 侧，`MetricsUtil.scala` 通过两个关键方法编排整个指标分发过程。

### 构建树：`treeifyMetricsUpdaters()`

`treeifyMetricsUpdaters(plan)` 从 SparkPlan 构建 `MetricsUpdaterTree`。这不是简单的递归复制 — 有几个调整：

- **HashJoin 处理**：树将构建侧和流侧子节点分开，因为 Velox 在不同管道中执行它们并使用不同的指标
- **SortMergeJoin 处理**：类似地将缓冲侧和流侧子节点分开
- **`MetricsUpdater.None` 算子**：这些被完全跳过 — 它们的子节点直接链接到父节点。这发生在 Gluten 用空操作替换的算子上（例如，某些适配器节点）
- **子节点被反转**：这一点至关重要。子节点列表被反转以匹配 C++ 侧 `getOrderedNodeIds()` 使用的后序遍历

### 遍历树：`updateTransformerMetricsInternal()`

`updateTransformerMetricsInternal()` 遍历 `MetricsUpdaterTree` 并将指标分发到特定类型的更新器：

| 更新器 | 算子 | 特殊处理 |
|--------|------|---------|
| `HashAggregateMetricsUpdater` | HashAggregate | 三阶段子指标（见下一节） |
| `JoinMetricsUpdaterBase` | HashJoin | 为构建阶段提取额外指标条目 |
| `SortMergeJoinMetricsUpdater` | SortMergeJoin | 缓冲/流阶段分离 |
| `LimitMetricsUpdater` | Limit over Sort | 跳过 Limit 自身的指标（Velox TopN 同时处理两者） |
| 默认 | 其他所有算子 | `mergeMetrics()` → `updateNativeMetrics()` |

对于 Join，有一个重要细节：Velox 将构建阶段的指标报告为 `relMap` 直接提供之外的**额外条目**。Join 更新器知道要提取这个额外条目并将其附加到构建侧指标上，这就是为什么即使构建和探测发生在不同管道中，你仍然能看到准确的构建侧时间。

对于 Limit over Sort，Gluten 完全跳过 Limit 自身的指标。Velox 将其实现为 TopN 算子，在一个融合操作中同时处理排序和限制，因此只有一组指标需要报告。

分发完成后，遍历器递归处理子节点，使用更新后的算子和指标索引，确保每个子节点从父节点在扁平指标数组中结束的位置继续。

## 聚合子阶段指标

Velox 中的 Hash 聚合比原生 Spark 更加精细。它最多可以执行**三个阶段**，由 `AggregationParams` 控制。理解这种拆分对诊断聚合性能至关重要。

### 阶段一：抽取（`extractionNeeded = true`）

聚合前的列抽取 — 例如，在分组和聚合之前从嵌套结构体中提取字段。

**指标：**
- `extractionCpuCount` — 抽取的 CPU 时间
- `extractionWallNanos` — 抽取的挂钟时间

如果抽取时间相对于总聚合时间较高，你的 Schema 可能需要在聚合前扁平化嵌套列。

### 阶段二：聚合（始终存在）

主要的 Hash 聚合工作 — 对分组键进行哈希、查找或创建分组、累积值。

**指标：**
- `aggOutputRows` — 输出行数（即不同分组数）
- `aggWallNanos` — 聚合的挂钟时间
- `aggPeakMemoryBytes` — 哈希表使用的峰值内存
- `aggSpilledBytes` — 内存压力触发溢写时溢出的字节数
- `flushRowCount` — 哈希表过大时刷新的中间行数
- `loadedToValueHook` — 下推聚合计数（一种将聚合下推到扫描算子的优化）

`flushRowCount` 对调试特别有用：高刷新计数意味着哈希表不断超出内存预算，导致中间结果被刷新并重新聚合。这会带来额外的工作量并降低查询速度。

### 阶段三：行构造（`rowConstructionNeeded = true`）

聚合后的行组装 — 例如，从聚合结果构造输出结构体列。

**指标：**
- `rowConstructionCpuCount` — 行构造的 CPU 时间
- `rowConstructionWallNanos` — 行构造的挂钟时间

### 阶段如何映射到指标条目

更新器按顺序遍历 `aggregationMetrics` 列表，每个阶段消费一个条目：

```
aggregationMetrics[0] → 抽取阶段（如果需要）
aggregationMetrics[1] → 聚合阶段
aggregationMetrics[2] → 行构造阶段（如果需要）
```

这种三阶段拆分是 Gluten/Velox 独有的 — 原生 Spark 的 `HashAggregateExec` 报告单个 `aggTime`，将所有内容混在一起。有了 Gluten，你可以精确定位聚合管道中的时间消耗*在哪里*。

## Shuffle 指标

Gluten 的列式 Shuffle 有自己的指标层，可用的指标因 **Shuffle 写入器类型**而异。了解使用的是哪种写入器能告诉你应该查看哪些指标 — 以及哪些调优手段是相关的。

### 基础指标（所有写入器）

| 指标 | 显示名称 | 测量内容 |
|------|---------|---------|
| `dataSize` | data size | 总 Shuffle 数据大小 |
| `bytesSpilled` | shuffle bytes spilled | Shuffle 期间溢出的字节数 |
| `spillTime` | time to spill | 溢写花费的时间 |
| `compressTime` | time to compress | 压缩时间 |
| `decompressTime` | time to decompress | 解压时间 |
| `deserializeTime` | time to deserialize | 反序列化时间 |
| `shuffleWallTime` | shuffle wall time | Shuffle 总挂钟时间 |
| `peakBytes` | peak bytes allocated | Shuffle 缓冲区的峰值内存 |

### Hash Shuffle 写入器额外指标

| 指标 | 显示名称 | 测量内容 |
|------|---------|---------|
| `splitTime` | time to split | 将行拆分到分区的时间 |
| `dictionarySize` | dictionary size | 字典编码列的大小 |

### Sort Shuffle 写入器额外指标

| 指标 | 显示名称 | 测量内容 |
|------|---------|---------|
| `sortTime` | time to shuffle sort | 按分区排序行的时间 |
| `c2rTime` | time to shuffle c2r | 为排序将列式→行式格式转换的时间 |

### RSS（远程 Shuffle 服务）写入器额外指标

| 指标 | 显示名称 | 测量内容 |
|------|---------|---------|
| `sortTime` | time to shuffle sort | 按分区排序行的时间 |

### 诊断 Shuffle 瓶颈

`c2rTime` 指标值得特别关注。它代表在基于排序的 Shuffle 写入器内部将列式批次转换为行格式的开销。在 Velox 这样的列式引擎中，数据天然以列式格式存在 — 将其转换为行格式进行排序是纯粹的开销。

如果 `c2rTime` 在 `shuffleWallTime` 中占主导地位，那么列式到行式的转换就是你的瓶颈。在这种情况下，切换到基于哈希的 Shuffle（可以直接在列式批次上操作）可能会带来显著的速度提升。这是 Gluten 用户面临的关键决策之一：哈希 Shuffle 对于列数较多的宽表更快，而排序 Shuffle 对于高基数分区键使用更少的内存。

## 总结

Gluten 的指标机制之所以复杂，是因为它桥接了两种非常不同的执行模型 — Spark 的逐行 Volcano 迭代器模型和 Velox 的管道并行向量化模型。需要记住的关键概念：

1. **节点 ID 映射**通过后序遍历保持 C++ 和 JVM 两侧同步
2. **多管道聚合**意味着单个 Spark 算子的指标可能来自多个 Velox 管道实例
3. **MetricsUpdaterTree** 将指标分发到理解每个算子内部结构的特定类型更新器
4. **聚合子阶段**让你分别观察抽取、聚合和行构造
5. **Shuffle 写入器类型**决定了可用的指标以及适用的调优策略

---

*在[第一部分](/zh/posts/spark/understanding-sql-metrics/)中，我们介绍了五种指标类型和完整参考。在[第二部分](/zh/posts/spark/sql-metrics-part2-internals/)中，我们追踪了内部生命周期和 AQE 对 Shuffle 统计信息的使用。在[第三部分](/zh/posts/spark/sql-metrics-part3-extension-api/)中，我们探索了扩展 API、UI 渲染和 REST API。在[第四部分](/zh/posts/spark/sql-metrics-part4-gluten/)中，我们分析了 Gluten 如何扩展指标系统。在第五部分（本文）中，我们深入了内部机制 — 从 Substrait 到 Velox 的节点映射、管道聚合、MetricsUpdaterTree 遍历、聚合子阶段到 Shuffle 指标。本系列到此结束。*
