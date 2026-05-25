---
title: "Branch Flip Analysis: A White-Box Way to Find Performance Bugs, and What It Means for Spark"
date: 2026-05-26
tags: ["spark", "query-optimizer", "performance", "testing", "catalyst"]
categories: ["Apache Spark"]
cover: /images/posts/branch-flip-analysis-cover.png
summary: "An ETH paper finds 21 previously unknown performance bugs in PostgreSQL, MySQL, CockroachDB and MariaDB by flipping optimization branches on and off. The technique is conceptually simple, the surface in Spark is unusually inviting, and the open-source engine community already ships one of the building blocks."
showToc: true
---

A paper landed on arXiv last week that is worth a second look from anyone who works on query engines: [*Finding Performance Issues in Database Systems by Exploiting Dormant Code Paths*](https://arxiv.org/abs/2605.22992) by Jinsheng Ba and Zhendong Su (ETH Zürich), arXiv:2605.22992, submitted 21 May 2026.

The headline finding is concrete: 21 previously-unknown, unique performance issues across **PostgreSQL, MySQL, CockroachDB, and MariaDB**, all surfaced with the workloads of TPC-H and TPC-DS. The technique that produced them — Branch Flip Analysis, or BFA — is conceptually simple, and the surface area in Apache Spark is unusually inviting. This post walks through what the paper does, why it works, and what an honest port to Spark would look like.

## What BFA actually is

The methodology is one sentence: **take every `if` branch that exists to turn an optimization on or off, flip it, and check whether the flipped path is significantly faster than the original path.** If it is, you have a performance bug — the optimization, by definition, is supposed to be at least neutral.

The authors implement this in a prototype called **QueryZen** and apply it to four mature open-source DBMSs. Three details make the method usable in practice rather than a flood of false positives:

1. **Differential testing for soundness.** A flipped branch must keep query results unchanged. QueryZen runs the original and flipped binaries against a corpus and discards any flip that changes outputs. The authors also manually inspect a sample to argue that the branches that survive are genuinely optimization-only (logging, caching, plan choice) rather than functional.
2. **Statistical significance.** A flip is reported only when the flipped runtime is significantly faster than the original across repeated trials. This filters out noise inherent to wall-clock benchmarking.
3. **Triage-friendly output.** Each finding is a (commit, branch, query) tuple, which means a developer can reproduce it with a single configuration toggle rather than re-deriving the workload.

Two limits the paper is honest about: results that look consistent on a given machine may shift on different hardware or memory configurations, and "true positive" is defined as "confirmed by the upstream developers" — a high bar that makes the 21 number a lower bound.

## Why this is not the same as A/B-ing a config flag

Database engines have always had configuration knobs that disable optimizations: `enable_hashjoin = off` in PostgreSQL, `optimizer_switch` in MySQL, the various `spark.sql.*` toggles in Spark. Practitioners have been flipping these for decades to debug regressions.

What BFA adds is **scale and coverage**: it does not rely on the optimizations that happen to have a config flag exposed. It targets every `if` in the source tree that the authors can classify as an optimization branch — including ones that no user-facing knob controls. Most of the 21 issues live in branches that **had no flag**. That is the part of the result that should make engine maintainers pay attention: the well-known knobs have been A/B-tested to death, but the un-flagged optimization branches buried deep in the planner and executor have not.

## The Spark surface area

Here is where this gets interesting for the Spark community. Two ingredients BFA needs are already shipped in mainline Spark:

- **A first-class way to disable a single optimizer rule.** [`spark.sql.optimizer.excludedRules`](https://spark.apache.org/docs/latest/configuration.html#runtime-sql-configuration) takes a comma-separated list of fully-qualified rule class names and removes them from the Catalyst optimizer batches. This is exactly the "branch flip" knob BFA wants — granular, declarative, and already maintained.
- **A canonical benchmark workload.** The [TPC-DS benchmark generator in `sql/core`](https://github.com/apache/spark/tree/master/sql/core/src/test/scala/org/apache/spark/sql) is already used in the project for performance regression work, and a public 99-query TPC-DS run is a familiar baseline in Spark performance discussions.

So the recipe for a Spark-side BFA is not exotic:

1. Enumerate the rules in `Optimizer.batches` and the rules registered via the SparkSessionExtensions API for a given build.
2. For each rule, run a fixed TPC-H or TPC-DS workload twice: once with the rule enabled (the default), once with the rule listed in `spark.sql.optimizer.excludedRules`. Take the median of N trials.
3. Verify that the produced query results are identical between the two runs. Discard the pair otherwise.
4. Report rule × query pairs where the rule-disabled run is significantly faster than the rule-enabled run.

There are honest complications. Optimizer rules in Catalyst are not all order-independent — disabling rule A may change whether rule B's pattern matches, so the local "what happens if I flip just this one" semantics can leak. AQE makes some of these decisions at runtime based on observed statistics, which means a deterministic flip needs deterministic inputs. And the cost of running TPC-DS once per rule, times the number of rules in modern Catalyst, is not trivial. None of those make the experiment impossible; they make it engineering work.

## What this is not

It is worth being precise about what BFA does and does not promise.

- It is **not a proof of optimality.** Finding 21 bugs in four mature systems is impressive, but BFA cannot tell you the optimizer is correct everywhere it did not flag.
- It is **not a substitute for cost-based reasoning.** The flipped branch is faster on a particular query under a particular configuration. The "fix" might be a change to a cost model or a heuristic threshold, not a wholesale removal of the optimization. Two of the false-positive categories the paper discusses are exactly this — branches whose authors made deliberate trade-offs that BFA cannot read.
- It is **not workload-free.** TPC-H and TPC-DS bias toward analytics. A BFA pass on Spark would likely miss issues that only manifest under streaming, structured streaming, or DSv2 connector-heavy workloads.

## A modest proposal, framed as a question

I am writing this in a personal capacity. But I think it is worth asking, in public, whether the open-source query engine community — Spark, Trino, DuckDB, Velox-backed engines, ClickHouse — should treat per-rule perf regression testing as part of the CI contract for new optimization work, the way most projects already treat correctness regression testing.

The materials are there. `excludedRules` already exists in Spark. Trino has [`optimizer.<rule>.disabled`](https://trino.io/docs/current/admin/properties-optimizer.html) flags for many of its optimizers. DuckDB exposes [`SET disabled_optimizers`](https://duckdb.org/docs/configuration/overview.html). Most major projects already run TPC-H or TPC-DS nightly. The missing piece is the harness: enumerate, flip, diff, report.

The cost of doing this is real — both compute time and the engineering work of distinguishing genuine regressions from deliberate trade-offs. The cost of not doing it is the kind of thing BFA just demonstrated: 21 bugs sitting in mature, well-reviewed codebases, in branches that nobody had a reason to specifically look at.

## Further reading

- The paper: [arXiv:2605.22992](https://arxiv.org/abs/2605.22992) (PDF, HTML versions linked from the abs page).
- For Spark's per-rule disable mechanism, see [`spark.sql.optimizer.excludedRules`](https://spark.apache.org/docs/latest/configuration.html#runtime-sql-configuration) in the Spark 3.5+ configuration reference.
- For prior work on automated DBMS performance testing — APOLLO ([Jung et al., 2019](https://doi.org/10.1145/3338906.3338937)), AMOEBA ([Liu et al., 2022](https://doi.org/10.1145/3510003.3510123)), CERT ([Ba et al., 2024](https://doi.org/10.1145/3641939)) — the BFA paper's related-work section is a compact map.

These are personal observations from someone who works on Apache Spark, not a project position. The materials linked above are the primary sources; please form your own view from them.
