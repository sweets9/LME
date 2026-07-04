#!/usr/bin/env python3
"""Validate LME's local-LLM configuration for drift.

This is a fast, read-only sanity check that catches the class of
misconfiguration where a consumer (the log analyzer, the dashboard) is
pointed at an LLM model name that the LiteLLM proxy does not actually serve.
Left unchecked, that shows up only at runtime as a "model not found" error
from the proxy the first time an analyst clicks "Analyze".

Checks performed:
  1. Every `LITELLM_MODEL=<name>` set in a quadlet container file refers to a
     model registered in config/litellm_config.yaml's `model_list`.
  2. Every in-app default `LITELLM_MODEL` (os.getenv fallback) does too.
  3. The model file that llama.cpp serves (--model .../<file>.gguf) matches the
     backend model the LiteLLM entry points at (best-effort, warning only).

Exit codes:
  0  all checks passed (warnings allowed)
  1  one or more errors (drift detected)
  2  could not run (missing files / parse failure)

Usage:
  scripts/validate_llm_config.py [--repo-root PATH] [--quiet]

No third-party dependencies are required; PyYAML is used if available for a
more precise parse, otherwise a small regex parser is used.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LITELLM_CONFIG = Path("config/litellm_config.yaml")
QUADLET_DIR = Path("quadlet")
APP_FILES = [
    Path("lme-log-analyzer/app_simple.py"),
    Path("lme-dashboard/app.py"),
]


def _registered_models_pyyaml(text: str) -> set[str] | None:
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    try:
        data = yaml.safe_load(text) or {}
    except Exception:
        return None
    models = set()
    for entry in data.get("model_list", []) or []:
        name = (entry or {}).get("model_name")
        if name:
            models.add(str(name))
    return models


def _registered_models_regex(text: str) -> set[str]:
    """Fallback parser: collect `model_name:` values under model_list.

    Good enough for the flat model_list LME ships; ignores commented lines.
    """
    models = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m = re.match(r"-?\s*model_name:\s*(['\"]?)([^'\"#\s]+)\1", stripped)
        if m:
            models.add(m.group(2))
    return models


def registered_models(config_path: Path) -> set[str]:
    text = config_path.read_text(encoding="utf-8")
    via_yaml = _registered_models_pyyaml(text)
    return via_yaml if via_yaml is not None else _registered_models_regex(text)


def quadlet_model_refs(quadlet_dir: Path) -> list[tuple[Path, str]]:
    refs = []
    for path in sorted(quadlet_dir.glob("*.container")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*Environment=LITELLM_MODEL=(\S+)", line)
            if m:
                refs.append((path, m.group(1)))
    return refs


def app_default_model_refs(app_files: list[Path]) -> list[tuple[Path, str]]:
    refs = []
    for path in app_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(
            r'os\.getenv\(\s*["\']LITELLM_MODEL["\']\s*,\s*["\']([^"\']+)["\']',
            text,
        ):
            refs.append((path, m.group(1)))
    return refs


def backend_model_file(config_path: Path) -> str | None:
    """Return the backend model id LiteLLM points at, e.g. LFM2.5-...-Q4_K_M."""
    text = config_path.read_text(encoding="utf-8")
    m = re.search(r"model:\s*openai/(\S+)", text)
    return m.group(1) if m else None


def served_model_file(quadlet_dir: Path) -> str | None:
    llama = quadlet_dir / "lme-llama-cpp.container"
    if not llama.exists():
        return None
    m = re.search(r"--model\s+\S*?/([^/\s]+)\.gguf", llama.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to the LME repo root (default: current directory).",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print problems.")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    config_path = root / LITELLM_CONFIG
    if not config_path.exists():
        print(f"ERROR: {config_path} not found; run from the repo root.", file=sys.stderr)
        return 2

    models = registered_models(config_path)
    if not models:
        print(f"ERROR: no models found in {LITELLM_CONFIG} model_list.", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"Registered LiteLLM models: {', '.join(sorted(models))}")

    errors = 0
    warnings = 0

    for path, model in quadlet_model_refs(root / QUADLET_DIR):
        rel = path.relative_to(root)
        if model in models:
            if not args.quiet:
                print(f"  OK   {rel}: LITELLM_MODEL={model}")
        else:
            print(f"  FAIL {rel}: LITELLM_MODEL={model} is not registered "
                  f"(known: {', '.join(sorted(models))})")
            errors += 1

    for path, model in app_default_model_refs([root / p for p in APP_FILES]):
        rel = path.relative_to(root)
        if model in models:
            if not args.quiet:
                print(f"  OK   {rel}: default LITELLM_MODEL={model}")
        else:
            print(f"  FAIL {rel}: default LITELLM_MODEL={model} is not registered "
                  f"(known: {', '.join(sorted(models))})")
            errors += 1

    backend = backend_model_file(config_path)
    served = served_model_file(root / QUADLET_DIR)
    if backend and served and backend.lower() != served.lower():
        print(f"  WARN backend model in {LITELLM_CONFIG} ({backend}) does not match "
              f"the file llama.cpp serves ({served}.gguf).")
        warnings += 1
    elif not args.quiet and backend and served:
        print(f"  OK   backend model matches served file: {served}.gguf")

    print()
    if errors:
        print(f"RESULT: FAIL — {errors} error(s), {warnings} warning(s).")
        return 1
    print(f"RESULT: PASS — 0 errors, {warnings} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
