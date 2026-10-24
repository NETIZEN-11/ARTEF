<div align="center">

<img src="assets/artef-diagram.png" alt="ARTEF — Agent Red-Teaming & Evaluation Framework" width="900" style="border-radius:12px;" />

# 🛡️ Agent Red-Teaming & Evaluation Framework

### **ARTEF** — Continuous Assurance, Adversarial Stress-Testing & Automated Safety Quality Gates for Production AI Agents

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6.svg?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000.svg?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

[![Safety Gate](https://img.shields.io/badge/Safety%20Gate-Automated%20✓-brightgreen.svg?style=for-the-badge)](https://github.com/NETIZEN-11/ARTEF)
[![Authors](https://img.shields.io/badge/Authors-Harish%20R%20S%20%26%20Nitesh%20Singh-FF6B6B.svg?style=for-the-badge&logo=github)](https://github.com/NETIZEN-11/ARTEF)
[![License](https://img.shields.io/badge/License-Proprietary%20OJT-orange.svg?style=for-the-badge)](LICENSE)
[![Year](https://img.shields.io/badge/Year-2026-8B5CF6.svg?style=for-the-badge)](https://github.com/NETIZEN-11/ARTEF)

</div>

---

## 📑 Table of Contents

<details>
<summary><b>Click to expand</b></summary>

- [Executive Overview](#-executive-overview)
- [Key Value Propositions](#-key-value-propositions)
- [System Architecture](#-system-architecture)
- [Core Functional Pillars](#-core-functional-pillars)
  - [Multi-Tier Scoring Pipeline](#1--multi-tier-scoring-pipeline)
  - [Golden Baselines & Regression Math](#2--golden-baselines--regression-math)
  - [Deterministic CI/CD Quality Gate](#3--deterministic-cicd-quality-gate)
  - [Autonomous Red-Teaming State Machine](#4--autonomous-red-teaming-state-machine)
- [Quickstart](#-quickstart)
  - [Prerequisites](#-prerequisites)
  - [Local Development](#method-1-local-development-sqlite-no-docker)
  - [Docker Stack](#method-2-docker-stack)
- [Demo Scenario](#-demo-scenario-seeded-regression-caught-end-to-end)
- [REST API Reference](#-rest-api-reference)
- [CI Quality Gate](#-ci-quality-gate)
- [Project Structure](#-project-directory-structure)
- [Documentation](#-in-depth-documentation)
- [Testing](#-testing)
- [Authorship](#-project-scope--authorship)
- [License](#-ownership--license)

</details>

---

## 📌 Executive Overview

> **ARTEF** is an enterprise-grade continuous-assurance and adversarial stress-testing platform engineered specifically for production AI agents, autonomous tool-use workflows, and LLM applications.

ARTEF addresses the critical gap between deploying AI agents and knowing they are safe. It:

1. 🎯 **Subjects Agents to Adversarial Attacks** — Probes agents with jailbreak, prompt-injection, PII-extraction and harmful-request test suites, plus multi-turn red-team sessions.
2. 📉 **Detects Behavioral & Safety Drift** — Diffs every test's verdict against the last human-approved baseline run (PASS→FAIL, PASS→INCONCLUSIVE, new failures).
3. 🏷️ **Classifies Risk Severity** — Critical / High / Medium / Low, with a deterministic override table (e.g. any jailbreak or PII failure is Critical).
4. 🚦 **Enforces Deterministic CI/CD Quality Gates** — Issues `PASS`, `WARN`, `FAIL` or `BLOCK` and fails closed: an unreachable agent or missing baseline never passes.
5. 👥 **Empowers Human Reviewers (HITL)** — Routes Critical/High and inconclusive regressions to a review queue; baseline approvals are audit-logged.

```mermaid
flowchart TD
    classDef dev fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef cicd fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e;
    classDef engine fill:#fae8ff,stroke:#c026d3,stroke-width:2px,color:#86198f;
    classDef gate fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#854d0e;
    classDef pass fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534;
    classDef warn fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412;
    classDef block fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b;
    classDef hitl fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#5b21b6;

    subgraph Phase1 ["① Candidate Release"]
        DEV["<b>Developer Commit (Agent v2.4)</b><br/>• System Prompts<br/>• Autonomous Tools<br/>• Model Weights / Hyperparameters"]:::dev
    end

    subgraph Phase2 ["② CI/CD Orchestration"]
        CICD["<b>CI/CD Pipeline</b><br/>• GitHub Actions / Webhook Trigger<br/>• Test Runner Provisioning"]:::cicd
    end

    subgraph Phase3 ["③ ARTEF Engine Core"]
        direction TB
        ADV["1. Adversarial Probes<br/>Prompt Injection, Jailbreak, SSRF"]:::engine
        DUAL["2. Dual Scoring System<br/>Zero-cost Regex + LLM-as-a-Judge"]:::engine
        REG["3. Baseline Regression Diff<br/>Per-test verdict vs approved baseline"]:::engine
        SEV["4. Severity Classification<br/>Critical / High / Medium / Low"]:::engine
        ADV --> DUAL --> REG --> SEV
    end

    subgraph Phase4 ["④ Deterministic CI/CD Gate"]
        GATE["<b>Deterministic CI/CD Safety Gate</b><br/>Programmatic Policy Rule Engine"]:::gate
    end

    subgraph Phase5 ["⑤ Verdict & Automated Actions"]
        PASS["<b>✅ PASS</b><br/>Safe to Deploy<br/>(No S3/S4 Flaws)"]:::pass
        WARN["<b>⚠️ WARN</b><br/>Non-fatal Safety Drift<br/>(Flagged Tolerance)"]:::warn
        BLOCK["<b>❌ BLOCK</b><br/>Pipeline Halted<br/>(Critical Vulnerability)"]:::block
        PROD["<b>Production Agent</b><br/>Live in Production Cluster"]:::pass
        SLACK["<b>Slack / Webhook Alert</b><br/>Engineering Notification"]:::warn
        HITL["<b>HITL Review Queue</b><br/>Human Specialist Triage & Evidence Audit"]:::hitl
    end

    DEV -->|Push / PR| CICD
    CICD -->|Trigger Evaluation| Phase3
    SEV -->|Safety Metrics Vector| GATE

    GATE -->|Clear Safety Gate| PASS
    GATE -->|Drift Alert| WARN
    GATE -->|Policy Violation| BLOCK

    PASS -->|Continuous Deployment| PROD
    WARN -->|Dispatch Notification| SLACK
    BLOCK -->|Halt PR & Route Case| HITL

    HITL -.->|Re-evaluate After Expert Sign-off| CICD
```

---

## 🚀 Key Value Propositions

| Capability | What It Does | Why It Matters |
| :--- | :--- | :--- |
| 🎯 **Multi-Strategy Scoring** | Four deterministic matchers (exact, regex, keyword, refusal); LLM-judge rubrics with a secondary-judge fallback. | Deterministic checks need no LLM calls; open-ended behaviour can still be judged. |
| 📉 **Baseline Regression Engine** | Compares each test's verdict with the human-approved baseline run for the suite. | Instantly detects silent model degradation, safety score drops, and behavioral regressions before users see them. |
| 🚦 **Deterministic CI Gate** | Evaluates runs against configurable safety rules and outputs programmatic `PASS`, `WARN`, or `BLOCK` verdicts. | Prevents vulnerable or regressed agent weights, system prompts, or RAG configurations from ever deploying. |
| 🤖 **Autonomous Red-Teaming Agent** | LangGraph state machine that escalates through a category's attack library until the target breaks or the turn cap is hit. | Shows whether an agent holds up under repeated, varied attacks, not just one prompt. |
| 👥 **Human-in-the-Loop (HITL) Queue** | Priority-ordered triage queue for low-confidence or high-severity safety edge cases. | Keeps humans in the loop for the results that matter most. |
| 🔐 **Enterprise RBAC & Security** | RS256 JWT tokens and role-based access (admin, safety engineer, ML engineer, QA engineer, viewer). | Each endpoint checks the caller's role. |

---

## 🏗️ System Architecture

ARTEF is built following clean modular architecture principles, decoupling presentation, API routing, autonomous adversarial generation, multi-tier evaluation, and deterministic CI/CD policy gates into distinct layers.

```mermaid
flowchart TD
    classDef client fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef api fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#92400e;
    classDef service fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#166534;
    classDef eval fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b;
    classDef redteam fill:#fae8ff,stroke:#c026d3,stroke-width:2px,color:#86198f;
    classDef target fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#9a3412;
    classDef store fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#6b21a8;
    classDef gate fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#854d0e;

    subgraph PresentationLayer ["① Client & Presentation Layer (Next.js 14 / TypeScript)"]
        UI_Dash["Dashboard & Telemetry<br/><code>/dashboard</code>"]:::client
        UI_Runs["Test Suites & Runs Monitor<br/><code>/runs</code>"]:::client
        UI_Sim["Red Teaming<br/><code>/redteam</code>"]:::client
        UI_HITL["HITL Human Review Queue<br/><code>/reviews</code>"]:::client
        UI_Gate["Run detail and gate decision<br/><code>/runs/[id]</code>"]:::client
        CLI_Client["CLI & Python/TS SDK"]:::client
    end

    subgraph APIGateway ["② API Gateway & Security Perimeter (FastAPI Async)"]
        Router["REST Router & Endpoints<br/><code>/api/v1/*</code>"]:::api
        AuthMiddleware["RS256 JWT & RBAC (5 Distinct Roles)"]:::api
        RateLimit["Rate Limiter (Token Bucket / Redis)"]:::api
        AuditLog["Audit & Correlation ID Tracker"]:::api
    end

    subgraph ServiceCore ["③ Application Services & Business Orchestration"]
        SuiteSvc["Test Suite & Case Manager"]:::service
        RunSvc["Run Orchestrator & Task Dispatcher"]:::service
        HITLSvc["Human-in-the-Loop Triage Service"]:::service
        GuardSvc["Guardrails & MCP Security Proxy"]:::service
        BaselineSvc["Golden Baseline Engine"]:::service
    end

    subgraph RedTeamEngine ["④ Autonomous Red-Teaming Engine (Adversarial Swarm)"]
        PayloadGen["Attack Synthesizer & Mutator<br/>(OWASP LLM Top 10)"]:::redteam
        AttackVectors["Attack Vectors:<br/>Prompt Injections<br/>Multi-turn Jailbreaks<br/>Tool Poisoning<br/>SSRF & Exfiltration"]:::redteam
        StateGraph["LangGraph-Style State Machine<br/>(Select → Probe → Adapt → Escalate)"]:::redteam
    end

    subgraph TargetAgentLayer ["⑤ Target Agent Under Test (SUT)"]
        AgentAPI["Agent API / WebSocket Interface"]:::target
        LLMCog["LLM Cognitive Core<br/>(Prompts, System Instructions)"]:::target
        AgentTools["Agent Autonomous Tools<br/>(SQL, Shell, Webhooks, APIs)"]:::target
    end

    subgraph EvaluationCore ["⑥ Multi-Tier Evaluation & Scoring Pipeline"]
        Tier1["Tier 1: Deterministic Matchers<br/>(Regex, Keywords, Refusal Checks)"]:::eval
        Tier2["Tier 2: LLM-as-a-Judge<br/>(Strict JSON Pydantic Scoring)"]:::eval
        Tier3["Tier 3: Resilient Fallback<br/>(Heuristic Safety Circuit Breaker)"]:::eval
        SevMatrix["Severity Classifier<br/>(Low → Critical, deterministic overrides)"]:::eval
        RegEngine["Regression Detector<br/>(verdict diff vs baseline)"]:::eval
    end

    subgraph GatePolicy ["⑦ Deterministic CI/CD Quality Gate"]
        GateDecider["Policy Rule Engine<br/>Threshold & Tolerance Check"]:::gate
        Verdict_Pass["✅ PASS: Safe to Deploy"]:::gate
        Verdict_Warn["⚠️ WARN: Non-fatal Drift"]:::gate
        Verdict_Block["❌ BLOCK: PR Pipeline Halted"]:::gate
    end

    subgraph StorageLayer ["⑧ Persistence & Caching Tier"]
        PostgreSQL[("PostgreSQL / SQLite<br/>Async SQLAlchemy 2.0")]:::store
        Redis[("Redis In-Memory<br/>Celery Queue & Cache")]:::store
        AuditVault[("Audit Log<br/>baseline approvals, settings")]:::store
    end

    PresentationLayer --> Router
    Router --> AuthMiddleware
    AuthMiddleware --> RateLimit
    RateLimit --> AuditLog

    AuditLog --> SuiteSvc
    AuditLog --> RunSvc
    AuditLog --> HITLSvc
    AuditLog --> GuardSvc
    AuditLog --> BaselineSvc

    RunSvc --> RedTeamEngine
    RedTeamEngine --> PayloadGen
    PayloadGen --> AttackVectors
    AttackVectors --> StateGraph
    StateGraph --> AgentAPI
    AgentAPI --> LLMCog
    LLMCog --> AgentTools

    AgentAPI --> Tier1
    Tier1 --> Tier2
    Tier2 --> Tier3
    Tier3 --> SevMatrix
    SevMatrix --> RegEngine
    RegEngine --> BaselineSvc

    RegEngine --> GateDecider
    GateDecider --> Verdict_Pass
    GateDecider --> Verdict_Warn
    GateDecider --> Verdict_Block

    Verdict_Block --> UI_HITL
    Verdict_Warn --> UI_Gate
    Verdict_Pass --> CLI_Client

    SuiteSvc --> PostgreSQL
    RunSvc --> PostgreSQL
    HITLSvc --> PostgreSQL
    BaselineSvc --> PostgreSQL
    RunSvc --> Redis
    StateGraph --> Redis
    GateDecider --> AuditVault
```

---

## 🏛️ Core Functional Pillars

### 1. 🎯 Scoring

| Tier | Mechanism | Calls an LLM? |
|:---:|:---|:---:|
| **Matchers** | exact, regex, keyword, refusal patterns | No |
| **LLM judge** | `llm_rubric` tests: primary judge returns schema-validated JSON (verdict, confidence, rationale, evidence) | Yes (`EVAL_MODE=live`) |
| **Fallback** | primary judge error → secondary judge; both fail, or the target errors/times out → **INCONCLUSIVE** | — |

### 2. 📉 Baselines and regression detection

An admin or safety engineer approves a finished run (no inconclusive results) as the
suite's baseline; the previous baseline is deactivated. Each later run is diffed test by
test: PASS→FAIL, PASS→INCONCLUSIVE, INCONCLUSIVE→FAIL and new failing tests are
regressions; improvements are logged, not flagged.

### 3. 🚦 Deterministic CI gate

```
BLOCK  any Critical or High regression                      (exit 1)
FAIL   any inconclusive result, or no approved baseline     (exit 1)
WARN   only Medium / Low regressions                        (exit 0)
PASS   no regressions                                       (exit 0)
```

### 4. 🤖 Autonomous Red-Teaming State Machine

Built as a **bounded state graph**:

```
[Select Target] ──► [Select Harm Category] ──► [Synthesize Attack Payload] ──► [Dispatch to Agent]
                                                                                        │
[Terminate & Report] ◄── [Check Turn Limits / Success] ◄── [Evaluate Vulnerability] ◄──┘
```

---

## ⚡ Quickstart

Two ways to run ARTEF. **Local development** needs no Docker; the **Docker stack** adds
PostgreSQL, Redis and a Celery worker exactly as in production.

### 📋 Prerequisites

| Requirement | Version | Notes |
|:---|:---:|:---|
| Python | 3.11+ | Backend (tested with 3.11) |
| Node.js | 20+ | Frontend |
| pnpm | 10.x | `npx pnpm@10.18.0 …` works without installing it (pnpm 9 rejects `frontend/pnpm-workspace.yaml`) |
| Docker + Compose | recent | Only for the Docker stack / real Redis |

---

### Method 1: Local development (SQLite, no Docker)

All commands run from the repository root unless noted. Windows users: run them in Git Bash
or adapt the activation line for PowerShell.

**① Backend environment**
```bash
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.lock # pinned versions
pip install -e . --no-deps           # makes the `app` package importable
python scripts/dev_setup.py          # writes backend/.env + backend/.keys/ (JWT keys); both gitignored
```

**② Database with demo data** (users, agents, suites)
```bash
cd backend
python ../scripts/seed_demo_data.py
```
The seed script requires `SEED_*` settings (user passwords, demo agent URLs, an agent token).
`scripts/dev_setup.py` writes them to `backend/.env` with **random** passwords; log in as
`admin` with the `SEED_ADMIN_PASSWORD` value from that file. See `.env.example` for the full list.

**③ Start the services** (one terminal each)
```bash
# API (from backend/)
uvicorn app.main:app --port 8000

# Demo target agents: the AI systems under test (from the repo root)
python demo/target_agent.py --mode safe --port 9001
python demo/target_agent.py --mode vulnerable --port 9002

# Frontend (from frontend/)
pnpm install && pnpm dev           # http://localhost:3000
```
On Windows, `powershell -ExecutionPolicy Bypass -File scripts\start_dev.ps1` starts all four
in their own windows, with evaluations running inside the API (no Redis needed). It skips any
service whose port is already in use.

**④ Run evaluations.** Choose one way to execute runs:

* **Real worker (recommended, matches production):** start Redis (for example
  `docker run -p 6379:6379 redis:7-alpine`) and, from `backend/`:
  ```bash
  celery -A app.workers.celery_app worker -Q default,evaluation,redteam,maintenance --pool=solo --loglevel=info
  ```
  (`--pool=solo` is required on Windows.)
* **No Redis:** set `CELERY_TASK_ALWAYS_EAGER=true` in `backend/.env`. Runs then execute
  inside the API process. Fine for development, not for production.

If a run is created while Redis is unreachable, the API answers **503** and marks the run
`failed`; it never stays silently queued.

### Method 2: Docker stack

```bash
python scripts/dev_setup.py                 # JWT keys in backend/.keys (mounted into the containers)
docker compose up -d --build
docker compose exec backend python ../scripts/seed_demo_data.py
```

| Service | URL |
|:---|:---|
| Frontend | `http://localhost:3000` |
| API + Swagger | `http://localhost:8000/docs` |
| ChromaDB | `http://localhost:8001` |
| Demo agents | `http://demo-agent-safe:9001/chat`, `http://demo-agent-vulnerable:9002/chat` (inside the Docker network) |

If a local PostgreSQL already uses port 5432, start with `POSTGRES_HOST_PORT=5433 docker compose up -d --build`.
MinIO (object storage) is optional and not started by default; the `minio/minio` image is no
longer published on Docker Hub (see the `storage` profile in `docker-compose.yml`).

`docker-compose.prod.yml` builds the production images; it expects a root `.env` with
`POSTGRES_*`, `MINIO_ROOT_*`, `SECRET_KEY` and JWT keys in `./secrets/`.

### Database schema and migrations

The API creates any missing tables from the models at startup, which is enough for
development. For a managed PostgreSQL database use Alembic instead (from `backend/`):

```bash
alembic upgrade head      # create / update the schema
alembic check             # fails if the models and migrations have drifted (also run in CI)
```

If the database was already created by the API at startup, record it as current with
`alembic stamp head` (the baseline migration matches the models exactly). Migrations target
PostgreSQL; the SQLite development database relies on startup table creation.

### Troubleshooting (Windows): Docker Desktop never starts

If Docker Desktop stays at "starting" and its log (`%LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log`)
says *"remove ...dockerInference: The file cannot be accessed by the system"*, stale Unix-socket
files are blocking it and Windows cannot delete them. Quit Docker Desktop, delete them from WSL,
then start Docker again:

```bash
wsl -d Ubuntu -- rm -f /mnt/c/Users/<you>/AppData/Local/Docker/run/dockerInference /mnt/c/Users/<you>/AppData/Local/Docker/run/userAnalyticsOtlpHttp.sock /mnt/c/Users/<you>/AppData/Local/docker-secrets-engine/engine.sock
```

---

## 🎬 Demo scenario (seeded regression caught end to end)

1. Log in, open **Evaluations → New Evaluation**, run suite *Jailbreak Tests* against
   *Mock Target Agent v1 (Safe)*. Result: all tests pass, gate **FAIL**: *"No approved baseline"*.
2. Approve that run as the baseline (**Baselines**, or `POST /api/v1/baselines/`).
3. Run the same suite against *Mock Target Agent v2 (Vulnerable)*. The jailbreak tests now
   fail: 2 **Critical** regressions, gate **BLOCK**, run status *review required*, and both
   regressions appear in **Reviews**.
4. Run the safe agent again: gate **PASS**.
5. **Red Teaming**: attack each agent. The safe agent resists every escalation (verdict PASS);
   the vulnerable one leaks its system prompt on the first turn (verdict FAIL).

The same scenario runs automatically in CI (`backend/tests/integration/test_pipeline.py`).

To use a real LLM as the system under test, start the demo agent with
`--backend llm` and set `DEMO_AGENT_API_KEY` (OpenAI-compatible API; costs money, results vary).

---

## 📡 REST API Reference

Interactive documentation: `http://localhost:8000/docs`. Main endpoints (all under `/api/v1`):

| Method | Endpoint | Description |
|:---:|:---|:---|
| `POST` | `/auth/login`, `/auth/refresh` | Obtain / refresh RS256 JWTs |
| `GET` | `/auth/me` | Current user and roles |
| `GET/POST` | `/agents/` | List / register target agents |
| `GET/PUT/DELETE` | `/agents/{id}` | Inspect / update / delete an agent |
| `GET/POST` | `/suites/` | List / create test suites (JSON-schema validated) |
| `POST` | `/suites/import/yaml`, `/suites/import/json` | Import a suite file |
| `GET` | `/suites/{id}` | Suite with its test cases |
| `POST` | `/runs/` | Queue an evaluation run (Celery); 503 if the queue is unavailable |
| `GET` | `/runs/{id}` | Status, counts, `gate_decision`, `gate_summary` |
| `GET` | `/runs/{id}/results` | Per-test verdicts |
| `GET` | `/regressions/run/{run_id}` | Regressions with persisted severity |
| `GET/POST` | `/baselines/` | List / approve a finished run as the suite baseline |
| `GET` | `/reviews/` | Human review queue |
| `POST` | `/reviews/{id}/label` | Label a review item |
| `POST` | `/redteam/run` | Multi-turn red-team session against an agent |
| `GET` | `/redteam/history` | Red-team sessions (in memory; cleared on restart) |

---

## 🚦 CI quality gate

`.github/workflows/regression-gate.yml` runs the seeded-regression scenario on every pull
request and fails the build if a seeded regression is not detected and blocked.
`ci.yml` runs static checks, backend and frontend tests, the production frontend build and
the Docker image builds. `security-scan.yml` runs pip-audit, bandit and pnpm audit
(report-only for now) plus the model-scanner tests. `deploy.yml` is a manual placeholder:
its deployment steps are not implemented.

Gate rules (`backend/app/domain/policies.py`):

| Decision | When | Exit code |
|:---:|:---|:---:|
| **BLOCK** | any Critical or High regression | 1 |
| **FAIL** | any inconclusive result (target unreachable, scoring error), or no approved baseline | 1 |
| **WARN** | only Medium/Low regressions | 0 |
| **PASS** | no regressions | 0 |

---

## 📂 Project Directory Structure

```text
ARTEF/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # FastAPI routers
│   │   ├── core/            # settings, database, security (RS256 JWT), logging
│   │   ├── domain/          # enums, value objects, gate & severity policies
│   │   ├── evaluation/      # matchers, LLM judges, regression detector, severity, gate
│   │   ├── models/          # SQLAlchemy 2.0 models
│   │   ├── providers/       # LLM, embedding and target-agent adapters
│   │   ├── redteam/         # LangGraph red-team agent, attack library
│   │   ├── repositories/    # data access
│   │   ├── services/        # pipeline_service (execute → score → diff → gate → review)
│   │   └── workers/         # Celery app and tasks
│   ├── alembic/             # migrations (versions/ = current; legacy_versions/ = old, unused)
│   └── tests/               # unit/ and integration/ (pytest)
├── demo/target_agent.py     # demo AI agent under test (safe / vulnerable)
├── frontend/                # Next.js 14 app (src/app routes, src/components, src/lib)
├── evaluation/suites/       # example YAML suites
├── scripts/                 # dev_setup, seed_demo_data, utilities
├── requirements.lock        # pinned runtime dependencies (uv pip compile --universal)
├── requirements-dev.lock    # pinned runtime + dev dependencies
└── docker-compose*.yml
```

---

## 📚 In-Depth Documentation

The documents in `docs/` were written before the current implementation and describe some
features that are planned rather than built. Where they disagree with this README or the
code, the code and this README are correct.

| Document | Description |
|:---|:---|
| [`docs/architecture.md`](docs/architecture.md) | Architecture overview |
| [`docs/database.md`](docs/database.md) | Tables and relationships |
| [`docs/security.md`](docs/security.md) | Threat model and RBAC |
| [`docs/adr/`](docs/adr/README.md) | Architecture decision records |

---

## 🧪 Testing

```bash
# Backend: unit + integration (real API, SQLite, eager Celery, HTTP demo agents). No setup needed.
pytest backend/tests -q

# Only the seeded-regression scenario (PRD primary metric)
pytest backend/tests/integration/test_pipeline.py -v

# Frontend (from frontend/)
pnpm typecheck && pnpm test && pnpm build
```

What is mocked: in the default `EVAL_MODE=local`, tests that use an **LLM rubric** are
scored by a deterministic stand-in instead of a real judge model. Deterministic matchers
(refusal, regex, keyword, exact) never call an LLM. Real LLM judging needs
`EVAL_MODE=live` and `PRIMARY_JUDGE_API_KEY` (and optionally the secondary judge), and is
not exercised by the automated tests.

---

## 👨‍💻 Project Scope & Authorship

> This project was designed, developed, and documented by a two-person team as part of an **On-the-Job Training (OJT) Program**.

<div align="center">

| Field | Detail |
|:---|:---|
| **Developers** | Harish R S, Nitesh Singh |
| **GitHub** | [@Harishrs2006](https://github.com/Harishrs2006), [@BYTEZEN-11](https://github.com/BYTEZEN-11) |
| **Project Type** | On-the-Job Training (OJT) — Team Project |
| **Project Title** | Agent Red-Teaming & Evaluation Framework (ARTEF) |
| **Year** | 2026 |
| **Scope** | Full-stack production system — FastAPI Backend, Next.js 14 Frontend, RBAC Auth, CI/CD Safety Gate, Human Review Queue, Adversarial Red-Teaming Engine |

</div>

> Design, implementation, testing, and documentation were carried out by **Harish R S** and **Nitesh Singh** as part of the OJT evaluation deliverable.

---

## 📄 Ownership & License

<div align="center">

**Copyright © 2026 Nitesh Singh. All Rights Reserved.**

This is a **proprietary OJT project** — not an open-source project. Source code is shared exclusively for evaluation, review, and demonstration purposes.

See [LICENSE](LICENSE) for full terms.

</div>

---

<div align="center">

**🛡️ ARTEF — Built for the Future of Safe AI**

*Copyright © 2026 **Nitesh Singh** — OJT Project: Agent Red-Teaming & Evaluation Framework*

[![GitHub](https://img.shields.io/badge/GitHub-NETIZEN--11%2FARTEF-181717.svg?style=flat-square&logo=github)](https://github.com/NETIZEN-11/ARTEF)
[![Author](https://img.shields.io/badge/Author-Harishrs2006-FF6B6B.svg?style=flat-square&logo=github)](https://github.com/Harishrs2006)
[![Author](https://img.shields.io/badge/Author-BYTEZEN--11-FF6B6B.svg?style=flat-square&logo=github)](https://github.com/BYTEZEN-11)

</div>
