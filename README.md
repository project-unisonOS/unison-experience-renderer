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

## Synthetic health export candidate

The optional `/static/health-export.html` experience supports choosing a synthetic
JSON export, consent before upload, source-linked fact review, a descriptive summary,
and revoke/delete/backup/restore controls. It uses the existing signed session in
session storage and requires the storage audience and narrowly scoped workflow
permissions. It does not provision identities or grant itself authority.

The API is disabled unless `UNISON_SYNTHETIC_HEALTH_WORKFLOW=true`. The configured
`UNISON_HEALTH_WORKFLOW_STORAGE_URL` must be a literal loopback HTTP origin. This is
a bounded test topology, not a remote transport or operational deployment claim.

The workspace browser test covers the actual controls with signed identities,
encrypted temporary storage, mobile/desktop widths, forced colors, enlarged text,
keyboard use and source links. Renderer-to-storage transport is in-process in that
test. Native conversational/Braille composition and participatory accessibility
qualification remain open. No health content is retained in browser web storage;
opaque workflow/snapshot IDs are retained within the current session only.
