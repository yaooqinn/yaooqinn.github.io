---
title: "LLMs for Join Order: An Apache Spark Perspective on the Three-Tier Ladder"
date: 2026-05-25
tags: ["spark", "query-optimizer", "llm", "join-order", "performance"]
categories: ["Apache Spark"]
summary: "Databricks and UPenn put an LLM agent to work as an offline join-order tuner and got P90 latency down 41% / geomean 1.288× speedup on JOB's 113 queries — beating even perfect cardinality estimates. From the trenches of an open-source query engine, here is what that result does and does not prove."
showToc: true
---

In April 2026, Databricks Engineering published a piece with UPenn called [*Are LLM agents good at join order optimization?*](https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization). The headline numbers were eye-catching: on the 113 queries of the [Join Order Benchmark (JOB)](https://www.vldb.org/pvldb/vol9/p204-leis.pdf), the join orders chosen by an LLM agent dropped Databricks Runtime's P90 latency by 41% and delivered a 1.288× geomean speedup — **better than what you get by feeding the optimizer perfect cardinality estimates**, and better than [BayesQO](https://rm.cab/bayesqo), an offline Bayesian optimizer.

If you have spent any time around query engines, your first reaction is probably skepticism. After reading the original post and the [UPenn follow-up](https://ucbskyadrs.github.io/blog/databricks/), most of mine went away — but a few observations are worth pulling out, especially in the context of an open-source engine like Apache Spark.

## What the study actually does

Stripped of marketing, the setup is surprisingly modest:

- **The agent does not enter the hot path.** It does not replace the cost-based optimizer. It does not run inside the ms-level query compiler. It does what human DBAs have done by hand for decades — **try plans offline, repeatedly, with feedback** — and automates that loop.
- **A single tool.** The agent has exactly one: `execute(plan)`, which returns wall-clock runtime plus the true cardinality of each subtree.
- **Structured output.** A grammar constrains the agent to emit only well-formed join orders, eliminating the need for any LLM-output validation logic.
- **Adjustable budget.** This is an anytime algorithm. The reported numbers use 15 rollouts per query; the agent keeps improving up to ~50 iterations.

The dataset is IMDb scaled 10× to about 20GB. Baselines include the default DBR optimizer, the same optimizer fed perfect cardinality estimates, a smaller-model agent, and BayesQO. The result is the headline above.

One case study (`q5b`) tells the story well. It is a 5-way join. The default DBR optimizer starts from "American VHS company" (12 rows, looks the most selective). The agent flips it around and starts by filtering "VHS releases referencing 1994" — because a `LIKE` predicate caused the CBO to mis-estimate cardinality there by an order of magnitude.

## Why "beating perfect cardinality" is not as mystical as it sounds

This is the most easily-misread claim in the post.

"Perfect cardinality estimates" sounds like a mathematical lower bound — if every step's true row count is given to the optimizer, how can an LLM still win?

The answer: **the cost model itself is not perfect.**

Every cost-based optimizer relies on two approximations:

```
cardinality   →   cost (CPU + I/O + network + shuffle)   →   wall-clock time
        ^approx 1                                  ^approx 2
```

The paper eliminates the first one by injecting perfect cardinalities. But the second one — the mapping from cost to actual time — is still there. The constants inside any cost model (shuffle rate, broadcast thresholds, spill penalties) reflect the hardware assumptions of the era they were tuned in. On NVMe / large memory / columnar / vectorized engines, those constants are routinely off.

The agent wins by **bypassing both approximations**: it observes the wall-clock returned by `execute(plan)` directly, trading trial-and-error cost for model bias.

That is not the LLM transcending mathematical optimality. It is **trial-and-error beating modeling** — a statement that only carries weight once you accept that the cost model is itself imperfect.

## A three-tier ladder for LLMs × query optimizers

Flatten every "LLM + query optimization" proposal you have ever seen, and they tend to fit into one of three tiers:

| Tier | Role | Latency budget | Engineering difficulty | Realistic today? |
|---|---|---|---|---|
| **L1 Hot-path replace** | Generate the final plan during compilation | ms | Very high (LLMs are too slow, expensive, non-deterministic) | ❌ Not realistic yet |
| **L2 Hint generation (online)** | Provide hints (join order, broadcast choice) at compile time | tens of ms ~ seconds | High (must coexist with ms-level compiler) | ⚠️ Partially feasible, needs to be async |
| **L3 Offline tuning + hint writeback** | Pick queries offline, tune with an agent, persist results as hints / MVs / stats | minutes ~ hours | Medium (fully offline, no SLA pressure) | ✅ Now demonstrated |

Databricks picked **L3**. That is a deeply pragmatic engineering call, worth unpacking:

1. **It does not block the query path.** Any online LLM call has 100+ ms of TTFB, which alone destroys interactive OLAP latency. L3 sidesteps this entirely.
2. **Failures are recoverable.** If the agent picks badly, discard the hint and run the query the old way. The downside of an L3 miss is one extra query execution. L1 and L2 failures pollute production traffic.
3. **The ROI is quantifiable.** "This query runs 200 times a day; the agent's one-time tuning saves 30% per run" is the kind of arithmetic that easily justifies the budget.
4. **Naturally anytime.** Strict-SLA queries get 5 rollouts; reports / ETL get 50. The "spend an hour tuning to save 30 minutes a day" model works.

**L3 is the most realistic productization path for LLMs × QO in 2026–2027.** L2 becomes interesting once inference prices fall another order of magnitude. L1 needs longer still.

## What this means for the Apache Spark ecosystem

Spark's join reordering goes through `JoinReorderDP` (the DPhyp algorithm) plus cost-based estimation, and the weak points are the same as in DBR: `LIKE` / range / string predicate cardinality, and stale hardware constants inside the cost model. The path Databricks walked is reproducible on OSS Spark, and open source actually has structural advantages here:

- **Statistics are accessible.** `DESCRIBE EXTENDED`, `ANALYZE TABLE`, column histograms — the true cardinality feedback the agent needs is already exposed by Spark APIs.
- **Plan history is accessible.** Spark UI, Spark History Server, SQL execution event logs — the raw material for both training the agent and feeding it candidate queries already exists.
- **Hint machinery is mature.** `/*+ BROADCAST(t) */`, `/*+ MERGE(t1, t2) */`, `/*+ SHUFFLE_HASH */`, `/*+ JOIN_REORDER */` — the plan an agent picks can be expressed as a hint without touching Catalyst.

If someone wanted to take L3 to OSS Spark, the shortest path looks roughly like:

1. **Mine the SQL execution event log for slow queries** — recurring, long wall-clock, wide join trees.
2. **Build the single tool** — an endpoint that accepts a join order, runs `EXPLAIN ANALYZE`, and returns the true cardinality and runtime of each child.
3. **Run N rollouts** (start at 15, give SLA-loose queries up to 50).
4. **Decompile the winning plan into a Spark hint** and persist it through any layer that can intercept SQL after parsing but before the optimizer — a gateway, a JDBC proxy, a SQL view layer, or a catalog-level hint table.
5. **Keep monitoring.** When statistics shift or table distributions drift, the tuning should fire again. Open source can do this better than Databricks does, because the community could co-design a cross-engine hint-catalog spec.

A note on vectorized execution (Gluten / Velox / Photon / Comet): join reordering still happens in Spark Catalyst. Native engines consume the plan; they do not rewrite it. **L3 is a Catalyst-layer story. Getting it right on classic Spark already captures most of the upside, well before any vectorized engine work is required.**

## Open questions the post leaves unanswered

The more carefully you read the piece, the more numbers you want to leave a question mark next to:

1. **How much does it cost in tokens?** 50 rollouts × N tokens × frontier-model price might exceed the query time saved. This is the core question for L3 viability, and the blog does not address it head-on.
2. **Which frontier model?** The piece only says "frontier model" — no GPT-5 / Claude / Gemini, no version. That means the result is sensitive to a moving target and hard to reproduce.
3. **The dataset is small.** 20GB of IMDb does not stand in for TPC-DS at 1TB. The generalization story for longer queries, wider fact tables, and large dimension tables is open.
4. **Which DBR version?** Spark 3.5? DBR 15? Without knowing the baseline runtime, you cannot separate "the agent's contribution" from "regular DBR runtime improvements."
5. **No code release.** Until UPenn or someone else publishes a minimum implementation that runs on PostgreSQL or Spark, the community cannot reproduce this independently.

## A closing note

The most interesting thing about L3 is that it turns decades of hand-tuned DBA craft into an **automatable loop, for the first time**.

This story does not need anyone to bet on "LLMs replacing the query optimizer" — a vision that may never arrive. It only needs an LLM to be marginally better than heuristics at one verifiable, recoverable task: try plans, submit the best one. That bar has now been cleared.

For open-source engine communities, the signal is clear. **L3 is a low-risk, quantifiable direction with real benchmark backing.** What is needed next is for someone to do the open-source reproduction on Spark / Trino / DuckDB and close at least one or two of those five open questions.

If you are working on this, I would love to compare notes. Find me at [@yaooqinn](https://github.com/yaooqinn).

---

**References**

- Databricks Engineering · [*Are LLM agents good at join order optimization?*](https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization) · 2026-04-22
- UPenn Sky-ADRs · [*How do LLM agents think through SQL join orders?*](https://ucbskyadrs.github.io/blog/databricks/)
- Leis et al. · [*How Good Are Query Optimizers, Really?*](https://www.vldb.org/pvldb/vol9/p204-leis.pdf) · VLDB 2015 (the original JOB paper)
- [BayesQO](https://rm.cab/bayesqo) — an offline Bayesian optimizer used as a baseline in the study
