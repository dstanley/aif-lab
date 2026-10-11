"""The LoRA use case as a Kubeflow Pipeline: train an adapter, evaluate it against its base model on
the records the training held out, and publish it only when it is better.

Kubeflow Pipelines orchestrates (the graph, the gate, the run history, ML Metadata's lineage); each
step's work is an AI Job in the project, submitted through the rancher_ai SDK's chain, so the
project's quota and queue, the compute profile's limits and the run record apply as they do from a
notebook or the AI Jobs UI. The adapter crosses steps as a Pipelines Model artifact that names where
it is (its volume, path and SHA-256) rather than as a copy: the files stay in the cluster.

    python3 lora_pipeline.py                      # writes lora_pipeline.yaml, to upload to Pipelines

Steps run as the profile namespace's service account (default-editor), which needs AI Job Submitter
in the project; see rbac-lab.yaml.
"""
from kfp import compiler, dsl
from kfp.dsl import Input, Metrics, Model, Output

SDK = "rancher-ai @ https://github.com/dstanley/aif/archive/refs/heads/pr/7-designs.tar.gz#subdirectory=sdk/python"
SCRIPTS = "https://raw.githubusercontent.com/dstanley/aif-lab/main/profile-packs/nvidia-180g/scripts/"
IMAGE = "registry.suse.com/bci/python:3.12"


@dsl.component(base_image=IMAGE, packages_to_install=[SDK])
def train(project: str, profile: str, chain: str, scripts: str, base_model: str, steps: int, lora_rank: int,
          kfp_run_id: str, kfp_run_name: str, kfp_task: str, pipelines_ui: str,
          adapter: Output[Model], metrics: Output[Metrics]) -> str:
    """Fine-tune an adapter as an AI Job; returns the run's name."""
    import json
    import urllib.request
    from rancher_ai import Client

    ai = Client(project=project)
    origin = {"kind": "kubeflow-pipeline", "name": "lora-train-evaluate-publish", "run": kfp_run_name, "runId": kfp_run_id,
              "task": kfp_task, "url": f"{pipelines_ui.rstrip('/')}/#/runs/details/{kfp_run_id}" if pipelines_ui else ""}
    script = urllib.request.urlopen(scripts + "lora_distributed_test.py").read().decode()
    env = {"MODEL": base_model, "STEPS": str(steps), "BATCH": "4", "SEQ_LEN": "256", "LOG_EVERY": "10",
           "HELD_OUT": "32", "LORA_R": str(lora_rank), "LR": "2e-4"}
    run = ai.chain(chain, origin=origin).run("train", profile, script=script, env=env)
    out = run.output("adapter")
    # the artifact names where the adapter is; the files stay on the run's volume
    adapter.metadata.update({"aijob": run.name, "project": project, "location": out.uri, "sha256": out.sha256,
                             "bytes": out.bytes, "base_model": base_model})
    with open(adapter.path, "w") as f:
        json.dump(adapter.metadata, f, indent=1)
    for k, v in ((run.result() or {}).get("metrics") or {}).items():
        try:
            metrics.log_metric(k, float(v))
        except (TypeError, ValueError):
            pass
    return run.name


@dsl.component(base_image=IMAGE, packages_to_install=[SDK])
def evaluate(project: str, profile: str, chain: str, scripts: str, train_run: str, adapter: Input[Model],
             kfp_run_id: str, kfp_run_name: str, kfp_task: str, pipelines_ui: str,
             metrics: Output[Metrics]) -> float:
    """Evaluate the adapter against its base model as an AI Job; returns how much it lowered the loss."""
    import urllib.request
    from rancher_ai import Client

    ai = Client(project=project)
    origin = {"kind": "kubeflow-pipeline", "name": "lora-train-evaluate-publish", "run": kfp_run_name, "runId": kfp_run_id,
              "task": kfp_task, "url": f"{pipelines_ui.rstrip('/')}/#/runs/details/{kfp_run_id}" if pipelines_ui else ""}
    trained = ai.runs.get(train_run, project)
    script = urllib.request.urlopen(scripts + "lora_eval_adapter.py").read().decode()
    run = ai.chain(chain, origin=origin).run("eval", profile, script=script, env={"REQUIRE_IMPROVEMENT": "0"},
                              inputs={"adapter": trained.output("adapter"), "dataset": trained.input("dataset")})
    m = (run.result() or {}).get("metrics") or {}
    for k, v in m.items():
        try:
            metrics.log_metric(k, float(v))
        except (TypeError, ValueError):
            pass
    print(f"adapter {adapter.metadata.get('location')}: held-out loss {m.get('base_loss')} -> {m.get('adapter_loss')}")
    return float(m.get("loss_reduction", 0))


@dsl.component(base_image=IMAGE, packages_to_install=[SDK])
def publish(project: str, train_run: str, models_volume: str, models_volume_size: str, adapter: Input[Model],
            published: Output[Model]):
    """Copy the adapter to the project's models volume, in the cluster, under the training run's name:
    where an inference endpoint takes it from (see serve-adapter-vllm.ipynb)."""
    import json
    from rancher_ai import Client

    ai = Client(project=project)
    vol, path = adapter.metadata["location"][len("volume://"):].split("/", 1)
    done = ai.volumes.copy(vol, path, models_volume, f"adapters/{train_run}", size=models_volume_size, overwrite=True)
    published.metadata.update({**adapter.metadata, "location": f"volume://{models_volume}/{done['path']}",
                               "files": done["files"], "published_from": adapter.metadata["location"]})
    with open(published.path, "w") as f:
        json.dump(published.metadata, f, indent=1)


@dsl.pipeline(name="lora-train-evaluate-publish",
              description="Fine-tune a LoRA adapter, evaluate it on held-out records, and publish it if it beats its base model. "
                          "Each step is an AI Job in the project.")
def lora_pipeline(project: str = "ai-data-science", profile: str = "shared-gpu-dev", chain: str = "lora-pipeline",
                  base_model: str = "Qwen/Qwen2.5-0.5B-Instruct", steps: int = 60, lora_rank: int = 16,
                  min_loss_reduction: float = 0.0, models_volume: str = "lora-models", models_volume_size: str = "10Gi",
                  scripts: str = SCRIPTS, pipelines_ui: str = ""):
    # where each AI Job came from, for its record and the AI Jobs view: this run and its task
    run_info = dict(kfp_run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER, kfp_run_name=dsl.PIPELINE_JOB_NAME_PLACEHOLDER,
                    kfp_task=dsl.PIPELINE_TASK_NAME_PLACEHOLDER, pipelines_ui=pipelines_ui)
    t = train(project=project, profile=profile, chain=chain, scripts=scripts, base_model=base_model, steps=steps,
              lora_rank=lora_rank, **run_info)
    e = evaluate(project=project, profile=profile, chain=chain, scripts=scripts, train_run=t.outputs["Output"],
                 adapter=t.outputs["adapter"], **run_info)
    with dsl.If(e.outputs["Output"] > min_loss_reduction, name="better-than-base"):
        publish(project=project, train_run=t.outputs["Output"], models_volume=models_volume,
                models_volume_size=models_volume_size, adapter=t.outputs["adapter"])
    # the chain decides what to rerun (unchanged steps reuse their earlier AI Job); Pipelines' own
    # cache would skip the step and lose the link to the run
    for task in (t, e):
        task.set_caching_options(False)


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_pipeline.yaml")
    compiler.Compiler().compile(lora_pipeline, out)
    print("wrote", out)
