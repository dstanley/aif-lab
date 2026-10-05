# SUSE dataset v0: review sample

Drafted from SUSE's public documentation; every record cites its source page. Please check facts, commands and product names.

## rancher

**Train · recommendation** — Auditors want proof our clusters meet CIS hardening. Anything built into Rancher?

Yes. The `rancher-compliance` app runs kube-bench against your clusters and collects the results with Sonobuoy. Pick the profile that matches the cluster, for example the RKE2 or K3s hardened or permissive profile, or the AKS, EKS or GKE profile for hosted clusters. You can schedule periodic scans and download the reports.

<sub>source: https://ranchermanager.docs.rancher.com/integrations-in-rancher/compliance-scans</sub>

**Train · command** — What commands install cert-manager before installing community Rancher?

`helm repo add jetstack https://charts.jetstack.io`
`helm repo update`
`helm install cert-manager jetstack/cert-manager --namespace cert-manager --create-namespace --set crds.enabled=true`
Then check the pods with `kubectl get pods --namespace cert-manager`.

<sub>source: https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster</sub>

**Train · troubleshooting** — Can I upgrade Rancher directly from a two-minor-versions-old release to the newest one?

No. The only tested and supported path between minor versions is from the latest patch of your current minor release to the latest patch of the next minor release. Upgrade one minor version at a time, take a backup before each step, and read the release notes for known issues.

<sub>source: https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/install-upgrade-on-a-kubernetes-cluster/upgrades</sub>

**Eval · command** — How can I follow the progress of a Rancher restore from the command line?

Graded on: cattle-resources-system; command `kubectl logs -n cattle-resources-system -l app.kubernetes.io/name=rancher-backup -f`

Follow the rancher-backup operator logs: `kubectl logs -n cattle-resources-system -l app.kubernetes.io/name=rancher-backup -f`.

<sub>source: https://ranchermanager.docs.rancher.com/how-to-guides/new-user-guides/backup-restore-and-disaster-recovery/restore-rancher</sub>

**Eval · command** — After migrating Rancher to a new cluster, how do I stop the old Rancher instance from conflicting with the agents?

Graded on: replicas=0; command `kubectl scale deployment rancher -n cattle-system --replicas=0`

Scale the old Rancher deployment to zero: `kubectl scale deployment rancher -n cattle-system --replicas=0`.

<sub>source: https://ranchermanager.docs.rancher.com/how-to-guides/new-user-guides/backup-restore-and-disaster-recovery/migrate-rancher-to-new-cluster</sub>

## rke2-k3s

**Train · recommendation** — I'm moving my RKE2 control plane to brand-new hosts using a snapshot. What do I need besides the snapshot file?

You need the original server token. When restoring to new hosts, pass `--token=<BACKED-UP-TOKEN-VALUE>` along with `--cluster-reset` and `--cluster-reset-restore-path`. Back up the token (from `/var/lib/rancher/rke2/server/token`) together with your snapshots.

<sub>source: https://docs.rke2.io/datastore/backup_restore</sub>

**Train · command** — How do I join a K3s agent to an existing server?

Pass the server URL and token to the installer: `curl -sfL https://get.k3s.io | K3S_URL=https://myserver:6443 K3S_TOKEN=mynodetoken sh -`. Setting `K3S_URL` makes the installer configure K3s as an agent. The token value comes from `/var/lib/rancher/k3s/server/node-token` on the server.

<sub>source: https://docs.k3s.io/quick-start</sub>

**Train · troubleshooting** — I edited rke2-coredns.yaml in the RKE2 manifests directory and my changes vanished after restart.

That's expected: RKE2 rewrites its packaged component files in `/var/lib/rancher/rke2/server/manifests` every time it starts, to ensure integrity. Customize packaged charts with a HelmChartConfig resource instead, or disable the component and deploy your own.

<sub>source: https://docs.rke2.io/install/packaged_components</sub>

**Eval · recommendation** — I want K3s with embedded etcd HA. What's the minimum number of servers and why?

Graded on: three, odd

Three servers; an embedded etcd cluster needs an odd number of server nodes to maintain quorum.

<sub>source: https://docs.k3s.io/datastore/ha-embedded</sub>

**Eval · definition** — What are rewrites in K3s registries.yaml?

Graded on: regular expression, regex, rewrite

Each mirror can have a set of rewrites, which use regular expressions to match and transform the name of an image before it is pulled from that mirror.

<sub>source: https://docs.k3s.io/installation/private-registry</sub>

## storage

**Train · recommendation** — We have nodes with local NVMe drives and want the lowest storage latency possible. Which Longhorn data engine should we pick?

The V2 Data Engine is the option built for this. It uses SPDK with user-space NVMe drivers for lower latency and higher IOPS, and local NVMe disks are strongly recommended for it. Plan for its requirements: an additional dedicated CPU core per node for the `spdk_tgt` process, 2 GiB of huge pages, Linux kernel 6.7 or later, and raw block-type disks in an isolatable IOMMU group. Also check the V1/V2 feature parity page; for example, strict-local data locality and engine live upgrade are not supported on V2.

<sub>source: https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/best-practices.html</sub>

**Train · command** — Is there a command that installs the open-iscsi and NFS prerequisites on all nodes for me?

Yes. `longhornctl` can install them: `longhornctl --kubeconfig ~/.kube/config --image longhornio/longhorn-cli:v<version> install preflight`. Add `--enable-spdk` to also prepare the V2 Data Engine prerequisites. Afterwards, run `longhornctl check preflight` to verify. On immutable distributions such as SLE Micro, reboot the nodes after the install sub-command and then run it again.

<sub>source: https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/requirements.html</sub>

**Train · troubleshooting** — After patching our nodes, Longhorn V1 volumes stopped attaching. The only change I see is open-iscsi was upgraded to 2.1.12.

That matches a known problem. The SUSE Storage requirements page warns against installing or upgrading to open-iscsi 2.1.12, because an upstream configuration change in that release breaks volume attachment. Use open-iscsi 2.1.11 or earlier, or 2.1.13 or later. Also confirm that `iscsid` is running and `iscsi_tcp` is loaded.

<sub>source: https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/requirements.html</sub>

**Eval · architecture** — Why would I schedule periodic full backups when Longhorn backups are incremental?

Graded on: full-backup-interval, corrupt

Incremental (delta) backups never replace a block that already exists in the backupstore, so a corrupted block stays corrupted and can make restores fail. Setting a non-zero `full-backup-interval` on a recurring backup job makes SUSE Storage take a full backup after that many incrementals. The full backup uploads all blocks and overwrites existing ones, including corrupted ones, at the cost of more time and network throughput.

<sub>source: https://documentation.suse.com/cloudnative/storage/latest/en/snapshots-backups/volume-snapshots-backups/create-recurring-backup-snapshot-job.html</sub>

**Eval · command** — What command creates the SUSE Application Collection image pull secret for a SUSE Storage install?

Graded on: dp.apps.rancher.io, application-collection; command `kubectl create secret docker-registry application-collection --docker-server=dp.apps.rancher.io --namespace=longhorn-system --docker-username=<your-username-or-service-account-username> --docker-password=<access-token-or-service-account-secret>`

`kubectl create secret docker-registry application-collection --docker-server=dp.apps.rancher.io --namespace=longhorn-system --docker-username=<your-username-or-service-account-username> --docker-password=<access-token-or-service-account-secret>`. Then set `global.imagePullSecrets` to `application-collection`.

<sub>source: https://documentation.suse.com/cloudnative/storage/latest/en/installation-setup/installation/install-using-rancher.html</sub>

## virtualization

**Train · recommendation** — Our Longhorn replication traffic is competing with management traffic on the same NICs. What should I configure in Harvester?

Configure the SUSE Virtualization storage network. It isolates SUSE Storage (Longhorn) replication traffic from mgmt and other cluster-wide workloads. Prerequisites:
1. Assign a dedicated VLAN ID on the switches.
2. Make sure a cluster network and VLAN network cover all nodes.
3. Choose an IPv4 range that does not overlap 10.42.0.0/16, 10.43.0.0/16, 10.52.0.0/16 or 10.53.0.0/16.
4. Stop all VMs before enabling it.
SUSE recommends using the UI (Advanced → Settings → storage-network).

<sub>source: https://documentation.suse.com/cloudnative/virtualization/latest/en/networking/storage-network.html</sub>

**Train · command** — How can I see which migration object belongs to a running Harvester VM?

During a migration, the VirtualMachineInstance records the migration object's UID:
`kubectl get vmi demo -ojsonpath={.status.migrationState.migrationUID}`
In the other direction, the VirtualMachineInstanceMigration object stores the VMI name:
`kubectl get vmim demo-6crrk -ojsonpath={.spec.vmiName}`
Migrations started from the Migrate menu are named after the VM plus a random suffix. Automatic ones start with `kubevirt-evacuation-`.

<sub>source: https://documentation.suse.com/cloudnative/virtualization/latest/en/virtual-machines/live-migration.html</sub>

**Train · troubleshooting** — My Harvester VM is Unschedulable and its pod is Pending with a node affinity error on network.harvesterhci.io/cn2. Why?

SUSE Virtualization automatically adds affinity rules based on VM configuration. A VM attached to cluster network cn2 gets the rule `network.harvesterhci.io/cn2`. If no active node has that cluster network configured and labeled, the VM cannot be scheduled. Check that cn2 has a network configuration covering active nodes and that those nodes carry the label. Manual edits to automatically applied rules are reverted by the webhook.

<sub>source: https://documentation.suse.com/cloudnative/virtualization/latest/en/troubleshooting/virtual-machines.html</sub>

**Eval · procedure** — I forgot the admin password of the Harvester dashboard. How do I reset it?

Graded on: reset-password

SSH to a management node, switch to root, and run the rancher pod's reset-password command: kubectl -n cattle-system exec $(kubectl --kubeconfig $KUBECONFIG -n cattle-system get pods -l app=rancher --no-headers | head -1 | awk '{ print $1 }') -c rancher -- reset-password. It prints a new password for the default administrator.

<sub>source: https://documentation.suse.com/cloudnative/virtualization/latest/en/troubleshooting/faq.html</sub>

**Eval · architecture** — What timeouts apply to live migration in SUSE Virtualization by default?

Graded on: 150

The completion timeout is 150 seconds per GiB of data (for example 1,200 seconds for an 8 GiB VM), set by completionTimeoutPerGiB; the progress timeout aborts a migration if memory copy stalls for 150 seconds, set by progressTimeout. Both are in the kubevirt-migration setting.

<sub>source: https://documentation.suse.com/cloudnative/virtualization/latest/en/virtual-machines/live-migration.html</sub>

## security

**Train · recommendation** — Someone could exec into a container and run nmap or a reverse shell. How can I detect or block that at runtime?

A runtime security tool that profiles process behavior can catch this. SUSE Security has built-in suspicious process detection for tools such as nmap, nc/ncat/netcat, socat, ssh and scp, and for reverse shells (stdin and stdout redirected to the same socket). These are alerted in Discover or Monitor mode and blocked in Protect mode unless explicitly allowed for that group. Process profile rules or zero-drift protection add a baseline so any unexpected new process is also flagged.

<sub>source: https://documentation.suse.com/cloudnative/security/latest/en/processrules.html</sub>

**Train · command** — What are the CLI options to set bandwidth thresholds on a NeuVector group?

Run `set group <group-name> setting -h` in the CLI to see them. The options are `--monitor_metric [enable|disable]`, `--cur_sess` (active session threshold), `--sess_rate` (session rate in cps) and `--bandwidth` (throughput in Mbps).

<sub>source: https://documentation.suse.com/cloudnative/security/latest/en/detectbandwidthddos.html</sub>

**Train · troubleshooting** — Registry scanning in NeuVector keeps failing. Where should I look?

According to the SUSE Security troubleshooting guide, most registry scanning issues are registry authentication errors or the controller being unable to reach the registry from the cluster. Verify the credentials and URL in Assets → Registries and network access from the cluster. Also make sure at least one repository filter is set, and that scanners have enough memory for large images.

<sub>source: https://documentation.suse.com/cloudnative/security/latest/en/troubleshooting.html</sub>

**Eval · architecture** — How does SUSE Security handle egress to destinations defined by Istio ServiceEntry?

Graded on: ServiceEntry

Since 5.1.0, SUSE Security can enforce egress rules for pods connecting to Istio ServiceEntry destinations, instead of classifying all such traffic as External. Implicit violations are reported for newly visible traffic without allow rules; rules can be learned in Discover mode, or you can create a custom group with the destination addresses or DNS name and add an allow rule.

<sub>source: https://documentation.suse.com/cloudnative/security/latest/en/networkrules.html</sub>

**Eval · definition** — What does the 'Scorable' setting on a NeuVector group control?

Graded on: Security Risk Score, risk score

The Scorable checkbox on a learned group controls whether that group's containers are used to calculate the Security Risk Score shown in the Dashboard.

<sub>source: https://documentation.suse.com/cloudnative/security/latest/en/groups.html</sub>

## linux

**Train · recommendation** — After moving to SLES 16, we need password-based root login over SSH again for a legacy tool. What does SUSE suggest?

On SUSE Linux 16, password-based root login over SSH is disabled by default, while console root login and key-based root login via `/root/.ssh/authorized_keys` still work. To re-enable password login, install the `openssh-server-config-rootlogin` package. If you can, prefer key-based login or a non-root user. The first user created during installation is added to the wheel group and can use sudo.

<sub>source: https://documentation.suse.com/sles/16.0/html/SLE-comparison/</sub>

**Train · command** — What's the Helm command to install SUSE AI Factory 2.2.0?

Run `helm install aif-operator oci://ghcr.io/suse/chart/aif-operator:2.2.0 --namespace aif-operator --create-namespace`. You can review the chart values first with `helm show values oci://ghcr.io/suse/chart/aif-operator --version 2.2.0`. Afterward, check the pods with `kubectl get pods -A | grep aif`. You should see `aif-operator` in the `aif-operator` namespace and `aif-ui-server` in `cattle-ui-plugin-system`.

<sub>source: https://documentation.suse.com/en-us/suse-ai-factory/latest/html/AI-Factory-deployment/aif-deployment.html</sub>

**Train · troubleshooting** — With my own access token I can pull the SUSE AI charts, but our CI's service account gets denied. Same person set both up.

This is how Application Collection subscriptions work. A user account inherits the subscriptions of every organization the user belongs to. A service account belongs to one organization and only has that organization's subscriptions. If the service account's organization has only a Prime subscription, it cannot pull content that requires SUSE AI. Create the service account under the organization that holds the SUSE AI subscription. Only organization admins can create service accounts.

<sub>source: https://docs.apps.rancher.io/get-started/authentication</sub>

**Eval · command** — Install only the patch for CVE-2010-2713 on SLES with zypper.

Graded on: --cve; command `sudo zypper patch --cve=CVE-2010-2713`

Run `sudo zypper patch --cve=CVE-2010-2713`. To list related patches first, run `zypper list-patches --cve=CVE-2010-2713`.

<sub>source: https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-sw-cl.html</sub>

**Eval · troubleshooting** — Our cluster suddenly gets HTTP 429 errors when pulling from dp.apps.rancher.io. What's happening?

Graded on: rate limit, ratelimit, quota

You have hit the Application Collection pull rate limit. Requests over the quota for the rolling 24-hour window receive 429 TOO MANY REQUESTS, and the quota depends on your subscription and on whether you use a user or service account. Check the `ratelimit-limit` and `ratelimit-remaining` response headers or your profile settings. Consider service accounts, which generally have higher limits, or mirroring images.

<sub>source: https://docs.apps.rancher.io/get-started/rate-limits</sub>

