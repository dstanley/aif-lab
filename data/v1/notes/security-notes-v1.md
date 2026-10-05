# SUSE Security (NeuVector) dataset v1: notes

## Counts
- Facts: 55 (knowledge 29, command 14, recommendation 8, troubleshooting 4)
- Train: 214 (knowledge 105, command 56, recommendation 29, troubleshooting 13, negative 11)
- Eval (taught): 55, one per fact

## Pages read (fetched raw with curl, converted with pandoc; copies in scratchpad/v1-sec/)
SUSE docs: `latest` resolves to **5.6** (5.7 also exists in the version switcher; not used).
Base: https://documentation.suse.com/cloudnative/security/latest/en/
- overview, requirements, helm, kubernetes, rancher, airgap, modes, networkrules, processrules, filerules, groups,
  scanning, registry-scanning-configuration, scanners, updating-cve-database, admission, compliance, troubleshooting,
  production, updating, remove, cli, configmap, usingcrd, internal, installation, policy-overview, 5x (release notes)

open-docs.neuvector.com (Version 5.6): deploying/production, deploying/kubernetes, deploying/rancher,
deploying/airgap, policy/admission, scanning/registry, scanning/updating, troubleshooting/troubleshooting,
basics/requirements. These were read to cross-check. Every fact cites the SUSE page. `deploying/helm` returned no content.

## Naming
- "SUSE Security" is the product name. NeuVector is the project name and appears in questions and in phrasings like
  "SUSE Security (the NeuVector project)".
- Technical identifiers keep NeuVector: chart names (`neuvector`, `neuvector-crd`, `neuvector/core`), namespaces
  (`neuvector`, `cattle-neuvector-system`), CRD kinds (`NvSecurityRule`, ...), and service and pod names.

## Contradictions and version issues
- **Default process/file protection.** processrules.html says zero-drift was the default "in NeuVector 5.6.0 and older"
  and that from 5.6.1 Basic is the default for new deployments. The 5.6.1 release note says "Revert zero-drift for
  Processes to NOT be the default". But filerules.html still says zero-drift "is the default mode", groups.html says
  "'nv.' groups start with zero drift enabled by default", and the configmap sample comment says
  `New_Service_Profile_Baseline` defaults to zero-drift.
  -> Fact sec-020 gives the version-specific statement only. No other example states a default baseline.
- **Default policy (network) mode.** modes.html says groups start in Discover, and the configmap says
  `New_Service_Policy_Mode` empty = Discover. These agree, so this is stated as fact. No 5.6.1 change was found for the
  network mode default.
- **Helm repos.** The Rancher Helm guide uses `rancher-charts` (https://charts.rancher.io/). The air-gap guide uses the
  `neuvector` repo (https://neuvector.github.io/neuvector-helm/, chart `neuvector/core`). Each is used only in its own
  context.
- **Manifest deployment.** open-docs says the raw manifests repo is deprecated in favour of Helm. The 5.4.0 manifest
  `kubectl apply` URLs were therefore left out.
- **Example-version commands left out**: the air-gap `helm upgrade -i ... --set tag=5.3.2`, the Prime compliance install
  (`tag=5.4.0-b2`, line-wrapped in the docs) and `kubectl set image ... :4.2.2`. All pin old versions.
- **Pod-name-specific doc examples left out**, such as `kubectl logs neuvector-controller-pod-777fdc5668-4jkjn ...` and
  `kubectl exec ... neuvector-manager-pod-5bb76b6754-rlmnp`. Training outputs use `<placeholder>` forms in prose only.
- **Auto-Scan location.** scanning.html says Assets → Nodes/Containers → Vulnerabilities. filerules.html mentions
  "Security Risks → Vulnerabilities". The dataset uses the scanning.html location.
- **The admission page** still shows `admissionregistration.k8s.io/v1beta1` examples (outdated). These are not used.

## Composite sources
Some facts combine two pages but cite one URL:
- sec-004 Manager: overview + kubernetes
- sec-011 Discover: modes + configmap
- sec-020 process default: processrules + 5x
- sec-050 PDB: production + updating
- sec-051 persistence: production + requirements

## Negatives (11)
Each is supported by an explicit statement in the docs:
- no Discover mode for admission control (only Monitor/Protect)
- IPv6 not supported
- custom groups have no protection mode
- nodes-group network violations never blocked
- predefined files are alert-only
- no NvNetworkPolicy kind (documented kinds list)
- registry Auto Scan is OpenShift imagestream only
- CRD-set mode can't be changed in the console
- no scanner auto-scaling with the OpenShift operator
- no Deny rule with wildcard name+path
- address criteria do not accept `!=`

Helm-value negatives were avoided because the full chart values reference was not in the allowed sources.

## Validation (scratchpad/v1-sec/build.py)
- All lines parse.
- 3-5 train examples per fact, and exactly one eval per fact.
- Eval-vs-train instruction similarity: max difflib ratio 0.59, token Jaccard <= 0.5.
- Every expect_command appears verbatim in its reference and in all of that fact's train outputs.
- Every reference passes its expect_any and expect_none checks.
