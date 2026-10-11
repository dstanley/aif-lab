# The LoRA use case as a Kubeflow Pipeline

[`lora_pipeline.py`](lora_pipeline.py) is the train -> evaluate -> publish flow as a Kubeflow Pipeline
(KFP v2):

```
train ──> evaluate ──> [loss reduction > min_loss_reduction] ──> publish
```

| Step | Does | As |
|---|---|---|
| `train` | fine-tunes a LoRA adapter (the LoRA Distributed Training Test's script) | an AI Job in the project |
| `evaluate` | compares the adapter with its base model on the records the training held out, the same dataset revision | an AI Job, its input the training run's adapter |
| `publish` | copies the adapter to the project's models volume, `adapters/<training run>`, in the cluster | a copy Job (`volumes.copy`) |

Pipelines orchestrates: the graph, the gate, run history and comparison, scheduled runs, and ML
Metadata's lineage. Each step's work is an AI Job submitted through the `rancher_ai` SDK's chain,
so the project's quota and KAI queue, the compute profile's limits and the run record apply exactly
as they do from a notebook or the AI Jobs UI. The adapter crosses steps as a Pipelines `Model`
artifact that names where it is (its volume, path and SHA-256): the files stay in the cluster, and
the AI Jobs' own lineage (`chain.lineage()`) agrees with what Pipelines shows.

The chain decides what to rerun: run the pipeline again unchanged and the train and evaluate steps
return their earlier AI Jobs at once, so Pipelines' own cache is off for them.

## Running it

Needs Kubeflow Pipelines 2.x (the lab runs 2.16.0, multi-user), AI Factory with the AIJob API in
the project, and a training profile that takes a script and a dataset volume and keeps a checkpoint
volume (`shared-gpu-dev` by default: a 4 GiB GPU share).

1. **Let the steps submit AI Jobs.** They run as the profile namespace's service account; grant it
   AI Job Submitter in the project (edit the two names first):

   ```sh
   kubectl apply -f rbac-lab.yaml
   ```

2. **Compile:** `pip install kfp==2.16.0 && python3 lora_pipeline.py` writes `lora_pipeline.yaml`.
3. **Upload and run** it from the Kubeflow Pipelines UI (Pipelines -> Upload pipeline, then Create
   run in the profile's namespace), setting `project` to the AI Factory project. Or through the API,
   for example with the KFP SDK:

   ```python
   import kfp
   client = kfp.Client(host="http://localhost:8888", namespace="kubeflow-user-example-com")   # port-forward svc/ml-pipeline
   client.create_run_from_pipeline_package("lora_pipeline.yaml", arguments={"project": "aif-submit"})
   ```

The steps install the SDK from the aif repository and fetch the training and evaluation scripts
from this repository when they start, so the cluster needs to reach GitHub and PyPI.

## What it shows

In Pipelines: the graph, each step's metrics (tokens per second and loss from training, the base and
adapter losses from evaluation), and the adapter as a Model artifact with its location and hash. In
AI Factory: each step's AI Job under the cluster's AI Jobs, with its queue, GPU and record, and the
chain's lineage from the SDK.
