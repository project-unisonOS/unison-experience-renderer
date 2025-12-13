# unison-experience-renderer

Presence-first renderer surface and envelope stream for UnisonOS. It hosts a single perceptual field and proxies a small set of capability and I/O endpoints (wake word, speech proxy, capability manifest).

## Status
Core service (active) — part of devstack, exposed on `8092`.

## Run
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
cp .env.example .env
uvicorn main:app --app-dir src --host 0.0.0.0 --port 8092
```
Environment knobs: `ORCHESTRATOR_BASE_URL`, `CONTEXT_BASE_URL`, `SPEECH_BASE_URL`, `UNISON_WAKEWORD_DEFAULT`, `DISABLE_AUTH_FOR_TESTS`, etc. See code comments for defaults.

## Testing
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OTEL_SDK_DISABLED=true python -m pytest
```

## Integration
- Consumes capability manifest from orchestrator.
- Reads wakeword/profile data from `unison-context`.
- Exposed through devstack and consumed by surfaces that can subscribe to SSE.
- Accepts intent/event envelopes via `POST /events` and streams them via `GET /events/stream`.

## Docs

Full docs at https://project-unisonos.github.io
Local docs:
- `ANTI_PATTERN_MAP.md`
- `ARCHITECTURE.md`
- `MOTION_GUIDE.md`
- `ACCESSIBILITY.md`
- `MIGRATION_NOTES.md`
