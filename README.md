# unison-experience-renderer

Experience/UI renderer that proxies capabilities between intent graph, orchestrator, context, and I/O surfaces (wakeword, speech proxy, capability manifest).

## Status
Core service (active) — part of devstack, exposed on `8092`.

## Run
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -c ../constraints.txt -r requirements.txt
cp .env.example .env
python src/main.py
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
- Exposed through devstack and consumed by `unison-agent-vdi` or browser clients.

## Docs

Full docs at https://project-unisonos.github.io
