import json
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = [
("rancher","rancher-035","Deleting a registered cluster in Rancher just detaches it and leaves the cluster running, right?","Yes. Deleting a registered cluster only detaches it from Rancher; it keeps running and stays accessible as before registration.",["detach","keeps running","running"]),
("rancher","rancher-016","The rancher-backup operator only backs up the Rancher application on the local cluster, not downstream workloads, correct?","Yes. It is installed on the local cluster and backs up only the Rancher application.",["Rancher application","local cluster"]),
("rancher","rancher-014","To roll back a bad Rancher upgrade I should restore a backup taken before the upgrade, yes?","Yes. Rolling back is only possible by restoring a pre-upgrade backup with the Rancher Backups application; changing versions with Helm or kubectl is not supported.",["backup"]),
("rancher","rancher-009","Upgrading Rancher one minor version at a time, from the latest patch to the next minor's latest patch, is the tested path, correct?","Yes. The only tested and supported path is from the latest patch of your current minor release to the latest patch of the next minor release.",["latest patch","next minor"]),
("rke2","rke2-031","The primary CNI in RKE2 can't be changed once the cluster is running, so I need to pick it before install, right?","Yes. Choose it with the cni key in config.yaml before the cluster is created; the primary CNI cannot be changed on a running cluster.",["cni","before"]),
("rke2","rke2-025","Restoring an RKE2 etcd snapshot onto a new host needs the original server token as well as the snapshot, correct?","Yes. Pass the original token from /var/lib/rancher/rke2/server/token with --token; it decrypts the bootstrap data in the snapshot.",["token"]),
("rke2","rke2-010","RKE2 servers need both 9345 and 6443 reachable from the other nodes, yes?","Yes. TCP 9345 is the supervisor API for node registration and 6443 the Kubernetes API; a load balancer in front of the servers must forward both.",["9345","6443"]),
("rke2","rke2-034","registries.yaml has to be on every RKE2 node that pulls from the registry, agents included, right?","Yes. /etc/rancher/rke2/registries.yaml must exist on every node that pulls from the registry, including agents and schedulable servers.",["every node","registries.yaml"]),
("storage","storage-006","Deleting files inside a SUSE Storage volume doesn't shrink its size on disk, correct?","Correct. SUSE Storage works at the block level and doesn't know the file system, so a volume's actual size does not shrink when files are deleted.",["block level","block"]),
("storage","storage-010","numberOfReplicas in a SUSE Storage StorageClass must be between 1 and 20, right?","Yes. The default is 3 and the value must be between 1 and 20.",["20"]),
("storage","storage-036","An S3 backup target URL needs the region and a trailing slash, like s3://bucket@region/, yes?","Yes. The form is s3://<bucket>@<region>/; it must end with a slash and include the region.",["region","slash"]),
("storage","storage-027","SUSE Storage recommends enabling only one data engine per cluster, because both engines add their own instance-manager pods, correct?","Yes. With both enabled each node runs separate V1 and V2 instance-manager pods with their own CPU reservations, so one data engine per cluster is recommended.",["instance-manager","one data engine"]),
("virtualization","virt-025","Cloud-init on a SUSE Virtualization VM only runs at first boot, so later Cloud Config changes need the cloud-init directory cleared, right?","Yes. Delete /var/lib/cloud/* inside the guest and restart for cloud-init to run again.",["/var/lib/cloud","first boot"]),
("virtualization","virt-032","SUSE Virtualization VM backups only cover SUSE Storage (Longhorn) volumes, correct?","Yes. Backup support is limited to SUSE Storage (Longhorn) volumes; volumes on external storage are not backed up.",["Longhorn","SUSE Storage"]),
("virtualization","virt-035","A SUSE Virtualization VM backup schedule has to be at least an hour apart, yes?","Yes. The schedule interval must be at least one hour.",["one hour","1 hour","an hour"]),
("virtualization","virt-004","SUSE Virtualization supports only local disks and hardware RAID for node storage, right?","Yes. Only local disks and hardware RAID are supported, and each disk should deliver 5,000+ random IOPS.",["local disk","hardware RAID"]),
("security","sec-019","SUSE Security never blocks network violations for the nodes group, even in Protect mode, correct?","Correct. Network violations for the nodes group are never blocked, even in Protect mode; only process violations are blocked on nodes.",["never","process"]),
("security","sec-032","Admission control in Monitor mode only logs a denied decision and still lets the resource be created, right?","Yes. Monitor mode only logs an alert; Protect mode is the inline mode that blocks denied resources.",["Protect","alert","logs"]),
("security","sec-015","When a Protect group talks to a Monitor group, SUSE Security evaluates the connection as Monitor, yes?","Yes. The effective mode is always the least restrictive of the two.",["least restrictive","Monitor"]),
("security","sec-051","SUSE Security's persistent configuration backup needs a ReadWriteMany volume, correct?","Yes. It needs an RWX persistent volume of 1Gi or more mounted at /var/neuvector.",["ReadWriteMany","RWX"]),
("linux","linux-018","On SUSE Linux Micro I should use transactional-update instead of plain zypper to install packages, right?","Yes. The root file system is read-only; transactional-update applies changes to a new snapshot that becomes active after a reboot.",["transactional-update","reboot"]),
("linux","linux-034","BCI-Micro has no RPM package manager, so it suits static binaries or multi-stage builds, correct?","Yes. BCI-Micro is like BCI-Minimal without RPM; it is meant for static binaries or multi-stage builds.",["multi-stage","static"]),
("linux","linux-030","On a new SUSE Linux Micro install, Cockpit won't let root log in with a password by default, yes?","Yes. Create an unprivileged user and switch to administrative access in Cockpit.",["unprivileged","administrative access"]),
("linux","linux-046","The SUSE AI Library applications need the SUSE AI entitlement, separate from SUSE Rancher Prime, right?","Yes. The SUSE AI entitlement is separate from SUSE Rancher Prime; the check is done at apps.rancher.io.",["separate","entitlement"]),
]
facts = {json.loads(l)["id"] for l in open(os.path.join(ROOT, "data", "v1", "facts.jsonl"))}
out=[]
for area, fact, q, ref, exp in rows:
    assert fact in facts and any(e.lower() in ref.lower() for e in exp), (fact, exp)
    out.append({"instruction": q, "input": "", "reference": ref, "area": area, "type": "true-premise", "premise": "true", "fact": fact, "expect_any": exp})
with open(os.path.join(ROOT, "eval", "true-premise.jsonl"),"w") as f:
    for r in out: f.write(json.dumps(r, ensure_ascii=False)+"\n")
print(len(out), "true-premise questions")
