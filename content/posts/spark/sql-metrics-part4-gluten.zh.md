---
title: "深入 Spark SQL Metrics（第四部分）：Gluten 如何扩展指标系统"
date: 2026-04-01
tags: ["spark", "sql", "metrics", "gluten", "velox", "native"]
categories: ["Apache Spark"]
summary: "SQL Metrics 系列的第四部分。Apache Gluten 如何将 Velox/ClickHouse 原生指标桥接回 Spark SQL Metrics 框架，添加了 60+ 个原生 Spark 没有的指标。"
showToc: true
---

这是 Spark SQL Metrics 系列的加餐篇：

- [第一部分：指标类型、完整参考和含义](/zh/posts/spark/understanding-sql-metrics/)
- [第二部分：内部实现机制，以及 AQE 如何利用指标做出运行时决策](/zh/posts/spark/sql-metrics-part2-internals/)
- [第三部分：扩展 API、UI 渲染和 REST API](/zh/posts/spark/sql-metrics-part3-extension-api/)
- **第四部分（本文）**：Gluten 如何扩展指标系统

## Gluten 原生引擎如何产生指标

Apache Gluten 用原生 C++ 引擎——[Velox](https://github.com/facebookincubator/velox) 或 [ClickHouse](https://github.com/ClickHouse/ClickHouse)——替换了 JVM 执行引擎。由于原生算子独立执行（没有被 JVM 代码生成融合），每个 C++ 算子都是一个独立的函数调用，拥有自己的计时基础设施。作为自然结果，Gluten 暴露了 **60+ 个**指标，包括每算子的墙钟时间、分阶段的 Join 指标、原生溢出追踪、动态过滤器统计和按存储层级分解的 I/O 指标。

## 三层架构

Gluten 的指标系统桥接了两个世界：Spark 的 JVM 端 `SQLMetric` 框架和原生 C++ 执行引擎。架构分为三层：

```
Spark SQLMetric (JVM)     ←── MetricsUpdater（桥接层） ←── Velox/CH (C++)
Map[String, SQLMetric]        updateNativeMetrics()         long[] 数组，通过 JNI 传递
```

### 第一层：Spark SQLMetric（不变）

每个 `*ExecTransformer`——Gluten 对原生 Spark `*Exec` 算子的替代——都重写了 `lazy val metrics`，使用与原生 Spark 相同的模式。但它不是硬编码指标集，而是委托给后端：

```scala
BackendsApiManager.getMetricsApiInstance
  .genFilterTransformerMetrics(sparkContext)
```

这意味着 Velox 后端和 ClickHouse 后端可以为同一个逻辑算子定义完全不同的指标。运行在 Velox 上的 `FilterExecTransformer` 可能暴露 `wallNanos` 和 `peakMemoryBytes`，而运行在 ClickHouse 上的同一算子可能暴露不同的内部计数器。指标定义是后端特有的，但它们最终都成为标准的 `SQLMetric` 对象，Spark UI 和 REST API 可以正常显示。

### 第二层：MetricsUpdater（Gluten 的桥接抽象）

`MetricsUpdater` trait 是 Gluten 的核心桥接抽象。它定义了一个方法：

```scala
trait MetricsUpdater extends Serializable {
  def updateNativeMetrics(opMetrics: IOperatorMetrics): Unit
}
```

每个算子都有对应的 `MetricsUpdater` 实现。这些 updater 被组织成 `MetricsUpdaterTree`，镜像计划 DAG——每个算子一个 updater，以与物理计划相同的父子结构连接。

为什么需要一棵单独的树？因为 `MetricsUpdaterTree` 是 `Serializable` 的——它可以被发送到 Executor 端，而无需序列化完整的 `SparkPlan`（后者包含不可序列化的对象如 `SparkContext`）。在 Executor 上，原生执行完成后，这棵树遍历原生指标并更新 `SQLMetric` 累加器。

三个特殊的哨兵实例处理边界情况：

- `MetricsUpdater.None` —— 算子没有需要更新的指标
- `MetricsUpdater.Todo` —— 该算子的指标支持尚未实现
- `MetricsUpdater.Terminate` —— 分支在此终止（没有子节点需要递归）

以下是一个具体例子——`FilterMetricsUpdater`：

```scala
class FilterMetricsUpdater(val metrics: Map[String, SQLMetric]) extends MetricsUpdater {
  override def updateNativeMetrics(opMetrics: IOperatorMetrics): Unit = {
    val m = opMetrics.asInstanceOf[OperatorMetrics]
    metrics("numOutputRows") += m.outputRows
    metrics("outputVectors") += m.outputVectors
    metrics("outputBytes") += m.outputBytes
    metrics("cpuCount") += m.cpuCount
    metrics("wallNanos") += m.wallNanos
    metrics("peakMemoryBytes") += m.peakMemoryBytes
    metrics("numMemoryAllocations") += m.numMemoryAllocations
  }
}
```

注意每个原生指标字段（如 `m.wallNanos`）如何直接映射到 `SQLMetric` 的键。updater 是原生 C++ 命名和 Spark 指标命名空间之间的翻译层。

### 第三层：通过 JNI 传递的原生指标

在 C++ 端，Velox 引擎在执行过程中以数组形式收集指标——每个算子索引一个条目。当一个任务完成时，Gluten 通过 JNI 边界将这些指标作为包含 `long[]` 数组的 `Metrics` 对象传递：

```
inputRows[]       — 每个算子消费的行数
outputRows[]      — 每个算子产出的行数
wallNanos[]       — 每个算子的墙钟纳秒数
cpuCount[]        — 每个算子的 CPU 时间
peakMemoryBytes[] — 每个算子的峰值内存
...               — 还有 20+ 个数组
```

`MetricsUpdatingFunction` 遍历 `MetricsUpdaterTree`，按算子索引从数组中提取每个算子的值。这是一次批量传输——每个任务一次 JNI 调用，而非每行一次——将开销降到最低。

## Gluten 新增了什么——60+ 个指标

让我们按类别看看 Gluten 引入的具体指标。

### 每算子执行指标

在原生 Spark 中，大多数算子仅报告 `numOutputRows`。在 Gluten 中，**每个算子**都拥有以下指标：

| 指标 | 类型 | 测量内容 |
|-----|------|---------|
| `wallNanos` | nsTiming | 每算子的墙钟时间 |
| `cpuCount` | timing | CPU 时间计数 |
| `peakMemoryBytes` | size | 峰值内存使用 |
| `numMemoryAllocations` | sum | 内存分配次数 |
| `outputRows` | sum | 输出行数 |
| `outputVectors` | sum | 输出向量（批次）数 |
| `outputBytes` | size | 列式格式的输出数据量 |
| `loadLazyVectorTime` | timing | 加载惰性求值向量的时间 |

在每个算子上都有 `wallNanos` 使得识别原生执行中的瓶颈算子变得直观。

### 深入理解 wallNanos 和 cpuCount

这两个指标值得特别关注，因为它们对性能分析最为重要。

两者都来自 Velox 的 `CpuWallTiming` 结构体，通过 RAII 计时器（`DeltaCpuWallTimer`）包装每个算子的 `getOutput()` 调用来收集：

```cpp
struct CpuWallTiming {
  uint64_t count;      // getOutput() 调用次数（批次数）
  uint64_t wallNanos;  // 总墙钟时间（steady_clock，纳秒）
  uint64_t cpuNanos;   // 总 CPU 时间（CLOCK_THREAD_CPUTIME_ID，纳秒）
};
```

**wallNanos** — 使用 `std::chrono::steady_clock` 测量。捕获总实际经过时间，**包括**算子等待子算子产生数据、I/O 等待或线程调度延迟的时间。

**cpuCount** — 尽管名字叫 cpuCount，但它实际上是**调用次数**（`getOutput()` 被调用的次数 = 处理的批次数），而不是 CPU 时间。Gluten JNI 桥接将 `CpuWallTiming.count` 映射到 `cpuCount` 指标。

**如何解读：**

| 场景 | wallNanos | cpuCount | 含义 |
|------|:---------:|:--------:|------|
| 大数据量，均匀工作 | 高 | 高 | 处理了很多批次，符合预期 |
| 少量批次，每个很慢 | 高 | 低 | 可能存在数据倾斜或复杂的每批处理逻辑 |
| 叶子算子（扫描） | 高 | — | 主要是 I/O 时间（另查 `ioWaitTime`） |
| 中间算子（过滤） | 高 | — | 包含等待子算子的时间——与子算子的 wallNanos 对比 |

**重要提醒——wallNanos 包含子算子等待时间：**

由于 `wallNanos` 包装了整个 `getOutput()` 调用，父算子的 wallNanos 包含了等待子算子产生数据的阻塞时间。因此：

- **叶子算子**（扫描）：wallNanos ≈ I/O + 计算时间
- **中间算子**（过滤）：wallNanos = 自身计算 + 子算子扫描时间
- **不能简单地对所有算子的 wallNanos 求和**——那会重复计算

要隔离算子自身的贡献，将其 wallNanos 与子算子的 wallNanos 做差。Velox 还单独追踪 I/O 相关指标（`ioWaitTime`、`dataSourceReadTime`）以帮助分离纯 I/O 与计算。

### 扫描专用指标

原生 Spark 的扫描算子有 `scanTime` 和 `numFiles`。Gluten 深入得多：

| 指标 | 测量内容 |
|-----|---------|
| `skippedSplits` / `processedSplits` | 文件分片裁剪效果 |
| `skippedStrides` / `processedStrides` | 文件内行组/条带级裁剪 |
| `ioWaitTime` | I/O 操作的等待时间 |
| `storageReadBytes` | 从远程存储读取的字节数 |
| `localReadBytes` | 从本地 SSD 缓存读取的字节数 |
| `ramReadBytes` | 从内存缓存读取的字节数 |
| `preloadSplits` | 预加载的分片数（预取） |
| `dataSourceAddSplitTime` | 管理分片分配的时间 |
| `dataSourceReadTime` | 从数据源读取数据的时间 |

`storageReadBytes` / `localReadBytes` / `ramReadBytes` 的分解在云环境中尤其有价值。如果大部分读取来自 `storageReadBytes`，说明缓存还没热起来。如果 `ioWaitTime` 在 `wallNanos` 中占主导地位，瓶颈是网络 I/O 而非 CPU。

### 溢出指标

原生 Spark 在阶段级别追踪溢出。Gluten 在每算子、每阶段级别追踪：

| 指标 | 测量内容 |
|-----|---------|
| `spilledBytes` | 溢出到磁盘的数据量 |
| `spilledRows` | 溢出的行数 |
| `spilledPartitions` | 涉及溢出的分区数 |
| `spilledFiles` | 创建的溢出文件数 |

对于 Join 算子，溢出在构建阶段和探测阶段分别追踪（见下一节），因此你可以精确定位哪个阶段正面临内存压力。

### 动态过滤器指标

动态过滤器（也称运行时过滤器）由 Join 算子生成，用于在运行时裁剪扫描结果。原生 Spark 没有相关指标。Gluten 追踪了完整的生命周期：

| 指标 | 测量内容 |
|-----|---------|
| `numDynamicFiltersProduced` | Join 构建端生成的运行时过滤器数 |
| `numDynamicFiltersAccepted` | 被扫描算子应用的运行时过滤器数 |
| `numReplacedWithDynamicFilterRows` | 被运行时过滤器消除的行数 |

如果 `numDynamicFiltersProduced` > 0 但 `numDynamicFiltersAccepted` = 0，说明过滤器已生成但未被应用——这表明扫描和 Join 之间的连接方式与优化器的预期不符。如果 `numReplacedWithDynamicFilterRows` 是一个很大的数字，说明运行时过滤器节省了大量工作。

### Join 阶段分离——每个 Join 20+ 个指标

这可以说是 Gluten 最强大的指标增强。原生 Spark 的 Join 算子仅报告一个 `buildTime` 和 `numOutputRows`。Gluten 将每个 Join 拆分为其组成阶段，每个阶段都有独立的指标：

**构建阶段：**

| 指标 | 测量内容 |
|-----|---------|
| `hashBuildInputRows` | 构建端消费的行数 |
| `hashBuildOutputRows` | 哈希表中的行数 |
| `hashBuildWallNanos` | 构建阶段的墙钟时间 |
| `hashBuildPeakMemoryBytes` | 构建阶段的峰值内存 |
| `hashBuildSpilledBytes` | 构建阶段溢出的数据量 |
| `hashBuildSpilledRows` | 构建阶段溢出的行数 |
| `hashBuildSpilledPartitions` | 构建阶段溢出的分区数 |
| `hashBuildSpilledFiles` | 构建阶段创建的溢出文件数 |

**探测阶段：**

| 指标 | 测量内容 |
|-----|---------|
| `hashProbeInputRows` | 探测端消费的行数 |
| `hashProbeOutputRows` | 探测后输出的行数 |
| `hashProbeWallNanos` | 探测阶段的墙钟时间 |
| `hashProbePeakMemoryBytes` | 探测阶段的峰值内存 |
| `hashProbeSpilledBytes` | 探测阶段溢出的数据量 |
| `hashProbeSpilledRows` | 探测阶段溢出的行数 |
| `hashProbeSpilledPartitions` | 探测阶段溢出的分区数 |
| `hashProbeSpilledFiles` | 探测阶段创建的溢出文件数 |

**前置/后置投影：**

| 指标 | 测量内容 |
|-----|---------|
| 前置投影计时 | Join 前表达式求值时间 |
| 后置投影计时 | Join 后表达式求值时间 |

在原生 Spark 中，一个慢 Join 几乎不给你任何可用信息——你只知道它很慢，但不知道为什么。有了 Gluten，你可以立即看到：是构建阶段慢（也许构建端数据太大了）？还是探测阶段慢（也许哈希冲突导致了过多的探测）？构建阶段是否在溢出（内存压力）？这种级别的细节彻底改变了你诊断 Join 性能的方式。

### 写入指标

| 指标 | 测量内容 |
|-----|---------|
| `physicalWrittenBytes` | 实际写入存储的字节数 |
| `writeIOTime` | 写入过程中的 I/O 时间 |
| `numWrittenFiles` | 产生的文件数 |

## Gluten vs 原生 Spark vs DataFlint

## 在 Spark UI 中阅读 Gluten 指标

Gluten 的指标出现在同一个 Spark SQL 标签页中，因为它们使用相同的 `SQLMetric` 框架。算子名称有所变化（例如 `HashAggregateExecTransformer` 替代了 `HashAggregateExec`），但当你点击算子节点时，指标仍出现在同一个侧边面板中。

### 关键观察点

以下是阅读 Gluten 指标时需要关注的关键模式：

**定位瓶颈算子：**

查看每个算子上的 `wallNanos`。在健康的查询中，扫描和 Join 算子通常占据大部分时间。如果 `FilterExecTransformer` 或 `ProjectExecTransformer` 有较高的 `wallNanos`，说明过滤或投影表达式本身开销较大——考虑简化它。

**诊断慢 Join：**

对比 `hashBuildWallNanos` 和 `hashProbeWallNanos`。如果构建端占主导地位，说明构建输入太大——考虑改变 Join 顺序或添加过滤条件来减小构建端。如果探测端占主导地位，查看 `hashProbeInputRows`——过多的探测行或哈希冲突可能是原因。

**检查原生谓词下推：**

如果 `skippedSplits` > 0，说明原生文件级裁剪正在生效。如果 `skippedStrides` > 0，说明文件内行组或条带级裁剪正在生效。如果两者都为零，说明谓词没有被下推到原生扫描中——检查列类型是否支持下推。

**验证运行时过滤器效果：**

如果 `numDynamicFiltersAccepted` > 0，说明来自 Join 构建端的运行时过滤器正在被应用到扫描中。查看 `numReplacedWithDynamicFilterRows` 以了解消除了多少行——数字越大意味着 I/O 节省越多。

**检测原生引擎中的内存压力：**

如果任何算子上 `spilledBytes` > 0，说明原生引擎正在溢出到磁盘。对于 Join，检查是构建阶段还是探测阶段在溢出。对于聚合，溢出意味着分组基数很高。考虑增加原生内存分配或减少数据量。

**I/O 层级分析：**

对比扫描算子上的 `storageReadBytes`、`localReadBytes` 和 `ramReadBytes`。在缓存良好的环境中，你希望大部分读取来自 `ramReadBytes` 或 `localReadBytes`。高 `storageReadBytes` 意味着你在从远程存储（S3、HDFS）读取——检查缓存层的配置是否正确。

### 通过 spark-history-cli 访问

Gluten 指标也可以通过 REST API 和 `spark-history-cli` 获取，因为它们以标准 `SQLMetric` 值的形式存储：

```bash
spark-history-cli --json -a <app> sql <id>  # 包含 Gluten 指标
```

JSON 输出将包含所有 Gluten 特有的指标以及原生 Spark 指标，使用[第三部分](/zh/posts/spark/sql-metrics-part3-extension-api/)中描述的相同 `{name, value}` 格式。

## 架构启示

Gluten 的指标系统为扩展 Spark 的可观测性提供了几个重要启示：

**引擎替换自然带来全面指标。** 当引擎控制每个算子的执行时，它可以测量每一个边界。每个 C++ 算子都是独立的函数调用，拥有自己的开始和结束时间戳。

**MetricsUpdater 模式是可复用的。** 任何原生后端都可以采用这一模式：定义一棵轻量级的、可序列化的 updater 对象树来镜像计划，通过 JNI 传输批量指标数组，然后遍历树来更新 `SQLMetric` 累加器。

**基于 JNI 数组的传输将开销降到最低。** Gluten 没有为每次指标更新都回调 JVM，而是将所有指标批量打包到 `long[]` 数组中——每个任务一次批量 JNI 传输。即使每个算子有 60+ 个指标，指标开销也可以忽略不计。

**通过 MetricsApi 实现后端无关设计。** `MetricsApi` 抽象意味着 Velox 后端和 ClickHouse 后端可以为同一算子类型定义完全不同的指标。添加新的后端（比如 DataFusion）只需实现 `MetricsApi` 接口——无需修改核心桥接代码。

---

*在[第一部分](/zh/posts/spark/understanding-sql-metrics/)中，我们介绍了五种指标类型和完整参考。在[第二部分](/zh/posts/spark/sql-metrics-part2-internals/)中，我们追踪了内部生命周期和 AQE 对 Shuffle 统计信息的使用。在[第三部分](/zh/posts/spark/sql-metrics-part3-extension-api/)中，我们探索了扩展 API、UI 渲染和 REST API。本加餐篇分析了 Apache Gluten 如何通过将原生引擎指标桥接回 Spark 框架来扩展指标系统。*
