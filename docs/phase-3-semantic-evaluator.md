# Phase 3 — Atomic semantic category evaluator

## Executive summary

Phase 2 showed that explicit lexical matching is not an adequate category-quality strategy on the real London catalog. The deterministic baseline has micro precision of 55.98% but micro recall of only 3.51%.

Phase 3 therefore introduces semantic reasoning, but deliberately does **not** replace the deterministic layer with one broad prompt. The evaluator remains atomic: one entity, one target category, one structured decision.

The first calibration vertical is `museum` because the real baseline exposes both sides of the error trade-off:

- 30 museum false negatives;
- 98 museum false positives;
- many false positives are adjacent entities such as galleries rather than museums;
- some true museums or heritage interpretation sites do not contain an obvious lexical museum cue.

This makes `museum` useful for testing whether semantic reasoning improves both recall and boundary precision.

## Benchmark decisions carried forward

The design follows the earlier benchmark decisions:

1. **Eval before optimization.** The deterministic baseline and human-labelled set exist before the LLM is introduced.
2. **Atomic evaluators.** The model is asked one narrow quality question instead of "find every problem".
3. **Programmatic + semantic layers.** Cheap deterministic checks remain in place rather than sending every decision to an LLM.
4. **Human-in-the-loop.** The semantic contract supports `uncertain`; uncertainty is routed rather than forced into a binary answer.
5. **Version everything.** Ontology, prompt and model are recorded with each prediction.

## Category definition is a product input

The model is not allowed to invent what `museum` means. `config/category_ontology.yml` contains a project-level business definition, inclusion cases and exclusion boundaries.

This is important because the London source publishes human category labels but does not publish the annotators' full decision rubric. A disagreement between the semantic evaluator and ground truth can therefore be:

- a model error;
- a weak or ambiguous source record;
- or an ontology mismatch.

Those cases must be inspected rather than automatically treated as model failure.

## Semantic contract

Each evaluation returns exactly:

```json
{
  "decision": "member | not_member | uncertain",
  "confidence": 0.0,
  "reason_codes": ["..."],
  "evidence": "..."
}
```

The contract is enforced with Structured Outputs / JSON Schema and revalidated in application code.

`uncertain` is a first-class outcome. It is measured as abstention/coverage instead of silently converting every ambiguous case into a confident label.

## Ground-truth isolation

The semantic prompt receives only:

- entity name;
- source category;
- descriptive metadata;
- selected review snippets;
- the explicit category ontology.

It does **not** receive:

- `is_member` human label;
- deterministic prediction;
- false-positive / false-negative status.

The human label is merged back only after inference for evaluation.

## Calibration sampling

The first run uses a bounded calibration sample rather than spending inference budget across every category immediately. The sampler deliberately includes deterministic:

- true positives;
- false positives;
- false negatives;
- true negatives.

This gives the first semantic iteration exposure to both obvious cases and known baseline failure modes.

The calibration sample is not claimed to represent production prevalence. A later validation run must use a representative holdout or the full target-category population before thresholds are frozen.

## Metrics

Phase 3 reports:

- deterministic precision / recall / F1 on the same sample;
- semantic precision / recall / F1 on decided cases;
- conservative semantic metrics with `uncertain` treated as no automatic positive action;
- coverage;
- abstention rate;
- token usage;
- deterministic-vs-semantic disagreements.

A semantic evaluator is not considered production-ready merely because F1 improves. Automated actions will require a later risk-based threshold policy with explicit false-positive and false-negative costs.

## Provider design

The first provider uses the OpenAI Responses API with strict structured output. Provider access is isolated behind an interface so another provider can be added without changing the evaluation dataset or metric layer.

The model is configuration, not business logic. The default calibration model is `gpt-5.6-luna`, but the workflow accepts a model input and records the selected model in every result.

No API credential is stored in source control. GitHub Actions reads `OPENAI_API_KEY` from repository secrets.

## Run locally

After Phase 1 and Phase 2:

```bash
export OPENAI_API_KEY="..."
python -m src.semantic.run_phase3   --category museum   --sample-size 240   --model gpt-5.6-luna
```

On GitHub, use the **Semantic category calibration** workflow after adding the `OPENAI_API_KEY` Actions secret.

## What remains out of scope in this phase

This phase does not:

- evaluate all 12 categories at once;
- auto-edit catalog metadata;
- tune confidence thresholds for automatic remediation;
- introduce RAG or embeddings;
- fine-tune a model;
- use multiple models or disagreement routing.

Those are deferred until the first semantic evaluator is calibrated and its failure modes are understood.

## Next decision gate

After the first real `museum` semantic run, inspect:

1. precision improvement vs deterministic baseline;
2. recall improvement;
3. abstention rate;
4. gallery-vs-museum boundary errors;
5. heritage-site false negatives;
6. high-confidence wrong predictions;
7. ontology-vs-ground-truth disagreements.

Only after that review should the evaluator expand to the next category or receive confidence-based automation thresholds.
