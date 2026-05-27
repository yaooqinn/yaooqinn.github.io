---
title: "−46% or −2%? Rule-Based Rewriters Only Work at Home"
date: 2026-05-27
tags: ["query-optimizer", "sql-rewrite", "performance", "benchmark", "llm"]
categories: ["Query Engines"]
summary: "On TPC-H 10GB, a state-of-the-art learned rewriter cuts mean execution time from 69.84s to 37.57s — a 46% win. On DSB 10GB, the same rewriter takes 32.62s to 31.93s — a 2.1% non-event. The gap isn't query difficulty; it's whether the benchmark is in the rewriter's training distribution. \"Rule-based systems are stable and reliable\" is often a benchmark artifact, not an engineering fact."
cover:
  image: /images/posts/rule-rewrite-blindspot-cover.png
  relative: false
showToc: true
---

My previous post argued that [just asking an LLM to rewrite SQL does almost nothing](/en/posts/query-engines/llm-only-rewrite-doesnt-work/) — without plan signals or feedback, prompting a commercial LLM on TPC-H 10GB takes 78.81s down to 74.92s, statistically indistinguishable from doing nothing.

That post left an obvious follow-up. What about the traditional path — the rule-based and learned rewriters that the database research community has been refining for decades? Surely those are stable?

After reading the [QUITE](https://arxiv.org/abs/2506.07675) paper's Table 3 (arXiv:2506.07675, June 2025), my answer to that question changed: **they're not stable. They only look stable on the benchmarks they were trained on.**

## One number that collapses when you change the schema

QUITE compares rewriters across three benchmarks. Pull out the row for **LearnedRewrite** (SIGMOD'22, "LR" hereafter):

| Benchmark | Original mean latency | LR rewritten | Improvement |
|---|---|---|---|
| **TPC-H** (SF=10) | 69.84s | **37.57s** | **−46.2%** |
| **DSB** (SF=10) | 32.62s | **31.93s** | **−2.1%** |
| Calcite | 23.88s | 22.88s | −4.2% |

(Source: QUITE paper Table 3. All benchmarks at SF=10, PostgreSQL, three-run average, 300s timeout.)

LR's TPC-H report card is respectable — nearly half the execution time gone. If you only looked at TPC-H, you'd conclude this is a real rewriter.

**But the same LR, same code, on DSB takes 32.62 to 31.93 — a 2.1% gain.** Inside benchmark noise. Effectively no rewrite happened.

DSB isn't an obscure dataset — it's Microsoft's 2021 decision-support benchmark, with deeper nested subqueries, more CTEs, and more realistic filter patterns than TPC-H. **The rewrite headroom is objectively there**: in the same paper QUITE takes DSB from 31.93 down to 5.85. The equivalent-rewrite space exists; LR just can't see it.

## The paper says so itself

The most direct statement of the problem is in QUITE's Section 7.2:

> "The LR we use is trained on the TPC-H, LR can proficiently identify effective rewrite rules and navigate their constrained search spaces."

LR works on TPC-H **because it was trained on TPC-H**.

The phrasing is mild, but it surfaces a structural issue with three decades of rule-rewriter research. Whether "training" is meant in the learning sense or not, **rule libraries themselves are shaped by benchmark distributions**:

- Which rules get into Calcite/Orca's rule library? Usually because a paper demonstrated their value on a benchmark.
- Which rules get heavily refined? Usually because they show measurable gains on TPC-H / TPC-DS / JOB.
- Which rules get pruned? Ones that contribute nothing — or regress — on the standard benchmarks.

The rule set evolved against **the academic benchmark distribution**, not the real-world query distribution. Rule-based rewriting is pattern matching at its core; if a pattern isn't in the training distribution, the system can't see it. Not my words — QUITE quotes Leis et al. (VLDB'15, the canonical join-order benchmark paper):

> "fixed rewrite rules rely on pattern matching and therefore are fundamentally unable to optimize unseen or complex query patterns"

## What "rule-based systems are reliable" actually means

Back to those two numbers, −46% and −2.1%.

If your impression of rule-based rewriters is "mature, proven, stable," that's because almost every published evaluation you've seen runs on TPC-H, TPC-DS, or JOB. **These benchmarks *are* the training set for rule-based systems.** Looking good on the training set isn't "stable and reliable."

DSB isn't part of that training set — it came out after LR was published, and the rule library hasn't had time to grow the patterns it needs. Result: −2.1%.

The general form of this problem: **there is virtually no public data on how rule-based rewriters perform on real production workloads.** What does production SQL actually look like at a real company? Nesting depth, predicate shapes, join patterns, UDF usage — almost none of it resembles TPC-H. When you deploy a rewriter that won "−46% on TPC-H" against a real workload, you might get −5%, or 0, or some queries getting slower (rule fires, payoff is negative).

This is why the LLM path is still interesting for rewriting, despite the previous post's bleak baseline. Rule-system search space is **closed, hand-curated, and lags behind real workload evolution**. LLM pattern space is **open and can extrapolate to unseen schema shapes**. The former has a hard ceiling inside its training distribution; the latter has an unclear ceiling but at least won't freeze when it encounters DSB for the first time.

QUITE's own numbers on the three benchmarks — bringing LR's −46% / −2% / −4% up to roughly −63% / −82% / −58% — make the shape of the blind spot visible: **small relative gains on TPC-H, huge relative gains on DSB.** That's exactly what a benchmark-overfit baseline looks like: little headroom left where it was trained, lots of headroom left everywhere else.

## Three questions still open

The thesis is clear: **rule-based rewriters aren't broken — they're just untested outside their benchmark.** But QUITE's recipe still leaves several open problems:

**1. How do you measure a rewriter's coverage generalization?**

All current benchmarks are single points — one number on TPC-H, one on DSB, one on Calcite. But generalization isn't about how high any single point is, it's about **the variance across points**. A system that scores −46% / −2% / −4% and one that scores −20% / −15% / −18% can have the same average but very different stability profiles. The field needs a cross-schema stability metric, not more benchmark data points.

**2. Is there public data on the gap between rewriter training distribution and production distribution?**

Vendors with massive production SQL — Databricks, Snowflake, Alibaba, ByteDance — could publish "real query shape distribution vs TPC-H shape distribution" comparisons: subquery depth histograms, predicate count distributions, join type breakdowns. Right now, the entire industry is operating on intuition about whether rule-based rewriters will land in production.

**3. Where are the cost-quality-coverage boundaries between free LLM generation, FSM-constrained generation, and rule enumeration?**

Free LLM generation has equivalence risk (the previous post noted E³-Rewrite without fine-tuning hit only 84.8% equivalence). Rule enumeration has the coverage blind spots discussed here. QUITE-style "FSM frame + LLM generation + Calcite equivalence check" sits in the middle. But the actual curves of cost (tokens, latency, ops), quality (equivalence rate, hit rate, average speedup), and coverage (number of schemas where it stays stable) across all three — no public comparison exists. This is the real industrial-readiness gap.

---

I don't have an actionable takeaway. What I want to leave is two numbers — **−46% and −2.1%** — and one caution:

**A rewriter's score on any single benchmark only proves it works on that benchmark.** Before debating "should we use LLMs to rewrite SQL," it might be worth asking the prior question: our current rule-based rewriter — does it score −46% on our actual workload, or −2%?

If it's the latter, then the real question isn't whether LLMs work. It's whether **the way we've been evaluating rewriters this whole time** is the problem.
