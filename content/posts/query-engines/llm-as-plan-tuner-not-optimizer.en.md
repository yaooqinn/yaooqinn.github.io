---
title: "LLMs Shouldn't Replace the Query Optimizer — They Should Sit Behind It"
date: 2026-05-27
tags: ["llm", "query-optimization", "spark", "datafusion", "physical-plan"]
categories: ["query-engines"]
summary: "Putting the LLM after the optimizer, emitting JSON patches for local plan tuning, is easier to reason about as engineering than asking it to replace the cost-based optimizer."
cover:
  image: "/images/posts/llm-as-plan-tuner-cover.png"
  alt: "LLM as plan-tuner, sitting behind the optimizer"
  relative: false
showToc: true
---

![LLM as plan-tuner, sitting behind the optimizer](/images/posts/llm-as-plan-tuner-cover.png)

My previous three posts ([LLM × join order](/posts/query-engines/llm-only-rewrite-doesnt-work/) · [the blind spot of rule-based rewrites](/posts/query-engines/rule-rewrite-blindspot-dsb/) · [anatomy of a 120-line prompt](/posts/query-engines/prompt-anatomy-for-plan-generation/)) all asked the same question from different angles: **how should an LLM participate in query optimization?** Those posts dissected mechanism — rewriting SQL text, rewriting plans, the prompt that drives the rewrite. This one asks a different question: **where in the optimizer pipeline does the LLM belong?**

My answer: **behind the optimizer**, emitting small patches, not replacing the cost-based optimizer. This is not a claim about technical novelty. It is a claim about engineering governance.

## Three routes, laid out

Across the LLM × QO work I've read this year, the integration paths fall into roughly three buckets:

| Route | Representative work | What the LLM emits | Output granularity |
|---|---|---|---|
| **A. Rewrite SQL text** | (SQL → SQL rewriting, covered in earlier posts) | Rewritten SQL string | Whole statement |
| **B. LLM makes plan decisions directly** | Databricks 2026-04 blog: LLM agent picking join order[^1] | A specific decision (e.g. join order) | Whole-plan dimension |
| **C. LLM emits patches against the optimizer's plan** | DBPlanBench (arXiv:2602.10387)[^2] | RFC 6902–style JSON Patch | Local edits |

A has been discussed. Its core difficulty is that the SQL text layer doesn't carry enough information to fix problems that only show up in the physical plan (join order, projection column order, operator choice). B and C differ in a finer way, which is what this post is about.

## Why the patch route is worth taking seriously

DBPlanBench is the most complete open-source implementation of route C. The workflow: let DataFusion compile SQL to a physical plan using its own optimizer, flatten that plan into JSON, feed it to GPT-5, **have the LLM emit RFC 6902[^3] JSON patches** (e.g. swap a hash join's build/probe sides), and apply the patches back to DataFusion for real execution.

On TPC-H and TPC-DS (SF=3/10), the paper reports **up to 4.78× speedup on individual queries**[^2]. That number is not the point of this post — I want to surface its caveats first:

- The baseline is DataFusion's own optimizer; there is no head-to-head against learned optimizers (Bao/Balsa) or against Photon / Spark CBO.
- The experiments stop at SF=10 (<10 GB), not TB.
- "Transfer to larger scale" is demonstrated only between SF=3 and SF=10, via a one-shot deterministic rewrite script — not a true TB-scale validation.

So I'd read 4.78× as **"the improvement headroom in DataFusion's current physical optimizer on these queries"**, not as "LLM beats cost-based optimizer." That framing matters, because the rest of this post is about architectural choices, not about who wins on accuracy.

What actually makes route C interesting relative to route B is three properties **that have nothing to do with accuracy**.

## Argument 1 · A patch is the smallest unit you can review

Anyone who has written a Catalyst rewrite rule in Spark (`PushDownPredicates`, `ColumnPruning`, and friends) knows a common review difficulty: **after a rule mutates a `LogicalPlan`, the diff is structural, and it is hard to see at a glance which fibre the rule actually pulled**.

JSON Patch gives you a smaller unit:

```json
[
  { "op": "replace", "path": "/nodes/3/build_side", "value": "left" },
  { "op": "remove",  "path": "/nodes/5" }
]
```

Each patch is atomic. It can be reverted independently. It can have a single regression test pinned to it. From an engineering-governance standpoint, **I'd argue this is more controllable than "we wrote a new rule" or "the agent picked this join order"** — particularly compared to route B, where the LLM agent emits "use this join order" with no diff. You either trust the agent's choice or you don't.

This is not an argument that patches are always correct. It is an argument that **when they're wrong, you can point at exactly which patch was wrong**.

## Argument 2 · OLAP queries repeat — API cost amortises

Per-query LLM cost is the first engineering objection to any "LLM in the optimizer" proposal.

The DBPlanBench paper reports per-query optimization cost typically in "a few cents"[^2]. I can't independently reproduce that number, but it points at a useful framing: **OLAP workloads have one defining property — the same query template runs over and over**. Dashboards, scheduled reports, ETL — running a query a thousand times is normal. If a few cents of LLM call buys a patch that's reused a thousand times, the economics work.

The paper also has a detail that supports this view: an optimization the LLM found on SF=3 was carried over to SF=10 via a **one-shot deterministic rewrite script**[^2], retaining the speedup. The scalability of that mechanism still needs validation on bigger data (the paper doesn't show SF=100/1000), but the pattern it points at is the right one: **find once with an LLM, reuse as a rule for a long time**. Not invoke the LLM on every execution.

By contrast, in route B the agent goes through its reasoning loop every time. The amortisation path is not natural.

To be honest: the paper does not include a "after how many reuses does the patch pay for itself" experiment either. Until someone publishes that curve on real workloads, "amortisable" is a hypothesis, not a conclusion.

## Argument 3 · Patch caches can become real infrastructure

If you accept the "find once, reuse many" model, the patch is no longer a one-off optimization result. It is **an asset — indexable by query signature, storable, auditable**.

That opens several natural engineering extensions:

1. **Dedupe by query signature**: same query template with different literals, the same patch likely still applies.
2. **A/B and shadow execution**: a patch can hang off the plan, run as shadow, only become active after measured wins.
3. **Audit trail**: every applied patch is logged, so "which query was changed by whose patch" is answerable.

This is well-aligned with practices SQL gateways already run — signature-keyed plan caches, plan-level audit logs. The LLM's role here is closer to "patch generator" than "runtime decision maker."

## Where to plug in on Spark — the hook already exists

If you wanted to actually try this on Spark, the API surface is already there. `SparkSessionExtensions` exposes `injectPlannerStrategy`, `injectOptimizerRule`, and `injectPostHocResolutionRule` extension points[^4]; in particular, `injectPlannerStrategy` lets you register a `SparkStrategy` that runs during logical → physical conversion — **exactly after the optimizer has done its work and before execution begins**. A patch applier can plug in there.

The real engineering bottleneck is not the API. It is **serialisation/deserialisation between `SparkPlan` and JSON**. Catalyst plan tree nodes don't ship with an official JSON codec.

From what I can tell, that codec is the prerequisite the patch route needs before anything else lands. DBPlanBench's flat node-id schema on DataFusion (node id + input/left/right references) is a reasonable reference point.

## LLM-PM is a separate route, not a cheaper C

There is one obvious objection to address head-on: **if you want an LLM helping pick plans, isn't training-free plan retrieval cheaper?**

There is such work. **LLM-PM** (arXiv:2506.05853)[^5] uses `text-embedding-3-large` to embed `EXPLAIN` plan text into vectors; for a new query it runs KNN against a history of past plans and applies the most similar historical plan's shape. Fully training-free. On OpenGauss + JOB-CEB the paper reports **mean −21% latency**.

Look at the distribution: **about 20% of queries are slowed down, 60% unchanged**[^5]. The mean −21% is driven by a minority of queries getting a large speedup — which is a well-known reporting-discipline problem in this area. Any "mean +N%" result deserves the follow-up: "what's the speed-up / slow-down / no-change distribution?"

But distribution isn't the main point. The main point is that **LLM-PM and DBPlanBench are not solving the same problem**:

- **LLM-PM** = retrieve and apply an existing plan. **It cannot create new structure.** Whatever isn't in the history library falls back to baseline.
- **DBPlanBench** = generate new plan variants. **It can produce structures the original optimizer never explored**, at the cost of paying a GPT-5 call.

So this isn't "cheaper vs. more expensive." It's two different jobs: **retrieval reuses what's known; generation fills what's missing**. A realistic deployment probably stacks them — try KNN first, fall back to LLM patch generation on miss — rather than choosing one.

## Closing — what the next experiment should actually measure

The discussion of "LLM in the query optimizer" has often stalled at "can it replace the cost-based optimizer?" That may be the wrong question.

**Putting it behind the optimizer, doing last-mile tuning via patches**, looks better than the alternatives on three engineering properties: small output granularity is review-friendly; the amortisation model is clean and fits OLAP's repeating-query nature; and the landing hook in engines like Spark already exists (`SparkSessionExtensions.injectPlannerStrategy`).

But to move this from "engineering-plausible" to "benchmark-proven," what's missing isn't more framing — it's a concrete set of numbers. If I had to name what the next round of work should report, it would be these:

1. **Spark CBO + AQE as baseline, TPC-DS SF≥100, how much head-room is left for patches on top-cost queries.** 4.78× is from DataFusion at SF=10; what's left on a mature CBO at TB scale is the real question.
2. **Patch cache hit-rate curves**: same template, different literals — how often the patch still applies; when it doesn't, what selectivity drift caused the miss.
3. **Payback curves**: how many reuses, on average, does a patch need to cover its LLM-generation cost, on real dashboard traffic.
4. **Regression rate**: corresponding to LLM-PM's 20% slowdown share, what does the patch route show on the same benchmarks, and is there auto-detection + auto-revert.

Until those numbers exist, this post is a direction, not a conclusion. If I were running the experiment myself, the first thing I'd build is the `SparkPlan ↔ JSON` codec — the LLM, the rule-isation, the cache all attach to it, but without the codec the route can't take a single step.

---

[^1]: Databricks Blog. "Are LLM agents good at join order optimization?" 2026-04-22. <https://www.databricks.com/blog/are-llm-agents-good-join-order-optimization>
[^2]: Erol M.H., Hao X., Bianchi F., Greco C., Tagliabue J., Zou J. "Making Databases Faster with LLM Evolutionary Sampling." arXiv:2602.10387. <https://arxiv.org/abs/2602.10387> · Code (MIT): <https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling>
[^3]: IETF RFC 6902: JavaScript Object Notation (JSON) Patch. <https://datatracker.ietf.org/doc/html/rfc6902>
[^4]: Apache Spark API: `org.apache.spark.sql.SparkSessionExtensions` — `injectOptimizerRule` / `injectPlannerStrategy` / `injectPostHocResolutionRule`. <https://spark.apache.org/docs/latest/api/java/org/apache/spark/sql/SparkSessionExtensions.html>
[^5]: arXiv:2506.05853, "Training-Free Query Optimization via LLM-Based Plan Similarity." <https://arxiv.org/abs/2506.05853>
