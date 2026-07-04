# Firehose Log Diversion & SIEM Cost Control

_`sweets9/LME` fork. Status: design/adoption guide. Last updated: 2026-07-04._

> **What this is:** a pattern and adoption guide for using LME as a cheap,
> searchable landing zone for high-volume ("firehose") logs, so teams forward
> only high-value events to expensive per-GB SIEMs like Splunk or Microsoft
> Sentinel. It documents what LME can do **today** and what a small additive
> **router** component would add. Config snippets are illustrative starting
> points, not shipped files.

---

## 1. The problem: SIEM ingest is priced by volume

Splunk, Sentinel, and most SaaS SIEMs charge primarily on **GB ingested per
day**. The painful truth in most enterprises is that the *cheapest-to-produce*
logs are also the *highest-volume and lowest-signal*: firewall accept/deny,
proxy/CDN access logs, DNS, NetFlow, load-balancer logs, verbose cloud audit
trails. They can be **70-90% of ingest volume** while containing a small
fraction of the security signal — yet they must be *retained and searchable*
for investigations, audit, and compliance.

Paying premium SIEM rates to store a DNS firehose you query twice a year is
the canonical "SIEM tax."

## 2. The pattern: land everything cheap, forward the signal

```
                 ┌─────────────────────────────────────────┐
   firehose      │  Router / filter (syslog-ng or Vector)   │
  (firewalls,    │                                          │
   proxies,  ───►│   ├─ ALL events ──────────► LME          │  cheap, searchable
   DNS, cloud,   │   │                          (Elastic)   │  evidence store
   netdev)       │   └─ high-value subset ────► Splunk /    │  premium SIEM,
                 │       (auth, threats, IOC     Sentinel   │  only what matters
                 │        hits, KEV-relevant)                │
                 └─────────────────────────────────────────┘
```

- **LME becomes the bulk store.** Everything lands in Elasticsearch, where
  it is full-text searchable, dashboards work, and detections run — at
  self-hosted storage cost, not per-GB SIEM cost.
- **The premium SIEM gets the signal.** Only security-relevant events
  (authentication, IDS/IPS hits, EDR alerts, IOC/KEV matches, anomalies) are
  forwarded onward, cutting licensed ingest dramatically.
- **Nothing is lost.** When an investigation needs the raw firehose, it is in
  LME and searchable; you pivot from the SIEM to LME by shared keys
  (timestamp, host, IP, user).

This is the same "tier your telemetry" strategy vendors now sell as
"observability pipelines" — LME lets you own it.

## 3. What LME can do today

| Capability | How | Notes |
| --- | --- | --- |
| Receive syslog | **Wazuh Manager listens on `514/udp`** (`quadlet/lme-wazuh-manager.container`). | Network devices and appliances can send syslog straight to LME today; Wazuh decoders/rules normalise and alert. |
| Receive endpoint logs | **Elastic Agent + Fleet** (`lme-fleet-server.container`). | Windows/Linux endpoints ship via Fleet-managed Elastic Agent. |
| Ingest arbitrary syslog/UDP/TCP to Elasticsearch | **Elastic Agent "Custom UDP/TCP Logs" / "Syslog" integrations** (configured in Fleet/Kibana). | Lets an Elastic Agent act as a syslog receiver that writes directly to Elasticsearch. |
| Store cheaply & search | Elasticsearch + Kibana. | ILM/retention tiers control storage cost. |
| Detect on the stream | Wazuh rules, ElastAlert2, Kibana detection rules. | Detections run on the bulk store, so alerts are generated *before* anything is forwarded. |

So the "land everything in LME" half of the pattern is achievable with the
components already in the stack. What LME does **not** yet ship is a
**first-class outbound router** that forwards a filtered subset to Splunk/
Sentinel — that is the additive piece below.

## 4. The proposed router component

Add an optional syslog router as a sidecar container (kept **off by default**,
enabled per deployment). Two engine choices, both battle-tested:

- **syslog-ng** — the same engine **SC4S** is built on, so it is the natural
  SC4S-compatible bridge (see §5).
- **Vector** (`vector.dev`) — a modern, high-throughput pipeline with rich
  transforms and a Splunk HEC sink; good when you want in-pipeline filtering
  and sampling.

### Routing policy (what to keep vs forward)

| Keep in LME only (bulk) | Forward to premium SIEM (signal) |
| --- | --- |
| Firewall permit logs, NetFlow, LB access logs | Firewall **deny** to sensitive segments, IDS/IPS alerts |
| Proxy/CDN access logs, DNS query logs | DNS to known-bad / newly-registered domains, IOC hits |
| Verbose cloud read/list audit events | Cloud **write/permission-change/console-login** events |
| Routine host telemetry | Auth failures, privilege escalation, EDR detections |
| Everything, as searchable evidence | Anything matching a KEV/threat-intel enrichment |

### Illustrative Vector config (firehose → LME + filtered → Splunk HEC)

```toml
# Receive the syslog firehose
[sources.firehose]
type = "syslog"
address = "0.0.0.0:5514"
mode = "udp"

# ALL events -> LME (Elasticsearch)
[sinks.lme_elasticsearch]
type = "elasticsearch"
inputs = ["firehose"]
endpoints = ["https://lme-elasticsearch:9200"]
bulk.index = "firehose-%Y.%m.%d"
# auth + TLS via env/secrets

# Only high-value events -> Splunk HEC
[transforms.high_value]
type = "filter"
inputs = ["firehose"]
condition = '''
  includes(["deny","alert","failure","malware"], .action) ||
  .severity <= 3
'''

[sinks.splunk_hec]
type = "splunk_hec_logs"
inputs = ["high_value"]
endpoint = "https://splunk.example.com:8088"
# token via secret; index/sourcetype as needed
```

## 5. SC4S compatibility & adoption bridge

**SC4S (Splunk Connect for Syslog)** is a containerized **syslog-ng** with
Splunk-maintained parsers and vendor/product routing that normalises syslog
and forwards it to **Splunk HEC**. Many enterprises already run SC4S in front
of Splunk. That makes SC4S the ideal *adoption bridge* into LME — three
migration postures, lowest-disruption first:

### Posture A — Tee from existing SC4S (zero re-plumbing)

Keep SC4S exactly as is and add **one extra destination** that mirrors traffic
into LME. SC4S is syslog-ng, so this is a config add, not a redesign:

```conf
# syslog-ng / SC4S: add an LME destination and log both
destination d_lme_elastic {
    elasticsearch-http(
        url("https://lme-elasticsearch:9200/_bulk")
        index("firehose-${YEAR}.${MONTH}.${DAY}")
        type("")
        # tls + basic-auth options
    );
};

log {
    source(s_SC4S);          # existing SC4S source
    destination(d_lme_elastic);   # NEW: mirror everything to LME
    # existing Splunk HEC destination stays in place
};
```

Result: Splunk ingest is unchanged, but now **everything is also in LME**.
You can then *shrink* what SC4S sends to Splunk once you trust LME as the
system of record for the bulk data.

### Posture B — LME in front, SC4S/Splunk downstream

Point the firehose at the LME router first; land everything in LME and forward
only the high-value subset onward to SC4S/Splunk HEC. This is where the real
ingest savings appear, because Splunk now only sees the filtered stream.

### Posture C — Replace SC4S with an LME-managed syslog-ng

Run syslog-ng under LME using **SC4S-compatible routing conventions** (vendor/
product-based `log {}` paths, the same source framing), landing everything in
LME and keeping a Splunk HEC destination for high-value events only. Teams keep
their mental model from SC4S while LME owns the pipeline.

### Compatibility notes

- **Same engine.** Because SC4S is syslog-ng, LME's syslog-ng router can reuse
  SC4S filter/parser patterns and vendor routing with minimal translation.
- **HEC preserved.** High-value forwarding uses Splunk **HEC** exactly as SC4S
  does, so Splunk-side sourcetypes/indexes and downstream searches keep
  working.
- **Bidirectional pivot.** Shared normalised fields (timestamp, host, source/
  destination IP, user) let analysts pivot Splunk ↔ LME during an
  investigation.

## 6. Cost model (rule of thumb)

Let `V` = total firehose GB/day and `s` = the high-signal fraction actually
worth premium SIEM ingest (often **0.1-0.3**).

- **Before:** premium SIEM ingests `V` → cost ∝ `V`.
- **After:** premium SIEM ingests `s·V`; LME stores `V` at self-hosted cost.
- **Saving** ≈ `(1 - s)` × premium per-GB rate × `V`, minus LME storage cost.

For a 500 GB/day firehose at `s = 0.2`, that is **~400 GB/day removed from
premium SIEM ingest** while remaining fully searchable in LME.

Validate `s` empirically per source before committing — the routing policy in
§4 is the lever.

## 7. Roadmap hooks

- Ship the router as an **opt-in quadlet** (`lme-syslog-router.container`) with
  a documented `enable_syslog_router` flag and example syslog-ng/Vector
  configs under `config/`.
- Provide a **starter routing policy** encoding the §4 keep/forward table.
- Add a **HEC forwarding health check** (analogous to
  `scripts/check_fleet_api.sh`).
- Tie diversion into the [agentic SOC roadmap](agentic-soc-roadmap.md): the
  local LLM can *explain* why an event was/wasn't forwarded and *propose*
  routing-policy changes (a T1 draft action).

## 8. Related

- [agentic-soc-roadmap.md](agentic-soc-roadmap.md)
- [dependency-inventory.md](dependency-inventory.md)
- [fork-maintenance-strategy.md](fork-maintenance-strategy.md)
