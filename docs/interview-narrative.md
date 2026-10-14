# Interview Narrative — Activity Metadata Quality Platform

## One-line positioning

> I built a small eval-driven metadata quality system to explore how an activity marketplace could use LLMs safely: not just to detect bad metadata, but to decide when there is enough evidence to act, when a human should review, and how reviewed cases should improve future evaluations.

---

## 30-second version

Supplier-generated marketplace metadata can be incomplete, ambiguous, or semantically misclassified.

I used a real London tourism dataset and built a pipeline that combines deterministic checks with Gemini semantic evaluation.

The important part is the control system around the model: explicit ontology, confidence and coverage gates, human review, an impact score, an action policy, and a feedback loop.

One location case had a 26.9 km geocoder discrepancy. A naive system could conclude the coordinates were wrong. My pipeline instead routed it to review, where the evidence showed the **address was incomplete and the coordinate should not be changed**. That outcome then became a regression case.

---

## 60-second version

The problem I wanted to explore was supplier metadata quality in a marketplace.

An LLM can classify or enrich content, but the harder product problem is: **when do we trust the output enough to act?**

So I built the system in layers.

First, humans define the ontology — what counts as a museum, a nature activity, acceptable location evidence, and so on.

Then deterministic checks and an atomic Gemini evaluator generate quality signals.

Those signals do not directly modify data. They go through confidence, coverage, address and entity gates.

I combine the outputs into a review-priority score and an action policy that can pass a record, request more evidence, or send it to human review.

Finally, reviewer outcomes become structured regression cases.

The best example is Acorn 20/20. The geocoder resolved its short address 26.9 km away. Instead of assuming the pin was wrong, the gate detected that the external reference did not match the entity. Review showed the address lacked locality context; the coordinate was not changed. That reviewed mistake is now a regression test.

---

# Five-minute walkthrough

## 1. Problem — ~45 seconds

> Travel marketplaces depend on supplier-generated metadata for discovery, ranking, customer expectations, and operations. But metadata quality is not one problem. You can have missing fields, wrong categories, ambiguous addresses, stale attributes, or inconsistent signals.

> The easy demo is “call an LLM and ask whether this listing is good.” I deliberately did not do that. I wanted to explore the decision architecture around the model.

Key sentence:

> **The model can generate evidence; the product still needs to decide what evidence is sufficient for an action.**

---

## 2. Define “good” — ~45 seconds

> Before evaluating anything, I made the ontology explicit.

For example:

- museum has a written inclusion/exclusion definition;
- nature has a different semantic boundary;
- location quality separates address completeness from coordinate correctness.

Explain why:

> Otherwise the LLM is implicitly inventing the marketplace taxonomy, and precision/recall numbers become hard to interpret.

Mention public-label noise:

> The real dataset has labels, but it does not publish the full annotator rubric. So I treat those labels as an evaluation reference rather than unquestioned ground truth.

---

## 3. Evaluator design — ~60 seconds

Describe the atomic evaluator:

```text
one entity
× one category
→ member / not_member / uncertain
→ confidence
→ reason codes
→ evidence
```

Why atomic:

> It is easier to evaluate, debug, version, and route than a single prompt that tries to rewrite an entire listing.

Real results:

- Nature representative holdout:
  - 95.8% model coverage;
  - 90.6% precision;
  - 85.2% recall;
  - 87.8% F1 against public labels.
- Deterministic nature recall was only 0.47%.

Then caveat:

> I would not ship based on those numbers alone. The museum evaluation showed that label/ontology disagreement can dominate the apparent error rate.

---

## 4. Safety / routing — ~75 seconds

Move to Acorn 20/20.

> This is the part I would spend most of the interview on.

Input:

```text
Acorn 20/20
20 Richmond Rd
source coordinate
```

External geocoder:

```text
26.9 km disagreement
```

Ask rhetorically:

> Is the coordinate wrong?

Answer:

> We do not know yet.

Explain pipeline:

```text
distance anomaly
→ address-specificity check
→ entity-reference match
→ ADDRESS_OR_GEOCODER_REVIEW
→ score 35
→ HUMAN_REVIEW
```

Review result:

> Independent evidence pointed to 20 Richmond Road in Kingston. The original address lacked enough location context, so the geocoder chose another Richmond Road. There was no evidence to overwrite the coordinate.

Senior-level framing:

> The system separates **anomaly detection from root-cause diagnosis**, and root-cause diagnosis from **permission to act**.

---

## 5. Operationalization — ~45 seconds

Explain the unified action policy:

```text
PASS
NEED_MORE_EVIDENCE
HUMAN_REVIEW
```

Current 30-record integrated sample:

- 15 human review;
- 11 need more evidence;
- 4 pass;
- 11 can be internally auto-flagged.

But:

> Supplier contact and metadata mutation remain disabled.

Then explain why this matters:

> I can automate queue creation before automating remediation. That lets us capture operational value while keeping the expensive mistakes behind a human gate.

---

## 6. Feedback loop — ~45 seconds

> I also avoided calling assisted review “human gold.”

Two evidence-reviewed location cases produced:

- two confirmed address defects;
- zero confirmed coordinate corrections;
- two regression safety cases.

Policy:

```text
assisted review
→ regression protection

independent human gold
→ threshold calibration candidate
```

Key sentence:

> **The system learns from reviewed cases without silently training on its own opinions.**

---

## 7. Close — ~30 seconds

> This is a prototype, not a claim that these exact rules should go to production.

> If I were working on this at GetYourGuide, I would pick one metadata defect with measurable business impact, build an independent multilingual gold set, run this in shadow mode, measure action-level precision and review reduction, and only then introduce automation lane by lane.

Close with:

> The core idea is not “LLM quality checking”. It is an **evaluation and decision system that lets us use model intelligence without giving model uncertainty direct control over the catalog**.

---

# Architecture explanation

Use this if asked to walk through the system technically:

```text
raw supplier / catalog metadata
        ↓
deterministic checks
        ↓
atomic semantic evaluator
        ↓
field-specific quality gates
        ↓
confidence + coverage
        ↓
Quality Impact Score
        ↓
Action Policy
        ↓
internal flag / review queue
        ↓
reviewer decision
        ↓
structured feedback
        ↓
regression evaluation
```

Do not describe the Quality Impact Score as a business-impact model.

Say:

> It is currently an explicit prioritization heuristic. To turn it into a real business-impact score, I would need downstream marketplace data and causal or experimental validation.

---

# What is genuinely strong in this prototype

1. **Explicit ontology instead of prompt-defined truth**
2. **Real dataset instead of synthetic demo records**
3. **Independent representative holdouts**
4. **Abstention and provider-error handling**
5. **Asymmetric safety thinking around different action types**
6. **Root-cause routing rather than anomaly-only detection**
7. **Coverage-aware scoring**
8. **Clear separation between internal flags and external mutations**
9. **Feedback trust tiers**
10. **Regression protection from reviewed cases**

---

# Trade-offs to volunteer proactively

## Why not automate more?

> Because the current evidence supports internal prioritization much more strongly than external mutation. I would rather first prove review precision and review-volume reduction.

## Why Gemini?

> I needed one real structured-output provider to test the evaluator architecture. The platform logic is intended to be provider-independent; the important asset is the ontology, eval set, routing policy, and feedback loop.

## Why not use an LLM for everything?

> Deterministic checks are cheaper and more auditable when the rule is explicit. The LLM is useful for semantic/contextual judgment. I use the cheapest reliable method per failure mode.

## Why is museum precision only 47% on the holdout?

> That metric is against public labels. The disagreement review found probable label and ontology mismatches. I intentionally preserve the weak-looking public-reference metric rather than “cleaning” it away. It shows why evaluation quality matters as much as prompt quality.

## Why is the score heuristic?

> Because I do not have GetYourGuide's actual conversion, booking, cancellation, support, or supplier-remediation outcome data. Calling it a business-impact model would be false precision.

## Why no automated retraining?

> Online feedback is correlated with the current model and routing policy. Automatically training on it risks self-reinforcing errors. Independent human gold has a higher trust tier.

---

# What I would do next at GetYourGuide

## First 30 days

- understand existing content-quality taxonomy and ownership;
- identify one costly metadata failure mode;
- quantify current defect prevalence and review cost;
- collect historical accepted/rejected corrections;
- define action-level success metrics.

## Next 30–60 days

- build multilingual, market-stratified gold data;
- run evaluator and routing policy in shadow mode;
- compare LLM vs deterministic vs hybrid strategies;
- measure precision by remediation action, not only classification accuracy;
- instrument reviewer feedback.

## Then

Introduce automation in order of reversibility:

```text
internal flag
→ reviewer recommendation
→ supplier suggestion
→ reversible auto-enrichment
→ high-risk mutation only with very strong evidence
```

---

# Questions this project should invite

A good interview presentation should create useful follow-up questions.

Likely questions:

- How would you choose the first production metadata domain?
- How would you create gold data?
- How would you evaluate multilingual listings?
- How would you measure business impact?
- When would you automate supplier-facing actions?
- How would you handle changing taxonomies?
- How would you monitor drift?
- How would you compare vendors/models?
- What belongs in deterministic logic vs an LLM?
- How would you estimate review-cost savings?

Those are better discussion directions than spending the interview on prompt syntax.

---

# Files to show during the interview

If time is short, show only these:

1. `README.md` — product framing and verified results.
2. `reports/demo/end_to_end_demo.md` — one concrete listing.
3. `config/category_ontology.yml` — “define good” before prompting.
4. `src/quality/address_gate.py` — a concrete safety gate.
5. `src/policy/quality_action_policy.py` — separation of evidence and action.
6. `reports/feedback/closed_loop_regression_cases.csv` — feedback becoming regression protection.

Avoid walking line-by-line through the whole repository.

---

# Final sentence

> **I would describe this project as an eval-driven decision layer for marketplace metadata quality, with LLMs as one source of evidence—not as the authority that directly controls catalog data.**
