# Data lifecycle: a LoRA run through S3-compatible storage

**Question:** can a training run's data and outputs move through S3-compatible object storage end to
end (upload, stage, train, collect, archive, restore) with every object verified, and without the
people and pods doing the work holding storage credentials?

The study runs the operations of the data lifecycle design in the aif repo
(`docs/design/data-lifecycle.md`) by hand, one Kubernetes Job per operation, before any controller
exists. The workload is the baseline LoRA recipe from [`../lora`](../lora/README.md) (test 5), trained
from a dataset that arrives through object storage instead of a ConfigMap.

## The path

```text
workstation ──upload (presigned PUT)──▶ s3://aif/<project>/datasets/suse-docs/v1/
                                              │ stage (presigned GET, verified)
                                              ▼
                                   RWX volume ds-suse-docs-v1 (read-only for runs)
                                              │ train (../lora recipe test5)
                                              ▼
                                   run volume <run>-checkpoints
                                              │ collect (inventory, then presigned multipart PUT)
                                              ▼
                                   s3://aif/<project>/runs/<run>/      ── run volume deleted
                                              │ archive (copy, verify, delete active)
                                              ▼
                                   s3://aif-cold/<project>/runs/<run>/
                                              │ restore (copy, verify)
                                              ▼
                                   s3://aif/<project>/runs/<run>/ ──stage──▶ volume ──▶ evaluate (../lora)
```

## Who holds what

`scripts/lifecycle.py` plays the platform's part, the operator API of the design: it alone reads the
storage credentials, presigns URLs scoped to one object or one part for one hour, completes multipart
uploads, writes manifests and verifies objects. `scripts/mover.py` is the Data Mover, the same script
in every Job, with one operation per Job:

| Operation | Runs in | Holds | Does |
|---|---|---|---|
| `get` | the project's namespace | presigned GET URLs | downloads objects onto a volume, checks each SHA-256 |
| `inventory` | the project's namespace | nothing | lists a volume's files with sizes and SHA-256 |
| `put` | the project's namespace | presigned PUT URLs (single or per part) | uploads files, reports part ETags |
| `copy` | the storage platform's namespace | the storage credentials | copies objects between buckets server-side, reads every copy back to verify it, then (archive) deletes the source |

Operations that touch a volume must run in the volume's namespace, which is the project's; project
users can read Secrets there, so those Jobs get URLs, not credentials. Operations between buckets run
where the credentials are.

Every dataset and run prefix carries a manifest, `.aif-manifest.json`, with each object's path, size
and SHA-256. A multipart object's ETag is not a hash of its content, so verification reads objects
back and hashes them.

## Running it

The study needs a cluster with SUSE AI Factory's training workloads, the `rancher_ai` SDK from the
aif repo (`sdk/python`), the LoRA study's ConfigMaps (`../lora/harness/make_configmaps.sh`), an
S3-compatible store with an RWX storage class, and these settings:

| Variable | Meaning | Lab value |
|---|---|---|
| `AIF_CONTEXT`, `AIF_PROJECT`, `AIF_PROFILE` | kubeconfig context, project namespace, training profile (as in `../lora`) | the lab's |
| `S3_ENDPOINT` | the S3 endpoint as pods reach it | `http://seaweedfs-s3.seaweedfs:8333` |
| `S3_LOCAL_ENDPOINT` | the S3 endpoint as this machine reaches it; unset, the script port-forwards `S3_SERVICE` on a free local port | unset (`S3_SERVICE=seaweedfs/seaweedfs-s3:8333`) |
| `S3_CREDENTIALS_SECRET` | `<namespace>/<secret>` holding the store's identities (key `seaweedfs_s3_config`); copy Jobs run in that namespace | `seaweedfs/aif-lab-s3-config` |
| `ACTIVE_BUCKET`, `ARCHIVE_BUCKET` | the active and archive storage targets | `aif`, `aif-cold` |
| `RWX_STORAGE_CLASS`, `RWO_STORAGE_CLASS` | dataset volumes, run volumes | `seaweedfs-rwx`, `longhorn` |
| `MOVER_NODES` | nodes that can mount the RWX class (comma-separated); empty for any | the lab's |

The lab store is SeaweedFS with S3 authentication on; any S3-compatible store with presigned URLs
(Ceph RGW, MinIO) serves, with the credentials read from wherever that store keeps them.

```
pip install -r data-lifecycle/requirements.txt
export PYTHONPATH=<aif>/sdk/python
cd data-lifecycle
python scripts/lifecycle.py upload ../lora/data/v1 --name suse-docs --version v1
python scripts/lifecycle.py stage --name suse-docs --version v1 --volume ds-suse-docs-v1
python scripts/lifecycle.py train dev-dl-lora-1 --recipe test5 --volume ds-suse-docs-v1 --file train.jsonl
python scripts/lifecycle.py collect dev-dl-lora-1
python scripts/lifecycle.py archive dev-dl-lora-1
python scripts/lifecycle.py restore dev-dl-lora-1
python scripts/lifecycle.py evaluate dev-dl-lora-1 --set taught
```

Each step appends its measurements to `results/steps.jsonl`. The results and what they say about
the design are in [`results/RESULTS.md`](results/RESULTS.md).
