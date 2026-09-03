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

### L-003 - Exercite separadamente classes IEEE nomeadas explicitamente no contrato
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `ndvi` · harmful: 0
- features: ndvi-polyhok-prototype
- evidence: validation.md:NDVI-06 (ndvi)
- last seen: 2026-09-03T12:17:35Z

### L-004 - Para provar ausência de clamp, use um resultado esperado fora do intervalo de clamp
- signal: `ac_gap` · recurrence: 1 feature(s) · scope: `ndvi` · harmful: 0
- features: ndvi-polyhok-prototype
- evidence: validation.md:NDVI-08 (ndvi)
- last seen: 2026-09-03T12:17:35Z

### L-005 - Teste publicação metadata-last com uma falha induzida entre os dois pontos de promoção
- signal: `surviving_mutant` · recurrence: 1 feature(s) · scope: `persistence` · harmful: 0
- features: ndvi-polyhok-prototype
- evidence: validation.md:M3 (persistence)
- last seen: 2026-09-03T12:17:35Z

### L-006 - Inicialize explicitamente metadata JIT efêmera antes de executar kernels PolyHok em aplicações Mix compiladas
- signal: `spec_deviation` · recurrence: 1 feature(s) · scope: `polyhok` · harmful: 0
- features: ndvi-polyhok-prototype
- evidence: lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:42 (polyhok)
- last seen: 2026-09-03T12:17:35Z

## Quarantined (failed when applied - ignore)

A confirmed lesson that recurred alongside failure. Kept for the maintainer to review.

_none_
