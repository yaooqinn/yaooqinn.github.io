---
title: "SQL 执行详情页终于能直观展示作业运行状态了"
date: 2026-03-14
tags: ["spark", "ui", "sql", "execution", "web-ui"]
categories: ["Apache Spark"]
summary: "Spark Web UI 的 SQL 执行详情页过去只用逗号分隔的 ID 展示关联作业。现在它有了完整的 Associated Jobs 表格，包含状态、耗时、Stage 进度和 Task 进度条——让你无需逐个点击即可调试 SQL 查询。"
showToc: true
---

你在 Spark Web UI 中点击某条 SQL 执行记录，想知道：*这条查询启动了哪些作业？进展如何？有没有失败？*

以前页面只给你看这些：

```
Running Jobs: 0, 1, 2
Succeeded Jobs: 3, 4
```

就这样。光秃秃的 ID，没有状态、没有耗时、没有 Stage 数量、没有进度条。要弄清楚到底发生了什么，你得逐个点击 Job ID，查看作业详情页，再返回来，点下一个，然后在脑子里把信息拼起来。对于一个会启动十几个作业的复杂查询来说，这真的很痛苦。

**[SPARK-55971](https://issues.apache.org/jira/browse/SPARK-55971) 解决了这个问题。** SQL 执行详情页现在有了完整的 **Associated Jobs** 表格，所有信息一目了然。

## 界面展示

下面是一个成功执行的查询，展示新的作业表格：

![SQL 执行详情页上的 Associated Jobs 表格](https://raw.githubusercontent.com/yaooqinn/spark/SPARK-55786-screenshots/55971-exec0-jobs-table.png)

下面是一个失败的执行，包含被终止的任务——注意进度条上简洁的标签：

![包含被终止任务的失败执行](https://raw.githubusercontent.com/yaooqinn/spark/SPARK-55786-screenshots/55971-exec1-failed-jobs.png)

完整页面展示，作业表格位于 Plan Details 下方：

![完整的执行详情页](https://raw.githubusercontent.com/yaooqinn/spark/SPARK-55786-screenshots/55971-exec0-full-page.png)

作为对比，这是 Jobs 页面——新表格与其保持一致的视觉风格：

![Jobs 页面风格对比](https://raw.githubusercontent.com/yaooqinn/spark/SPARK-55786-screenshots/55971-jobs-page-compare.png)

## 表格内容

| 列 | 展示内容 |
|----|----------|
| **Job ID** | 跳转到作业详情页的链接 |
| **Description** | Stage 名称和描述 |
| **Submitted** | 提交时间（可排序） |
| **Duration** | 可读的耗时（可排序） |
| **Stages: Succeeded/Total** | Stage 完成进度，含失败/跳过计数 |
| **Tasks: Succeeded/Total** | 带 Task 级别明细的进度条 |

表格标题显示 **"Associated Jobs (N)"**，让你立刻知道这条查询启动了多少个作业。点击标题可以折叠或展开该区块——状态通过 `localStorage` 持久化，刷新页面后依然保持。

列支持排序。点击 **Duration** 找到最慢的作业，点击 **Submitted** 查看执行顺序。**Stages** 和 **Tasks** 列使用与 Jobs 主页面相同的进度条样式，保持视觉语言的一致性。

## 为什么这很重要

SQL 执行详情页是工程师在查询缓慢或失败时第一个去的地方。问题总是一样的：

1. **这条查询创建了多少个作业？** — 现在直接显示在区块标题中。
2. **哪个作业是瓶颈？** — 按 Duration 排序即可。
3. **作业还在运行吗？进展如何？** — Task 进度条即时呈现。
4. **有 Stage 失败吗？** — Stages 列内联显示失败/跳过计数。
5. **每个作业在做什么？** — Description 列展示 Stage 名称。

以前，回答*任何一个*问题都需要离开执行详情页。现在它们都在同一张表格、同一个页面上得到解答，无需任何额外点击。

## 额外收获：简洁的进度条标签

同一个 PR 还修复了一个长期存在的进度条可读性问题，影响**整个 Web UI**。当任务被终止时，Spark 以前会在进度条标签中显示完整的终止原因——包括堆栈跟踪：

```
[====>    ] 45/100 (5 killed: org.apache.spark.SparkException: Job 3 cancelled
because SparkContext was shut down at org.apache.spark.scheduler.DAGScheduler...)
```

现在显示简洁的标签，详细原因通过悬停查看：

```
[====>    ] 45/100 (5 killed)
                    ↑ 悬停查看完整原因
```

这适用于 Jobs 页面、Stages 页面和新的 SQL 执行作业表格的进度条。截断后的原因（最多 120 个字符）保留在工具提示中。

## 更大的现代化计划

这是 [SPARK-55760](https://issues.apache.org/jira/browse/SPARK-55760) Web UI 现代化工作的一部分。其他近期改进包括：

- **[暗黑模式]({{< ref "dark-mode-spark-ui.zh.md" >}})** — 一键切换，系统偏好检测（[SPARK-55766](https://issues.apache.org/jira/browse/SPARK-55766)）
- **[紧凑型 SQL 计划可视化]({{< ref "sql-plan-visualization.zh.md" >}})** — 边上的行数标签，可点击的指标面板（[SPARK-55785](https://issues.apache.org/jira/browse/SPARK-55785)）
- **[Offcanvas 详情面板](https://github.com/apache/spark/pull/54589)** — 滑出式 Executor 视图（[SPARK-55767](https://issues.apache.org/jira/browse/SPARK-55767)）
- **[Bootstrap 5 折叠 API](https://github.com/apache/spark/pull/54574)** — 替换所有页面的自定义 JS 折叠逻辑（[SPARK-55773](https://issues.apache.org/jira/browse/SPARK-55773)）
- **[Bootstrap 5 升级](https://github.com/apache/spark/pull/54552)** — 从 4.6.2 升级到 5.3.8（[SPARK-55761](https://issues.apache.org/jira/browse/SPARK-55761)）

目标很简单：Spark Web UI 在帮助你理解查询方面，应该和 Spark 执行查询一样出色。

## 试试看

该功能已合入 `master` 分支，将在下一个 Apache Spark 版本中发布。如果你从源码构建，今天就可以体验。

---

*该功能作为 [SPARK-55971](https://issues.apache.org/jira/browse/SPARK-55971)（[PR #54768](https://github.com/apache/spark/pull/54768)）贡献。欢迎在 [SPARK-55760](https://issues.apache.org/jira/browse/SPARK-55760) 提供反馈和参与 Spark Web UI 现代化工作。*
