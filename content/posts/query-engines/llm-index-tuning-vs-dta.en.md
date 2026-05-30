---
title: "When the Index Tuner's Cost Model Lies: Where LLMs See What DTA Can't"
date: 2026-05-30
tags: ["query-optimizer", "llm", "index-tuning", "performance", "cost-model"]
categories: ["Query Engines"]
summary: "A Microsoft team evaluates LLM-driven index tuning on real enterprise customer workloads. On query 22 of Real-R, the SOTA commercial tuner DTA recommends indexes that cause a near-10x regression; on the same query, GPT-5 cuts execution time from 10 seconds to 4. The LLM wins precisely where the what-if cost model is wrong. But that intuition is high-variance, can't be bolted into the existing architecture, and can't be validated cheaply — it's not a replacement for DTA today, it's a source of the candidate indexes DTA can't see."
cover:
  image: /images/posts/llm-index-tuning-cover.png
  relative: false
showToc: true
---

The earlier posts in this series were all about query rewriting: [just asking an LLM to rewrite SQL does almost nothing](/posts/query-engines/llm-only-rewrite-doesnt-work/), [the blind spot of rule-based rewriting on DSB](/posts/query-engines/rule-rewrite-blindspot-dsb/), and [treating the LLM as a plan-tuner rather than an optimizer](/posts/query-engines/llm-as-plan-tuner-not-optimizer/). This one switches axes — to **physical design**, specifically **index tuning**.

The source is an evaluation paper from Microsoft's own team (Xiaoying Wang, Wentao Wu, Vivek Narasayya, Surajit Chaudhuri) released in March 2026 (arXiv:2603.09181), with a deliberately restrained title: *Evaluating the Practical Effectiveness of LLM-Driven Index Tuning with Microsoft Database Tuning Advisor*. Narasayya and Chaudhuri have been the foundational figures behind SQL Server index tuning (AutoAdmin / DTA) for over two decades — them stepping in to evaluate LLMs is itself worth reading.

And this paper has a particularly honest posture: it's not here to announce that LLMs won. It's here to tell you *where* the LLM wins, and *why* it still can't go to production.

## One query, two opposite endings

Start with the single most striking number in the paper.

On a real enterprise customer workload called Real-R, there's a query 22. Microsoft's DTA — the industry's SOTA commercial index tuner — recommends a set of indexes for it, and those indexes **regress the query's execution time by nearly 10x** (a severe query performance regression, or QPR).

Same query, hand it to GPT-5: execution time drops from **10 seconds to 4 seconds**, roughly a 60% improvement.

Same query optimizer, same data, same SQL. One pushed it off a cliff; the other walked around the edge. Why?

## Where the blind spot comes from: the what-if cost model

To understand this, you first need to know how DTA works.

DTA is a textbook cost-based architecture with three stages: (1) **workload analysis**, identifying indexable columns from the queries (columns appearing in filters and join conditions); (2) **candidate index generation**, deciding the key columns, included columns, and column ordering of each potentially useful index; and (3) **configuration enumeration**, selecting a subset of candidates that minimizes the *estimated* execution cost of the whole workload while respecting constraints like the maximum number of indexes or storage budget.

The operative word is *estimated*. DTA estimates each configuration's cost using the optimizer's **what-if API** — which can answer "if this index existed, roughly how much would this query cost?" *without actually materializing the index*. It's a clever design that avoids the expensive cost of building indexes.

But it inherits the original sin of the cost model: **when the estimate is wrong, the recommendation is suboptimal, and in extreme cases it causes a production incident.** This isn't a bug in DTA's implementation; it's the twenty-year-old problem of cost-based architectures — cardinality estimates propagate errors, join result sizes get mis-estimated, exactly as Leis et al.'s well-known *How Good Are Query Optimizers, Really?* demonstrated repeatedly. The 10x regression on query 22 is what-if estimating a genuinely bad set of indexes as a bargain.

The LLM route bypasses this whole explicit cost model. It doesn't compute cost; it draws directly on the web-scale-trained intuition for "what kind of query wants what kind of index" and hands you a configuration. Where DTA was misled by its cost estimate, that intuition happened not to fall into the same hole.

## Why this evaluation is credible

There are plenty of papers on LLMs for database tuning, and most share a flaw: they benchmark on public datasets that have almost certainly leaked into the LLM's training set. This paper deliberately avoids that:

- **Real execution time, not estimated cost.** Each query is actually run 5 times and the median is taken, with a 300-second timeout. It measures wall-clock, not the cost the optimizer reports about itself — the same methodological stance as #1 in this series.
- **Four of the five workloads are real enterprise customer workloads** (Real-D / Real-M / Real-R / Real-S), with CTEs, views, and many manually created indexes — the "dirt" that public benchmarks (here only TPC-H SF10 was used) lack.
- **The baseline is the real commercial DTA**, not the simplified index recommender common in papers.
- **The primary LLM is GPT-5** (they also tried DeepSeek-R1, Qwen3, and GPT-4o; GPT-5 was best, and all reported results use it).

This setup makes the conclusions far more solid than "yet another leaderboard paper."

## Complementarity: where the LLM wins

In the single-query setting, within 5 invocations, GPT-5 matches or beats DTA in most cases. And there's a counterintuitive detail: it often achieves the same effect with **fewer indexes**. On query 4 of Real-D, DTA recommends **17 indexes**; GPT-5 recommends only **7**, and most of those 7 are actually used by the execution plan.

More important is *where* the LLM wins. The places where it substantially beats DTA are exactly where DTA was led astray by inaccurate cost estimates — on query 4 of Real-D and query 27 of Real-M, DTA's recommendations both caused QPRs, and the LLM avoided them. The paper puts it bluntly: those most useful LLM-recommended indexes were *never even candidates* in DTA's candidate-generation stage — because what-if judged them to have higher estimated cost and culled them early.

The paper also does something interesting: it distills the rules of thumb from GPT-5's reasoning — prioritize indexes that cut expensive scans, order key columns by cues from the plan's filters/joins/sorts, build covering indexes where possible (to enable index-only scans), and ignore small-table scans. Then it writes a **purely rule-based tuner that calls no LLM** from those rules. In other words, part of the LLM's value here can be *distilled into deterministic rules*.

## Three walls: why it can't go to production yet

If the paper stopped here, it would be an LLM puff piece. But the Microsoft team honestly raises three walls.

**Wall one: high variance.** Invoke GPT-5 five times on the same query and the gap between best and worst is enormous. On TPC-H's query 20, the worst case degrades into an outright QPR. If you take the worst-case result for each query, **the LLM no longer wins a single query**, and in most cases performs substantially worse than DTA. That beautiful 10s→4s ending could be a disaster on the next invocation. The intuition is unstable.

**Wall two: direct integration degrades.** A natural idea: since the LLM can come up with good indexes that aren't in DTA's candidate pool, why not inject the LLM's recommendations into DTA's candidate pool and let DTA pick? Expanding the search space should only help. The opposite happened — after merging the single-query LLM recommendations into the candidate pool, the final configuration got **significantly slower**. The cause, again, is what-if: the pool is larger, but the selection criterion is still that inaccurate cost estimate, so it picks a worse configuration from the bigger pool. (The one exception: workload-level multi-query recommendations can improve DTA by more than 2x — but that, conversely, shows the problem is in the cost model, not the candidate indexes.)

**Wall three: validation is prohibitively expensive.** So step back: since the estimate can't be trusted, why not just materialize the candidate indexes, run the workload, and pick the best by real execution time? The paper does an end-to-end time breakdown, and the answer is: **validation costs far more than tuning itself, and the bottleneck is index creation.** Actually materializing the candidate indexes and re-running the workload — index creation alone accounts for a disproportionately large share of the total cost. And the diversity of LLM recommendations amplifies this — different invocations give different configurations, and the set of indexes to validate keeps piling up. In production, this road is essentially a dead end.

## What it means for engine builders

Put the three walls together and the conclusion is clear — and it dovetails exactly with the through-line of #1 in this series: **bypassing the cost model's approximations is not free; the price is reliability.**

In #1, the LLM rewriting SQL bypassed the cost model using real `execute()` wall-clock, at the cost of needing training and feedback. In this paper, the LLM recommending indexes bypasses what-if, at the cost of high variance, non-integrability, and un-cheap validation. Same exchange rate, different underlying.

So the correct positioning of the LLM in index tuning today is not as a replacement for DTA, but as a **source of the candidate indexes the cost model can't see**. The real open problem is not "can the LLM come up with good indexes" — it can; query 22 is the proof — but **"how do you cheaply trust the candidates it offers, without rebuilding indexes across the entire warehouse to find out?"**

For engine builders, that's a very concrete architectural signal. Physical-design automation — index recommendation and materialized-view recommendation in systems like Spark and Kyuubi — should next be thinking not about "should we switch to an LLM," but about **how to decouple "generating candidates" from "trusting candidates"**: let the LLM (or any cost-model-free source) expand the candidate space, and treat "how to build trust cheaply in a world where what-if is inaccurate" as a separate sub-problem worth investing in on its own. This paper doesn't give the answer, but it asks the question correctly.

---

<div class="sources">
<strong>Sources</strong>
<ul>
<li>Xiaoying Wang, Wentao Wu, Vivek Narasayya, Surajit Chaudhuri. <em>Evaluating the Practical Effectiveness of LLM-Driven Index Tuning with Microsoft Database Tuning Advisor</em>. arXiv:2603.09181, March 2026. <a href="https://arxiv.org/abs/2603.09181">https://arxiv.org/abs/2603.09181</a> (accessed 2026-05-30)</li>
<li>Viktor Leis et al. <em>How Good Are Query Optimizers, Really?</em> PVLDB 2015.</li>
</ul>
</div>
