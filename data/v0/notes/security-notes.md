# Security area (SUSE Security / NeuVector): source notes

## Pages read
Read in full as text (curl + HTML strip), SUSE docs v5.6 ("latest"), base https://documentation.suse.com/cloudnative/security/latest/en/:
overview, modes, policy-overview, networkrules, processrules, filerules, groups, admission, assessment, sigstore,
responserules, dlp, threats, detectbandwidthddos, namespaceboundary, usingcrd, federated, multicluster, scanning,
vulnerabilities, registry-scanning-configuration, build-image-scanning, scanners, updating-cve-database, compliance,
customcompliance, helm, rancher, production, kubernetes, configmap, requirements, users, restore, updating,
troubleshooting, cli (first part), testing, local, navigation (fetched, only skimmed).
Also https://documentation.suse.com/cloudnative/security/5.4/en/airgap.html and the landing page
https://documentation.suse.com/cloudnative/security/.
Read through WebFetch summaries: https://open-docs.neuvector.com/ (home), /deploying/kubernetes, /deploying/production,
/basics/installation, /deploying/publick8s.

## Naming decisions
- Product name: **SUSE Security**, with NeuVector as the project name. The landing page title/heading is
  "SUSE Security (NeuVector)" (https://documentation.suse.com/cloudnative/security/). The page text uses
  "SUSE® Security" throughout (for example overview.html). I dropped the ® in the dataset.
- "NeuVector" kept for technical identifiers the docs still use: the `neuvector` namespace/images, `neuvector.com/v1` CRDs,
  the `NeuvectorNamespaceBoundary` label, the `neuvector` / `neuvector-crd` Helm charts, `permission.neuvector.com`
  (helm.html, usingcrd.html, namespaceboundary.html, rancher.html). The open-docs site uses "NeuVector" only.
- Other SUSE products are named as helm.html and rancher.html name them: "SUSE Rancher", "Rancher Prime",
  "Rancher Extensions", "Apps & Marketplace", "RKE2", "K3s", plus "SUSE Linux" from requirements.html.

## Uncertain or deliberately left out
- **Default process/file protection mode is inconsistent in the docs**: processrules.html says zero-drift was the default
  up to 5.6.0 and Basic is the default for new deployments from 5.6.1. filerules.html still says zero-drift is the
  default, and groups.html says `nv.` groups start with zero-drift. The training data states the 5.6.1 change once
  (architecture record) and otherwise avoids saying which mode is the default.
- Helm `--set` flags such as containerd/k3s runtime toggles, controller.replicas and manager service type values are
  left out. None of the pages I read show them verbatim. Only the rancher-charts commands from helm.html and the
  neuvector-helm repo commands from airgap (5.4) are used.
- The compliance.html "Prime compliance" Helm example is garbled across lines and uses internal image repos
  (nvlab/nvpublic), so it is not used.
- The production.html PDB sample uses `policy/v1beta1`. It is reproduced as documented with no comment added.
- The admission webhook ValidatingWebhookConfiguration example in the docs is from 2019 (v1beta1, `failurePolicy: Ignore`),
  so failurePolicy is not stated as a current default.
- Licensing and "open source" wording (the landing page calls it "fully open source"; overview says "5.x (Open Source)")
  is left out, per the positioning rule.
- Cosign: the docs say only cosign v2 signatures are verified. This is used as stated.
- Port numbers are used only where the docs show them: 8443 console, 10443 REST/fed-managed, 11443 fed-master,
  443→20443 admission webhook service.
