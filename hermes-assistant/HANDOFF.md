# Hermes Digital Assistant — Session Handoff

## Goal
Personal digital assistant running locally via Docker, using an existing Ollama instance as the model backend, with Hermes (NousResearch) as the default model. No cloud/Anthropic token usage unless explicitly enabled.

## What Was Built

### Files (all in `hermes-assistant/`)
| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Main compose definition |
| `.env.example` | Environment variable template |

Copies also written to `/home/user/` (outside repo) for direct use.

### Key Design Decisions
- **Open WebUI** (`ghcr.io/open-webui/open-webui:main`) — standard Ollama-compatible assistant UI
- **No bundled Ollama** — connects to host machine's existing Ollama via `host.docker.internal:11434`
- `ENABLE_OPENAI_API=false` — disables all outbound cloud API calls (OpenAI, Anthropic, etc.)
- `DEFAULT_MODELS=hermes3:latest` — overridable via `.env`
- Port bound to `127.0.0.1:3000` only — not exposed to LAN
- `no-new-privileges:true` security option
- Healthcheck on `/health` endpoint
- All telemetry disabled (`SCARF_NO_ANALYTICS`, `DO_NOT_TRACK`, `ANONYMIZED_TELEMETRY`)

### Enabling Anthropic / Cloud APIs
Commented out in `.env.example`. To enable, add to `.env`:
```env
ENABLE_OPENAI_API=true
OPENAI_API_KEY=your-key
OPENAI_API_BASE_URL=https://api.openai.com/v1
```

## Setup (First Run)

```bash
# 1. Pull the Hermes model into your Ollama instance
ollama pull hermes3

# 2. Create your .env
cp .env.example .env
# Fill in WEBUI_SECRET_KEY:
openssl rand -hex 32   # paste output into .env

# 3. Start
docker compose up -d

# 4. Open
# http://localhost:3000
```

## Hermes Model Variants (Ollama)
```bash
ollama pull hermes3          # 8B, default
ollama pull hermes3:70b      # 70B
ollama pull nous-hermes2     # Hermes 2, Mistral base
ollama pull nous-hermes2:34b
```
Change `DEFAULT_MODELS=` in `.env` to switch.

## Git State
- **Repo:** `ArcBeard/rss-screensaver`
- **Branch:** `claude/docker-ollama-hermes-compose-EmA34`
- **Commit:** `5197a4c` — "Add Hermes digital assistant Docker Compose setup"

## Intended Next Steps (per user)
- Expand into a full personal digital assistant
- Possibly add memory, tools, or additional services to the compose stack

## Sources Referenced
- Open WebUI official compose: `github.com/open-webui/open-webui/blob/main/docker-compose.yaml`
- Open WebUI config source: `backend/open_webui/config.py` — confirmed `ENABLE_OPENAI_API` (default `true`), `ENABLE_OLLAMA_API` (default `true`), `DEFAULT_MODELS` (default `null`)
- Ollama Docker Hub: `hub.docker.com/r/ollama/ollama`
