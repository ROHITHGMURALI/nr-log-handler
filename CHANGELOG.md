# Changelog

## 0.1.1 (2026-03-29)

- Fixed deprecated `license` table format in `pyproject.toml` (now uses SPDX string)
- Removed redundant `License` classifier
- Added `LICENSE` file (MIT)
- Added GitHub Actions workflow to publish to PyPI on merge to `main`

## 0.1.0 (2026-03-26)

- Initial release
- `NewRelicHandler`: drop-in `logging.Handler` for New Relic Log API
- `NewRelicLogger`: standalone convenience logger
- Sync and async (batched) modes
- US and EU region support
- Exponential backoff retry with silent drop
- Global and per-call custom attributes
