# RKE2 / K3s dataset notes

Generated 2026-10-04. Train: 114 records. Eval: 18 records. Generator script: `../gen_rke2_k3s.py`.

## Pages read (47 fetches, 46 distinct pages)

RKE2 (docs.rke2.io): `/`, `/install/quickstart`, `/install/configuration`, `/install/ha`, `/install/requirements`, `/install/methods`, `/install/private_registry`, `/install/registry_mirror`, `/install/airgap`, `/install/uninstall`, `/install/server_roles`, `/install/packaged_components`, `/datastore/backup_restore` (read twice), `/networking/basic_network_options`, `/networking/networking_services`, `/security/hardening_guide`, `/security/token`, `/security/secrets_encryption`, `/security/selinux`, `/security/fips_support`, `/security/certificates`, `/upgrades/manual`, `/upgrades/automated`, `/architecture`, `/cluster_access`, `/known_issues`, `/add-ons/gpu_operators`, `/reference/ingress_migration`.

K3s (docs.k3s.io): `/`, `/quick-start`, `/installation/configuration`, `/installation/requirements`, `/installation/private-registry`, `/installation/registry-mirror`, `/installation/airgap`, `/installation/packaged-components`, `/installation/uninstall`, `/datastore`, `/datastore/ha-embedded`, `/cli/etcd-snapshot` (read twice), `/cli/token`, `/networking/basic-network-options`, `/networking/networking-services`, `/architecture`, `/cluster-access`, `/upgrades/automated`.

SUSE: https://documentation.suse.com/cloudnative/rke2/latest/en/introduction.html, https://documentation.suse.com/cloudnative/k3s/latest/en/introduction.html

Failed or empty: `docs.rke2.io/upgrades/manual_upgrade` and `/upgrades/automated_upgrade` (old URLs; the sitemap gave the current ones). `docs.k3s.io/related-projects` returned 503 once and then loaded, but it doesn't compare K3s with RKE2.

## Naming decisions

- "RKE2" and "K3s" as written on docs.rke2.io and docs.k3s.io.
- SUSE product names: "SUSE Rancher Prime: RKE2" (https://documentation.suse.com/cloudnative/rke2/latest/en/introduction.html) and "SUSE Rancher Prime: K3s" (https://documentation.suse.com/cloudnative/k3s/latest/en/introduction.html). I used these only in the two naming definitions and kept the docs' short names everywhere else.
- "RKE Government" is mentioned as a former or alternate name (https://docs.rke2.io/).
- The management product is just "Rancher", because that is how the RKE2 pages put it ("integrated into Rancher", "use the Rancher UI"). I found no page in this area that says "SUSE Rancher Prime" for the manager, so I didn't use that name.
- "ServiceLB (Klipper)" (https://docs.k3s.io/networking/networking-services). "Spegel" for the embedded registry mirror (https://docs.rke2.io/install/registry_mirror, https://docs.k3s.io/).
- No Longhorn, Harvester or NeuVector content appears, so no renamed products are referenced.

## Uncertain or deliberately left out

- **RKE2 default ingress:** `/reference/ingress_migration` and `/networking/networking_services` say Traefik is the default from v1.36, and ingress-nginx reaches end of life in March 2026. The FIPS page still calls NGINX the "default ingress provider", which looks out of date, so I didn't train that claim. The HA page's line about "NGINX Ingress and Metrics Server" not deploying under the CriticalAddonsOnly taint is rewritten as "ingress and Metrics Server add-ons".
- **GPU operator:** `CONTAINERD_CONFIG` path left out because the fetch didn't give it. Only `CONTAINERD_SOCKET` is used.
- **Air-gap file list:** the exact artifact list (tarball name, checksum file names) beyond `rke2-images*.tar.zst` and `install.sh` is left out.
- **`INSTALL_RKE2_TAR_PREFIX`:** seen only in the quickstart cleanup-path note. Not trained as a standalone fact.
- **Secrets encryption:** whether it's on by default isn't stated on the page, so it's left out.
- **WebFetch summaries:** pages were read through WebFetch's summarizer, which paraphrases. Commands came through as quoted code, but a spot-check of the commands against the live pages before training would be prudent.
- **Version-specific facts** that will age: Traefik default from v1.36; GPU operator v25.3.x vs v25.10.x behaviour; certificate auto-renewal at 120 days (it used to be 90).
