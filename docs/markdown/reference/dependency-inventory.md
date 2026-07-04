# LME Dependency Inventory & Upgrade Plan

_Maintained in the `sweets9/LME` fork. Last reviewed: 2026-07-04._

This inventory lists every pinned dependency in the repository, its exact
location, the current version, and a considered upgrade recommendation. It
supports a "safe, small, reviewable upgrades" policy: prefer patch/minor bumps
that can be verified locally, and treat core data-plane components (Elastic,
Wazuh, Podman) as high-risk changes needing a documented test path.

Upstream CISA LME was retired on 2026-05-22; this community-maintained fork
keeps the dependencies current, so keeping this list up to date is part of
routine maintenance hygiene.

## Legend

| Risk | Meaning |
| --- | --- |
| 🟢 low | Patch/minor bump, no API break expected, verifiable locally. |
| 🟡 medium | Minor bump of a core component; needs a deploy/test pass. |
| 🔴 high | Major bump or core data-plane change; needs a documented test plan and migration notes before adoption. |

---

## 1. Container images

Pinned in [`config/containers.txt`](../../../config/containers.txt) and
[`config/containers-llm.txt`](../../../config/containers-llm.txt). These are the
data-plane and AI-plane images pulled at install time.

| Image | Current pin | Latest line (as of review) | Risk | Recommendation |
| --- | --- | --- | --- | --- |
| `docker.elastic.co/elasticsearch/elasticsearch` | `8.18.8` | 8.18.x patch / 8.19.x / 9.x | 🟡 / 🔴 | Track the **8.18.x** patch line for security fixes; keep the four Elastic images in lockstep. A 9.x jump is 🔴 — needs index-compat and Fleet/agent testing. |
| `docker.elastic.co/beats/elastic-agent` | `8.18.8` | — | 🟡 | Must match the Elasticsearch/Kibana version exactly. |
| `docker.elastic.co/kibana/kibana` | `8.18.8` | — | 🟡 | Must match the Elasticsearch version exactly. |
| `docker.elastic.co/package-registry/distribution` | `lite-8.18.8` | — | 🟡 | Must match the stack version. |
| `docker.io/wazuh/wazuh-manager` | `4.9.1` | 4.x | 🟡 | Stay on the 4.x line; a manager bump must be matched by the agent version shipped to endpoints. Test alert forwarding before adopting. |
| `docker.io/jertel/elastalert2` | `2.20.0` | 2.x | 🟢 | Minor bumps are low risk; validate existing rules still load. |
| `docker.io/pgvector/pgvector` | `pg17` | pg17 patch | 🟢 | Tag floats the Postgres 17 patch line already. Consider pinning a digest for reproducibility. |
| `ghcr.io/ggml-org/llama.cpp` | **`:server`** (rolling) | — | 🔴 (supply chain) | **Unpinned rolling tag** — non-reproducible builds and no rollback anchor. Pin to a dated/tagged release or a digest. See §4. |
| `ghcr.io/berriai/litellm` | **`:main-latest`** (rolling) | — | 🔴 (supply chain) | **Unpinned rolling tag** — same problem. Pin to a stable LiteLLM release tag or a digest. See §4. |

> Note: the Elastic stack version is also mirrored in
> [`config/example.env`](../../../config/example.env) (`STACK_VERSION=8.18.8`)
> and Wazuh in `WAZUH_VERSION=4.9.1`. Any image bump must update these in the
> same commit so offline installs and agent downloads stay consistent.

## 2. Python dependencies

| File | Package | Current | Recommendation | Risk |
| --- | --- | --- | --- | --- |
| [`lme-log-analyzer/requirements.txt`](../../../lme-log-analyzer/requirements.txt) | streamlit | **1.54.0** ✅ | Applied (was 1.40.1). | 🟢 |
| | requests | **2.33.0** ✅ | Applied (was 2.32.3). | 🟢 |
| | urllib3 | **2.7.0** ✅ | Applied (was 2.2.3). | 🟢 |
| [`lme-dashboard/requirements.txt`](../../../lme-dashboard/requirements.txt) | fastapi | `==0.115.0` | Candidate: bump to current 0.11x; verify `UploadFile`/`StreamingResponse` usage. | 🟡 |
| | uvicorn | `==0.32.0` | Candidate: bump with fastapi. | 🟡 |
| | httpx | `==0.28.1` | Candidate: current line. | 🟢 |
| | python-multipart | `>=0.0.9` | Floor allows patched ≥0.0.18 (DoS fixes). Consider raising the floor to `>=0.0.18`. | 🟢 |
| | psycopg2-binary / pgvector / pyyaml / cryptography / beautifulsoup4 / markdownify / lxml | floor-pinned | Reproducibility risk — the Dockerfile resolves "latest that satisfies" at build. Consider freezing exact versions. | 🟡 |
| [`dashboards/requirements.txt`](../../../dashboards/requirements.txt) | requests, urllib3 | unpinned | Pin exact versions for reproducible dashboard export runs. | 🟢 |
| [`scripts/sbom/requirements.txt`](../../../scripts/sbom/requirements.txt) | pyyaml | unpinned | Pin for reproducible SBOM generation. | 🟢 |
| [`scripts/upgrade/requirements.txt`](../../../scripts/upgrade/requirements.txt) | requests, urllib3 | unpinned | Pin for reproducible upgrades. | 🟢 |
| [`testing/tests/requirements.txt`](../../../testing/tests/requirements.txt) | pytest, selenium, paramiko, … | floor-pinned | Test-only; acceptable, but a lockfile would stabilise CI. | 🟢 |

## 3. Base images & Ansible collections

| Location | Dependency | Current | Notes |
| --- | --- | --- | --- |
| `docker/22.04`, `docker/24.04` | `ubuntu:22.04` / `24.04` | LTS | Fine; these are CI/test build environments. |
| `docker/d12.10` | `debian:12.10` | stable | Fine. |
| `docker/rocky9`, `docker/rhel9` | `rockylinux:9`, `ubi9:9.6` | current | Fine. |
| `lme-log-analyzer`, `lme-dashboard` | `python:3.11-slim` | 3.11 | Fine; 3.12 is a candidate but not required. |
| [`ansible/requirements.yml`](../../../ansible/requirements.yml) | community.general, ansible.posix | `>=1.0.0` | Very loose floors. Consider raising to tested minimums for predictable role behaviour. |

## 4. Priority: pin the rolling AI image tags 🔴

`ghcr.io/ggml-org/llama.cpp:server` and `ghcr.io/berriai/litellm:main-latest`
are **rolling tags**. Every rebuild can silently pull different code, which
means:

- builds are not reproducible,
- there is no version to roll back to after a regression,
- a compromised upstream tag is adopted automatically.

**Recommended change** (once a maintainer can pull and smoke-test the images on
a real Podman host):

1. Resolve the current working image to a digest, e.g.
   `podman inspect --format '{{index .RepoDigests 0}}' localhost/litellm:LME_LATEST`.
2. Replace the rolling tag in `config/containers-llm.txt` with either a stable
   release tag or the `@sha256:…` digest.
3. Record the pin and its provenance here.

This is deferred rather than applied because it cannot be verified in a
CI/dev sandbox without pulling multi-GB images and standing up the full
Podman stack; it should be done on a real deployment host where the pinned
images can be smoke-tested before adoption.

## 5. Applied in this pass

- `lme-log-analyzer/requirements.txt`: streamlit 1.40.1→1.54.0, requests
  2.32.3→2.33.0, urllib3 2.2.3→2.7.0. Verified: clean `pip install`, `pip
  check` reports no broken requirements, `python -m py_compile app_simple.py`
  passes against the new pins.
- `quadlet/lme-log-analyzer.container` + `lme-log-analyzer/app_simple.py`:
  corrected `LITELLM_MODEL` from the unserved `gemma-3-1b` to the served
  `lfm2.5-1.2b-instruct` (config correctness, not a version bump).
