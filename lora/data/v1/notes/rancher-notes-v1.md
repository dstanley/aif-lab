# Rancher area — dataset v1 notes

Built 2026-10-04. Generator: `build_facts.py` (content) + `build.py` (emit JSONL) + `validate.py` (checks). Raw page text saved under `pages/` (community docs) and `pages/suse/` (SUSE docs).

## Counts
- Facts: 58 (27 command, 25 knowledge, 4 recommendation, 2 troubleshooting). 7 drafted facts were dropped to stay near the ~50 target.
- Train: 206 = 195 fact-tied (3–5 per fact) + 11 negative.
- Eval: 58 (one per fact).

## Pages read (fetched raw with curl + BeautifulSoup; code blocks preserved)
Primary citations are all SUSE docs, `https://documentation.suse.com/cloudnative/rancher-manager/latest/en/`:
- installation-and-upgrade/install-rancher.html, upgrades.html, rollbacks.html
- installation-and-upgrade/resources/bootstrap-password.html
- installation-and-upgrade/troubleshooting/rancher-ha.html
- installation-and-upgrade/references/helm-chart-options.html
- rancher-admin/back-up-restore-and-disaster-recovery/{back-up-restore-and-disaster-recovery, back-up, restore, migrate-to-a-new-cluster}.html
- rancher-admin/back-up-restore-and-disaster-recovery/configuration/{backup, restore, storage}.html
- cluster-deployment/register-existing-clusters.html, register-existing-clusters-troubleshooting.html, about-rancher-agents.html
- integrations/fleet/{overview, fleet, architecture}.html; rancher-admin/experimental-features/continuous-delivery.html
- rancher-admin/cli/rancher-cli.html, cli/kubectl.html; rancher-admin/users/settings/api-keys.html
- rancher-admin/users/authn-and-authz/manage-role-based-access-control-rbac/{global-permissions, cluster-and-project-roles}.html
- cluster-admin/manage-clusters/projects-and-namespaces.html, access-clusters/use-kubectl-and-kubeconfig.html
- cluster-admin/helm-charts-in-rancher/helm-charts-in-rancher.html (+ oci-repositories.html read only)
- observability/monitoring-and-dashboards/enable-monitoring.html, observability/logging/logging.html
- faq/technical-items.html, faq/rancher-is-no-longer-needed.html
- Also read and compared with the community equivalents on ranchermanager.docs.rancher.com (back-up-rancher, restore-rancher, migrate-rancher-to-new-cluster, install-upgrade-on-a-kubernetes-cluster, upgrades, rollbacks, registered-clusters, rancher-ha, etc.).

## Naming decisions
- Product: "SUSE Rancher Prime", or "Rancher" for the server/UI, as the SUSE pages do. Fleet: "Fleet (SUSE Rancher Prime: Continuous Delivery)"; the UI menu is "Continuous Delivery".
- Backup tooling: "rancher-backup operator", with the UI app name "Rancher Backups". CRDs use their exact names (`backups.resources.cattle.io` etc.).
- "Register" and "import" are used together. The docs say registration replaced import, but the UI button is still "Import Existing".
- No pricing or licensing language. The word "free" is absent; it was checked by the validator. The install page's "Let's Encrypt is a free service" line was deliberately not reused.

## Contradictions / choices made
- **Helm repo**: the community docs use `rancher-latest`/`rancher-stable` (`releases.rancher.com/server-charts/...`). The SUSE docs use `rancher-prime` with a URL that is only in the Prime-only (SCC-gated) docs. All commands use `rancher-prime/rancher` and the placeholder `<helm-chart-repo-url>`. No URL was invented, and one eval `expect_none` guards against a guessed `releases.rancher.com/server-charts/prime`.
- **Rancher Prime v2.13.1 special case**: the FAQ gives alternative reset-password/ensure-default-admin commands that use `app=rancher-prime` / `-c rancher-prime`, and the upgrade page has an Ingress conflict note. These were left out to keep each fact single; they are worth a separate fact if v2.13.1 users matter.
- **Monitoring**: the latest SUSE page marks `rancher-monitoring` as deprecated in favour of `rancher-monitoring-dashboards`, but the install steps on the same page are still for the legacy app. Both are stated as facts: the Cluster Tools install and requirements, plus the deprecation.
- **Restore log commands differ between pages**: the restore page uses `-l app.kubernetes.io/name=rancher-backup -f`, and the migration page uses `--tail 100 -f -l app.kubernetes.io/instance=rancher-backup`. The restore-page command is the canonical one. The migration variant appears once, as a secondary mention.
- **Multi-line commands**: commands written with `\` continuations in the docs (helm install/upgrade, kubectl create secret) are collapsed to one line, with identical tokens.
- **Rollback page wording**: it says both that "changing versions using kubectl or Helm is not supported" and "rolled back using the Helm CLI" (`helm rollback`). This is read as: Helm rollback is step 2 after a backup restore, never on its own. Training data is phrased that way.
- **Global permissions**: the page says "four default global permissions" but lists three (Administrator, Standard User, User-Base). The data uses the three named roles and does not repeat "four".

## Negatives (11)
Each one gives the documented mechanism and cites a source. Non-existence is stated strongly only where the docs explicitly support it: the CLI cannot install apps or feature charts, Helm/kubectl version changes are unsupported for rollback, the operator is local-cluster only, nested S3 folders are unsupported, Fleet cannot be fully disabled, and there are only two official ResourceSets. For invented commands and flags (`rancher cluster backup --now`, `kubectl rancher import`, `backup.enabled`, `fleet.disabled`, `rancher reset-password`), the wording is "not a documented command/option", because the docs list commands and options rather than ruling out everything else.

## Validation (validate.py)
Every line parses. Each fact has 3–5 train examples and exactly 1 eval. Each command appears verbatim in the fact text, in every train output for its fact, and in the eval reference. expect_any and expect_none pass on each reference. Eval and train instructions were compared pairwise: max difflib ratio 0.56 (limit 0.6) and token Jaccard below 0.45. Train outputs are 2–6 sentences.
