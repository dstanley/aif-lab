# SUSE dataset v1 (draft, for review)

Version 1 of the SUSE instruction-tuning dataset, rebuilt after test 1 (see ~/Downloads/lora-testing).
v0 stated ~700 different facts once each; the model learned the style but not the facts, and invented
confident commands. v1 teaches fewer facts, each several ways, and teaches the model not to invent.
Drafted 2026-10-04 from SUSE's public documentation; **not reviewed yet**.

| File | Records | Use |
|---|---|---|
| `suse-facts-v1.jsonl` | 338 | canonical facts: `{id, fact, kind, command?, source}` |
| `suse-train-v1.jsonl` | 1,306 | training: 3–4 independently worded examples per fact (`fact` = its id), plus 66 negative examples |
| `suse-eval-taught.jsonl` | 338 | one held-back question per fact, worded differently from all its training examples: did the adapter **learn**? |
| `suse-eval-untaught.jsonl` | 109 | test 1's evaluation questions, frozen: does the adapter **invent**? `v1_taught` marks the 27 whose fact v1 now teaches |
| `suse-eval-false-premise.jsonl` | 42 | questions built on a wrong premise: does the adapter **correct it**? 24 contradict a v1 fact (`fact` = its id), 18 name an invented command or setting found nowhere in v1; 1 restates a premise a training negative corrects (`premise_taught`) |

Training examples by type: command 518, knowledge 519, recommendation 116, troubleshooting 90,
negative 66. Each command fact's command appears verbatim in every one of its training examples.
Negative examples ask for a plausible but undocumented command or feature, and answer that it is not
documented, with the documented way. All 66 correct a **false premise**; none declines a real
question the data doesn't answer, so they teach premise correction, not abstention. Three training examples that copied a frozen question were removed.

| Area | Facts | Sources |
|---|---|---|
| SUSE Rancher Prime | 58 | ranchermanager.docs.rancher.com, documentation.suse.com |
| RKE2 and K3s | 57 | docs.rke2.io, docs.k3s.io |
| SUSE Storage (Longhorn) | 60 | documentation.suse.com (1.12), longhorn.io |
| SUSE Virtualization (Harvester) | 53 | documentation.suse.com (v1.8) |
| SUSE Security (NeuVector) | 55 | documentation.suse.com (5.6), open-docs.neuvector.com |
| SLES, SUSE Linux Micro, BCI, Application Collection, SUSE AI | 55 | documentation.suse.com, registry.suse.com, docs.apps.rancher.io |

Most pages were read as raw text this time, so commands are copied, not summarised. What to check
before training beyond the lab demo is as for v0 (version-tied facts, places the docs contradict
themselves, documentation licences); each area's notes list its decisions and contradictions.
