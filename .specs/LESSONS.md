# LESSONS - auto-maintained by scripts/lessons.py

> Machine-owned. Do NOT hand-edit. Changes are overwritten on the next `lessons.py` write.
> Canonical state lives in `.specs/lessons.json`. Edit lessons only via the script.
> promote_threshold=2 distinct features · window_days=45 · quarantine_threshold=2

## Confirmed (load these at Specify/Design)

Corroborated across multiple features. Safe to apply as guidance.

_none_

## Candidates (under observation - do NOT load as guidance yet)

Seen once or not yet corroborated. Tracked, not trusted.

### L-001 - Assert every required terminal outcome for observability contracts, not only one representative result
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `sentinel-2/orchestration` · harmful: 0
- features: sentinel-2-data-preparation
- evidence: .specs/features/sentinel-2-data-preparation/validation.md:44 (sentinel-2/orchestration)
- last seen: 2026-08-21T00:53:24Z

### L-002 - Test every required repository ignore and tracking rule as an executable contract
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `repository/configuration` · harmful: 0
- features: sentinel-2-data-preparation
- evidence: .specs/features/sentinel-2-data-preparation/validation.md:57 (repository/configuration)
- last seen: 2026-08-21T00:53:25Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
