# LME Fork Reference Docs

Public reference documentation for the community-maintained `sweets9/LME`
fork. These complement the upstream install/usage docs with maintenance
information for the open-source project.

| Doc | What it covers |
| --- | --- |
| [dependency-inventory.md](dependency-inventory.md) | Every pinned dependency, its location, risk rating, and upgrade recommendation. |

## Related tooling

- [`scripts/validate_llm_config.py`](../../../scripts/validate_llm_config.py)
  — validates that LLM model references match the served model; run in CI via
  `.github/workflows/validate-config.yml`.
- [`LITELLM_USAGE.md`](../../../LITELLM_USAGE.md) — using the local LiteLLM
  proxy.
