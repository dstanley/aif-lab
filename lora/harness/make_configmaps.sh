#!/usr/bin/env bash
# The ConfigMaps runs mount at /mnt/config: the training script with each dataset, and the evaluation
# script with each evaluation set (plus the v1 training file, for the held-out check).
# usage: AIF_CONTEXT=<context> AIF_PROJECT=<namespace> harness/make_configmaps.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
K="kubectl --context ${AIF_CONTEXT:?} -n ${AIF_PROJECT:?}"
make() { $K delete configmap "$1" --ignore-not-found >/dev/null; $K create configmap "$@" >/dev/null; echo "configmap $1"; }
make lora-train-v0 --from-file=train.py="$ROOT/scripts/lora_train.py" --from-file=suse-train.jsonl="$ROOT/data/v0/train.jsonl"
make lora-train-v1 --from-file=train.py="$ROOT/scripts/lora_train.py" --from-file=suse-train-v1.jsonl="$ROOT/data/v1/train.jsonl"
for x in taught untaught false-premise true-premise; do
  make "lora-eval-$x" --from-file=train.py="$ROOT/scripts/lora_eval.py" --from-file="suse-eval-$x.jsonl=$ROOT/eval/$x.jsonl" \
       --from-file=suse-train-v1.jsonl="$ROOT/data/v1/train.jsonl"
done
