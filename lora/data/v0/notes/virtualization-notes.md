# Virtualization dataset notes (SUSE Virtualization / Harvester)

Built 2026-10-04. The SUSE docs "latest" pointed to **SUSE Virtualization v1.8 (Latest)** (v1.9 Dev). All SUSE URLs below use the `latest` path, which resolved to v1.8. If "latest" moves to v1.9, version-specific facts (component table, UEFI-only from v1.8.0, vGPU via PCI passthrough from v1.8.0) should be checked again.

Output: `virtualization-train.jsonl` (114 records, 19 of each type), `virtualization-eval.jsonl` (18 records, 3 of each type). Both validated: JSON parses, the key sets are correct, each eval reference contains at least one expect_any term and its expect_command, no duplicate instructions, and no eval instruction overlaps a train instruction by more than 0.25 Jaccard.

## Pages read (38)

Base: https://documentation.suse.com/cloudnative/virtualization/latest/en/

- introduction/overview.html
- installation-setup/requirements.html
- introduction/deploy-ha-cluster.html
- introduction/deploy-singlenode-cluster.html
- introduction/glossary.html
- installation-setup/airgap.html
- installation-setup/config/configuration-file.html
- virtual-machines/create-vm.html
- virtual-machines/live-migration.html
- virtual-machines/backup-restore.html
- virtual-machines/vm-images/upload-image.html
- virtual-machines/access-vm.html
- virtual-machines/vm-resources/resource-overcommit.html
- networking/cluster-network.html
- networking/vm-network.html
- networking/storage-network.html
- networking/vm-migration-network.html
- upgrades/upgrades.html
- upgrades/troubleshooting.html
- integrations/rancher/rancher-integration.html
- integrations/rancher/virtualization-management.html
- integrations/rancher/node-driver/rke2-cluster.html
- integrations/rancher/cloud-provider.html
- integrations/rancher/csi-driver.html
- add-ons/add-ons.html
- add-ons/pcidevices-controller.html
- add-ons/nvidia-driver-toolkit.html
- add-ons/vm-import-controller.html
- hosts/hosts.html
- hosts/vgpu-support.html
- hosts/witness-node.html
- storage/storage.html
- storage/volumes/volume-snapshots.html
- troubleshooting/virtual-machines.html
- troubleshooting/installation.html
- troubleshooting/faq.html
- https://docs.harvesterhci.io/v1.6/ (Harvester Overview)
- https://docs.harvesterhci.io/v1.6/vm/hotplug-volume

## Naming decisions

| Decision | Evidence |
|---|---|
| Product name is **SUSE Virtualization**. Harvester is the open-source project name, used as "SUSE Virtualization (Harvester)" or simply "Harvester" in user questions | SUSE docs title "SUSE® Virtualization v1.8"; the overview says "SUSE® Virtualization is a modern, open, interoperable, hyperconverged infrastructure (HCI) solution built on Kubernetes" (introduction/overview.html). The community docs use the same sentence with "Harvester" (https://docs.harvesterhci.io/v1.6/). |
| Component names keep "Harvester": Harvester Node Driver, Harvester Cloud Provider, Harvester CSI Driver, Harvester UI Extension, Harvester Terraform Provider | introduction/glossary.html, integrations/rancher/csi-driver.html, installation-setup/airgap.html, virtual-machines/create-vm.html |
| Built-in storage is **SUSE Storage**, with "Longhorn" where the docs use it (StorageClass `harvester-longhorn`, "Longhorn V1/V2 Data Engine", embedded Longhorn UI). Written as "SUSE Storage (Longhorn)". | introduction/overview.html ("SUSE® Storage is the built-in storage system"); hosts/witness-node.html ("Longhorn, a distributed block storage system") |
| Rancher is **SUSE Rancher Prime**, often just "Rancher" in UI steps, as the docs do | integrations/rancher/rancher-integration.html; installation-setup/requirements.html |
| OS is **SUSE Rancher Prime: OS Manager for SUSE Linux Enterprise Micro**; the v1.8 component table says SUSE Linux Micro 6.2 | introduction/overview.html; upgrades/upgrades.html |
| GitOps is **SUSE Rancher Prime: Continuous Delivery**. Mentioned only in passing. | integrations/rancher/rancher-integration.html |

No pricing or licensing claims were made. "Open-source" is used only where the docs use it (Harvester project; the overview's "open-source alternative" wording was not repeated). The one comparison question ("is it a good fit vs. our current platform") answers in terms of what the choice depends on, with no claims about other products.

## Uncertain items left out or handled carefully

- **VirtualMachine YAML example on create-vm.html**: in the published example, `networks:` is indented under `domain:` (KubeVirt expects it under `template.spec`), and `memory: "3996Mi"` sits directly under `domain`. I did not reproduce the YAML. The command example uses the docs' Terraform `harvester_virtualmachine` block instead and only mentions that a KubeVirt `VirtualMachine` object can be used.
- **Harvester CSI Driver RWX**: the feature table shows RWX volumes from driver 0.1.20, but a note on the same page says the driver "only supports single-node read-write (RWO) volumes". Because the page contradicts itself, RWX claims were left out.
- **Upgrade phase 1** (upgrades/troubleshooting.html) describes a repository *VM*, while upgrades.html says v1.7.0+ uses a deployment-based repository. The phase was written generically as "Provision the upgrade repository".
- **Stale cloud credentials** fix: only the cause and the docs topic name are given. The linked fix page was not read.
- The **kubevirt-migration setting** field names (`allowAutoConverge`, `completionTimeoutPerGiB`, `progressTimeout`) are used as named, but no full JSON value is given because the docs page shows none.
- **Overlay network (Kube-OVN)** is marked experimental. Its long limitation list was summarized only briefly (mgmt-only in v1.6, external networks cannot reach these VMs).
- Leftovers in the docs that still say "Harvester version below v1.2.0" (cloud-provider backward-compatibility notice) were not used.
- **Not covered** (pages not read): Terraform provider page, rancher-rbac, resource quotas, K3s guest clusters, vm-dhcp-controller, the full Windows VM page, CPU pinning and hotplug details, monitoring and logging.
