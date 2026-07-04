# LME Log Analyzer

A lightweight Streamlit web interface for triaging Elasticsearch security
alerts and analyzing them with LME's local LLM.

## Features

- 🔍 **Alert triage** — lists the 50 most recent detection alerts from the
  `.alerts-security.alerts-*` indices, newest first, with severity colour
  coding, host/user/IP context, and the triggering command line.
- 🤖 **Per-alert AI analysis** — a "🤖 Analyze" button on each alert sends the
  raw alert document to the LLM (via the LiteLLM proxy) and returns a short
  "what happened / risk / next step" summary.
- 💬 **AI assistant chat** — a sidebar chat backed by the same local model for
  free-form questions.
- 📄 **Full JSON view** — every alert is expandable to its raw `_source`.

The single application file is `app_simple.py`.

## Quick Start

### Local development

```bash
cd lme-log-analyzer

# Install dependencies
pip install -r requirements.txt

# Point at your Elasticsearch + LiteLLM endpoints and provide the password
export ELASTICSEARCH_URL="https://localhost:9200"
export ELASTICSEARCH_PASSWORD="your-elastic-password"
export LITELLM_URL="https://localhost:4000"

# Run the app
streamlit run app_simple.py
```

Access at: http://localhost:8501

### Docker

```bash
# Build
docker build -t lme-log-analyzer .

# Run
docker run -p 8501:8501 \
  -e ELASTICSEARCH_URL="https://your-es-host:9200" \
  -e ELASTICSEARCH_PASSWORD="your-elastic-password" \
  -e LITELLM_URL="https://your-litellm-host:4000" \
  lme-log-analyzer
```

### LME integration

Within an LME deployment the analyzer is built and started automatically by
the `podman` Ansible role (`roles/podman/tasks/llama_cpp_setup.yml`) as the
`lme-log-analyzer` Podman container defined in
[`quadlet/lme-log-analyzer.container`](../quadlet/lme-log-analyzer.container).
It runs over HTTPS with the internal LME certificate and reaches
Elasticsearch and the LiteLLM proxy over the private `lme` network.

Access at: https://localhost:8501

## Configuration

Set via environment variables (the container wires these up for you):

| Variable | Default | Notes |
| --- | --- | --- |
| `ELASTICSEARCH_URL` | `https://lme-elasticsearch:9200` | |
| `ELASTICSEARCH_USER` | `elastic` | |
| `ELASTICSEARCH_PASSWORD` | _(none)_ | **Required** — injected from the `elastic` Podman secret in LME. |
| `LITELLM_URL` | `https://lme-litellm:4000` | LiteLLM OpenAI-compatible proxy. |
| `LITELLM_API_KEY` | `sk-lme-llama-proxy` | |
| `LITELLM_MODEL` | `lfm2.5-1.2b-instruct` | Must match a model registered in `config/litellm_config.yaml`. |

## Architecture

```
Streamlit app (port 8501, HTTPS)
    |
    +--> Elasticsearch  (reads .alerts-security.alerts-*)
    +--> LiteLLM proxy --> llama.cpp (AI analysis + chat)
```

## License

Same as the LME project.
