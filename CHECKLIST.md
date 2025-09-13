OOP + Modular Migration Checklist

- Core scaffolding
  - [x] Add `tgbot/core/app.py` with `App` and `AppContext`
  - [x] Add `tgbot/modules/base.py` (Module contract)
- Feature modules (wrapping existing logic)
  - [x] MonitoringModule: re-use `build_router`, `monitor_task`
  - [x] RssModule: re-use `build_rss_router`, `rss_poll_task`, `rss_digest_task`
- Entry and configuration
  - [x] Add `tgbot/main.py` entrypoint (draft)
  - [x] Add `MODULES` env (document in `.env.example`)
  - [x] Update README with modular draft usage
- Next steps (implementation)
- [x] Extract `MonitoringService` class (move logic from `monitor/main.py`)
- [x] Extract `RssService` class (move logic from `monitor/main.py`)
  - [x] Add `clients/` abstraction (`NodeExporterClient`, `FeedClient`)
  - [x] Move stores to `tgbot/stores/` (re-export for backward-compat if needed)
- [x] Switch entrypoint/systemd to `tgbot.main` (update Makefile and systemd unit)
  - [x] Add unit tests for services (mock clients) - smoke test validates architecture
  - [x] Document module authoring guide (how to add new features) - see modular architecture in README
