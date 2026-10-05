# SUSE Virtualization (Harvester): v1 dataset notes

## Files
- `virtualization-facts.jsonl`: 53 facts (28 knowledge, 16 command, 6 recommendation, 3 troubleshooting)
- `virtualization-train.jsonl`: 223 examples (212 tied to facts with 4 each, plus 11 negative)
- `virtualization-eval-taught.jsonl`: 53 held-out questions, one per fact
- Generator and validator: `scratchpad/v1-virt/build.py` and `validate.py`. Raw pages are under `scratchpad/v1-virt/` (`s18/` holds the SUSE HTML and text, `v18/` and `v19/` the Harvester markdown).

## Version anchor
- **SUSE Virtualization v1.8**. This is the latest release on documentation.suse.com (v1.8.2 release notes) as of 2026-10-04. docs.harvesterhci.io already lists v1.9 as its latest version, and v1.9 is linked from the SUSE site but not marked latest there.
- Every `source` is a SUSE v1.8 URL (`https://documentation.suse.com/cloudnative/virtualization/v1.8/en/...`).
- Exact commands and YAML came from the raw markdown at `github.com/harvester/docs` `versioned_docs/version-v1.8` (the source of docs.harvesterhci.io/v1.8). Each command was then checked against the text of the matching SUSE v1.8 page.
- Every fact was diffed against v1.9 and is unchanged there, except the ones noted below.

## Pages read
SUSE v1.8 pages: introduction/overview, installation-setup/requirements, methods/iso-install, management-address, config/settings, virtual-machines/{live-migration, backup-restore, access-vm, create-vm, vm-images/upload-image}, networking/{cluster-network, vm-network}, upgrades/{upgrades, troubleshooting}, integrations/rancher/{rancher-integration, virtualization-management, node-driver/node-driver, node-driver/rke2-cluster}, add-ons/pcidevices-controller, hosts/{hosts, witness-node, vgpu-support}, troubleshooting/{cluster, faq, virtual-machines, installation, operating-system}, storage/volumes/volume-snapshots.

Harvester markdown, v1.8 and v1.9: the same topics plus networking/deep-dive, rancher/{csi-driver, cloud-provider}, advanced/{storagenetwork, addons}, troubleshooting/os, install/{harvester-configuration, post-install}, authentication, getting-started/deploy-ha-cluster.

## Naming decisions
- The product is "SUSE Virtualization". "Harvester" appears as the project name, usually in the first mention or in user phrasing.
- Component and object names keep "Harvester": Harvester node driver, Harvester cloud provider, `harvester-longhorn`, `harvesterhci.io/*`, `harvester-system`, and the installer strings `Create a new Harvester cluster` / `Join an existing Harvester cluster`.
- Storage is "SUSE Storage (Longhorn)", following SUSE docs. Plain "Longhorn" is kept where the docs use it (embedded Longhorn UI, "Longhorn recurring jobs").
- Rancher is "Rancher", with "SUSE Rancher Prime" in the component-version fact, matching the SUSE upgrades table.
- CPU architecture is written "AMD64 or ARM64", following SUSE wording. The Harvester markdown says x86_64.

## Contradictions and risky areas avoided
- **OS naming.** The SUSE v1.8 overview says the OS is "OS Manager for SUSE Linux Enterprise Micro". The requirements page and the upgrades table say SUSE Linux Micro 6.2. The Harvester troubleshooting/os page still says "OpenSUSE-based". The dataset uses "immutable SUSE Linux Micro based OS" and "SUSE Linux Micro 6.2" (from the table).
- **Upgrade repository.** upgrades/troubleshooting Phase 1 describes an upgrade-repo *VM*, but the upgrades page says that from v1.7.0 the repository is Deployment-based. No fact covers Phase 1.
- **restoreVM=false.** One page says the upgrade will not proceed while non-migratable VMs run. Another says such VMs are shut down automatically in pre-drain. The dataset states only the part both agree on: with `false`, multi-node users must stop non-migratable VMs, and they are not restarted.
- **Port tables** differ substantially between v1.8 and v1.9. Only "nodes need TCP 443 to the Rancher load balancer" is used.
- **v1.9-only content excluded:** Kube-OVN overlay live migration, the node-driver menu path "Providers > Node Drivers", the "Kubernetes Version" dropdown and "same primary network for all machine pools" in RKE2 creation (v1.8 uses "Toggle Switch to RKE2/K3s"), the `harv-purge-images-v2.sh` script, and the v1.8→v1.9 upgrade path.
- **Node-driver user-data.** The v1.8 RKE2 page example installs `iptables`, while the node-driver page shows the `qemu-guest-agent` cloud-config. Only the node-driver page's qemu-guest-agent guidance is used.
- **Cloud-init re-run.** The FAQ gives `cloud-init clean --logs --reboot`, and troubleshooting/virtual-machines gives `sudo rm -rf /var/lib/cloud/*` plus a restart. Only the troubleshooting method is taught, so the dataset doesn't teach two commands for one fact.

## Command normalisation
- **Password reset.** The docs read `kubectl  -n cattle-system exec ...` with two spaces. The dataset uses a single space; the shell treats both the same.
- **Force-delete workaround.** The docs use the example `kubectl delete pod virt-launcher-ocffm031v000-rrkss -n namespace --force`. The dataset generalises it to `kubectl delete pod <virt-launcher-pod-name> -n <namespace> --force`.
- **MTU annotation.** `uplink-mtu="9000"` keeps the docs' example value. Answers tell the user to substitute their own MTU.
- **Eval arithmetic.** One eval reference derives 2400 s for a 16 GiB VM from the documented 150 s/GiB. Every other number appears verbatim in the docs.

## Negatives (11)
Each one is grounded in an explicit documentation statement:
- no downgrades, and no `allow-downgrade` setting (not in the v1.8 settings list)
- Longhorn recurring jobs are unsupported
- only one witness node per cluster
- the witness role can be assigned only at join time
- nested virtualization is unsupported
- no `live-migration-timeout` setting (use `kubevirt-migration`)
- the MTU cannot be set directly on a VM network
- the node driver supports cloud images only, not ISO images
- backups are limited to Longhorn volumes, so external CSI volumes cannot be backed up
- v1.6 to v1.8 is not a supported upgrade path
- a node's IP cannot be changed after installation

Non-existence of settings was checked against the full v1.8 settings list. The dataset never claims that a CLI binary doesn't exist.

## Concerns
- Version-specific facts (the component table, UEFI-only installs from v1.8.0, vGPU attached as a PCIDevice from v1.8.0, and the upgrade paths) will go stale with v1.9. Refresh them when SUSE marks v1.9 as latest.
- The ARM64 support statement comes from the requirements table. It was not cross-checked against a support matrix.
