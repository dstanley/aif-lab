# RKE2 / K3s dataset v1 — notes

Built 2026-10-04. Pages were fetched as raw HTML with curl and converted to text locally (scratchpad `suse-dataset-v1/raw/`), so commands are copied from the page source rather than summarised. All pages showed "Last updated on Oct 1, 2026".

## Counts
- Facts: 57 (25 command, 23 knowledge, 5 troubleshooting, 4 recommendation); 42 RKE2 (`rke2-001`..`rke2-042`), 15 K3s (`k3s-001`..`k3s-015`).
- Train: 211 = 200 fact-linked (3–5 per fact) + 11 negative.
- Eval (taught): 57, one per fact.
- Generator and validator: `build_part1.py`..`build_part3.py`, `build.py` (rerun `python3 build.py` to regenerate and re-validate).

## Pages read
RKE2: `/` (intro, RKE2 vs K3s), `/install/quickstart`, `/install/configuration`, `/install/ha`, `/install/requirements`, `/install/airgap`, `/install/private_registry`, `/install/methods`, `/install/uninstall`, `/install/packaged_components`, `/datastore/backup_restore`, `/datastore/embedded`, `/upgrades/upgrade`, `/upgrades/manual`, `/upgrades/automated`, `/networking/basic_network_options`, `/networking/networking_services`, `/security/hardening_guide`, `/security/selinux`, `/reference/server_config`, `/reference/linux_agent_config`, `/reference/cli_tools`, `/reference/ingress_migration`, `/known_issues`, `/add-ons/helm`.
K3s: `/quick-start`, `/installation/configuration`, `/installation/requirements`, `/installation/airgap`, `/installation/private-registry`, `/installation/registry-mirror`, `/installation/uninstall`, `/installation/packaged-components`, `/datastore`, `/datastore/ha-embedded`, `/cli/etcd-snapshot`, `/cli/server`, `/cli/agent`, `/upgrades/manual`, `/upgrades/automated`, `/cluster-access`, `/networking/basic-network-options`.
Also checked: the live `https://get.rke2.io` script, to verify the INSTALL_RKE2_* variable names (see below).

## Naming decisions
- I used "RKE2" and "K3s" as the docs spell them. Unit names follow the docs: `rke2-server` / `rke2-agent` and `k3s` / `k3s-agent`.
- I wrote "SUSE Rancher Prime" for the manager when it is named as a product. Where the RKE2 upgrade docs say "Rancher" (managed, provisioned or imported clusters), I kept "Rancher".
- Placeholders are kept exactly as the docs write them (`<PATH-TO-SNAPSHOT>`, `vX.Y.Z+rke2rN`, `<EXISTING_K3S_ENV>`, `myserver`/`mynodetoken`), so eval checks can match them verbatim.
- The examples make no pricing or licensing claims. Comparing RKE2 and K3s, I used the docs' own wording: K3s "diverged… to optimize for edge", and RKE2 stays aligned with upstream.

## Contradictions and ambiguities avoided
1. **Default ingress.** The ingress migration guide says Traefik is the default for new clusters from RKE2 v1.36, while older pages (packaged components, the HA taint note, the CIS network-policy list) still name ingress-nginx. Fact `rke2-033` always states the version ("v1.36+ Traefik; earlier ingress-nginx"). Nothing else in the set names a default ingress.
2. **Snapshot directory.** The backup and restore pages give the default as `${data-dir}/db/snapshots`, but the server reference gives `${data-dir}/server/db/snapshots`, and the example output on the same backup page shows `/var/lib/rancher/rke2/server/db/snapshots`. I used `/var/lib/rancher/rke2/server/db/snapshots` (K3s: `/var/lib/rancher/k3s/server/db/snapshots`).
3. **S3 flag spelling.** The flag tables use `--etcd-s3-*`, but the CLI examples on the same page use `--s3 --s3-bucket …` on `etcd-snapshot`. I only taught `--etcd-s3-*`.
4. **RKE2 datastore default.** The server reference lists `datastore-endpoint` with a default of "sqlite", which conflicts with the HA guide (servers run etcd). The examples make no claim about the RKE2 datastore default. The SQLite-default fact is taught for K3s only, where the datastore page is explicit.
5. **Flannel VXLAN port on RKE2.** The requirements prose says UDP 8472, but the Flannel CNI tab says 4789. The RKE2 port facts leave out the Flannel-specific port. K3s 8472 is unambiguous and is taught.
6. **INSTALL_RKE2_EXEC.** I drafted a negative example saying this variable doesn't exist, because the docs' variable table omits it. The live install script does reference it, so I dropped that negative. Lesson: the docs' tables are not a complete list. The negatives I kept rely only on explicit lists: the etcd-snapshot subcommands, the `cni` values, the Security flag list, the kubeconfig and unit names, and the k3s/rke2 commands.
7. **Prune command.** The docs have a double space (`--snapshot-retention  <NUM…>`). I normalised it to a single space.
8. **K3s HA bootstrap.** I dropped the optional `--tls-san=<FIXED_IP>` continuation line from the docs' command and mention it in the prose instead.
9. **CIS profile names.** Version-specific profiles (`cis-1.23`, `cis-1.6`) are not taught. Only `profile: "cis"` for v1.29+ is taught, with that version stated.
10. **CriticalAddonsOnly note.** The HA page says NGINX Ingress and Metrics Server stay pending. I only mention metrics-server, to avoid the ingress-version problem.

## Known limitations
- Several RKE2 and K3s facts are near-twins (install, snapshot, restore, registries.yaml). Evals for those carry `expect_none` for the other product's path or command, to catch mix-ups.
- Not covered: Windows agents, SELinux details, external datastores, certificate rotation, secrets encryption and the embedded registry (Spegel). Candidates for v2.
