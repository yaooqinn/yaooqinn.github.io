---
title: "spark-advisor：AI 驱动的 Spark 性能工程师"
date: 2026-03-20
tags: ["spark", "performance", "agent-skill", "debugging", "tpc-ds"]
categories: ["Apache Spark"]
summary: "spark-advisor 是一个 Agent Skill，将你的 AI 编程助手变成 Spark 性能工程师——诊断慢作业、检测数据倾斜、对比基准测试、生成可操作的调优建议。"
showToc: true
---

每个 Spark 工程师都经历过这种场景：昨天还好好运行的作业，今天突然慢了 3 倍。有人问"这个查询为什么慢？"，然后你花了一个小时在 Spark History Server UI 上点来点去，用肉眼对比各个标签页的数字，在脑中 diff 配置。

如果你的 AI 助手能帮你做这些呢？

## 什么是 spark-advisor？

**spark-advisor** 是一个 Agent Skill，将你的 AI 编程助手变成 Spark 性能工程师。它支持 GitHub Copilot、Claude Code、Cursor 等 30 多种 Agent。

当你说 *"为什么我的 Spark 应用很慢？"* 或 *"对比这两次 TPC-DS 跑测"*，Agent 会：

1. 通过 `spark-history-cli` 连接你的 Spark History Server
2. 收集结构化 JSON 数据（概览、Stage、Executor、SQL 计划）
3. 应用诊断规则找到瓶颈
4. 生成优先级排序的报告和可操作的建议

无需手动点击，无需切换上下文。只需开口问。

## 快速开始

安装 CLI 和 Skill：

```bash
pip install spark-history-cli
npx skills add yaooqinn/spark-history-cli
```

然后告诉你的 Agent：

> "诊断一下 History Server 上最新的 Spark 应用"

就这么简单。Agent 会列出应用、选择最新的、收集指标、分析它们，然后告诉你问题在哪。

## 它能诊断什么

这个 Skill 将经验丰富的 Spark 工程师的诊断直觉编码为结构化规则。以下是它检查的内容：

### 任务倾斜

Spark 性能的头号杀手。spark-advisor 获取任务指标分位数并比较 p50 和 p95：

- **p95/p50 > 3x** → 中度倾斜
- **p95/p50 > 10x** → 严重倾斜

然后根据根因推荐：AQE 倾斜 Join、分区数调优或 Key 加盐。

### GC 压力

当 GC 时间超过 Executor 总运行时间的 10% 时标记警告，20% 以上标记严重。建议从增加 Executor 内存到减少单 Executor 并发度不等。

### Shuffle 开销

当 Shuffle 字节数超过输入大小的 2 倍时检测到 Shuffle 密集型 Stage。Skill 会检查计划中的冗余 Exchange、错误的 Join 策略（本应用 BroadcastHashJoin 却用了 SortMergeJoin），以及不足的分区数。

### 内存 Spill

任何非零的 `memoryBytesSpilled` 或 `diskBytesSpilled` 都会触发告警。Spill 意味着 Executor 的聚合或排序缓冲区内存不足——这个问题在 UI 中几乎不可见，除非你知道在哪里看。

### 掉队任务

Stage 中耗时超过中位数 5 倍以上的任务。spark-advisor 会检查掉队者是否集中在特定 Executor（硬件问题）还是处理了更多数据（倾斜变体）。

### Gluten/Velox 感知

对于 Gluten 加速的 Spark 应用，Skill 能检测：

- **回退算子**：最终计划中的非 Transformer 节点（如 `SortMergeJoin` 而非 `ShuffledHashJoinExecTransformer`）
- **列式转行式边界**：`VeloxColumnarToRow` 转换表示回退
- **原生指标模式**：Gluten Stage 与原生 Spark Stage 不同的 GC 和内存特征

## TPC-DS 基准对比

spark-advisor 最强大的功能之一是结构化基准对比。比如说：

> "对比这两次 TPC-DS 跑测：app-20260315120000-0001 和 app-20260320120000-0001"

Agent 会：

1. 跨两次运行匹配查询（q1–q99，处理 q14a/b、q23a/b 等拆分查询）
2. 计算每个查询的加速比和回退比
3. 生成对比表：

```
| 查询 | 基线   | 候选   | 差值  | 加速比 | 状态        |
|------|--------|--------|-------|--------|-------------|
| q67  | 72s    | 85s    | +13s  | 0.85x  | ⚠ 回退      |
| q1   | 61s    | 45s    | -16s  | 1.36x  | ✓ 提升      |
| q50  | 34s    | 33s    | -1s   | 1.03x  | ≈ 持平      |
```

4. 深入分析 Top-3 回退查询——对比最终计划、Stage 指标和配置差异
5. 报告总体加速比（所有查询的几何平均值）

这替代了每次跑完基准后数小时的手工表格工作。

## 诊断报告

spark-advisor 生成结构化的 Markdown 报告：

```markdown
# Spark 性能报告

## 摘要
应用 65% 的时间花在 3 个 Shuffle 密集型 Stage 上。
GC 压力中等（占 Executor 时间的 12%）。
Stage 14 检测到任务倾斜（p95/p50 = 8.2x）。

## 发现
### 发现 1：Stage 14 严重任务倾斜
- **严重程度**：高
- **证据**：p95 耗时 45s vs p50 5.5s（8.2x 比率）
- **建议**：启用 AQE 倾斜 Join 优化

### 发现 2：Executor 3、7 GC 压力
- **严重程度**：中
- **证据**：18% GC 时间（阈值：10%）
- **建议**：将 spark.executor.memory 从 4g 增加到 8g

## 建议
1. 启用 spark.sql.adaptive.skewJoin.enabled=true
2. 增加 Executor 内存到 8g
3. 审查 Stage 14 的 Join 策略——考虑 Broadcast Join
```

## 底层原理

spark-advisor 是一个纯 SKILL.md——没有代码，只有结构化的指令，教会 Agent 如何成为 Spark 性能工程师。它使用：

- **spark-history-cli** 收集所有数据（`--json` 模式获取结构化输出）
- `references/diagnostics.md` 中的**诊断规则**，包含具体阈值和启发式方法
- `references/comparison.md` 中的**对比方法论**，用于 TPC-DS 基准测试
- `sample_codes/` 中的**示例脚本**，用于常见模式

Agent 读取这些参考文件，将规则应用到你的数据上，并对结果进行推理。无需模型微调，无需训练数据——只需要结构良好的领域知识。

## 安装

```bash
# 安装 CLI
pip install spark-history-cli

# 为你的 Agent 安装 Skill
npx skills add yaooqinn/spark-history-cli
```

这会安装两个 Skill：
- **spark-history-cli** — 查询 Spark History Server
- **spark-advisor** — 诊断、对比和优化

## 未来计划

- **自动修复**：建议可直接应用的配置补丁
- **历史趋势**：跨版本追踪性能变化
- **可视化**：生成 SVG 火焰图和 DAG 标注

---

*spark-advisor 在 [github.com/yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli) 开源。如果觉得有用，欢迎 Star。*
