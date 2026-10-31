# AeroLog — Voice Agent for Aircraft Maintenance Logging

A voice-powered AI agent that lets aircraft maintenance technicians log inspection findings and maintenance actions by **talking** — hands-free, in a noisy hangar — and produces validated, compliance-grade digital maintenance records.

Built for the aircraft MRO (Maintenance, Repair, Overhaul) domain with authentic aviation language: ATA chapter codes, tail numbers, part numbers, torque specs, airworthiness sign-offs, and CAT-A/B/C defect severity.

```
┌───────────────────────────────────────────────────────────────┐
│                        AeroLog Architecture                   │
│                                                               │
│  ┌──────────┐    ┌──────────────────────────────────────────┐ │
│  │ Technician│───▶│  Voice Provider Layer                   │ │
│  │ (Phone/   │   │  LocalSim │ Bolna │ Plivo │ Exotel       │ │
│  │  Browser) │   │  ┌──────┐   ┌──────┐                     │ │
│  └──────────┘    │  │ ASR  │   │ TTS  │                     │ │ 
│                  │  │Deepgram  │Cartesia                    │ │
│                  │  │Sarvam│   │Sarvam│                     │ │
│                  │  └───┬──┘   └──┬───┘                     │ │
│                  └──────┼────────┼──────────────────────────┘ │
│                         │        │                            │
│                         ▼        ▲                            │
│  ┌───────────────────────────────────────────────────────┐    │
│  │              Agent Pipeline (State Machine)           │    │
│  │  LISTENING → EXTRACTING → CLARIFYING → CONFIRMING     │    │
│  │     ↕           ↕            ↕            ↓           │    │
│  │  ANSWERING   HISTORY    ESCALATION    FINALIZED       │    │
│  │   _QUERY    _READBACK    _CHECK                       │    │
│  │                                                       │    │
│  │  Tools: extract_fields │ ask_followup │ search_manual │    │
│  │         lookup_history │ escalate │ save_record       │    │
│  └──────────┬──────────┬──────────┬──────────────────────┘    │
│             │          │          │                           │
│     ┌───────▼──┐  ┌────▼───┐  ┌───▼─────┐                     │
│     │ LLM Layer│  │  RAG   │  │   DB    │                     │
│     │ Claude / │  │ Manual │  │ Records │                     │
│     │ OpenAI / │  │ Search │  │ Aircraft│                     │
│     │ RuleBased│  │ TF-IDF │  │ History │                     │
│     └──────────┘  └────────┘  └─────────┘                     │
│                                     │                         │
│  ┌──────────────────────────────────┼────────────────────┐    │
│  │          WebSocket / SSE         │                    │    │
│  └──────────────────────────────────┼────────────────────┘    │
│                                     │                         │
│  ┌──────────┐              ┌────────▼──────────┐              │
│  │Technician│              │   Supervisor      │              │
│  │ Console  │              │   Dashboard       │              │
│  │(Mobile)  │              │   (Desktop)       │              │
│  └──────────┘              └───────────────────┘              │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start (LocalSim — no API keys needed)

```bash
# Clone and enter
cd BOLNA-YC-HACKATHON

# One-command setup + run
make dev
# OR manually:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py
cd frontend && npm install && cd ..
# Start backend + frontend
python -m uvicorn app.main:app --port 8000 &
cd frontend && npm run dev &
```

Open:
- **Technician Console**: http://localhost:5173/
- **Supervisor Dashboard**: http://localhost:5173/dashboard
- **API Docs**: http://localhost:8000/docs

## Features

### Voice-to-Structured Record
Speak naturally: *"On tail N-one-two-three, ATA 72, number four bearing, found oil residue, torque below spec at 25 inch-pounds, replaced O-ring MS29513-012, ops check good"*

→ Produces a validated record with aircraft registration, ATA chapter, component, discrepancy, corrective action, parts, measurements (with in-spec/out-of-spec), and severity.

### Missing-Field Follow-Up
The agent inspects the record for missing required fields (registration, ATA chapter, discrepancy, corrective action, technician ID) and asks targeted follow-up questions one at a time until the record is complete.

### Hands-Free Manual Q&A (RAG)
Ask mid-log: *"What's the torque spec for the number four bearing B-nut?"* — answered from indexed maintenance manuals with section citations. Never invents values.

### Service History Read-Back
*"Read me the last service on VT-ABC"* — queries prior records and reads back a spoken summary. Flags repeat defects (same ATA/component within 90 days).

### Safety Escalation
CAT-A findings or safety trigger words (crack, fuel leak, FOD, control surface damage) immediately escalate to supervisors via phone call, dashboard alert, or webhook.

### Multilingual Support
Supports English, Hindi, and Telugu with English technical terms mixed in (code-switching). Hindi: *"VT-DEF pe ATA 79, oil filter replace kiya"* → clean English record.

### Live Supervisor Dashboard
Real-time view of all records via WebSocket. Escalated records pinned at top. Overdue inspections surfaced. Sign-off workflow built in.

## Switching to Real Providers

Edit `.env`:

```bash
# Use Claude for extraction
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Use Deepgram for ASR
ASR_PROVIDER=deepgram
DEEPGRAM_API_KEY=...

# Use Sarvam for Hindi/Telugu ASR + TTS
ASR_PROVIDER=sarvam
TTS_PROVIDER=sarvam
SARVAM_API_KEY=...

# Use Bolna for phone-based voice agent
VOICE_PROVIDER=bolna
BOLNA_API_KEY=...
BOLNA_AGENT_ID=...

# Use Plivo/Exotel for telephony
VOICE_PROVIDER=plivo  # or exotel
PLIVO_AUTH_ID=...
PLIVO_AUTH_TOKEN=...

# Escalate via phone call
ESCALATION_CHANNEL=call
```

## Demo Scenarios

Run all 5 scripted scenarios through the real pipeline:

```bash
python demo/run_demo.py
```

1. **English Inspection** — out-of-spec torque, CAT-B, parts logged, ops check
2. **Crack Finding** — CAT-A, safety escalation fires, supervisors notified
3. **Manual Q&A** — torque spec lookup from AMM, then continues logging
4. **Hindi Code-Switch** — "VT-DEF pe ATA 79..." → clean English record
5. **History Read-Back** — prior service on VT-ABC, repeat defect flagged

Or test interactively via the API:

```bash
# Start a session
curl -X POST http://localhost:8000/api/session/start \
  -H "Content-Type: application/json" \
  -d '{"technician_id": "TECH-001"}'

# Send voice input (text in LocalSim mode)
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/input \
  -H "Content-Type: application/json" \
  -d '{"text": "On tail N456CD, ATA 28, found fuel leak at wing root fitting"}'
```

## Project Structure

```
├── app/
│   ├── main.py              # FastAPI app, lifespan, startup
│   ├── config.py             # Pydantic Settings (.env loading)
│   ├── api/
│   │   ├── routes.py         # REST endpoints (records, aircraft, metrics)
│   │   ├── session.py        # Voice session management
│   │   └── websocket.py      # WebSocket + SSE for live updates
│   ├── agent/
│   │   ├── pipeline.py       # Agent state machine + tool-use loop
│   │   └── escalation.py     # Safety escalation manager
│   ├── schemas/
│   │   └── maintenance.py    # Pydantic models (record, parts, measurements)
│   ├── db/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── database.py       # Async engine/session setup
│   │   └── repository.py     # Data access layer
│   ├── llm/
│   │   ├── base.py           # LLM provider interface
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   ├── rule_based.py     # Regex fallback (no API key needed)
│   │   ├── tools.py          # Agent tool definitions
│   │   └── factory.py
│   ├── voice/providers/
│   │   ├── base.py           # ASR/TTS/Voice/Telephony interfaces
│   │   ├── local_sim.py      # Browser-based simulation
│   │   ├── bolna_provider.py
│   │   ├── deepgram_asr.py
│   │   ├── sarvam_asr.py
│   │   ├── cartesia_tts.py
│   │   ├── sarvam_tts.py
│   │   ├── plivo_provider.py
│   │   └── exotel_provider.py
│   ├── rag/
│   │   ├── chunker.py        # Manual document chunking
│   │   ├── embeddings.py     # TF-IDF / LLM embeddings
│   │   └── engine.py         # RAG search engine
│   └── normalize/
│       └── normalize.py      # NATO phonetic, numbers, units, registrations
├── frontend/                  # React + Vite + TypeScript + Tailwind
│   └── src/
│       ├── pages/TechnicianConsole.tsx
│       └── pages/SupervisorDashboard.tsx
├── manuals/                   # Synthetic AMM task cards for RAG
├── demo/run_demo.py          # Scripted demo scenario runner
├── tests/
│   ├── test_normalize.py     # 86 unit tests
│   └── test_pipeline_live.py # End-to-end pipeline tests
├── seed.py                    # Database seeder
├── docker-compose.yml
└── Makefile
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2
- **Database**: SQLite (default) / PostgreSQL
- **Realtime**: WebSocket + SSE
- **LLM**: Anthropic Claude (tool use) / OpenAI / Rule-based fallback
- **ASR**: Deepgram / Sarvam (Hindi/Telugu) / Browser Web Speech API
- **TTS**: Cartesia / Sarvam / Browser Speech Synthesis
- **Telephony**: Bolna / Plivo / Exotel
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **RAG**: TF-IDF embeddings + cosine similarity over manual chunks

## Key Metrics (from seeded data)

| Metric | Value |
|--------|-------|
| Records logged | 8+ |
| Avg time to log | ~4 min |
| Escalation rate | 12.5% |
| Overdue inspections | 1 |
| Repeat defects caught | 1 |
