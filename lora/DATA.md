# About the data

## What it is

| Path | Contents |
|---|---|
| `data/v0/` | ~700 instruction/answer pairs across six SUSE product areas, each fact stated once |
| `data/v1/` | 338 canonical facts (`facts.jsonl`) and 1,306 training examples: 3–4 independently worded examples per fact, plus 66 premise corrections |
| `eval/` | four evaluation sets: taught (338), untaught (109, the v0 evaluation, frozen), false-premise (42), true-premise (24) |
| `results/*/answers-*.jsonl` | every answer a base model and an adapter gave to the evaluation sets, with its grade |

## How it was made

Each product area was drafted by a language model working from public documentation:
documentation.suse.com, ranchermanager.docs.rancher.com, docs.rke2.io, docs.k3s.io, longhorn.io,
docs.harvesterhci.io, open-docs.neuvector.com, registry.suse.com and docs.apps.rancher.io. Every
fact and training example carries the URL it came from (`source`). Pages were read as raw text where
possible so that commands were copied, not summarised; the drafting notes (`data/*/notes/`) record
the pages read, naming decisions, places the documentation contradicts itself, and what was left
out. Automated checks ran over the result (valid records, no evaluation question in the training
data, each command verbatim in its examples, held-out wordings distinct from training wordings).

## What it is not

- **Not reviewed.** No one has checked the facts against the products. Expect errors, including
  wrong or outdated commands, and facts tied to versions current when the pages were read (for
  example SUSE Virtualization v1.8 and SUSE Storage 1.12).
- **Not a reference.** Use the product documentation, not this data, to operate any product.
- **Not official.** It is not SUSE documentation and is not endorsed or supported by SUSE.
- **The answers are model output.** The graded answers in `results/` are what small fine-tuned
  models said; many are wrong by design of the study (that is what it measures).

## Terms

The code in this repository is under the Apache License 2.0. The facts are paraphrased from the
documentation listed above, which remains subject to its own terms; check them before reusing the
data, in particular before redistributing it or training on it outside this study.
