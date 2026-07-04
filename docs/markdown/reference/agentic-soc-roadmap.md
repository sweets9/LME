# Agentic SOC-in-a-Box: Design & Roadmap

_`sweets9/LME` fork. Status: design doc / roadmap. Last updated: 2026-07-04._

LME already ships a local, self-hosted AI layer. This document describes
**what exists today**, the **design principles** that must govern an agentic
SOC (especially human-approval boundaries), and a **phased roadmap** for
turning today's assistive features into a trustworthy analyst co-pilot.

The north star: give a small team the triage leverage of a much larger SOC,
**without sending their logs to a third-party AI service** and **without
letting an LLM take unsupervised action** on production security data.

---

## 1. What exists today

All AI runs locally, on the private `lme` Podman network, behind TLS.

### Components

| Component | Quadlet | Role |
| --- | --- | --- |
| llama.cpp server | `lme-llama-cpp.container` | Serves the local chat model (`LFM2.5-1.2B-Instruct`, GGUF) over an OpenAI-compatible API. |
| Embeddings server | `lme-embeddings.container` | Serves `nomic-embed-text-v1.5` for RAG vector search. |
| LiteLLM proxy | `lme-litellm.container` | OpenAI-compatible gateway (auth, TLS, model routing) in front of llama.cpp; can also fan out to cloud models if a key is configured. |
| pgvector | `lme-pgvector.container` | Postgres + `pgvector` store for document/log embeddings. |
| Log Analyzer | `lme-log-analyzer.container` | Streamlit UI: security-alert triage + per-alert AI analysis + chat. |
| Security Dashboard | `lme-dashboard.container` | FastAPI SPA: the primary agentic surface (below). |

### Dashboard API surface (`lme-dashboard/app.py`)

The dashboard is already a substantial agentic backend:

- **Multi-source alert aggregation** — `/api/alerts/kibana`, `/api/alerts/wazuh`,
  `/api/alerts/sysmon`, `/api/alerts/defender`, plus `/api/alerts/hosts`.
- **Vulnerability context** — `/api/vulnerabilities` and per-agent detail.
- **AI triage** — `/api/analyze` (single-alert analysis), `/api/chat` and
  `/api/chat/stream` (assistant).
- **RAG over ingested docs** — `/api/chat/rag` and `/api/chat/rag/stream`,
  backed by `_embed_query` → pgvector `_retrieve_context` →
  `_build_rag_system_prompt`, with `/api/docs/ingest` and `/api/docs/status`.
- **Model management** — `/api/models` (list/add/delete), `/api/models/active`,
  and local GGUF lifecycle: `/api/local-models` list/switch/delete,
  HuggingFace GGUF search + download with progress (`/api/local-models/*`).
- **CISA KEV enrichment** — `/api/kev/pull`, `/api/kev/status`,
  `/api/kev/history` (see `scripts/kev_sync.py`).

This is a strong base: local inference, retrieval augmentation, threat-intel
enrichment, and multi-source detection data are all already wired together.

### Gaps observed

- **Assistive, not agentic.** The LLM summarises and answers; it does not yet
  take or propose actions (enrich, tag, escalate, draft a detection) through a
  governed workflow.
- **No approval/audit boundary.** There is no explicit human-in-the-loop gate
  or immutable audit log for AI-influenced actions — a prerequisite before any
  action-taking is added.
- **Config drift is unguarded.** The `LITELLM_MODEL` mismatch fixed in this
  pass (analyzer pointed at an unserved model) shows the value of a config
  validator — see `scripts/validate_llm_config.py`.
- **Small default model.** A 1.2B model is fine for summarisation but limited
  for multi-step reasoning; the model-management UI already lets operators
  swap in a larger local model or a cloud model per workload.

---

## 2. Design principles (non-negotiable)

1. **Local-first, private by default.** No log content leaves the deployment
   unless an operator explicitly configures a cloud model. The pitch is
   "AI triage without a data-egress problem."
2. **Human approval boundary.** The LLM may *read* and *propose*; a human
   *approves* any change to production state (rules, alert status,
   suppression, response actions). Actions are tiered — see §3.
3. **Everything auditable.** Every AI suggestion and every approved action is
   logged with prompt, model, model version, inputs referenced, the human who
   approved it, and the outcome. The audit log is append-only.
4. **Grounded, not hallucinated.** Analyst-facing answers cite their evidence
   (the alert doc, the KEV entry, the retrieved runbook chunk). RAG responses
   already carry source URLs; extend this to alert analysis.
5. **Cost/latency aware.** Route cheap/high-volume tasks (summarise, classify)
   to the local model; reserve larger/cloud models for explicit deep-dive
   requests. LiteLLM already makes this a config change.
6. **Fail safe.** If the model is unavailable, the SOC UI still shows raw
   alerts and context — AI is an accelerant, never a dependency for seeing
   your data.

## 3. Action tiers & human-in-the-loop

Define a capability ladder; the fork should climb it deliberately.

| Tier | Capability | Approval |
| --- | --- | --- |
| **T0 — Read/Explain** | Summarise alerts, answer questions, retrieve runbooks, enrich with KEV/threat intel. | None (read-only). **This is where LME is today.** |
| **T1 — Propose (draft)** | Draft a triage verdict, a Sigma/ES|QL detection, a suppression rule, an incident note. Output is a *draft* the analyst edits. | Analyst reviews before anything is saved. |
| **T2 — Apply-on-approve** | Set alert status, add tags/labels, open a case, write an approved detection to the rules store. | Explicit per-action human approval; full audit entry. |
| **T3 — Supervised automation** | Auto-run T0/T1 on new alerts and queue proposals; auto-apply only pre-approved, reversible, low-blast-radius actions (e.g. tagging) under policy. | Policy-scoped auto-approval + audit; human can revoke. |
| **T4 — Response actions** | Isolate host, disable account, block IP via Fleet/Wazuh active response. | Two-person / out-of-band approval; never LLM-initiated without it. Likely out of scope for the fork's core. |

The roadmap below only commits the fork through **T2** as a governed feature,
with T3 behind an explicit opt-in policy and T4 documented as intentionally
gated.

## 4. Roadmap

### Phase 0 — Harden the base (in progress)

- [x] Fix the analyzer model mismatch so AI triage actually works.
- [x] Sync LiteLLM docs/config (model name, proxy port).
- [x] `scripts/validate_llm_config.py` to catch model/config drift in CI.
- [ ] Pin the rolling AI image tags (llama.cpp, litellm) — see
      [dependency-inventory.md](dependency-inventory.md) §4.
- [ ] Health surface: fold the AI containers into a single
      `/api/health`-style readiness check (dashboard already has `/api/health`;
      extend to report llama.cpp / embeddings / pgvector / litellm status).

### Phase 1 — Grounded T0/T1 triage

- Alert analysis (`/api/analyze`) cites the exact fields and any KEV/RAG
  evidence it used, mirroring the RAG endpoints' source attribution.
- Add a "draft detection" T1 action: from a cluster of alerts, propose a
  Sigma rule (the repo already has `scripts/sigma/convert_sigma_to_kibana.sh`
  and a detection-engineering track to plug into).
- Add a "draft triage note" T1 action producing an editable analyst summary.

### Phase 2 — Approval boundary + audit

- Introduce an append-only AI action log (new pgvector/Postgres table or a
  dedicated index) capturing prompt, model+version, evidence, proposed action,
  approver, and outcome.
- Add T2 "apply-on-approve" for low-risk actions: set alert status, add tags,
  save an analyst-approved detection.
- Surface the audit trail in the dashboard.

### Phase 3 — Detection-engineering co-pilot

- Wire the AI layer into the `detection-engineering/` track: given telemetry
  from a Ludus/Caldera emulation run, propose and refine detections, then
  validate them against replayed events.
- Close the loop: emulate → detect gap → AI drafts rule → analyst approves →
  rule deployed → re-emulate to confirm.

### Phase 4 — Supervised automation (opt-in)

- Policy engine for T3: which alert types get auto-triaged, which actions are
  pre-approved, blast-radius limits, and a global kill switch.
- Everything reversible and audited; off by default.

## 5. Success measures

- **Time-to-triage** for a new alert (raw → analyst decision) drops.
- **% of alerts with an evidence-cited AI first pass** rises.
- **Zero** AI-initiated production changes without a recorded human approval.
- **Reproducible AI plane**: pinned images, validated config, health-gated.

## 6. Related

- [firehose-log-diversion.md](firehose-log-diversion.md) — the cost-control
  ingestion story the SOC sits on top of.
- [dependency-inventory.md](dependency-inventory.md) — AI image pinning.
- [`LITELLM_USAGE.md`](../../../LITELLM_USAGE.md) — using the local proxy.
- `lme-dashboard/app.py`, `lme-log-analyzer/app_simple.py` — the code.
