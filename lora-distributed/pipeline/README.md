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
the AI Jobs' own artifact records (`chain.artifacts()`) agree with what Pipelines shows.

The chain decides what to rerun: run the pipeline again unchanged and the train and evaluate steps
return their earlier AI Jobs at once, so Pipelines' own cache is off for them.

## Running it

Needs Kubeflow Pipelines 2.x (the lab runs 2.16.0, multi-user), AI Factory with the AIJob API in
the project, and a training profile that takes a script and a dataset volume and keeps a checkpoint
volume (`shared-gpu-dev` by default: a 4 GiB GPU share).

1. **Let the steps submit AI Jobs.** They run as the profile namespace's service account; grant it
   what a person submitting runs has: AI Job Submitter in the project, AI Scheduler Cluster Read
   (read-only: nodes, chart repositories, queues), and read access to the project's Namespace
   object, where its KAI queue is recorded (edit the two names first):

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

Without Kubeflow's front door (Istio, oauth2-proxy and the central dashboard scaled down, as on
the lab), [`ui_proxy.py`](ui_proxy.py) serves the Pipelines UI locally with the user and namespace
the front door would add.

## On the lab

Run `lora-2`: train (60 steps, Qwen2.5-0.5B on a 4 GiB GPU share) -> evaluate -> publish, about seven
minutes. The training's held-out loss went from 1.415 to 1.372; the evaluation, separately, measured
1.4154 for the base model and 1.3722 with the adapter, so the gate passed and the adapter was copied
to `lora-models` under `adapters/<training run>`. The evaluation's adapter input carries the training
output's hash, and both read the same dataset commit. Run `lora-3`, unchanged, reused both AI Jobs
(the chain had still two) and took four minutes, which is Pipelines starting its pods.

## What it shows

In Pipelines: the graph, each step's metrics (tokens per second and loss from training, the base and
adapter losses from evaluation), and the adapter as a Model artifact with its location and hash. In
AI Factory: each step's AI Job under the cluster's AI Jobs, with its queue, GPU and record, and the
chain's artifacts from the SDK.
