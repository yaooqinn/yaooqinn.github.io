---
title: "spark-history-cli：在终端里查询 Spark History Server"
date: 2026-03-18
tags: ["spark", "cli", "history-server", "python", "copilot", "tooling"]
categories: ["Apache Spark"]
summary: "spark-history-cli 将 Spark History Server 带到你的终端——一个交互式 REPL 和一次性命令行工具，覆盖全部 20 个 REST API 端点。列出应用、检查作业、深入 Stage、查看 SQL 执行、下载事件日志，无需打开浏览器。还可以作为 GitHub Copilot CLI 技能使用。"
showToc: true
---

Spark History Server 有不错的 Web UI 和完善的 REST API。但如果你已经在终端里——SSH 到网关节点、在 CI 里调试管道、或者编写事后分析脚本——切到浏览器总感觉是一次不必要的上下文切换。

**[spark-history-cli](https://github.com/yaooqinn/spark-history-cli)** 把整个 Spark History Server 放到你指尖。它是一个 Python CLI 工具，将全部 20 个 REST API 端点封装为交互式 REPL 和一次性命令。列出应用、深入作业和 Stage、检查 SQL 执行、查看 Executor 状态、下载事件日志——全在终端里完成。

## 安装

```bash
pip install spark-history-cli
```

就这样。需要 Python 3.10+ 和一个运行中的 Spark History Server。

## 两种使用方式

### 交互式 REPL

直接运行 `spark-history-cli` 进入 REPL：

```bash
$ spark-history-cli --server http://my-shs:18080

spark-history> apps --status completed --limit 5
ID                           Name           Status     Start Time           Duration
app-20260318091500-0003      ETL Pipeline   COMPLETED  2026-03-18 09:15:00  4m 32s
app-20260318080000-0002      Daily Report   COMPLETED  2026-03-18 08:00:00  12m 15s
...

spark-history> use app-20260318091500-0003
Current app: app-20260318091500-0003 (ETL Pipeline)

spark-history> jobs
Job ID  Status     Stages  Duration  Description
0       SUCCEEDED  3/3     1m 02s    save at ETLPipeline.scala:45
1       SUCCEEDED  2/2     2m 18s    save at ETLPipeline.scala:78
2       SUCCEEDED  1/1     1m 12s    save at ETLPipeline.scala:112

spark-history> stages
spark-history> sql
spark-history> executors
spark-history> env
```

`use` 命令设置"当前应用"上下文，这样你不用在每个命令里重复 app ID。就像 SQL 里的 `USE database` 一样。

### 一次性命令

适用于脚本、CI 管道或快速查询：

```bash
# 列出已完成的应用
spark-history-cli apps --status completed --limit 10

# 查看指定应用的作业
spark-history-cli --app-id app-20260318091500-0003 jobs

# 下载事件日志用于离线分析
spark-history-cli --app-id app-20260318091500-0003 logs ./events.zip

# JSON 输出，方便管道处理
spark-history-cli --json --app-id app-20260318091500-0003 stages
```

`--json` 标志输出原始 JSON——可以直接管道到 `jq`，喂给监控脚本，或与其他工具集成。

## 功能概览

CLI 覆盖 Spark History Server REST API 的 **全部 20 个端点**：

| 命令 | 功能 |
|------|------|
| `apps` | 列出所有应用，含状态、时间、耗时 |
| `app <id>` | 查看应用详情并设为当前应用 |
| `jobs` | 列出作业，含状态、Stage 数和耗时 |
| `job <id>` | 查看作业详情 |
| `stages` | 列出所有 Stage |
| `stage <id>` | 查看 Stage 详情和任务汇总 |
| `executors` | 列出活跃 Executor |
| `executors --all` | 包含已失效的 Executor |
| `sql` | 列出 SQL 执行记录 |
| `sql <id>` | 查看 SQL 执行详情和计划图 |
| `rdds` | 列出缓存的 RDD |
| `env` | 查看 Spark 配置和环境变量 |
| `logs [path]` | 下载事件日志（ZIP 格式） |
| `version` | 查看 History Server 的 Spark 版本 |

## 为什么不直接用 Web UI？

Web UI 在有浏览器的时候很好用。但有些场景下 CLI 更合适：

**SSH 调试。** 你在跳板机或网关节点上排查生产集群问题，没有浏览器，不想做端口转发——只有终端。`spark-history-cli --server http://shs:18080 apps` 立即开始工作。

**脚本和自动化。** 想检查昨天的 ETL 作业是否全部成功？写一个 cron 任务运行 `spark-history-cli --json apps --status failed`，输出非空就告警。`--json` 标志让这一切变得简单。

**事后分析工作流。** 用 `logs` 下载事件日志，用 `jobs` 对比作业耗时，用 `executors --all` 检查 Executor 内存——全在一个终端会话里完成，不用在多个浏览器标签页间来回切换。

**CI/CD 集成。** 在管道中提交 Spark 应用后，查询 History Server 验证作业是否成功完成、检查 Stage 指标、或将事件日志归档为构建产物。

## GitHub Copilot CLI 技能

spark-history-cli 还可以作为 **GitHub Copilot CLI 技能** 使用。安装方式：

```bash
spark-history-cli install-skill
```

这会将内置的技能定义复制到 `~/.copilot/skills/spark-history-cli`。重新加载技能（`/skills reload`）后，你可以用自然语言提示：

```
Use /spark-history-cli to inspect the latest completed SHS application.
```

Copilot CLI 会调用工具、解读输出，并用对话的方式回答你关于 Spark 应用历史的问题——无需记住命令语法。

## 配置

服务器 URL 默认为 `http://localhost:18080`。覆盖方式：

```bash
# 命令行参数
spark-history-cli --server http://my-shs:18080

# 环境变量
export SPARK_HISTORY_SERVER=http://my-shs:18080
spark-history-cli

# REPL 中动态切换
spark-history> server http://another-shs:18080
```

## 开始使用

```bash
pip install spark-history-cli
spark-history-cli
```

源码在 GitHub：[yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli)，基于 Apache 2.0 许可证。欢迎提 Issue、PR 和反馈。

---

*[spark-history-cli](https://pypi.org/project/spark-history-cli/) v1.0.1 已发布在 PyPI。源码：[github.com/yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli)。*
