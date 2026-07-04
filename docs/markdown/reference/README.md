# LME Fork Reference Docs

Reference and product-direction documentation for the maintained
`sweets9/LME` fork. These complement the upstream install/usage docs and
capture the fork's strategy, roadmaps, and maintenance inventories.

| Doc | What it covers |
| --- | --- |
| [fork-maintenance-strategy.md](fork-maintenance-strategy.md) | Why the fork exists, principles, branching, and versioning. |
| [agentic-soc-roadmap.md](agentic-soc-roadmap.md) | The local-LLM agentic SOC design, human-approval action tiers, and phased roadmap. |
| [firehose-log-diversion.md](firehose-log-diversion.md) | Using LME to cut premium-SIEM ingest cost, with SC4S/Splunk adoption bridges. |
| [dependency-inventory.md](dependency-inventory.md) | Every pinned dependency, its location, risk, and upgrade recommendation. |
| [agentic-soc-spike-summary.md](agentic-soc-spike-summary.md) | Summary of the first maintenance/modernization pass: changes, verification, risks, next lanes. |

## Related tooling

- [`scripts/validate_llm_config.py`](../../../scripts/validate_llm_config.py)
  — validates that LLM model references match the served model; run in CI via
  `.github/workflows/validate-config.yml`.
- [`LITELLM_USAGE.md`](../../../LITELLM_USAGE.md) — using the local LiteLLM
  proxy.
