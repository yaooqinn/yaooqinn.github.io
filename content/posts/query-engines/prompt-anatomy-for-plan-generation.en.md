---
title: "Anatomy of a 120-Line Prompt That Lets an LLM Rewrite Physical Plans"
date: 2026-05-27
tags: ["query-optimizer", "llm", "prompt-engineering", "datafusion", "json-patch"]
categories: ["Query Engines"]
summary: "DBPlanBench gets GPT-5 to deliver a 4.78× geometric-mean speedup on DataFusion TPC-H SF10 by letting the model rewrite physical plans directly. I read its sql_optimization_prompts.py end to end — 120 lines, 30 of methodology, 90 of contract. That ratio is the most transferable thing in the paper."
cover:
  image: /images/posts/prompt-anatomy-cover.png
  relative: false
showToc: true
---

My previous two posts ([LLM × join order](/posts/query-engines/llm-only-rewrite-doesnt-work/) and [the blind spot of rule-based rewrites](/posts/query-engines/rule-rewrite-blindspot-dsb/)) were both about **letting an LLM rewrite SQL text** — string in, string out, execution engine unchanged. That route is easy to start with, but it can't touch problems that only show up at the physical-plan level: join order, projection column order, physical operator choice.

What if you let the LLM rewrite the physical plan directly?

I recently read a February 2026 paper, [Making Databases Faster with LLM Evolutionary Sampling](https://arxiv.org/abs/2602.10387) (arXiv:2602.10387), with the companion repo [BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling](https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling). That's exactly what it does. On DataFusion, GPT-5 rewrites physical plans through structural transforms and lands a **4.78× geometric-mean speedup on TPC-H SF10**.

The number is nice, but the more transferable thing is the prompt. I read [`sql_optimization_prompts.py`](https://github.com/BauplanLabs/Making-Databases-Faster-with-LLM-Evolutionary-Sampling/blob/main/src/sampling/sql_optimization_prompts.py) line by line. **Exactly 120 lines.**

## How those 120 lines are spent

Roughly by content:

| Layer | What's in it | Share |
|---|---|---|
| **L1 · Input schema** | Defines the three inputs (`structure`, `succinct_table_info`, `query`) and gives a three-node sample JSON | ~20% |
| **L2 · Methodology** | Step 1: cardinality estimation. Step 2: apply join-side selection and join reordering on those estimates | ~30% |
| **L3 · Invariant contract + output schema** | Three invariants, a projection-index calculation rule with a worked example, output must be a `<patch>[...]</patch>` block wrapping an RFC 6902 JSON Patch array | ~50% |

The ratio is what made me stop. **Methodology gets 30%. The other 70% is spent on defining what counts as a valid output.**

That is counter-intuitive. My default assumption was that a prompt for query optimization should mostly *teach the LLM how to optimize* — what makes a good plan, when to broadcast, when to shuffle. The DBPlanBench authors compress that to 30% and put the remaining 70% into **making the LLM's output machine-verifiable**.

Look at the results again — 4.78× geometric mean, and roughly **half of LLM outputs pass the validator** (paper §4) — and the ratio starts making sense. With a looser prompt, the model would produce plans that look reasonable but don't compile; if only 1 in 5 passes, the evolutionary loop has nothing to search over.

## Three designs worth borrowing

### ① "Be not lazy": explicitly forbid the empty response

One block in the prompt reads:

```
You should assume that the current plan can almost always be improved
and must not be lazy: actively search for semantics-preserving structural
changes instead of defaulting to making no changes.

By default, the JSON patch array you output should contain at least one
operation that changes the plan structure. Returning an empty array []
... is acceptable only in critical cases ...
```

That made me smile. When an LLM has to decide whether something can be improved, it tends to take the lazy path and return an empty array. Most prompt authors know this, but few bother to write it down. The authors here flip the default — *try* is the baseline, *empty* is the escape hatch.

This pattern has nothing to do with query optimization specifically. It applies to **any agent-style tool call** where you don't want the model to bail out with "looks fine to me": PR review, performance triage, error attribution.

### ② "Use semantics, not defaults": delegate cardinality estimation to world knowledge

Step 1 includes:

```
CRITICAL: Do not use defaultFilterSelectivity or other default values.
Instead, perform semantic analysis of column names, table contexts, and
filter predicates to make intelligent cardinality estimates based on
real-world knowledge.
```

This is the central bet of the whole approach. Cost-based optimizers fall back to constants when statistics are missing (PostgreSQL's equality default is `DEFAULT_EQ_SEL = 0.005`, see [`selfuncs.h`](https://github.com/postgres/postgres/blob/master/src/include/utils/selfuncs.h)). DBPlanBench bets that the LLM can read the column name `order_status` and the predicate `= 'completed'` and come up with something like 0.7.

It's also the **biggest limitation** of the method — more on that below.

### ③ Projection-index calculation: invariants written as code comments

The bit I found most interesting is in L3:

```
When you swap the left and right inputs of a HashJoin, you MUST update
the projection indexes to reflect the new schema order. The projection
calculation follows this rule:
- If projection references a left field: use the index as-is
- If projection references a right field: offset by len(left_schema),
  i.e., len(left_schema) + right_projection[i]
```

Then four worked examples: `A[name, id] × B[dept_name, budget]`, original projection `[0, 3]`, after swap it should be `[2, 1]` — spelled out step by step.

I rarely see this style in prompt engineering: **the engine's physical invariants written as code comments to the LLM**. The common move is to write "preserve semantics after swap" and then get back plans that compile but reference columns at the wrong positions. The authors hand the LLM the exact arithmetic. The model doesn't need to *understand* — it only needs to *repeat*.

## Why the 4.78× doesn't transplant cleanly

My first reaction was to copy the recipe. My second was to slow down. A real share of that 4.78× is a DataFusion-shaped tailwind, not evidence that LLMs out-think cost models.

**DataFusion's physical optimizer is famously sparse.** Statistics propagation only landed in the last few months, histograms are still in RFC stage, and equality-filter selectivity in many paths really does fall back to that 0.005-class default. When the LLM uses semantics to land on 0.7 for `order_status = 'completed'`, the baseline it's beating is 0.005. **That ~100× gap is "DataFusion lacks statistics", not "LLM beats CBO."**

Run the same method on Spark's CBO with histograms, or on Photon or Trino with a real cost model, and the headroom shrinks. Not zero — just much smaller. The 4.78× does not extrapolate.

The projection-index rule has the same flavor. DataFusion schemas are flat `Vec<Field>`, so index arithmetic is clean. Catalyst uses `StructType` + `ExprId` + `AttributeReference`, and "how projection moves after a join swap" is scattered across transforms like `ResolveReferences` and `BindReferences`. There is no single rule to copy-paste into a prompt. The work has to start one step earlier: **extract those invariants explicitly** — and that itself is a non-trivial engineering project.

## What actually transfers

Strip the numbers away and three pieces hold up:

1. **The three-layer structure** (schema / methodology / invariants) and especially the ratio — 70% spent on what counts as a valid output. Not specific to query optimization. It applies to any task that produces a structured artifact the system has to validate.
2. **JSON Patch (RFC 6902) as the output format.** Industry standard, off-the-shelf appliers, and it matches the diff-shaped reasoning LLMs already do. No need to invent a wire format.
3. **The "be not lazy" instruction.** Whenever you don't want the LLM to short-circuit with "no change needed", this pattern is worth keeping.

The cardinality-via-semantics part — the source of the 4.78× on DataFusion — is more likely a liability on Spark or any engine with real statistics. **Invert it: inject the real numbers into the prompt and stop asking the model to guess.**

## One question I'm not answering

What I haven't decided yet: **whether a ~50% validator pass rate is good enough for production.**

DBPlanBench runs offline. Evolutionary sampling can afford to spend a night, sample hundreds of plans, and keep the fastest. 50% pass rate is fine. An online plan tuner is a different game — five rewrites per query before one compiles costs both latency and tokens, and it's not obvious which side runs out of budget first.

I'm not sure how far this route goes yet. Reading the prompt end to end gave me at least a clearer map of where to look next time someone shows up selling "let the LLM rewrite plans."

---

**Sources for the numbers in this post**

- 4.78× geometric mean: [arXiv:2602.10387](https://arxiv.org/abs/2602.10387), TPC-H SF10
- 120-line prompt: `wc -l sql_optimization_prompts.py` against the 2026-05-26 commit
- ~50% validator pass rate: paper §4
- PostgreSQL `DEFAULT_EQ_SEL = 0.005`: [`selfuncs.h`](https://github.com/postgres/postgres/blob/master/src/include/utils/selfuncs.h)
- JSON Patch: [RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902)
