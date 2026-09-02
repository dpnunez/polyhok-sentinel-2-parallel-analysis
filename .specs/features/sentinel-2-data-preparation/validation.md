# Sentinel-2 Data Preparation Validation

## Validation: Sentinel-2 Data Preparation - PASS ✅

**Verdict**: PASS ✅
**Round**: independent re-verification 2 after `c305714` and `9262139`
**Date**: 2026-08-20
**Spec**: `.specs/features/sentinel-2-data-preparation/spec.md`
**Diff range**: `233b81a..9262139`
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1–T15 | ✅ Done | Todos os itens de `tasks.md` estão concluídos; os 15 commits de implementação e os dois commits de correção existem no diff. |
| Fix ORCH-10 | ✅ Done | `c305714` adiciona cobertura dos quatro resultados terminais. |
| Fix SAFE-07 | ✅ Done | `9262139` torna a política completa de versionamento e ignore executável. |

## Spec-Anchored Acceptance Criteria

| Criterion | Spec-defined outcome | `file:line` + assertion expression | Result |
| --------- | -------------------- | ---------------------------------- | ------ |
| PREP-01 | Descobrir exatamente B04/B08 10 m e os dois XML do mesmo produto/tile | `python/tests/test_metadata.py:42` — `assert product.product_id == ...`; `:47-50` — caminhos exatos; `:94` — granules diferentes geram `MetadataError` | ✅ PASS |
| PREP-02 | Qualquer divergência de largura, altura, CRS, origem, pixel ou extensão falha | `python/tests/test_raster.py:91-126` — casos parametrizados exigem `RasterError` com o campo divergente | ✅ PASS |
| PREP-03 | Recortes centrais 1024/4096/8192 usam a fórmula definida | `python/tests/test_raster.py:129-136` — offsets `4978`, `3442`, `1394` e dimensões exatas | ✅ PASS |
| PREP-04 | B04 e B08 usam a mesma janela | `python/tests/test_raster.py:180` — `assert b04.read_windows[0] is b08.read_windows[0]` | ✅ PASS |
| PREP-05 | Conversão exata por banda em float32 | `python/tests/test_raster.py:168-179` — valores esperados de B04/B08 e dtype `<f4` | ✅ PASS |
| PREP-06 | NODATA/SATURATED em qualquer banda vira NaN nas duas | `python/tests/test_raster.py:168-177` — matrizes esperadas têm NaN compartilhado para ambas as causas | ✅ PASS |
| PREP-07 | Grade de 10 m preservada, sem clipping ou operação fora do escopo | `python/tests/test_raster.py:180-181` — janela/offsets preservados; `:193-194` — valores `-0.05` e `1.1` não limitados | ✅ PASS |
| PREP-08 | Binário `<f4`, row-major, sem cabeçalho e com bytes exatos | `python/tests/test_artifacts.py:77-81` — tamanho e primeiros bytes C-order exatos | ✅ PASS |
| PREP-09 | Metadata contém todos os campos mínimos, paths relativos e checksums | `python/tests/test_artifacts.py:89-134` — conjunto de campos, valores, paths e SHA-256 exatos | ✅ PASS |
| PREP-10 | Preview lado a lado, escala independente, NaN preto e máximo 2048x1024 | `python/tests/test_artifacts.py:150-165` — forma, pixels pretos/brancos e dimensão máxima exatos | ✅ PASS |
| PREP-11 | Releitura valida contrato, tamanho e checksums antes do sucesso | `python/tests/test_artifacts.py:168-209` — metadata exata; contrato, tamanho e checksum inválidos falham | ✅ PASS |
| PREP-12 | Três recortes publicados e manifesto atualizado por último | `python/tests/test_pipeline.py:103-117` — três crops validados e último `os.replace` é `manifest.json` | ✅ PASS |
| PREP-13 | Grade insuficiente falha antes de ler/publicar | `python/tests/test_raster.py:197-207` — `RasterError` e listas de leitura vazias | ✅ PASS |
| PREP-14 | Sucesso Python retorna 0 e diagnóstico identifica scene-id | `python/tests/test_cli.py:44-50` — status `0`, JSON exato e stderr vazio | ✅ PASS |
| ORCH-01 | Executável e entrypoint usam argumentos separados, sem shell | `test/integration/preparation_worker_test.exs:31-39` — paths com espaços chegam como argumentos separados | ✅ PASS |
| ORCH-02 | Chamada aguarda sem bloquear outros processos BEAM | `test/integration/preparation_test.exs:30-44` — processo externo pendente e ticker não relacionado executa | ✅ PASS |
| ORCH-03 | Resultado só é decidido após exit status | `test/integration/preparation_worker_test.exs:24-28` — saída parcial/final retorna somente com status 7 | ✅ PASS |
| ORCH-04 | Status não zero retorna erro, nunca sucesso | `test/integration/preparation_worker_test.exs:24-28` — retorno exato `{:error, {:process_failed, 7, "partialdone"}}` | ✅ PASS |
| ORCH-05 | Status 0 exige manifesto, metadados e seis binários válidos | `test/integration/python_elixir_contract_test.exs:43-49` — zero sem artefatos falha; contrato completo retorna três crops | ✅ PASS |
| ORCH-06 | Falha de validação após status 0 retorna erro | `test/integration/preparation_worker_test.exs:67-73` — retorno exato `{:error, :invalid_manifest}` | ✅ PASS |
| ORCH-07 | Sucesso retorna scene-id, paths e três metadados | `test/sentinel_2/artifact_validator_test.exs:15-21` — identidade, checksum, tamanhos e paths do descriptor | ✅ PASS |
| ORCH-08 | Timeout retorna exatamente `{:error, :timeout}` | `test/integration/preparation_worker_test.exs:76-80` — retorno exato | ✅ PASS |
| ORCH-09 | Worker é separado e supervisionado | `test/sentinel_2/application_test.exs:11-15` — DynamicSupervisor ativo; `test/integration/python_elixir_contract_test.exs:118-127` — PID registrado permanece vivo | ✅ PASS |
| ORCH-10 | Sucesso, falha de processo, falha de validação e timeout geram um log terminal com scene-id, duração, resultado e diagnóstico limitado, sem matriz | `test/integration/preparation_worker_test.exs:94-107` — falha de processo e limite; `:110-126` — sucesso e ausência da matriz; `:129-145` — falha de validação; `:148-162` — timeout; todos afirmam registro terminal e campos exigidos | ✅ PASS |
| ORCH-11 | API pública expõe somente tagged tuples | `test/integration/preparation_test.exs:7-25`, `:47-75` — sucesso, falha, duplicidade, timeout e entrada inválida retornam tuples exatas | ✅ PASS |
| READ-01 | Paths relativos resolvem sob a raiz configurada | `test/sentinel_2/prepared_reader_test.exs:6-16` — leitura na fixture root; `:35-39` — escape rejeitado | ✅ PASS |
| READ-02 | Bytes little-endian row-major viram float32 na forma declarada | `test/sentinel_2/prepared_reader_test.exs:10-16` — tipo, forma e ordem de valores exatos | ✅ PASS |
| READ-03 | Byte count divergente retorna `:invalid_byte_size` antes do tensor | `test/sentinel_2/prepared_reader_test.exs:28-32` — erro exato | ✅ PASS |
| READ-04 | B04/B08 têm forma idêntica e NaNs preservados | `test/sentinel_2/prepared_reader_test.exs:19-25` — listas exatas com NaN na mesma posição | ✅ PASS |
| READ-05 | Processo externo transporta só argumentos/status/diagnóstico; dados ficam no filesystem | `test/integration/python_elixir_contract_test.exs:10-26` — Python grava e Elixir lê valores/NaN; `python/tests/test_cli.py:45-49` — diagnóstico não contém matrizes | ✅ PASS |
| SAFE-01 | Novas saídas usam `.partial` no filesystem de destino | `python/tests/test_pipeline.py:120-139` — três destinos sob `prepared.partial`, removido após sucesso | ✅ PASS |
| SAFE-02 | Artefatos validados são promovidos por rename atômico antes do manifesto | `python/tests/test_pipeline.py:97-117` — replaces observados, crops validados e manifesto por último | ✅ PASS |
| SAFE-03 | Interrupção não publica cena e temporários não são lidos | `python/tests/test_pipeline.py:142-173` — falha mantém manifesto ausente e stage órfão; `test/integration/python_elixir_contract_test.exs:52-57` — processo interrompido sem manifesto | ✅ PASS |
| SAFE-04 | Saída íntegra é reutilizada sem tocar seis binários | `python/tests/test_pipeline.py:176-196` — `reused is True` e seis mtimes idênticos; integração em `test/integration/python_elixir_contract_test.exs:59-68` | ✅ PASS |
| SAFE-05 | Fonte/checksum divergente força regeneração | `python/tests/test_pipeline.py:199-239` — corrupção e identidade alterada executam os três tamanhos novamente | ✅ PASS |
| SAFE-06 | Segunda solicitação ativa da mesma scene-id retorna `:already_running` | `test/integration/python_elixir_contract_test.exs:71-83` — segundo retorno exato e primeiro segue ativo | ✅ PASS |
| SAFE-07 | Código, testes, manifesto e metadados permanecem versionáveis; `.SAFE`, JP2/TIFF, `.f32`, previews, venv e temporários são ignorados | `python/tests/test_package.py:38-71` — venv e todos os padrões gerados via `git check-ignore`; `:74-95` — arquivos obrigatórios rastreados e metadata/source JSON não ignorados; `:98-102` — nenhum artefato gerado rastreado | ✅ PASS |
| EDGE-01 | Arquivo obrigatório ausente ou ambíguo falha | `python/tests/test_metadata.py:59-84` — ausências parametrizadas e B04 duplicada geram `MetadataError` | ✅ PASS |
| EDGE-02 | Offset/quantificação ausente ou inválido falha antes da conversão | `python/tests/test_metadata.py:98-127` — casos radiométricos exigem `MetadataError` específico | ✅ PASS |
| EDGE-03 | Interpretador ou entrypoint ausente retorna `:executable_not_found` | `test/integration/preparation_worker_test.exs:10-21` — ambos os casos retornam o erro exato | ✅ PASS |
| EDGE-04 | Falta de espaço/permissão retorna erro e não publica manifesto | `python/tests/test_cli.py:58-89` — espaço/permissão retornam status 1; `python/tests/test_pipeline.py:270-287` — manifesto permanece ausente | ✅ PASS |
| EDGE-05 | Metadata ou binário inválido falha sem construir matriz | `test/sentinel_2/artifact_validator_test.exs:24-95` — JSON, campos, paths, presença, tamanho, checksum e fonte inválidos falham; `test/sentinel_2/prepared_reader_test.exs:28-32` — tamanho rejeitado antes do tensor | ✅ PASS |
| EDGE-06 | Timeout permanece erro após mensagens tardias; reutilização exige validação | `test/integration/preparation_worker_test.exs:83-91` — timeout, término normal e ausência de segundo resultado; `test/integration/python_elixir_contract_test.exs:43-49` — status 0 só é aceito após validação | ✅ PASS |

**Status**: ✅ 43/43 critérios possuem evidência `file:line` e as asserções correspondem ao resultado definido na spec. Zero gaps de precisão.

## Discrimination Sensor

O `git worktree add` foi tentado, mas o sandbox bloqueou escrita em `.git/worktrees`. O fallback copiou o repositório para `/tmp/sentinel2-reverify2.CrJpvH/repo`, sem venv, deps ou build, e executou os runners contra a cópia. O scratch e seu build foram removidos ao final.

| Mutation | File:line | Description | Killed? |
| -------- | --------- | ----------- | ------- |
| 1 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/preparation_worker.ex:91-94` | Substituir todo diagnóstico terminal por string vazia | ✅ Killed: 3 falhas em `test/integration/preparation_worker_test.exs:125`, `:144`, `:161` |
| 2 | `.gitignore:34` | Remover a regra que ignora matrizes `.f32` | ✅ Killed: 1 falha em `python/tests/test_package.py:70` para `b04.f32` |

**Sensor depth**: lightweight, 2 mutações direcionadas aos gaps corrigidos
**Sensor outcome**: 2/2 killed — PASS ✅
**Isolation**: o status real foi exatamente `?? .specs/LESSONS.md`, `?? .specs/features/sentinel-2-data-preparation/validation.md`, `?? .specs/lessons.json` antes e depois do sensor. `cmp` confirmou igualdade byte a byte do `git status --porcelain=v1`.

## Code Quality

| Principle | Status |
| --------- | ------ |
| No features beyond requested scope | ✅ |
| No unnecessary single-use abstractions or flexibility | ✅ |
| Surgical diff; unrelated code preserved | ✅ |
| Matches project language and style | ✅ |
| Spec-anchored asserted outcomes | ✅ 43/43 |
| Per-layer coverage expectation | ✅ Domain 1:1; integration covers success, edge and error paths |
| Every in-scope test is claimed by AC, edge case or done-when | ✅ |
| Test integrity | ✅ Nenhuma asserção removida ou enfraquecida; correções somente adicionam cobertura |
| Senior-engineer quality bar | ✅ |
| Documented guidelines | ✅ `.codex/skills/tlc-spec-driven/references/coding-principles.md:1`; matriz em `.specs/features/sentinel-2-data-preparation/tasks.md:10` |

## Edge Cases

- [x] EDGE-01 a EDGE-06 têm resultados exatos e evidência `file:line`.
- [x] Paths fora da raiz, JSON inválido, arquivos ausentes, tamanho/checksum inválido e fonte stale são rejeitados.
- [x] O teste CUDA preserva as asserções originais e é a única exclusão, por perfil explícito `:gpu`.

## Gate Check

- **Gate command**: `python/.venv/bin/python -m ruff check python && python/.venv/bin/python -m pytest python/tests -q && mix format --check-formatted && mix compile --warnings-as-errors && mix test --exclude gpu`
- **Result**: 119 passed, 0 failed, 0 skipped; 1 ExUnit test excluded por `:gpu`
- **Breakdown**: Ruff limpo; 74/74 pytest; format limpo; compile sem warnings; 45/45 ExUnit CPU
- **Test count before feature (`233b81a`)**: 0 Python; 3 ExUnit totais, sendo 2 CPU e 1 CUDA
- **Test count after feature**: 74 Python; 46 ExUnit totais, sendo 45 CPU e 1 CUDA
- **Delta**: +117 casos totais; nenhum teste removido
- **Excluded test**: `test/poly_hok_test.exs:5`, GPU opt-in conforme T2; as asserções originais permanecem em `:12-14`
- **Failures**: none

## Requirement Traceability Update

`spec.md` foi atualizado nesta rodada: PREP-01–PREP-14, ORCH-01–ORCH-11, READ-01–READ-05, SAFE-01–SAFE-07 e EDGE-01–EDGE-06 passaram de `Implemented` para `✅ Verified`.

## Lessons

Esta rodada não encontrou AC sem cobertura, gap de precisão, mutante sobrevivente ou `SPEC_DEVIATION`. Nenhuma lesson nova foi registrada.

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 43/43 ACs matched the specified outcome; 0 spec-precision gaps.
**Sensor**: 2/2 mutations killed.
**Gate**: 119 passed, 0 failed; 1 justified GPU exclusion.

**What works**: produtor Python, publicação transacional, CLI, validação Elixir, leitura Nx, worker supervisionado, logging terminal completo, concorrência por scene-id, política de artefatos e contrato cruzado.

**Issues found**: none.

**Next steps**: feature pronta para integração.
