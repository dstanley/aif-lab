# Results: a LoRA run through S3-compatible storage

One pass of the whole path with the LoRA study's dataset (`../lora/data/v1`) and baseline recipe
(test 5). The store is SeaweedFS with S3 authentication on, one volume server on a Longhorn volume;
the cluster is the lab's RKE2 cluster on virtual machines. The timings say what each step costs at
this scale on this hardware, not what a production store delivers. The raw measurements are in
`steps.jsonl`.

## Every step completed, and every object verified

| Step | Data | Through | Time | Verified |
|---|---|---|---|---|
| **upload** | 10 files, 867 KB | presigned PUTs from the workstation | 0.6 s | 10 of 10 SHA-256 match |
| **stage** | 10 files, 867 KB, onto RWX volume `ds-suse-docs-v1` | presigned GETs, Job in the project | 9.9 s (0.3 s of transfer; the rest is the pod starting) | 10 of 10 |
| **train** | run `dev-dl-lora-1`, recipe test 5, `DATASET=/mnt/dataset/train.jsonl` | the training chart's dataset volume | 846 s, including the image pull | — |
| **collect** | 3 files, 295 MB: the final adapter (one 295 MB file, 36 parts of 8 MiB), its config, `training.json` | inventory Job, then presigned multipart PUTs | 27.6 s inventory + 37.5 s upload Job (2.7 s of transfer) | 3 of 3, in a verify Job (6.7 s) |
| **archive** | 4 objects (3 files and the manifest) to `aif-cold` | copy Job holding the credentials | 9.9 s | read back, then the active copies deleted: 0 objects left in `aif`, 4 in `aif-cold` |
| **restore** | 4 objects back to `aif` | the same copy Job | 9.9 s | read back; the archive copy kept |
| **evaluate** | the restored adapter, staged onto a new volume `dev-dl-lora-1-restored` | presigned GETs, then `../lora`'s taught evaluation | 19.4 s stage + 542 s evaluation | 3 of 3 staged files match |

The restored adapter evaluates exactly as test 5's own adapter did: held-out loss 2.854 → 1.476
(48.3% lower) and taught questions correct 13% → 36% of 338. The bytes that came back through
collect, archive and restore are the bytes training wrote.

## Credentials stayed with the platform

With authentication on, an anonymous S3 request is refused (`AccessDenied`). Only two places read
the storage identity: the platform stand-in (`lifecycle.py`) and the copy Jobs, which run in the
store's namespace. The Jobs in the project's namespace (stage, inventory, collect, verify) received
URLs signed for one object or one part, valid for an hour, and nothing else. The upload from the
workstation used the same kind of URL.

## What the run showed about the design

These are the places where the design in the aif repo (`docs/design/data-lifecycle.md`) met
something it does not yet say.

1. **Operations on volumes run in the project's namespace.** A pod mounts only volumes in its own
   namespace, so stage, collect and verify cannot run in the platform's namespace with the
   credentials. Presigned URLs carried them without credentials; the alternative is short-lived
   credentials scoped to the prefix, which needs a store with STS.
2. **Collecting takes two passes.** The platform needs each file's size before it can presign a
   multipart upload, so an inventory Job lists the run volume first and the upload Job follows.
3. **Verification belongs next to the store.** Reading 1.2 GB back through the platform's own link
   (a kubectl port-forward) failed twice with dropped connections; the same check as a Job, reading
   through presigned GETs, took 0.3 s for 295 MB.
4. **The artifact policy decides the size of everything after collect.** Without it, collect took
   the final adapter and the three per-epoch adapters the recipe keeps: 1.2 GB instead of 295 MB.
   With the policy (final adapter and the run's record), the epoch checkpoints stayed on the run
   volume.
5. **A run volume outlives its collection while the run's pods exist.** The volume's deletion was
   requested after verification, and the volume stayed bound: Kubernetes keeps a volume while pods
   that mounted it exist, and the AIJob keeps the finished run's pods for its execution retention
   (168 h by default). Deleting run volumes on collection means removing the run's execution objects
   at the same time.
6. **Restoring goes to a new volume.** Reusing the run volume's name collided with the old volume
   still being deleted; the restore went to `dev-dl-lora-1-restored`.
7. **Profile rules apply to these runs too.** The training profile requires run names to start with
   `dev-`; the SDK refused `dl-lora-1` before submitting.
