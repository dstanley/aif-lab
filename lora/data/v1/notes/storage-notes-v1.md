# SUSE Storage (Longhorn) dataset v1: notes

## Output
- `storage-facts.jsonl`: 60 facts (25 command, 23 knowledge, 6 troubleshooting, 6 recommendation)
- `storage-train.jsonl`: 224 examples (command 94, knowledge 79, troubleshooting 20, recommendation 20, negative 11). Each fact has 3 to 5 examples.
- `storage-eval-taught.jsonl`: 60 held-out questions, one per fact
- The pages were read as raw HTML and converted to text; a generator built the records and a validator checked them (neither is included).

## Version baseline
- SUSE docs "latest" = **SUSE Storage 1.12 (1.12.1)**. Citations use the `/cloudnative/storage/latest/en/...` URLs, so they will move when 1.13 becomes latest.
- longhorn.io "latest" is 1.13.0. I fetched the **1.12.1** pages to match the SUSE version and used them only to cross-check.

## Pages read (fetched raw with curl, converted with pandoc)
SUSE (`https://documentation.suse.com/cloudnative/storage/latest/en/`): introduction/concepts, installation-setup/requirements, installation-setup/best-practices, installation-setup/installation/install-using-helm, installation-setup/uninstallation, important-notes, v1-v2-volume-behavior-and-feature-parity, volumes/storageclass-parameters, volumes/create-volumes, volumes/rwx-volumes, volumes/volume-expansion, volumes/volume-conditions, volumes/volume-encryption, high-availability/data-locality, high-availability/node-failure, high-availability/replica-rebuilding, high-availability/volume-recovery, snapshots-backups/volume-snapshots-backups/{configure-backup-target, create-backup, create-snapshot, create-recurring-backup-snapshot-job}, snapshots-backups/csi-snapshots/{csi-snapshot-longhorn-backup, csi-snapshot-longhorn-snapshot}, data-integrity-recovery/disaster-recovery-volumes, data-integrity-recovery/data-recovery/{recover-from-full-disk, recover-from-data-errors}, nodes/{scheduling, storage-tags, multiple-disks, default-disk-and-node-config, disks-or-nodes-eviction, node-conditions}, upgrades/upgrades, upgrades/longhorn-components/{upgrade-longhorn-manager, manually-upgrade-engine, auto-upgrade-engine}, troubleshooting-maintenance/{troubleshooting, support-bundle, maintenance}, longhorn-system/{settings, customize-default-settings}, longhorn-system/system-access/longhorn-cli, volumes/delete-volumes, glossary/glossary.
longhorn.io 1.12.1: references/storage-class-parameters, references/settings, advanced-resources/deploy/customizing-default-settings, maintenance/maintenance, snapshots-and-backups/backup-and-restore/set-backup-target, nodes-and-volumes/volumes/rwx-volumes, deploy/install/install-with-kubectl, deploy/uninstall.

## Naming decisions
- The product is called "SUSE Storage", as in the SUSE docs. Longhorn identifiers stay exactly as they are: longhorn-system, driver.longhorn.io, longhorn.io API group, longhorn-manager, instance-manager, settings.longhorn.io, node.longhorn.io, and the "Longhorn Engine/Manager" component names. Fact storage-001 teaches this mapping explicitly.
- The Helm examples use the SUSE Application Collection chart `oci://dp.apps.rancher.io/charts/suse-storage`, not the community `longhorn/longhorn` repository.
- No pricing or licensing wording, and the word "free" does not appear in any output. No comparisons with other storage products.

## Contradictions and rendering problems avoided
1. **staleReplicaTimeout default**: the SUSE StorageClass page says the default is 30. The examples on the same page and the longhorn.io 1.12.1 page use or state 2880. The dataset never states a default.
2. **disableRevisionCounter**: the stated default is true, but the example YAML shows false. Not used.
3. **freezeFSForSnapshot** (example YAML comment) vs **freezeFilesystemForSnapshot** (field definition). Not used.
4. **V2 maturity**: important-notes says V2 is generally available in v1.12.0. The settings page still calls the V2 setting "experimental". I followed important-notes (storage-029). The settings text looks stale.
5. **Kubernetes minimum**: requirements says v1.34 or later; best-practices says "v1.21 or later before upgrading". The dataset states no minimum.
6. **Snapshot limit**: concepts says 254 (read index); volume-conditions and settings say 250 (Snapshot Maximum Count). Not used.
7. **Recurring-job label commands**: the SUSE HTML renders `<RECURRING-JOB-NAME≥enabled` (a typo for `>=enabled`). I used `=enabled`, which is confirmed by the concrete examples on the same page (`recurring-job.longhorn.io/backup=enabled`).
8. **DR volume manifest/patch**: the text says the field is `standby`, but the YAML uses `Standby: true` and the patch path `/spec/Standby`. The kubectl DR commands were left out; DR facts cover concepts and UI activation only.
9. **Default backup target config**: SUSE says to use the `longhorn-default-resource` ConfigMap from v1.8 onward. The longhorn.io 1.12.1 customizing page still shows `backup-target` in `longhorn-default-setting`. Not used.
10. **longhornctl install** command contains an unrendered `{{< current-version >}}` placeholder. Only `./longhornctl check preflight` is taught as a command; `install preflight` is mentioned by name only.
11. **Multi-line commands joined**: the helm upgrade command (inline `# Replace…` comment removed) and the S3 `kubectl create secret` command appear in the docs with `\` line continuations. The dataset gives them as single lines with identical flags.
12. `kubectl edit node.longhorn.io <node-name>` is kept verbatim as documented, without `-n longhorn-system`.

## Negatives (11, type "negative")
Each covers a plausible but undocumented item: the `replicaCount` parameter, `dataLocality: "strict"`, `dataEngine: "spdk"`, the ReadOnlyMany access mode, helm-rollback downgrade, skip-minor upgrades, a `full-backup` RecurringJob task, VolumeSnapshotClass `type: backup`, a `minio://` backup target scheme, V2 live engine upgrade in 1.12, and strict-local on RWX. Each is grounded in a documented list of valid values or an explicit "not supported" statement.

## Concerns
- There are 60 facts rather than about 50. The V2 strict-local fact was split out so that each fact cites a single page.
- Several command facts are YAML key lines or URL templates with placeholders such as `<VOLUME-NAME>`. Eval checks match on those exact strings.
- A few answers mention related settings or commands from the same page in addition to the fact itself (for example, `systemctl enable iscsid` next to the open-iscsi install).
