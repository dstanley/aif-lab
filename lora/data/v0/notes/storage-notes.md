# Storage dataset notes (SUSE Storage / Longhorn)

Built 2026-10-04. Train: 122 records, eval: 18 records. Generators: `gen_storage_train.py`, `gen_storage_eval.py` (same directory).

## Doc versions used
- SUSE docs: `documentation.suse.com/cloudnative/storage/latest/en/`, which the page header labels "SUSE® Storage 1.12 (Latest)". The pages reference v1.12.1.
- Upstream: `longhorn.io/docs/1.12.2/`. I picked 1.12.2 to match the SUSE 1.12 line. The upstream site also lists 1.13.0, but I did not use it.

## Pages read (fetched and read in full)
SUSE (`https://documentation.suse.com/cloudnative/storage/latest/en/` + path):
introduction/introduction.html, introduction/concepts.html, introduction/terminology.html, glossary/glossary.html,
installation-setup/requirements.html, installation-setup/best-practices.html, installation-setup/installation/install-using-helm.html,
installation-setup/installation/install-using-rancher.html, migration/migration.html, volumes/create-volumes.html,
volumes/storageclass-parameters.html, volumes/rwx-volumes.html, volumes/volume-expansion.html, volumes/volume-encryption.html,
volumes/volume-conditions.html, high-availability/data-locality.html, high-availability/node-failure.html,
high-availability/replica-rebuilding.html, high-availability/volume-recovery.html, high-availability/automatic-replica-balancing.html,
snapshots-backups/volume-snapshots-backups/volume-snapshots-backups.html, .../configure-backup-target.html,
.../create-recurring-backup-snapshot-job.html, .../restore-volume-from-backup.html, snapshots-backups/csi-snapshots/csi-snapshot-longhorn-backup.html,
data-integrity-recovery/disaster-recovery-volumes.html, data-integrity-recovery/data-recovery/recover-from-full-disk.html,
nodes/storage-tags.html, nodes/disks-or-nodes-eviction.html, nodes/default-disk-and-node-config.html, nodes/multiple-disks.html,
troubleshooting-maintenance/maintenance.html, troubleshooting-maintenance/troubleshooting.html, troubleshooting-maintenance/support-bundle.html,
troubleshooting-maintenance/v2-data-engine-issues.html, upgrades/upgrades.html, upgrades/longhorn-components/upgrade-longhorn-manager.html,
upgrades/longhorn-components/auto-upgrade-engine.html, v1-v2-volume-behavior-and-feature-parity.html,
longhorn-system/networking/storage-network.html, longhorn-system/settings.html (only the relevant sections).

Longhorn (`https://longhorn.io/docs/1.12.2/` + path):
deploy/install/install-with-kubectl/, deploy/uninstall/, deploy/accessing-the-ui/, nodes-and-volumes/nodes/scheduling/,
nodes-and-volumes/volumes/trim-filesystem/, nodes-and-volumes/volumes/detaching-volumes/, snapshots-and-backups/setup-a-snapshot/,
snapshots-and-backups/snapshot-space-management/, snapshots-and-backups/backup-and-restore/create-a-backup/,
snapshots-and-backups/csi-volume-clone/, high-availability/rwx-volume-fast-failover/, advanced-resources/longhornctl/,
advanced-resources/system-backup-restore/backup-longhorn-system/, advanced-resources/data-recovery/data-error/,
advanced-resources/deploy/customizing-default-settings/, data-engine-comparison/.

## Naming decisions
- **Product name: "SUSE Storage"**, with Longhorn as the upstream project. The SUSE docs use "SUSE® Storage" throughout. The concepts page says: "SUSE Storage is derived from the upstream open-source Longhorn project. While this documentation refers to its conceptual components as SUSE Storage, the underlying codebase, Kubernetes resources, and command-line tools intentionally retain the longhorn nomenclature" — https://documentation.suse.com/cloudnative/storage/latest/en/introduction/concepts.html
  - In the dataset, answers say "SUSE Storage (Longhorn)" on first mention. Technical identifiers keep their Longhorn names (`longhorn-system`, `driver.longhorn.io`, `longhorn.io` CRDs, Longhorn Engine/Manager), following the same page and the glossary's "Upstream Technical Identifiers" section (https://documentation.suse.com/cloudnative/storage/latest/en/glossary/glossary.html).
  - Answers sourced from longhorn.io say "Longhorn" where the page does.
- **SUSE Rancher Prime**: the name is used only as the docs show it, for installing and upgrading the SUSE Storage app on clusters managed by SUSE Rancher Prime. Sources: https://documentation.suse.com/cloudnative/storage/latest/en/upgrades/longhorn-components/upgrade-longhorn-manager.html and https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/installation/install-using-rancher.html
- **SUSE Application Collection**: the chart source `oci://dp.apps.rancher.io/charts/suse-storage` — https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/installation/install-using-helm.html
- SUSE Virtualization and SUSE Security are not mentioned. None of the storage pages I read needed them.

## Positioning
- No "free", "no licensing", pricing or support claims appear anywhere. A grep for "free" finds only "free disk space".
- The pages I read do not literally say "component of the SUSE Rancher Prime stack". So the dataset says only what they support: SUSE Storage installs from SUSE Application Collection and can be installed and upgraded as an app on SUSE Rancher Prime-managed clusters.
- No comparisons with other storage products. The docs I read do not make any.

## Uncertainties and things left out
- Stale Replica Timeout default: the StorageClass parameters page says the default is 30, but its example YAML uses "2880" with the comment "48 hours". I left the default out and used only the examples as written.
- Disable Revision Counter: listed as "Default: true" on the StorageClass parameters page. I did not cover it.
- Allow Volume Creation with Degraded Availability: the setting's default is `true` (settings page), while best practices recommend `false`. The dataset states both.
- V2 engine upgrade: I stated "not supported in 1.12; detach before upgrade" as the docs do. I did not repeat the planned 1.12-to-1.13 support as a fact.
- `{patch-version}` and `{{< current-version >}}` placeholders in the SUSE docs: I kept them as `<version>` and did not guess a version.
- Sharding is described only as Experimental and not for production, as the docs say.
- Not covered: Kubernetes version minimums (the requirements page says v1.34+, but best practices says v1.21+ before upgrading, which looks inconsistent), the multipathd preflight warning (the docs only link to a KB article), backing images, ublk/interrupt mode, and Velero restore.

## Eval de-duplication
I checked that no eval `expect_command` string appears in the training outputs. I removed or reworded training items that gave away eval answers (NFSv4.1 kernel check, the application-collection secret command, the restore size format, kernel-default).

## Process note
The shared `scratchpad/pages/` directory, used by another agent (SUSE Virtualization pages), was hit by a filename clash early on. My `h2t.py` pass also regenerated the `.txt` files there from their `.html`. I then moved all my work to `scratchpad/stg/` and `scratchpad/lh/`. My first fetch may have briefly overwritten that agent's `installation-setup_requirements.html`. By the time I checked, the file held the Virtualization page again. Its `.txt` derivatives were rewritten by my converter.
