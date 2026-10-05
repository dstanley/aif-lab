# SUSE dataset v0

A small instruction-tuning dataset that teaches a chat model to answer Kubernetes and infrastructure
questions with accurate, SUSE-aware answers. Drafted from SUSE's public documentation;
**not reviewed** (see `DATA.md`).

| File | Records | Use |
|---|---|---|
| `suse-train.jsonl` | 701 | `lora_train.py` (`DATASET=…/suse-train.jsonl`) |
| `suse-eval.jsonl` | 109 | `lora_eval.py` (`EVAL_DATASET=…/suse-eval.jsonl`); none of its questions is in the training file |
| `review-sample.md` | 30 | a sample to review: three training and two evaluation records per area |
| `notes/<area>-notes.md` | | pages read, naming decisions with sources, facts left out |

## Coverage

| Area | Train | Eval | Sources |
|---|---|---|---|
| SUSE Rancher Prime (cluster management) | 120 | 18 | ranchermanager.docs.rancher.com, documentation.suse.com |
| RKE2 and K3s | 114 | 18 | docs.rke2.io, docs.k3s.io |
| SUSE Storage (Longhorn) | 122 | 18 | documentation.suse.com (Storage 1.12), longhorn.io |
| SUSE Virtualization (Harvester) | 113 | 18 | documentation.suse.com (v1.8), docs.harvesterhci.io |
| SUSE Security (NeuVector) | 110 | 18 | documentation.suse.com (5.6), open-docs.neuvector.com |
| SLES, SUSE Linux Micro, BCI, Application Collection, SUSE AI | 122 | 19 | documentation.suse.com, registry.suse.com, docs.apps.rancher.io |

Six question types, roughly evenly: definition, recommendation ("I need … what should I use?"),
command, troubleshooting, architecture, procedure. 248 distinct source pages; every record has a
`source` URL.

## Format

Training: `{"instruction", "input", "output", "area", "type", "source"}`.

Evaluation: `{"instruction", "input", "reference", "area", "type", "source", "expect_any",
"expect_none", "expect_command"}`. `lora_eval.py` scores the base model and the adapter against the
`expect_*` fields (an expected product or feature named; a wrong one not named; an exact command
present) and against `reference` (answer-only loss). Every reference passes its own checks.

## Decisions made while drafting

- **Product names follow current SUSE documentation**: SUSE Rancher Prime, SUSE Storage (Longhorn),
  SUSE Virtualization (Harvester), SUSE Security (NeuVector), SUSE Linux Micro (from 6.1), SUSE Linux
  BCIs, SUSE Application Collection. Project names remain where the docs keep them: component and
  resource names (`longhorn-system`, Longhorn Manager, the Harvester Node Driver, NeuVector Helm charts).
- **SUSE AI and SUSE AI Factory are kept apart**: the docs describe them as separate products.
- **Positioning**: factual, no pricing or licensing claims, nothing disparaging other products.
  Where the docs called a product "free", that wording was left out.

## What to check before training on it

1. **Commands in the Rancher and RKE2/K3s areas**: those pages were read through a summarising
   fetcher, so commands and YAML may have lost a flag. The Storage, Security, Virtualization and Linux
   areas were read as full text.
2. **Places the docs contradict themselves**, where the dataset avoids a claim or picks the newer
   page (details in the notes): RKE2's default ingress (Traefik from v1.36; the FIPS page still says
   NGINX), SUSE Security's default protection mode (changed in 5.6.1), `SUSEConnect -list-extensions`
   vs `--list-extensions`, the Longhorn stale-replica timeout default, RWX support in the Harvester CSI
   driver.
3. **Facts tied to versions**, which will age: Harvester v1.8 specifics, Storage 1.12, certificate
   renewal at 120 days for RKE2, GPU Operator behaviour.
4. **Licensing of the source text**: the answers paraphrase SUSE and upstream project documentation.
   Check the documentation licences before publishing the dataset outside SUSE.
