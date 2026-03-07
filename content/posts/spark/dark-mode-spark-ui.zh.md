---
title: "Apache Spark Web UI 迎来暗黑模式"
date: 2026-03-06
tags: ["spark", "ui", "dark-mode", "bootstrap", "web-ui"]
categories: ["Apache Spark"]
summary: "Apache Spark 的 Web UI 现已支持暗黑模式——这是开发者们期待已久的改进，尤其对于那些长时间调试作业的工程师而言。"
showToc: true
cover:
  image: "/images/spark-ui/dm-dark-jobs.png"
  alt: "Spark Web UI 暗黑模式"
  caption: "暗黑模式下的 Spark Jobs 页面"
---

如果你曾在凌晨 2 点盯着 Spark Web UI 调试一个失败的作业，你一定体会过那种感觉：一片刺眼的白光打在眼睛上，而你还在翻阅 Stages、Executors 和 SQL 执行计划。这个时代结束了。

**Apache Spark 的 Web UI 现已支持暗黑模式**，作为 [SPARK-55766](https://issues.apache.org/jira/browse/SPARK-55766) 的一部分合入 master 分支。一键切换，记住你的偏好，尊重你的系统设置。覆盖所有页面——Jobs、Stages、SQL、Executors、Environment 等。

## 为什么需要暗黑模式？

暗黑模式不是一种视觉潮流——它是开发者生产力工具。以下是它对 Spark 用户的意义：

### 1. 减轻长时间调试的眼疲劳

Spark 作业可能运行数小时。当出现问题时，工程师需要花费大量时间在 Web UI 上——查看 DAG 可视化、阅读 Executor 日志、追踪 SQL 查询计划。暗色界面降低了屏幕与昏暗房间之间的对比度，而深夜调试正是最常见的场景。

### 2. 尊重开发者偏好

现代开发工具已经普遍采用暗黑模式——[VS Code](https://code.visualstudio.com/docs/getstarted/themes)、[GitHub](https://github.blog/news-insights/product-news/new-from-universe-2020-dark-mode-github-sponsors-for-companies-and-more/)、[IntelliJ IDEA](https://www.jetbrains.com/help/idea/user-interface-themes.html)、终端模拟器，甚至操作系统本身。当开发者的整个环境都处于暗黑模式，然后在浏览器中打开 Spark UI 时，刺眼的白色页面令人不适。Spark UI 应该成为开发者工作流程的自然组成部分，而不是一个例外。

### 3. 社区一直在呼唤

暗黑模式一直是 Spark 社区最受期待的 UI 特性之一。随着 Web UI 向 Bootstrap 5 现代化（[SPARK-55760](https://issues.apache.org/jira/browse/SPARK-55760)）迈进，基础设施终于可以正确地支持它——无需 hack、无需自定义 CSS 主题、无需额外的维护负担。

## 效果展示

以下是 Spark Web UI 在两种模式下的对比：

### Jobs 页面

| 亮色 | 暗色 |
|:----:|:----:|
| ![亮色 Jobs](/images/spark-ui/dm-light-jobs.png) | ![暗色 Jobs](/images/spark-ui/dm-dark-jobs.png) |

### SQL 查询计划可视化

| 亮色 | 暗色 |
|:----:|:----:|
| ![亮色 SQL](/images/spark-ui/dm-light-sql.png) | ![暗色 SQL](/images/spark-ui/dm-dark-sql.png) |

### Executors 页面

| 亮色 | 暗色 |
|:----:|:----:|
| ![亮色 Executors](/images/spark-ui/dm-light-executors.png) | ![暗色 Executors](/images/spark-ui/dm-dark-executors.png) |

### Environment 页面

| 亮色 | 暗色 |
|:----:|:----:|
| ![亮色 Env](/images/spark-ui/dm-light-env.png) | ![暗色 Env](/images/spark-ui/dm-dark-env.png) |

## 实现理念

我们有意选择了最简洁、最易维护的方案：

- **基于 Bootstrap 5 颜色模式。** 没有自定义 CSS 颜色系统，没有独立的样式表。Bootstrap 的 `data-bs-theme` 属性自动处理 95% 的工作——按钮、卡片、表格、导航栏和文本都会自动适配。

- **尊重系统偏好。** 首次访问时，UI 会检查 `prefers-color-scheme`——如果你的操作系统处于暗黑模式，Spark 会自动跟随。无需配置。

- **记住你的选择。** 点击一次切换按钮，`localStorage` 会在所有页面和会话中保存你的偏好。

- **无内容闪烁（FOUC）。** 一段内联脚本在页面渲染前运行，因此在暗黑模式下加载时不会出现白色闪烁。

这种理念与最优秀的开发工具处理主题的方式一致：

- **GitHub** 在 [2020 年 12 月](https://github.blog/news-insights/product-news/new-from-universe-2020-dark-mode-github-sponsors-for-companies-and-more/) 以类似的方式引入暗黑模式——尊重系统偏好、持久化用户选择、使用 CSS 自定义属性而非并行样式表。
- **VS Code** 从第一天起就支持暗黑模式，将其视为核心功能而非事后补充。
- **Grafana**——另一个工程师需要长时间注视的工具，甚至默认就是暗黑模式。

这些工具的经验告诉我们：**暗黑模式对于面向开发者的工具不是可选的，而是必需的。**

## 更大规模现代化的一部分

暗黑模式是 [SPARK-55760](https://issues.apache.org/jira/browse/SPARK-55760) 下 Spark Web UI 现代化工作的一部分。同期落地的其他改进包括：

- **[紧凑 SQL 执行计划可视化](https://github.com/apache/spark/pull/54565)** ——可点击的详情侧边面板
- **[Offcanvas 面板](https://github.com/apache/spark/pull/54589)** ——用于 Executor 详情视图
- **[表格悬停效果](https://github.com/apache/spark/pull/54620)** ——提升行可读性
- **[Bootstrap 5 工具类](https://github.com/apache/spark/pull/54615)** ——替换旧版 CSS
- **[全局页脚](https://github.com/apache/spark/pull/54657)** ——在所有页面显示版本、运行时间和用户

目标很简单：Spark Web UI 应该与它所代表的引擎一样现代。Spark 用前沿的分布式计算处理 PB 级数据——它的 UI 也应该体现这种品质。

## 来试试吧

暗黑模式将在下一个 Apache Spark 版本中发布。如果你从源码构建，它已经在 `master` 分支上了。

点击导航栏中的 **◑** 按钮即可切换。就是这么简单。

---

*本功能作为 [SPARK-55766](https://issues.apache.org/jira/browse/SPARK-55766) 的一部分贡献。欢迎在 [SPARK-55760](https://issues.apache.org/jira/browse/SPARK-55760) 上提供反馈和贡献。*
