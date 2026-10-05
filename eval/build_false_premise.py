import json
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C, I = "contradicts", "invented"
rows = [
# rancher
("rancher",C,"rancher-035","Deleting a registered cluster in Rancher also wipes the downstream nodes, right? I want to be sure the old cluster is gone.","No. Deleting a registered cluster from Rancher only detaches it; the cluster keeps running and is accessible as before. Only EKS, AKS or GKE clusters that Rancher created are destroyed when deleted.",["detach","keeps running"]),
("rancher",C,"rancher-016","Since the rancher-backup operator backs up every downstream cluster's workloads, I can skip Velero, yes?","No. The rancher-backup operator runs only on the local cluster and backs up only the Rancher application, not downstream workloads.",["only the Rancher","Rancher application","local cluster"]),
("rancher",C,"rancher-014","To roll back a bad Rancher upgrade I'll just run helm rollback on the rancher release. That's the supported way?","No. Changing Rancher versions with Helm or kubectl is not supported; roll back by restoring a backup made before the upgrade with the Rancher Backups application.",["backup","Rancher Backups"]),
("rancher",C,"rancher-009","We're on Rancher v2.12; jumping straight to v2.14 in one upgrade is the tested path, correct?","No. The only tested and supported path is from the latest patch of your current minor release to the latest patch of the next minor release, one minor version at a time.",["next minor","latest patch"]),
("rancher",I,None,"What does `rancher cluster migrate --to-prime` do when moving a community install to Prime?","There is no documented `rancher cluster migrate` command in the Rancher CLI. Rancher Prime is installed and upgraded with Helm from the Prime chart repository.",["helm","Helm"]),
("rancher",I,None,"How do I set the Rancher Helm value `autoHeal.downstreamAgents=true` so disconnected cluster agents restart themselves?","There is no documented `autoHeal` value in the Rancher chart. If a registered cluster stays Pending, check the cattle-cluster-agent pod in cattle-system and its connection to the server-url.",["cattle-cluster-agent","server-url"]),
("rancher",I,None,"Which Rancher global setting, `fleet-gitops-strict-mode`, blocks manual kubectl changes on downstream clusters?","There is no documented `fleet-gitops-strict-mode` setting. Fleet (Continuous Delivery) deploys from Git, but Rancher does not document a setting that blocks manual kubectl changes.",["Fleet","Continuous Delivery"]),
# rke2
("rke2",C,"rke2-031","We installed RKE2 with Canal. I'll just change cni: cilium in config.yaml and restart to switch, right?","No. The primary CNI cannot be changed on a running cluster; choose it with the cni key before the cluster is created.",["cannot be changed","cannot"]),
("rke2",C,"rke2-025","Restoring an RKE2 etcd snapshot onto a fresh host only needs the snapshot file, nothing else?","No. You also need the original server token from /var/lib/rancher/rke2/server/token, passed with --token, because it decrypts the bootstrap data in the snapshot.",["token"]),
("rke2",C,"rke2-010","RKE2 servers only need port 6443 open between nodes, since agents register over the Kubernetes API, correct?","No. Servers also listen on TCP 9345 for node registration (the supervisor API); both 9345 and 6443 must be reachable and forwarded by any load balancer.",["9345"]),
("rke2",C,"rke2-034","registries.yaml only needs to be on the RKE2 server nodes; agents pick up the mirror config from the servers, yes?","No. /etc/rancher/rke2/registries.yaml must exist on every node that pulls from the registry, including agents and schedulable servers.",["every node"]),
("rke2",I,None,"How do I use `rke2 cluster-upgrade --auto` to upgrade all nodes in one go?","There is no documented `rke2 cluster-upgrade` command. Upgrade nodes with the install script or packages, or automate it with the system-upgrade-controller.",["system-upgrade-controller","install script"]),
("rke2",I,None,"What's the `ingress-autotls: true` key in RKE2's config.yaml for turning on automatic Let's Encrypt certificates?","There is no documented `ingress-autotls` key in RKE2's config.yaml.",["not documented","no documented"]),
("rke2",I,None,"Which `rke2 doctor` subcommand checks a node's prerequisites before install?","There is no documented `rke2 doctor` command. Check the requirements in the RKE2 documentation (ports, OS, resources) before installing.",["requirements"]),
# storage
("storage",C,"storage-006","When I delete files inside a SUSE Storage volume, its size on disk shrinks automatically, right?","No. Volumes are thin-provisioned, but their actual size does not shrink when files are deleted, because SUSE Storage works at the block level and doesn't know the file system.",["block level","does not shrink","not shrink"]),
("storage",C,"storage-010","numberOfReplicas in a SUSE Storage StorageClass can go up to 50 for critical volumes, correct?","No. numberOfReplicas must be between 1 and 20; the default is 3.",["20"]),
("storage",C,"storage-036","For an S3 backup target, s3://my-bucket is enough; the region is detected automatically, yes?","No. The URL must include the region and end with a slash: s3://<bucket>@<region>/.",["@","region"]),
("storage",C,"storage-027","Running both V1 and V2 data engines on every node costs nothing extra, so we should just enable both?","No. SUSE Storage recommends one data engine per cluster: with both enabled each node runs separate V1 and V2 instance-manager pods with their own CPU reservations.",["instance-manager","one data engine"]),
("storage",I,None,"How do I run `longhornctl volume shrink` to reclaim space from an oversized volume?","Shrinking volumes is not documented. SUSE Storage volumes can be expanded, but not shrunk.",["expand"]),
("storage",I,None,"What value should the SUSE Storage setting `replica-auto-dedupe` have to save space across volumes?","There is no documented `replica-auto-dedupe` setting in SUSE Storage.",["not documented","no documented"]),
("storage",I,None,"Which annotation, `longhorn.io/backup-priority: high`, makes a volume's backups run first?","There is no documented `longhorn.io/backup-priority` annotation. Backups are scheduled with recurring jobs.",["recurring"]),
# virtualization
("virtualization",C,"virt-025","If I enable Install guest agent in Cloud Config on a running SUSE Virtualization VM, it applies on the next reboot automatically?","No. cloud-init runs only on a VM's first boot; remove /var/lib/cloud/* inside the guest and restart for the change to apply.",["first boot","/var/lib/cloud"]),
("virtualization",C,"virt-032","SUSE Virtualization VM backups cover volumes from any CSI driver we attach, correct?","No. Backup support is limited to SUSE Storage (Longhorn) volumes; volumes from external storage are not backed up.",["Longhorn","SUSE Storage"]),
("virtualization",C,"virt-035","A VM backup schedule in SUSE Virtualization every 15 minutes is fine, yes?","No. The schedule interval must be at least one hour.",["one hour","1 hour"]),
("virtualization",C,"virt-004","We can put SUSE Virtualization VM disks on an iSCSI SAN as the node's main storage, that's supported?","No. Only local disks and hardware RAID are supported for node storage, and each disk should deliver 5,000+ random IOPS.",["local disk","hardware RAID"]),
("virtualization",I,None,"How do I use `harvesterctl vm clone --live` to clone a running VM?","There is no documented `harvesterctl` command.",["not documented","no documented"]),
("virtualization",I,None,"What's the `vm-auto-balance` setting in SUSE Virtualization that moves VMs between hosts on load?","There is no documented `vm-auto-balance` setting in SUSE Virtualization.",["not documented","no documented"]),
("virtualization",I,None,"Which SUSE Virtualization setting, `gpu-overcommit-ratio`, lets several VMs share one passthrough GPU?","There is no documented `gpu-overcommit-ratio` setting.",["not documented","no documented"]),
# security
("security",C,"sec-019","In Protect mode, SUSE Security blocks network violations on the nodes group too, right?","No. Network violations of rules for the nodes group are never blocked, even in Protect mode; only process violations are blocked on nodes.",["never blocked","process"]),
("security",C,"sec-032","Admission control in Monitor mode stops denied deployments from being created, yes?","No. In Monitor mode a denied decision only logs an alert and the resource is still created; Protect mode blocks it.",["still created","Protect"]),
("security",C,"sec-015","If one group is in Protect and the other in Monitor, the connection between them is enforced as Protect, correct?","No. The effective mode is the least restrictive of the two, so it is evaluated as Monitor.",["least restrictive","Monitor"]),
("security",C,"sec-051","SUSE Security's persistent config backup works with a ReadWriteOnce volume, correct?","No. It needs a ReadWriteMany (RWX) persistent volume of 1Gi or more mounted at /var/neuvector.",["ReadWriteMany","RWX"]),
("security",I,None,"How do I enable `auto-quarantine-on-cve` so SUSE Security quarantines pods with critical CVEs?","There is no documented `auto-quarantine-on-cve` setting. Use admission control rules to keep vulnerable images from being deployed.",["admission"]),
("security",I,None,"What does the `neuvector-cli scan --deep` option add over a normal scan?","There is no documented `neuvector-cli scan --deep` option.",["not documented","no documented"]),
("security",I,None,"Which CRD, `NvRuntimeProfile`, holds a group's learned process profile?","There is no documented `NvRuntimeProfile` CRD. The policy CRDs are NvSecurityRule, NvClusterSecurityRule, NvAdmissionControlSecurityRule and NvGroupDefinition.",["NvSecurityRule"]),
# linux
("linux",C,"linux-018","On SUSE Linux Micro I can just run zypper install to add a package, right?","No. The root file system is read-only; use transactional-update, which applies changes to a new snapshot that becomes active after a reboot.",["transactional-update"]),
("linux",C,"linux-034","BCI-Micro includes RPM, so I can add packages to it in my Dockerfile, yes?","No. BCI-Micro is like BCI-Minimal but without the RPM package manager; it's meant for static binaries or multi-stage builds.",["without","multi-stage"]),
("linux",C,"linux-030","On a new SUSE Linux Micro install, Cockpit lets root log in with a password by default, correct?","No. Root password login is not allowed by default; create an unprivileged user and switch to administrative access in Cockpit.",["unprivileged","administrative access"]),
("linux",C,"linux-046","A SUSE Rancher Prime subscription includes the SUSE AI Library applications, so no other entitlement is needed?","No. The SUSE AI Library applications require the SUSE AI entitlement, which is separate from SUSE Rancher Prime.",["separate","SUSE AI entitlement"]),
("linux",I,None,"How do I use `zypper ai-install vllm` to set up vLLM on SLES?","There is no documented `zypper ai-install` command. vLLM is deployed as a SUSE AI Library application with Helm.",["Helm","helm"]),
("linux",I,None,"What does `SUSEConnect --auto-modules` do on SLES 15 SP7?","There is no documented `SUSEConnect --auto-modules` option. List available modules with SUSEConnect --list-extensions and activate one with SUSEConnect -p.",["--list-extensions","-p"]),
("linux",I,None,"Which transactional-update option, `--live-apply`, applies changes without a reboot on SUSE Linux Micro?","There is no documented `--live-apply` option; transactional-update changes become active after a reboot into the new snapshot.",["reboot"]),
]
facts = {json.loads(l)["id"] for l in open(os.path.join(ROOT, "data", "v1", "facts.jsonl"))}
alltext = open(os.path.join(ROOT, "data", "v1", "facts.jsonl")).read() + open(os.path.join(ROOT, "data", "v1", "train.jsonl")).read()
import re
out = []
for area, kind, fact, q, ref, exp in rows:
    assert fact is None or fact in facts, fact
    if kind == I:
        for tok in re.findall(r"`([^`]+)`", q):
            key = tok.split("=")[0].split(":")[0].strip()
            assert key.lower() not in alltext.lower(), (key, q)
    assert any(e.lower() in ref.lower() for e in exp), (exp, ref)
    out.append({"instruction": q, "input": "", "reference": ref, "area": area, "type": "false-premise", "premise": kind, "fact": fact, "expect_any": exp})
with open(os.path.join(ROOT, "eval", "false-premise.jsonl"), "w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(out), "questions;", sum(r["premise"] == C for r in out), "contradict a fact,", sum(r["premise"] == I for r in out), "invented")
tq = [json.loads(l)["instruction"].lower() for l in open(os.path.join(ROOT, "data", "v1", "train.jsonl"))]
import difflib
print("max similarity to a training question:", round(max(max(difflib.SequenceMatcher(None, r["instruction"].lower(), t).ratio() for t in tq) for r in out), 2))
