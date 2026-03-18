---
title: "Introducing spark-history-cli: A Terminal-Native Way to Query the Spark History Server"
date: 2026-03-18
tags: ["spark", "cli", "history-server", "python", "copilot", "tooling"]
categories: ["Apache Spark"]
summary: "spark-history-cli brings the Spark History Server to your terminal — an interactive REPL and one-shot CLI that covers all 20 REST API endpoints. List apps, inspect jobs, drill into stages, check SQL executions, and download event logs without ever opening a browser. It also ships as a GitHub Copilot CLI skill."
showToc: true
---

The Spark History Server has a decent web UI and a comprehensive REST API. But if you're already in the terminal — SSH'd into a gateway node, debugging a pipeline in CI, or scripting a post-mortem — switching to a browser feels like a context switch you shouldn't need to make.

**[spark-history-cli](https://github.com/yaooqinn/spark-history-cli)** puts the entire Spark History Server at your fingertips. It's a Python CLI that wraps all 20 REST API endpoints into an interactive REPL and one-shot commands. List applications, drill into jobs and stages, inspect SQL executions, check executor stats, download event logs — all from your terminal.

## Install

```bash
pip install spark-history-cli
```

That's it. Requires Python 3.10+ and a running Spark History Server.

## Two Modes of Operation

### Interactive REPL

Just run `spark-history-cli` to enter the REPL:

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

The `use` command sets a "current app" context, so you don't have to repeat the app ID on every command. It works exactly like `USE database` in SQL.

### One-Shot Commands

For scripting, CI pipelines, or quick lookups:

```bash
# List completed apps
spark-history-cli apps --status completed --limit 10

# Check jobs for a specific app
spark-history-cli --app-id app-20260318091500-0003 jobs

# Download event logs for offline analysis
spark-history-cli --app-id app-20260318091500-0003 logs ./events.zip

# JSON output for piping into jq or other tools
spark-history-cli --json --app-id app-20260318091500-0003 stages
```

The `--json` flag outputs raw JSON — perfect for piping into `jq`, feeding into monitoring scripts, or integrating with other tools.

## What You Can Do

The CLI covers **all 20 endpoints** of the Spark History Server REST API:

| Command | What It Does |
|---------|-------------|
| `apps` | List all applications with status, time, duration |
| `app <id>` | Show application details and set as current |
| `jobs` | List jobs with status, stages, and duration |
| `job <id>` | Show detailed job info |
| `stages` | List all stages |
| `stage <id>` | Show stage details with task summary |
| `executors` | List active executors |
| `executors --all` | Include dead executors |
| `sql` | List SQL executions |
| `sql <id>` | Show SQL execution details with plan graph |
| `rdds` | List cached RDDs |
| `env` | Show Spark configuration and environment |
| `logs [path]` | Download event logs as ZIP |
| `version` | Show History Server Spark version |

## Why Not Just Use the Web UI?

The web UI is great when you're sitting at a browser. But there are real scenarios where a CLI is better:

**SSH debugging.** You're on a jump host or gateway node troubleshooting a production cluster. No browser, no port forwarding — just a terminal. `spark-history-cli --server http://shs:18080 apps` gets you started immediately.

**Scripting and automation.** Want to check if yesterday's ETL jobs all succeeded? Write a cron job that runs `spark-history-cli --json apps --status failed` and alerts on non-empty output. The `--json` flag makes this trivial.

**Post-mortem workflows.** Download event logs with `logs`, cross-reference job durations with `jobs`, check executor memory with `executors --all` — all in one terminal session without clicking through multiple browser tabs.

**CI/CD integration.** After submitting a Spark application in a pipeline, query the History Server to verify the job completed successfully, check stage metrics, or archive event logs as build artifacts.

## GitHub Copilot CLI Skill

spark-history-cli also ships as a **GitHub Copilot CLI skill**. Install it with:

```bash
spark-history-cli install-skill
```

This copies the bundled skill definition to `~/.copilot/skills/spark-history-cli`. After reloading skills (`/skills reload`), you can use natural language prompts like:

```
Use /spark-history-cli to inspect the latest completed SHS application.
```

Copilot CLI will invoke the tool, interpret the output, and answer your questions about Spark application history in conversational English — no need to remember command syntax.

## Configuration

The server URL defaults to `http://localhost:18080`. Override it with:

```bash
# CLI flag
spark-history-cli --server http://my-shs:18080

# Environment variable
export SPARK_HISTORY_SERVER=http://my-shs:18080
spark-history-cli

# REPL command (change on the fly)
spark-history> server http://another-shs:18080
```

## Get Started

```bash
pip install spark-history-cli
spark-history-cli
```

The source is on GitHub: [yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli). It's Apache 2.0 licensed. Issues, PRs, and feedback are welcome.

---

*[spark-history-cli](https://pypi.org/project/spark-history-cli/) v1.0.1 is available on PyPI. Source code at [github.com/yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli).*
