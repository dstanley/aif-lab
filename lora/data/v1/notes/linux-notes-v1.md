# linux v1 dataset notes

Built 2026-10-04. 55 facts (30 command, 15 knowledge, 6 troubleshooting, 4 recommendation); 220 fact-linked train examples (4 per fact) + 11 negatives = 231 train; 55 eval questions (1 per fact).
Raw pages and the text extracts are in `scratchpad/v1-linux/`. The generator is `build.py` with `facts_a.py` and `facts_b.py`, and it runs the validation.

## Pages read (fetched raw with curl, converted to text locally)

| Page | Product/version | Used for |
|---|---|---|
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-register-sle.html | SLES 15 SP7 Deployment Guide, ch. 10 | SUSEConnect register/--url/-d/-p, extensions + regcode, no package install/removal, Basesystem warning, keep-alive timer |
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/article-modules.html | SLES 15 SP7 Modules and Extensions Quick Start | `--list-extensions` spelling, NVIDIA Compute Module |
| https://documentation.suse.com/sles/15-SP7/html/SLES-all/cha-sw-cl.html | SLES 15 SP7 Admin Guide, ch. 9 (Zypper) | patch, list-patches, --cve, patch vs update, ps, refresh -fdb, orphaned, registration needed for updates |
| https://documentation.suse.com/sle-micro/6.1/html/Micro-transactional-updates/transactional-updates.html | SUSE Linux Micro 6.1 | read-only root, pkg install, patch, --continue, shell, rollback, timer, /var, register options |
| https://documentation.suse.com/sle-micro/6.1/html/Micro-deployment-raw-images/index.html | SUSE Linux Micro 6.1 | `transactional-update register -r ... -e ...` |
| https://documentation.suse.com/sle-micro/6.1/html/Micro-cockpit/index.html | SUSE Linux Micro 6.1 | Cockpit install, socket, port 9090, firewalld, root login, 2FA |
| https://documentation.suse.com/sles/16.0/html/SLES-cockpit/ | SLES 16.0 | Cockpit install on SLES 16 (`zypper in -t pattern cockpit`) |
| https://documentation.suse.com/container/all/html/Container-guide/index.html | Container Guide (pub. 01 Oct 2026; SLES 15 SP7 / SUSE Linux 16 BCIs) | BCI types, sizes, tags/:latest migration, supportlevel label, dev stacks, LTSS login, EULA/SLE_BCI, Notary deprecation |
| https://registry.suse.com/ | SUSE Registry landing page | naming only (SUSE Linux BCI, redistributable) |
| https://docs.apps.rancher.io/get-started/authentication | SUSE Application Collection | user vs service accounts, docker/podman/helm/kubectl logins |
| https://docs.apps.rancher.io/get-started/deploy-helm-chart | SUSE Application Collection | helm install, global.imagePullSecrets, global.imageRegistry, secret namespace |
| https://docs.apps.rancher.io/get-started/first-steps | SUSE Application Collection | SCC account, access tokens |
| https://documentation.suse.com/suse-ai/1.0/html/AI-deployment/ai-deployment-kube-installing.html | SUSE AI 1.0 | recommended OS, NVIDIA driver on SLES/Micro, RKE2 install |
| https://documentation.suse.com/suse-ai/1.0/html/AI-deployment/suse-ai-deploy-prepare.html | SUSE AI 1.0 | GPU Operator checks, node labels, nvidia.com/gpu |
| https://documentation.suse.com/suse-ai/1.0/html/AI-deployment/ai-library-installing.html | SUSE AI 1.0 | entitlement, secrets, components, cert-manager, Ollama, vLLM limits |

## Naming decisions
- "SUSE Linux Micro" (6.1), never "SLE Micro". The SUSE AI guide still says "SUSE Linux Enterprise Micro" in its driver section; the dataset doesn't use that name.
- "SUSE Linux BCI" / "SUSE Linux BCI-Base" etc., with image names `bci-base`, `bci-minimal`, `bci-micro`, `bci-busybox`, `bci-init`. BCI-Nano exists in the current guide but has no fact of its own; it only comes up in passing.
- "SUSE Application Collection" and "Distribution Platform" (dp.apps.rancher.io); "SUSE Registry" (registry.suse.com).
- "SUSE Rancher Prime: RKE2" as the docs write it.
- SUSE AI only. The docs I read never mention SUSE AI Factory, so it does not appear anywhere in the dataset.
- SUSEConnect facts are scoped to SLES 15 SP7, the version whose pages I read. I did not read SLES 16 registration docs, so no SLES 16 SUSEConnect claims are made.

## Contradictions and choices
- **`--list-extensions` spelling:** the SLES 15 SP7 Deployment Guide (cha-register-sle) prints `SUSEConnect -list-extensions` with a single dash. The Modules and Extensions Quick Start uses `SUSEConnect --list-extensions`, and the Micro 6.1 `transactional-update register` option list also documents `--list-extensions`. I used the double-dash form everywhere. I did not fetch the man page itself (`man 8 SUSEConnect`).
- **NVIDIA Compute Module:** the Quick Start shows a lowercase `suseconnect -p ... --gpg-auto-import-keys` in one place and `SUSEConnect -p sle-module-NVIDIA-compute/15/x86_64` in the listing. I used the listing form as the canonical command and only mention the `--gpg-auto-import-keys` option.
- **SLES 16 Cockpit page typos:** the firewall line contains an en-dash (`–-reload`) and `sudo sudo`. I left those commands out and used the SUSE Linux Micro 6.1 firewall commands (`firewall-cmd --permanent --zone=public --add-service=cockpit`, `firewall-cmd --reload`).
- **SUSE AI NVIDIA driver package names differ:** SLES uses `nv-prefer-signed-open-driver` and Micro uses `nvidia-open-driver-G06-signed-cuda-kmp-default`. The SLES aarch64 snippet also has a stray "transactional update #" prompt. To avoid teaching wrong package names, the facts describe the flow (transactional-update shell, then zypper, then exit, reboot, nvidia-smi) without package names.
- **SUSE AI OS versions:** the SUSE AI guide recommends SLES 15 SP6, while the BCI and admin facts use 15 SP7. Both are kept as documented, each in its own context.
- **Placeholders kept verbatim:** REGISTRATION_CODE, EMAIL_ADDRESS, snapshot_number, package_name, <GPU_NODE_NAME>, <SUSE_AI_NAMESPACE> and so on.
- **Commands built from documented parts:** `transactional-update patch` (subcommand documented, no literal example; "as root" stated). `SUSEConnect -p sle-module-containers/15.7/x86_64` appears in the docs without sudo, so it is used without sudo.

## Negatives (11)
Each one is backed by an explicit statement in the docs:
- no direct zypper on Micro
- no no-reboot transactional-update option
- SUSEConnect doesn't install packages
- zypper patch skips third-party repos without --with-update
- Notary/DCT deprecated in favour of cosign/GPG
- no zypper in bci-micro
- no bash in bci-busybox
- SUSE AI entitlement is separate from Rancher Prime
- SUSE AI vLLM lacks Ray/LoraController
- Cockpit root login disabled on new Micro installs
- AppCo Distribution Platform uses access tokens, not the SCC password

## Validation
Checks performed:
- all lines parse
- every fact has 4 train examples and exactly 1 eval question
- every command fact's command appears verbatim in all its train outputs and in its eval reference
- every reference passes its own expect_any and expect_none checks
- no eval instruction duplicates a training instruction; the highest similarity between an eval and any train instruction is 0.56 (difflib)
- all outputs are 6 sentences or fewer

## Concerns
- Many docs pages carry publication dates of 2026 and contain material newer than my training (for example BCI-Nano, the :latest migration, the Notary deprecation). Facts follow the fetched text.
- Command-only answers are a single line by design (shorter than the 2-sentence floor).
- All 4 examples per fact were written in one pass, so phrasing variety is moderate. A paraphrase pass for v1.1 would help.
