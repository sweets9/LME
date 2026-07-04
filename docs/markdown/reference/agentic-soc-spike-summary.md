# Agentic SOC Modernization — Spike Summary

_Branch: `agentic-soc-platform-spike` · Fork: `sweets9/LME` · Date: 2026-07-04_

First maintenance/modernization pass on the LME fork after upstream CISA
retirement. Goal: safe, verifiable, small-commit improvements plus product
direction for an agentic SOC-in-a-box and firehose log-cost control.

## What changed

### Correctness fixes
- **Log-analyzer LLM model mismatch** (`fix(log-analyzer)`, `1b4fc17`). The
  analyzer container and app defaulted to `LITELLM_MODEL=gemma-3-1b`, a model
  not registered in `config/litellm_config.yaml`. AI analysis/chat would fail
  with "model not found". Repointed to the served `lfm2.5-1.2b-instruct`
  (matching the dashboard).

### Dependency upgrades (verified)
- **Log-analyzer Python deps** (`chore(deps)`, `8d6b4a9`), adopting the
  Dependabot-flagged versions:
  - streamlit `1.40.1 → 1.54.0`
  - requests `2.32.3 → 2.33.0`
  - urllib3 `2.2.3 → 2.7.0`

### Tooling / CI
- **`scripts/validate_llm_config.py`** (`feat(scripts)`, `0633b23`) — read-only
  validator asserting every LLM model reference resolves to a served model.
- **`.github/workflows/validate-config.yml`** (`ci`, `49a4603`) — runs the
  validator on push/PR.

### Documentation
- Corrected `LITELLM_USAGE.md` (stale model name + wrong proxy port), rewrote
  the drifted `lme-log-analyzer/README.md`, and added a `docs/markdown/reference/`
  set: fork strategy, agentic SOC roadmap, firehose/SC4S diversion guide,
  dependency inventory, and this summary. Added a "Maintained fork" note to the
  top-level README.

## Commits (oldest → newest)

| Hash | Commit |
| --- | --- |
| `1b4fc17` | fix(log-analyzer): align LITELLM_MODEL with the served model |
| `59b50f4` | docs(litellm): correct stale model name and proxy port references |
| `8d6b4a9` | chore(deps): bump log-analyzer python deps to security-patched versions |
| `4c911bd` | docs(log-analyzer): rewrite README to match the actual app |
| `da4a728` | docs: add dependency inventory and upgrade plan |
| `9e2b4d0` | docs: add fork maintenance strategy |
| `7a2855c` | docs: add agentic SOC-in-a-box design and roadmap |
| `4bd5c92` | docs: add firehose log diversion and SC4S bridge guide |
| `0633b23` | feat(scripts): add validate_llm_config.py to catch LLM config drift |
| `49a4603` | ci: run LLM config validator on push and PR |
| `ecb676f` | docs: add reference docs index and link fork direction from README |

## Verification performed

- **Dependency upgrade** — clean venv:
  - `pip install streamlit==1.54.0 requests==2.33.0 urllib3==2.7.0` → exit 0
  - `pip check` → "No broken requirements found."
  - `python -m py_compile lme-log-analyzer/app_simple.py` → OK against new pins
- **Config validator** —
  - `python3 scripts/validate_llm_config.py` on the tree → `RESULT: PASS`
  - Reintroducing the `gemma-3-1b` mismatch → `RESULT: FAIL` (exit 1),
    correctly flagged
  - PyYAML-absent regex fallback path → PASS
- **CI workflow YAML** — `yaml.safe_load` parses `validate-config.yml` OK.
- **Repo state** — `git status` clean; all commits pushed to
  `origin/agentic-soc-platform-spike`.

## Known risks / blockers

- **Rolling AI image tags not yet pinned.** `ghcr.io/ggml-org/llama.cpp:server`
  and `ghcr.io/berriai/litellm:main-latest` remain rolling. Pinning is
  **deferred** (not skipped): it cannot be safely verified in a CI/dev sandbox
  without pulling multi-GB images and standing up Podman. See
  [dependency-inventory.md](dependency-inventory.md) §4 for the exact procedure.
- **Core data-plane upgrades (Elastic 8.18.x, Wazuh 4.x) not attempted.** They
  require a live deploy/test pass; documented as candidates with risk ratings,
  not applied.
- **Dashboard Python deps left as-is.** Larger surface; upgrades deferred to a
  dedicated lane with a runtime test.
- No Podman/Ansible available locally, so end-to-end stack verification of the
  container changes (model fix, analyzer) was done by static analysis + the new
  validator rather than a live run.

## Recommended next lanes

1. **Pin the rolling AI images** on a Podman host and record digests.
2. **Elastic 8.18.x patch bump** with a range/CI deploy test.
3. **Ship the opt-in syslog router** (`lme-syslog-router.container`) from the
   firehose guide, with starter syslog-ng/Vector configs and a HEC health check.
4. **Agentic Phase 1** from the roadmap: evidence-cited alert analysis and a
   T1 "draft detection" action wired to the detection-engineering track.
5. **Freeze/lock dashboard + script Python deps** for reproducible builds.
