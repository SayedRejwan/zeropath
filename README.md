# ZeroPath

A local-first security validation agent with a reviewed MITRE ATT&CK triad knowledge base.

ZeroPath runs an intentionally vulnerable **local lab**, drives a safe, allowlisted
enumeration agent against it, and produces structured, replayable evidence per run.
It pairs that runtime with a curated knowledge layer that joins each ATT&CK technique
to pentest steps, observable evidence, detection logic, and remediation in one record.

```
┌─────────────┐   ┌──────────────┐   ┌────────────────────┐
│ Local lab    │←──│ Agent loop   │←──│ Triad knowledge base│
│ (Flask,      │   │ (heuristic / │   │ (YAML → SQLite +    │
│  loopback)   │──▶│  allowlisted │──▶│  NetworkX graph)    │
└─────────────┘   │  actions)    │   └────────────────────┘
                  └──────┬───────┘
                         ▼
              runs/<id>/ evidence: events.jsonl,
              report.json, report.md, summary.json
```

## Why

Scanners produce findings; humans produce proof. ZeroPath is built around that gap:
it executes an allowlisted action loop against a lab it controls, records every
request and response hash, and keeps the knowledge that explains each step
(ATT&CK mapping, evidence, detection, remediation) separate from the runtime claim
of "flag captured".

## Safety model

- **Loopback-only targeting.** Every HTTP request and redirect is checked against
  the loopback origin of the selected lab. Non-loopback hosts are refused in code,
  not by policy (`zeropath/tools/http_tools.py`, `zeropath/util.py`).
- **Allowlisted actions.** The agent can only run the enumeration verbs defined by
  the tool layer; there is no arbitrary shell against the lab.
- **Local subprocess lab.** `--backend local` is a loopback Flask process, not a
  sandbox. `--backend docker` runs the same rooms in a container.
- **Authorized use only.** This tool is for environments you own or are explicitly
  authorized to test.

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/SayedRejwan/zeropath.git
cd zeropath
python -m venv .venv && .venv\Scripts\activate   # Windows
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Quickstart

```bash
# List the synthetic demo rooms
zeropath rooms list

# Run one room with the deterministic heuristic agent (no API key needed)
zeropath run room01_robots --backend local

# Replay any recorded run
zeropath replay <run_id>

# Stop and remove a run's lab process/container
zeropath kill <run_id>
```

Every run writes `events.jsonl`, `report.json`, `report.md`, and `summary.json`
under `runs/<run_id>/`.

## Triad knowledge base

`data/triads/techniques/*.yaml` is the operational knowledge source. A **triad**
joins one MITRE ATT&CK technique to:

- ordered, lab-scoped pentest steps,
- observable evidence (log source, artifact, signal),
- detection logic (query/analytic + required telemetry),
- verified remediation (hardening action + verification procedure).

```bash
zeropath triads validate          # schema + quality gate over all YAML
zeropath triads sync              # load reviewed triads into SQLite + graph
zeropath triads list
zeropath triads show T1003.001
zeropath triads fetch --refresh --skip-nvd   # refresh official ATT&CK/D3FEND caches
zeropath triads skeleton --limit 50         # generate draft skeletons for enrichment
```

Draft records never load into the operating knowledge base. A record reaches
`reviewed` only after it passes the schema, contains real scoped commands, includes
evidence/detection/remediation, and cites at least two non-AI sources.
`data/thm_rooms/` remains a curriculum index only.

## Benchmark

```bash
python -m zeropath.cli benchmark --backend local --repeats 3 --output runs/benchmark.json
python -m pytest -q
```

The benchmark runs every room N times, records attempts, elapsed time (including
startup/cleanup), failures, and report paths. Failed runs or benchmark cases return
a nonzero CLI exit code.

## Status & honest scope

This is **v0.3.0**, a prototype:

- 6 synthetic rooms, deterministic heuristic agent, replayable evidence.
- 52 valid triads (4 reviewed, 48 draft awaiting enrichment review).
- The LLM agent path exists but is not a validated live capability.
- No Docker-less claim about `--backend local`: it is a loopback subprocess,
  not a security sandbox.
- Not a production exploitation platform: no Firecracker isolation, no multi-agent
  swarm, no financial impact engine. Those are future milestones.

## Project layout

```
configs/rooms/     demo room definitions (YAML)
data/triads/       reviewed + draft ATT&CK triads (source of truth)
data/thm_rooms/    curriculum index of TryHackMe-style scenarios
lab/               the intentionally vulnerable Flask app (local lab)
zeropath/          agent, tools, orchestrator, CLI, storage adapters
scripts/           official-data fetch, skeleton generation, validation
tests/             53 tests: schema, runtime, scope, sync, scraper
```

## License

MIT — see [LICENSE](LICENSE).