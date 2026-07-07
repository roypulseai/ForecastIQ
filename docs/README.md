# ForecastIQ Documentation

## For users

- **[../README.md](../README.md)** — main readme, quick start
- **[DATA_FORMAT.md](DATA_FORMAT.md)** — CSV column formats for each file type
- **[MODELS.md](MODELS.md)** — model registry, train/save/load workflow
- **[API_KEYS.md](API_KEYS.md)** — managing API keys

## For integrators

- **[API.md](API.md)** — full HTTP API reference (programmatic, versioned, /v1/*)
- Interactive docs at `http://<your-host>/docs` (Swagger UI)
- OpenAPI spec at `http://<your-host>/openapi.json`

## Surfaces at a glance

| Surface | Path | Auth | Use case |
| --- | --- | --- | --- |
| UI (browser) | `/api/v1/*` | None (browser session) | Frontend ↔ backend |
| Public API | `/v1/*` | API key (`Authorization: Bearer ...`) | Notebooks, scripts, other tools |
| Interactive docs | `/docs`, `/redoc` | None | Browse the API |
| Static assets | `/templates/*` | None | Download CSV templates |
| Health check | `/api/v1/health` | None | Liveness probe |
