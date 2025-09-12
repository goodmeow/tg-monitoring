Migration Plan: Procedural -> OOP + Modular

Goals
- Preserve current behavior while enabling a modular, testable architecture.
- Migrate incrementally without breaking deployments.

Phase 1 — Scaffolding (done)
- Add `tgbot/core/app.py` (App + AppContext)
- Add `tgbot/modules/base.py` (Module contract)
- Add Monitoring and RSS modules that simply wrap existing functions from `monitor/main.py`.
- Add `tgbot/main.py` entrypoint (draft) and `MODULES` env in `.env.example`.

Phase 2 — Extract Services
- Create `tgbot/services/monitoring_service.py` to host monitoring logic (router + loop).
- Create `tgbot/services/rss_service.py` to host RSS logic (router + poll + digest).
- Adjust modules to use the services rather than `monitor/main.py`.

Phase 3 — Clients and Stores
- Introduce `tgbot/clients/node_exporter.py` (HTTP + parse) and `tgbot/clients/feed_client.py` (wrap feedparser).
- Move stores to `tgbot/stores/` (re-export or alias to keep imports working during transition).

Phase 4 — EntryPoint Switch
- Provide a feature flag or direct switch to run `python -m tgbot.main` in systemd.
- Keep `monitor/main.py` as a thin compatibility entrypoint for one release.

Phase 5 — Cleanup & Docs
- Remove deprecated paths and update README.
- Document how to create a new module (Module contract, routers, tasks, config).

Testing Strategy
- Unit test services with mocked clients (no network).
- Smoke test App startup with monitoring+rss modules enabled.

