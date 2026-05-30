---
title: "当索引调优器的成本模型说谎时:LLM 在 DTA 看不见的地方"
date: 2026-05-30
tags: ["query-optimizer", "llm", "index-tuning", "performance", "cost-model"]
categories: ["Query Engines"]
summary: "微软团队拿真实企业客户负载评测 LLM 索引调优:在 Real-R 的 query 22 上,SOTA 商用调优器 DTA 推荐的索引导致近 10× 退化,同一条 query,GPT-5 把执行时间从 10 秒压到 4 秒。LLM 赢的地方,恰恰是 what-if 成本模型估错的地方。但这份直觉高方差、缝不进现有架构、也无法廉价验证——它现在不是 DTA 的替代品,是它视野之外的候选索引的来源。"
cover:
  image: /images/posts/llm-index-tuning-cover.png
  relative: false
showToc: true
---

本系列前几篇都在写查询改写:[只让 LLM 改 SQL 几乎什么都不会发生](/posts/query-engines/llm-only-rewrite-doesnt-work/)、[规则改写在 DSB 上的盲区](/posts/query-engines/rule-rewrite-blindspot-dsb/)、[把 LLM 当 plan-tuner 而不是 optimizer](/posts/query-engines/llm-as-plan-tuner-not-optimizer/)。这一篇换一个优化轴——**物理设计**,具体说是**索引调优**。

来源是微软自己团队（Xiaoying Wang、Wentao Wu、Vivek Narasayya、Surajit Chaudhuri）2026 年 3 月放出的一篇评测论文（arXiv:2603.09181），标题很克制：*Evaluating the Practical Effectiveness of LLM-Driven Index Tuning with Microsoft Database Tuning Advisor*。Narasayya 和 Chaudhuri 是 SQL Server 索引调优（AutoAdmin / DTA）二十多年的奠基者——他们亲自下场评 LLM，本身就值得读。

而且这篇有一个特别诚实的姿态:它不是来宣布 LLM 赢了的，它是来告诉你 LLM 在哪里赢、又为什么现在还不能上生产的。

## 一条 query,两个截然相反的结局

先看全文最扎眼的一个数字。

在一个叫 Real-R 的真实企业客户负载上，有一条 query 22。微软的 DTA——业界 SOTA 的商用索引调优器——给它推荐了一组索引，结果这组索引让这条 query 的执行时间**退化了将近 10 倍**（一次严重的 query performance regression，简称 QPR）。

同一条 query，让 GPT-5 来推荐索引，执行时间从 **10 秒压到了 4 秒**，改进约 60%。

同一个查询优化器、同一份数据、同一条 SQL。一个把它推下了悬崖，一个把它绕开了。为什么?

## 盲区从哪来:what-if 成本模型

要理解这件事，得先知道 DTA 是怎么工作的。

DTA 是一个标准的 cost-based 架构，三段式：（1）**workload 分析**，从查询里识别出可建索引的列（出现在 filter、join 条件里的列）；（2）**候选索引生成**，决定每个潜在索引的 key 列、included 列和列序；（3）**配置枚举**，从候选里挑出一个子集，使得整个 workload 的*估算*执行成本最小、同时满足索引数量/存储空间等约束。

关键在"估算"两个字。DTA 估每个配置成本用的是优化器的 **what-if API**——它能在*不真正建出索引*的前提下，问优化器"假如有这个索引，这条 query 大概要花多少成本"。这是个聪明的设计，省掉了建索引的昂贵代价。

但它继承了成本模型的原罪：**估算不准时，推荐就次优，极端情况下酿成生产事故。** 这不是 DTA 的实现 bug，是 cost-based 架构二十年的老问题——基数估计会传播误差、连接结果大小会估歪，正如 Leis 等人那篇著名的 *How good are query optimizers, really?* 反复证明的。query 22 的 10× 退化，就是 what-if 把一组其实很糟的索引估成了便宜货。

LLM 路线绕开了这整套显式成本模型。它不算 cost，直接凭 web 规模训练里学到的"什么样的 query 配什么样的索引"的直觉，给你一组配置。在 DTA 被成本估算误导的地方，这份直觉刚好没掉进同一个坑。

## 为什么这篇评测可信

LLM 做数据库调优的论文很多，大部分一个通病：在公开 benchmark 上刷分，而那些 benchmark 八成早进了 LLM 的训练集。这篇刻意避开了：

- **用真实执行时间，不用估算成本。** 每条 query 实际跑 5 次取中位数，设 300 秒超时上限。衡量的是 wall-clock，不是优化器自己报的 cost——这点和本系列 #1 是同一个方法论立场。
- **5 个负载里有 4 个是真实企业客户负载**（Real-D / Real-M / Real-R / Real-S），含 CTE、view、大量人工建的索引——这些"脏"正是公开 benchmark（这里只用了 TPC-H SF10）缺的。
- **baseline 是真·商用 DTA**，不是论文里常见的简化版索引推荐器。
- **LLM 主力是 GPT-5**（也试了 DeepSeek-R1、Qwen3、GPT-4o，GPT-5 最好，正文结果都用它）。

这套设定让结论比"又一篇刷榜论文"扎实得多。

## 互补性:LLM 赢在哪里

单 query 场景下，5 次调用以内，GPT-5 在多数 case 上能匹配甚至超越 DTA。而且有个反直觉的细节：它常常用**更少的索引**达到同样效果。Real-D 的 query 4，DTA 推荐了 **17 个索引**，GPT-5 只推荐了 **7 个**，而且这 7 个大多都被执行计划实际用上了。

更重要的是 LLM 赢的*位置*。它显著超越 DTA 的地方，恰恰是 DTA 被不准的成本估算带偏的地方——Real-D 的 query 4、Real-M 的 query 27，DTA 的推荐都造成了 QPR，而 LLM 绕开了。论文用一句话点破：那几个最有用的 LLM 推荐索引，DTA 的候选生成阶段*根本没把它们当候选*——因为 what-if 觉得它们估算成本更高，提前就被毙了。

论文还做了件有意思的事：把 GPT-5 推理过程里的经验法则蒸馏了出来——优先建能砍掉昂贵 scan 的索引、按计划里 filter/join/排序的线索决定 key 列顺序、能做 covering index 就做（换 index-only scan）、忽略小表 scan。然后用这几条规则写了个**不调用 LLM 的纯规则版 tuner**。换句话说，LLM 在这里的一部分价值是可以被*提炼成确定性规则*的。

## 三道墙:为什么现在还不能上生产

如果文章到此为止，那就成了一篇 LLM 吹捧文。但微软团队诚实地竖起了三道墙。

**第一道:高方差。** 同一条 query 重复调 5 次 GPT-5，best 和 worst 之间差距巨大。TPC-H 的 query 20，worst-case 直接退化成 QPR。如果你取每条 query 的 worst-case 结果来看，**LLM 不再赢任何一条 query**，多数情况下还显著差于 DTA。也就是说，那个 10s→4s 的漂亮结局，可能下一次调用就变成了灾难。直觉不稳定。

**第二道:直接集成就退化。** 一个自然的想法是：既然 LLM 能想出 DTA 候选池里没有的好索引，那把 LLM 的推荐塞进 DTA 的候选池、让 DTA 去选不就好了?扩大搜索空间，按理应该只赚不亏。结果相反——把单 query 的 LLM 推荐并进候选池后，最终配置反而**显著变慢**。原因还是 what-if：候选池大了，但选择依据还是那个不准的成本估算，于是从更大的池子里挑出了更差的配置。（唯一例外是整 workload 级别的多 query 推荐，能让 DTA 提升 2× 以上——但这恰恰反过来说明问题出在成本模型，不在候选索引本身。）

**第三道:验证成本高到不可行。** 那退一步:既然估算不可信，干脆把候选索引真建出来、跑一遍、用真实执行时间选最好的，不行吗?论文做了端到端的时间分解，答案是:**验证的代价远高于调优本身，瓶颈是建索引。** 把候选索引真 materialize 出来、再把 workload 跑一遍，光建索引这一步就占了总开销不成比例的大头。而 LLM 推荐的多样性还会放大这个问题——不同调用给出不同配置，要验证的索引越堆越多。在生产里，这条路基本走不通。

## 对做引擎的人意味着什么

把三道墙摆在一起，结论就清楚了，而且和本系列 #1 的主轴严丝合缝：**绕过成本模型的近似不是免费的，代价是可靠性。**

\#1 里 LLM 改 SQL 用 `execute()` 的真实 wall-clock 绕开 cost model，代价是要训练、要反馈。这一篇 LLM 推荐索引绕开 what-if，代价是高方差、不可集成、不可廉价验证。同一个换汇率，不同的标的。

所以 LLM 当下在索引调优里的正确定位，不是 DTA 的替代品，而是**成本模型看不见的那部分候选索引的来源**。真正的开放问题，不在"LLM 能不能想出好索引"——它能，query 22 就是证据——而在**"怎么在不把整座数据仓库重建一遍索引的前提下，廉价地信任它给的候选"**。

对做引擎的人，这是一个很具体的架构信号。物理设计自动化——Spark、Kyuubi 这类系统里的索引推荐、物化视图推荐——下一步该想的，不是"要不要换成 LLM"，而是**怎么把"生成候选"和"信任候选"这两件事拆开**:让 LLM（或任何不依赖成本模型的来源）负责扩张候选空间，把"在 what-if 估不准的世界里如何廉价建立信任"作为一个独立的、值得单独投入的子问题。微软这篇没给出答案，但它把问题问对了。

---

<div class="sources">
<strong>来源</strong>
<ul>
<li>Xiaoying Wang, Wentao Wu, Vivek Narasayya, Surajit Chaudhuri. <em>Evaluating the Practical Effectiveness of LLM-Driven Index Tuning with Microsoft Database Tuning Advisor</em>. arXiv:2603.09181, 2026-03. <a href="https://arxiv.org/abs/2603.09181">https://arxiv.org/abs/2603.09181</a>（访问日期 2026-05-30）</li>
<li>Viktor Leis et al. <em>How Good Are Query Optimizers, Really?</em> PVLDB 2015.</li>
</ul>
</div>
