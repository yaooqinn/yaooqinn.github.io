---
title: "Just Asking an LLM to Rewrite SQL Does Almost Nothing"
date: 2026-05-26
tags: ["query-optimizer", "llm", "sql-rewrite", "performance", "fine-tuning"]
categories: ["Query Engines"]
summary: "On TPC-H 10GB, asking GPT-4o to rewrite SQL takes mean execution time from 78.81s down to 74.92s — almost nothing. Swap in an open 14B model, feed it plans, add a reward, fine-tune once, and the same workload drops to 29.67s. Whether LLMs can help SQL rewriting is not a question about model strength; it's a question about whether you're willing to give the model the signals it actually needs."
cover:
  image: /images/posts/llm-only-rewrite-cover.png
  relative: false
showToc: true
---

My previous post covered the Databricks × UPenn [LLM-for-join-order experiment](/posts/spark/llm-for-join-order-an-apache-spark-perspective/), which argued that an LLM agent can do useful work on offline join-order tuning because it **bypasses the two layers of approximation in a cost model** — observing real `execute(plan)` wall-clock directly, trading trial-and-error budget against model bias.

The subtext of that post was: **"give the model the right signals and enough feedback, and the LLM earns its keep inside a query engine."** This post is the mirror image — **what happens when you don't feed, don't train, don't give feedback, and just call a commercial LLM API to rewrite a SQL string.**

The answer is a little embarrassing.

## One embarrassing number

I recently read [E³-Rewrite](https://arxiv.org/abs/2508.09023) (arXiv:2508.09023, August 2025), which targets LLM-driven SQL rewriting under three goals — **Executable / Equivalent / Efficient**. The contribution is a GRPO-based RL fine-tuning pipeline, which I'll come back to. But the number that actually made me stop was the "baseline" row in their Table 1:

| Method | TPC-H 10GB avg latency (s) | TPC-H p90 latency (s) |
|---|---|---|
| Original (no rewrite) | 78.81 | 300.00 |
| **LLM-only (GPT-4o)** | **74.92** | **300.00** |
| LearnedRewrite (SIGMOD'22) | 41.34 | 103.41 |
| LLM-R² | 54.76 | 300.00 |
| R-Bot | 39.89 | 84.27 |
| **E³-Rewrite (Qwen3-32B, post-training)** | **29.67** | **51.37** |

(Source: E³-Rewrite paper Table 1. PostgreSQL, TPC-H SF=10, ~2000 queries, 5 runs per query with min/max trimmed.)

Look at the second row: **directly asking what is widely considered the strongest commercial LLM (GPT-4o) to rewrite SQL via a prompt takes mean latency from 78.81s to 74.92s.**

Effectively no change. Statistically indistinguishable from "do nothing."

The last row is the same paper's own method: **same PostgreSQL, same workload, swap the model for a 14B/32B open-source Qwen, feed it plan signals, train it once with RL, and the mean drops from 74.92 to 29.67 — down to 38% of the original.**

The gap is not an LLM gap (GPT-4o is in fact stronger than Qwen3-32B on most general tasks). It's a **signal gap**.

## Why the LLM knows SQL but can't rewrite SQL

This looks counterintuitive on the surface: LLM training corpora are stuffed with SQL, and rewriting a query into an equivalent, faster form doesn't sound that hard. But think it through.

What does a human do before rewriting a SQL query?

- Run `EXPLAIN` to see the current plan
- Spot the full table scan, the nested-loop join
- Notice which filter chops 100M rows down to 1K
- Then decide: can this subquery be flattened? can this `OR` become a `UNION ALL`? can `EXISTS` become `IN`?

The human gets more than the SQL string — they get **the engine's interpretation of that string**: what's slow, why, where the bottleneck is.

Stuffing only the SQL text into the prompt is like asking a human to optimize the query **without looking at EXPLAIN**. The LLM knows ten thousand rewrite patterns, but it has no idea **which one matters for this query on this database right now**. So it either guesses based on schema names and applies some generic rewrite, or it just echoes the SQL back unchanged.

74.92 vs 78.81 — what that number is really telling you is: **it either echoes the SQL or rewrites it into something that runs about the same; the fraction that actually wins is too small to show up in the mean.**

## Step 1: feed it EXPLAIN

The first thing E³-Rewrite does is exactly this — they call it **Execution Hint Injection**: before handing the SQL to the model, run `EXPLAIN` (at training time, `EXPLAIN ANALYZE`), take the plan, **linearize the tree into indented text**, and prepend it to the SQL.

So the prompt now contains something like:

```
Seq Scan on lineitem  (cost=0.00..172800 rows=6000000)
  Filter: l_shipdate < '1998-12-01'::date
  Rows Removed by Filter: 4500000   ← bottleneck
->  Hash Join  (cost=...)
    Hash Cond: (l_orderkey = o_orderkey)
    ...
```

Now the model can see: **the filter on `lineitem` is throwing away 75% of the rows, and it's filtering after a full scan before the join.** It now has a concrete optimization target — push the filter down, suggest an index, or rewrite the predicate.

The effect is immediate. From the same paper's Table 4 ablation:

| E³-Rewrite variant | avg latency (s) | improved queries | equivalence ratio |
|---|---|---|---|
| Full | 29.67 | 210 | 99.6% |
| **w/o execution hint** | **39.56** | **163** | 100% |
| w/o RL | 32.29 | 194 | 90.1% |
| w/o demonstration retrieval | 35.39 | 177 | 96.5% |
| Vanilla (no fine-tune) | 56.71 | 125 | 84.8% |

(Same setup, TPC-H 10GB.)

Removing execution hints alone takes latency from 29.67 to 39.56 — **this single component accounts for a 25% regression**. A model that was rewriting nothing useful starts knowing where to push, just because it saw a piece of EXPLAIN text.

The general lesson: **the model doesn't lack ability, it lacks visibility.** Any serious LLM × query-engine work needs *some* representation of the plan in the prompt — not necessarily EXPLAIN text (JSON, protobuf, an operator graph all work), but something. SQL string alone is optimization with the lights off.

## Step 2: train it with a reward

Plans aren't enough. If you fed EXPLAIN to GPT-4o, would it just work? Better, but still far short.

Back to Table 4, third row: **"w/o RL" — keep the plan hint, keep the demonstrations, but skip RL fine-tuning, use the base model directly. Result: 32.29s and 90.1% equivalence.**

What does 90.1% mean? For every 100 queries rewritten, **10 of them come back not equivalent to the original** — different results, or syntax error. I don't need to spell out what that means in production.

E³-Rewrite's training objective is straightforward, three reward components:

1. **Executability**: does the rewritten SQL actually run (syntax + schema check)
2. **Equivalence**: does it return the same result as the original
3. **Efficiency**: given executable + equivalent, how much faster (cost-model estimate or actually run it)

The three components are weighted, and GRPO normalizes within a group of candidate rewrites. The **curriculum** is restrained: **stage 1 emphasizes executability + equivalence (force it to rewrite correctly first), stage 2 adds the efficiency reward** — avoiding the trap of optimizing for speed at the expense of correctness from day one.

After training, equivalence climbs from 90.1% to **99.6%**, and latency drops from 32.29 to 29.67. This step isn't icing — it's the line between "usable" and "not usable."

## Step 3: train on truth, infer on estimate

This is an engineering detail in E³-Rewrite I think is underrated — the paper covers it in a single short paragraph, but it's worth pulling out.

`EXPLAIN ANALYZE` in PostgreSQL **actually runs the query** and gives you true per-operator row counts and timing. Plain `EXPLAIN` only gives the optimizer's estimated cost, without running.

E³-Rewrite's setup: **training time uses `EXPLAIN ANALYZE` for ground-truth plans (slower at training is fine, sample quality matters more); inference/deployment uses plain `EXPLAIN` (production has to be fast — you can't run the original query before rewriting it).**

This is a plain but generalizable pattern: **give the model oracle signals during training, proxy signals during inference, and let it learn to infer the oracle from the proxy.** It's effectively a flavor of distillation, but it lands naturally on systems × LLM problems — almost every query optimization task has the same oracle/proxy asymmetry:

- cost model: real wall-clock during training, estimate at inference
- cardinality estimation: real row counts during training, stats lookup at inference
- index recommendation: what-if at training, no what-if at inference

A pattern worth remembering.

## Three questions still open

The thesis is in place — "LLM rewriting SQL" is bottlenecked by the signal path, not by the LLM. But the paper's recipe is still a step or two away from landing in an open-source engine. I'll leave three open questions:

**1. Is there a standard interface for feeding a plan to an LLM?**

EXPLAIN text is the most primitive option. It has versioning issues (different engines, different versions, different formats), information loss (much of the optimizer state never surfaces in EXPLAIN), and token waste (a deep plan linearized to text is long). If LLM × query engine is going to industrialize, **this layer probably needs an engine-neutral plan representation** — protobuf? Substrait? Some LLM-friendly intermediate? No consensus yet.

**2. There's no consensus tooling for equivalence verification.**

E³-Rewrite's reward function mentions "equivalence verification" but doesn't say exactly how — is it [SPES](https://dl.acm.org/doi/10.1145/3318464.3389761)? [SQLancer](https://github.com/sqlancer/sqlancer)? LLM-as-judge? Each has a ceiling: SPES is precise but only over a SQL subset; SQLancer is strong but it's differential testing — finds counterexamples, doesn't prove equivalence; LLM judge is flexible but may hallucinate. **Without a reliable equivalence verifier, no LLM rewrite proposal will pass a production review.** This infrastructure gap is glaring.

**3. Will the conclusions on a 10GB benchmark hold — or flip — at TB scale and on real multi-tenant workloads?**

E³-Rewrite runs TPC-H SF=10 (10GB), which is on the larger side academically but still two to three orders of magnitude shy of production. Two things change with scale: rewrites yield bigger absolute wins (slow queries are slower; the optimization headroom is larger), and side effects also scale (shuffle volume, memory pressure shift). **Whether a rewrite that wins -62% on small data lands as -80% or +10% on TB-scale data — there is no public data to answer this today.**

---

I don't have an actionable takeaway to leave you with. The entire point of this post is to put the 74.92 number at the entrance of every "use LLM to rewrite SQL" project:

**If your design doesn't show the LLM the plan, and doesn't use any form of feedback to train it or filter it, then it doesn't matter whether you're calling GPT-4o, Claude 4, or Gemini 3 — what you build will be statistically indistinguishable from doing nothing.**

Whether LLMs can rewrite SQL is a signal-path question, not a model-strength question.
