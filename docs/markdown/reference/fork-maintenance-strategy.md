# Fork Maintenance Strategy

_`sweets9/LME` — a maintained continuation of CISA Logging Made Easy._

## Why this fork exists

CISA retired Logging Made Easy (LME) on **2026-05-22**; upstream
`cisagov/LME` is archived and no longer maintained or supported. LME remains
a genuinely useful, low-cost logging and detection platform for small and
mid-sized teams, and a large amount of engineering value (Podman quadlet
stack, Ansible automation, Elastic + Wazuh + ElastAlert integration, and a
local-LLM agentic layer) is worth carrying forward.

This fork's goal is to keep LME **alive, secure, and enterprise-credible**,
and to lean into two differentiators the upstream project had only started:

1. **Agentic SOC-in-a-box** — a local, privacy-preserving LLM layer for
   alert triage, detection engineering, and analyst assistance
   (see [agentic-soc-roadmap.md](agentic-soc-roadmap.md)).
2. **Firehose log diversion / cost control** — using LME as a cheap,
   searchable landing zone for high-volume logs, forwarding only high-value
   events onward to expensive SIEMs like Splunk or Sentinel
   (see [firehose-log-diversion.md](firehose-log-diversion.md)).

## Principles

- **Preserve upstream compatibility.** Keep the install/upgrade paths,
  quadlet layout, and Ansible role interfaces stable so existing operators
  can adopt fork releases without relearning the product. Fork-specific
  direction lives in docs and additive components, not in rewrites.
- **Separate documentation from risky change.** Product-direction and doc
  commits are kept distinct from dependency/version bumps so each can be
  reviewed and reverted independently.
- **Small, coherent commits.** Every change is scoped to one concern with a
  conventional-commit message, so the history reads as steady maintenance,
  not big-bang drops.
- **Safe upgrades first.** Prefer patch/minor bumps that can be verified
  locally. Core data-plane components (Elastic, Wazuh, Podman) are not
  major-upgraded without a written compatibility risk and a test path — see
  [dependency-inventory.md](dependency-inventory.md).
- **Evidence over assertion.** Applied upgrades ship with verification
  output (install/compile/lint results) or a documented blocker.

## Branching

This fork keeps upstream's Git-flow conventions (`main` for releases,
`develop` for integration, `feature-*` / `hotfix-*` branches) described in
[`RELEASES.md`](../../../RELEASES.md). Product-direction spikes use a
descriptive branch name (e.g. `agentic-soc-platform-spike`) and merge through
`develop`.

`origin` is `sweets9/LME`; `upstream` (`cisagov/LME`) is retained read-only
for reference and cherry-picking any late upstream fixes.

## Versioning

Continue SEMVER as documented in `RELEASES.md`. Because upstream stopped at
`2.3.0`, the fork's first independent release should make its lineage explicit
in `RELEASES.md` and `version.txt` (e.g. a fork-tagged pre-release) rather
than silently reusing an upstream number.

## What "done" looks like for a maintenance lane

- A branch of small, conventional commits.
- Clean `git status`.
- A written summary of what changed, upgrades applied, tests run, and known
  risks.
- Every dependency change backed by verification output or a recorded
  blocker.
