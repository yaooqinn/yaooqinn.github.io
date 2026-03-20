---
title: "Introducing spark-advisor: An AI-Powered Spark Performance Engineer"
date: 2026-03-20
tags: ["spark", "performance", "agent-skill", "debugging", "tpc-ds"]
categories: ["Apache Spark"]
summary: "spark-advisor is an agent skill that turns your AI coding assistant into a Spark performance engineer — diagnosing slow jobs, detecting skew, comparing benchmark runs, and producing actionable tuning recommendations."
showToc: true
---

Every Spark engineer has been there. A job that ran fine yesterday is now 3x slower. Someone asks "why is this query slow?" and you spend the next hour clicking through the Spark History Server UI, eyeballing numbers across tabs, mentally diffing configurations.

What if your AI assistant could do that for you?

## What is spark-advisor?

**spark-advisor** is an agent skill that turns your AI coding assistant into a Spark performance engineer. It works with GitHub Copilot, Claude Code, Cursor, and 30+ other agents.

When you say *"why is my Spark app slow?"* or *"compare these two TPC-DS runs"*, the agent:

1. Connects to your Spark History Server via `spark-history-cli`
2. Collects structured JSON data (summary, stages, executors, SQL plans)
3. Applies diagnostic heuristics to find bottlenecks
4. Produces a prioritized report with actionable recommendations

No manual clicking. No context-switching. Just ask.

## Quick Start

Install the CLI and skill:

```bash
pip install spark-history-cli
npx skills add yaooqinn/spark-history-cli
```

Then tell your agent:

> "Diagnose the latest Spark app on my History Server"

That's it. The agent will list apps, pick the latest, collect metrics, analyze them, and tell you what's wrong.

## What It Diagnoses

The skill encodes the diagnostic instincts of an experienced Spark engineer into structured rules. Here's what it checks:

### Task Skew

The single most common Spark performance killer. spark-advisor fetches task metric quantiles and compares p50 vs p95:

- **p95/p50 > 3x** → moderate skew
- **p95/p50 > 10x** → severe skew

It then recommends: AQE skew join, partition count tuning, or key salting — depending on the root cause.

### GC Pressure

When GC time exceeds 10% of total executor runtime, spark-advisor flags it. At 20%+, it's marked severe. Recommendations range from increasing executor memory to reducing per-executor concurrency.

### Shuffle Overhead

Shuffle-heavy stages are detected when shuffle bytes exceed 2x the input size. The skill checks for redundant exchanges in the plan, wrong join strategies (SortMergeJoin where BroadcastHashJoin would work), and insufficient partition counts.

### Memory Spill

Any non-zero `memoryBytesSpilled` or `diskBytesSpilled` triggers an alert. Spill means the executor ran out of memory for aggregation or sort buffers — a problem that's invisible in the UI unless you know where to look.

### Straggler Tasks

Tasks that take 5x+ longer than the median in their stage. spark-advisor checks if the stragglers are on specific executors (hardware issue) or processing more data (skew variant).

### Gluten/Velox Awareness

For Gluten-accelerated Spark, the skill detects:

- **Fallback operators**: Non-Transformer nodes in the final plan (e.g., `SortMergeJoin` instead of `ShuffledHashJoinExecTransformer`)
- **Columnar-to-row transitions**: `VeloxColumnarToRow` boundaries that indicate fallback
- **Native metric patterns**: Different GC and memory profiles in Gluten vs vanilla stages

## TPC-DS Benchmark Comparison

One of spark-advisor's most powerful features is structured benchmark comparison. Say:

> "Compare these two TPC-DS runs: app-20260315120000-0001 and app-20260320120000-0001"

The agent will:

1. Match queries across runs (q1–q99, handling split queries like q14a/b, q23a/b)
2. Calculate per-query speedup and regression
3. Produce a comparison table:

```
| Query | Baseline | Candidate | Delta  | Speedup | Status       |
|-------|----------|-----------|--------|---------|--------------|
| q67   | 72s      | 85s       | +13s   | 0.85x   | ⚠ REGRESSED  |
| q1    | 61s      | 45s       | -16s   | 1.36x   | ✓ IMPROVED   |
| q50   | 34s      | 33s       | -1s    | 1.03x   | ≈ NEUTRAL    |
```

4. Drill into the top-3 regressions — comparing final plans, stage metrics, and config diffs
5. Report overall speedup (geometric mean across all queries)

This replaces hours of manual spreadsheet work after a benchmark run.

## The Diagnostic Report

spark-advisor produces a structured Markdown report:

```markdown
# Spark Performance Report

## Executive Summary
The application spent 65% of total time in 3 shuffle-heavy stages.
GC pressure is moderate (12% of executor time). Task skew detected
in stage 14 (p95/p50 = 8.2x).

## Findings
### Finding 1: Severe Task Skew in Stage 14
- **Severity**: High
- **Evidence**: p95 duration 45s vs p50 5.5s (8.2x ratio)
- **Recommendation**: Enable AQE skew join optimization

### Finding 2: GC Pressure on Executors 3, 7
- **Severity**: Medium
- **Evidence**: 18% GC time (threshold: 10%)
- **Recommendation**: Increase spark.executor.memory from 4g to 8g

## Recommendations
1. Enable spark.sql.adaptive.skewJoin.enabled=true
2. Increase executor memory to 8g
3. Review join strategy for stage 14 — consider broadcast join
```

## How It Works Under the Hood

spark-advisor is a pure SKILL.md — no code, just structured instructions that teach the agent how to be a Spark performance engineer. It uses:

- **spark-history-cli** for all data collection (`--json` mode for structured output)
- **Diagnostic rules** in `references/diagnostics.md` with specific thresholds and heuristics
- **Comparison methodology** in `references/comparison.md` for TPC-DS benchmarks
- **Sample scripts** in `sample_codes/` for common patterns

The agent reads these references, applies the rules to your data, and reasons about the results. No model fine-tuning, no training data — just well-structured domain knowledge.

## Installation

```bash
# Install the CLI
pip install spark-history-cli

# Install skills for your agent
npx skills add yaooqinn/spark-history-cli
```

This installs two skills:
- **spark-history-cli** — Query the Spark History Server
- **spark-advisor** — Diagnose, compare, and optimize

## What's Next

- **Auto-remediation**: Suggest config patches that can be applied directly
- **Historical trending**: Track performance across releases
- **Visualization**: Generate SVG flamecharts and DAG annotations

---

*spark-advisor is open source at [github.com/yaooqinn/spark-history-cli](https://github.com/yaooqinn/spark-history-cli). Star it if you find it useful.*
