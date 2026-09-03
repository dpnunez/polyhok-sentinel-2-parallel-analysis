# Validation: ndvi-polyhok-prototype - FAIL ❌

**Date**: 2026-09-03  
**Spec**: `.specs/features/ndvi-polyhok-prototype/spec.md`  
**Diff range**: `b695cd8^..2efaf53`  
**Verifier**: independent sub-agent (author ≠ verifier)

---

## Task Completion

| Task | Status | Notes |
| ---- | ------ | ----- |
| T1 | ✅ Done | Implementação e checklist concluídos; o gate GPU passa. Há gaps de discriminação em NDVI-06 e NDVI-08. |
| T2 | ✅ Done | Implementação e checklist concluídos; a mutação de ordem de publicação sobreviveu para NDVI-25. |

Nenhuma tarefa está marcada como parcial ou bloqueada em `tasks.md`.

## Spec-Anchored Acceptance Criteria

| Criterion | Spec-defined outcome | `file:line` + assertion/evidence | Status |
| --------- | -------------------- | -------------------------------- | ------ |
| NDVI-01 | Duas entradas Nx 2D, não vazias, `f32` e de mesma forma são transferidas H2D. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:18` — `{PolyHok.new_gnx(b04), PolyHok.new_gnx(b08)}`; execução válida em `test/sentinel_2/ndvi_test.exs:77`. | ✅ PASS |
| NDVI-02 | Uma única chamada de kernel produz toda a matriz. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:24` — única ocorrência de `Ske.map2/3`; os seis pixels são validados em `test/sentinel_2/ndvi_test.exs:78-87`. | ✅ PASS |
| NDVI-03 | Cada thread escreve no máximo uma posição linear válida. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:47-53` — `if id < size` e uma atribuição `a3[id]`; matriz de seis posições exercitada em `test/sentinel_2/ndvi_test.exs:74-87`. | ✅ PASS |
| NDVI-04 | Para dados finitos e denominador não nulo, escreve `(B08-B04)/(B08+B04)` em `f32`. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:31`; `test/sentinel_2/ndvi_test.exs:82-84` — `assert_in_delta` para `0.5`, `0.0` e `-0.5`. | ✅ PASS |
| NDVI-05 | `NaN` em qualquer banda produz `NaN` na mesma posição. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28-29`; `test/sentinel_2/ndvi_test.exs:86-87` — `assert nan_b04 == :nan` e `assert nan_b08 == :nan`. | ✅ PASS |
| NDVI-06 | Denominador exatamente `+0.0f` ou `-0.0f` produz `NaN`. | `test/sentinel_2/ndvi_test.exs:85` cobre cancelamento que resulta em zero, mas não apresenta um caso explícito de denominador `-0.0f`. A comparação de fonte em `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:28` é correta, porém não existe asserção para os dois resultados definidos pela spec. | ❌ GAP |
| NDVI-07 | Todo denominador diferente de zero é dividido sem epsilon. | `test/sentinel_2/ndvi_test.exs:92-98` — o menor subnormal positivo `f32` retorna exatamente `[1.0]`. | ✅ PASS |
| NDVI-08 | Nenhuma posição sofre clamp, máscara temática, classificação ou transformação geoespacial. | `test/sentinel_2/ndvi_test.exs:84` verifica `-0.5`, valor que continuaria igual sob clamp `[-1, 1]`. A fonte em `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:27-35` não contém essas operações, mas falta uma asserção capaz de rejeitar clamp. | ❌ GAP |
| NDVI-09 | O resultado é transferido D2H exatamente uma vez após o kernel. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:12-14` — uma chamada a `to_host/1` após `run_kernel/2`; resultado host observado em `test/sentinel_2/ndvi_test.exs:78-87`. | ✅ PASS |
| NDVI-10 | Retorna diretamente tensor Nx `f32`, mesma forma e ordem linear. | `test/sentinel_2/ndvi_test.exs:78-87` — destructuring linear, `Nx.type(result) == {:f, 32}`, `Nx.shape(result) == {2, 3}` e seis posições exatas. | ✅ PASS |
| NDVI-11 | Entrada não Nx levanta `ArgumentError` antes do PolyHok. | `test/sentinel_2/ndvi_test.exs:10-16` — `assert_raise ArgumentError` para B04 e B08; validação antecede H2D em `ndvi.ex:8-10`. | ✅ PASS |
| NDVI-12 | Entrada não `f32` levanta `ArgumentError` antes do PolyHok. | `test/sentinel_2/ndvi_test.exs:23-29` — `assert_raise ArgumentError` para B04 e B08. | ✅ PASS |
| NDVI-13 | Rank diferente de dois ou dimensão zero levanta `ArgumentError` antes do PolyHok. | `test/sentinel_2/ndvi_test.exs:36-42` e `test/sentinel_2/ndvi_test.exs:49-55` — `assert_raise ArgumentError` para ambas as bandas. | ✅ PASS |
| NDVI-14 | Formas divergentes levantam `ArgumentError` antes do PolyHok. | `test/sentinel_2/ndvi_test.exs:62-64` — `assert_raise ArgumentError` com mensagem de mesma forma. | ✅ PASS |
| NDVI-15 | Falha nativa é propagada sem tensor parcial de sucesso. | `test/sentinel_2/ndvi_test.exs:68-70` — `assert_raise FunctionClauseError` na fronteira pública D2H; `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:7-15` não captura nem converte falhas. | ✅ PASS |
| NDVI-16 | H2D, kernel e D2H permanecem operações públicas separadas. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:18`, `:21` e `:40` — `to_device/2`, `run_kernel/2` e `to_host/1` são funções públicas distintas. | ✅ PASS |
| NDVI-17 | Preparação fica fora da operação de cálculo. | `test/sentinel_2/ndvi_test.exs:74-77` — constrói tensores diretamente e chama `Ndvi.compute/2`; `ndvi.ex:1-91` não referencia preparação. | ✅ PASS |
| NDVI-18 | A API compõe H2D → kernel → D2H, sem NDVI CPU. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:10-14` — ordem explícita; `test/sentinel_2/ndvi_test.exs:77-87` valida a composição GPU. | ✅ PASS |
| NDVI-19 | B04 igual a B08 produz `0.0f`. | `test/sentinel_2/ndvi_test.exs:83` — `assert_in_delta zero, 0.0, 1.0e-6`. | ✅ PASS |
| NDVI-20 | B04 maior que B08 preserva resultado negativo. | `test/sentinel_2/ndvi_test.exs:84` — `assert_in_delta negative, -0.5, 1.0e-6`. | ✅ PASS |
| NDVI-21 | Menor `f32` não nulo é dividido normalmente. | `test/sentinel_2/ndvi_test.exs:92-98` — menor subnormal construído por bits e resultado `[1.0]`. | ✅ PASS |
| NDVI-22 | Threads excedentes não leem nem escrevem posições. | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:48-52` — bounds check; `test/sentinel_2/ndvi_test.exs:74-87` usa seis elementos, não múltiplo do bloco 256, e valida todas as posições. | ✅ PASS |
| NDVI-23 | Binário `f32` little-endian row-major, sem cabeçalho, com `height*width*4` bytes. | `test/sentinel_2/ndvi_result_writer_test.exs:17-22` — tamanho 24 e bytes literais little-endian na ordem esperada. | ✅ PASS |
| NDVI-24 | Metadata contém dimensões, tipo, endianidade, ordem, nome e SHA-256. | `test/sentinel_2/ndvi_result_writer_test.exs:24-34` — igualdade do mapa completo e do JSON relido. | ✅ PASS |
| NDVI-25 | `metadata.json` é substituído por último e representa o commit point. | A ordem implementada está correta em `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:34-36`, mas `test/sentinel_2/ndvi_result_writer_test.exs:34` observa apenas o estado final. O mutante M3 publicou metadata antes do binário e os três testes continuaram verdes. | ❌ GAP |
| NDVI-26 | Falha de escrita/validação retorna erro sem metadata final válido. | `test/sentinel_2/ndvi_result_writer_test.exs:64-67` — `assert {:error, :eisdir}` e `refute File.exists?(.../metadata.json)`. | ✅ PASS |
| NDVI-27 | Persistência é explícita e separada do fluxo GPU. | `test/sentinel_2/ndvi_result_writer_test.exs:11` chama `ResultWriter.write/2` diretamente; `result_writer.ex:1-77` não referencia PolyHok nem `Ndvi.compute/2`. | ✅ PASS |

**Coverage**: 24/27 critérios têm evidência compatível com o resultado normativo; NDVI-06, NDVI-08 e NDVI-25 têm gaps. A spec define resultados precisos para todos os critérios, portanto há 0 spec-precision gaps.

## Edge Cases

- [x] NDVI-19: igualdade produz `0.0f`.
- [x] NDVI-20: resultado negativo é preservado.
- [x] NDVI-21: menor subnormal `f32` não recebe tratamento por epsilon.
- [x] NDVI-22: tamanho seis, não múltiplo do bloco, preserva as seis posições.

O caso de `-0.0f` pertence a NDVI-06 e permanece sem evidência específica.

## Gate Check

- **Gate command**: `python/.venv/bin/python -m ruff check python && python/.venv/bin/python -m pytest python/tests -q && mix format --check-formatted && mix compile --warnings-as-errors && mix test --exclude gpu && mix test --include gpu test/sentinel_2/ndvi_test.exs`
- **Final run**: PASS fora do sandbox, exit 0.
- **Ruff**: pass.
- **Python**: 74 passed, 0 failed, 0 skipped.
- **Elixir CPU stage**: 56 discovered, 53 executed, 0 failed, 3 excluded by `:gpu`.
- **Elixir targeted CUDA stage**: 8 executed, 0 failed. Esse comando inclui os seis testes não GPU do arquivo e os dois testes NDVI marcados `:gpu`.
- **Excluded in CPU stage**: `test/poly_hok_test.exs:5` (smoke GPU legado, fora do gate CUDA específico da feature), `test/sentinel_2/ndvi_test.exs:73` e `test/sentinel_2/ndvi_test.exs:91` (ambos executados no estágio CUDA).
- **Sandbox note**: a primeira etapa CUDA no sandbox encerrou com exit 139; a repetição do gate integral com acesso à GPU terminou com exit 0.
- **Test count before feature (`35f20db`)**: 45 discovered, 44 executed, 0 failed, 1 GPU excluded.
- **Test count after feature (`2efaf53`)**: 56 discovered, 53 executed no estágio CPU, 0 failed, 3 GPU excluded.
- **Delta**: +11 testes totais, dos quais 9 não GPU e 2 GPU. Nenhum teste anterior foi removido ou teve asserção enfraquecida no diff.

## Discrimination Sensor

| Mutation | File:line | Description | Outcome |
| -------- | --------- | ----------- | ------- |
| M1 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:31` | Trocou o numerador `(b08 - b04)` por `(b08 + b04)`. | ✅ Killed: `test/sentinel_2/ndvi_test.exs:82` falhou, 8 tests / 1 failure. |
| M2 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:72` | Trocou metadata `order: row-major` por `column-major`. | ✅ Killed: `test/sentinel_2/ndvi_result_writer_test.exs:24` falhou, 3 tests / 1 failure. |
| M3 | `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex:34-36` | Moveu a promoção de `metadata.json` para antes da promoção do binário. | ❌ Survived: 3 tests / 0 failures. |

**Sensor depth**: lightweight, três mutações representativas.  
**Sensor score**: 2/3 killed. FAIL.

O sensor usou dois worktrees temporários e não usou `git stash`. O porcelain real antes e depois da limpeza foi idêntico: ` M .notebook/poly-hok-integration.md`. Essa modificação preexistente não pertence à feature nem foi tocada.

## Code Quality

| Principle | Status | Evidence |
| --------- | ------ | -------- |
| Minimum code | ✅ | Dois módulos específicos; nenhuma infraestrutura genérica. |
| Surgical changes | ✅ | O diff funcional adiciona apenas cálculo, writer e testes correspondentes. |
| No scope creep | ✅ | Sem CPU NDVI, benchmark, métricas ou produtos derivados. |
| Matches patterns | ✅ | Nx, ExUnit, tag `:gpu`, Jason e publicação `.partial` seguem os padrões existentes. |
| Would a senior engineer approve now? | ❌ | O sensor de NDVI-25 sobrevive e dois resultados explícitos não têm testes discriminatórios. |
| Tests map to requirements or Done-when | ✅ | Os testes novos mapeiam a NDVI-01..27 ou aos critérios de entrada inválida dos tasks. |
| Spec-anchored outcome check | ❌ | 24/27; gaps em NDVI-06, NDVI-08 e NDVI-25. |
| Per-layer coverage expectation | ❌ | O writer não discrimina o commit point e o kernel não discrimina `-0.0f` nem clamp fora de `[-1,1]`. |
| Documented guidelines | ✅ | `README.md:28-40`, `README.md:96-107`, `tasks.md:10-32`; strong defaults para o restante. |

`lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex:42` contém um `SPEC_DEVIATION` para restaurar metadata JIT do Ske. O desvio está explicado em `design.md` e é exercitado pelo gate GPU; não altera o contrato numérico.

## Interactive UAT

Não aplicável. A feature é uma biblioteca de cálculo GPU e persistência local sem interface interativa; os gates automatizados exercitam o comportamento observável.

## Ranked Gaps and Fix Plans

### 1. NDVI-25: teste não discrimina metadata-last — Major

- **Root cause**: o happy path verifica apenas os dois artefatos depois da conclusão. A falha existente ocorre na primeira escrita, antes de a ordem entre as promoções ser relevante.
- **Fix task**: adicionar em `test/sentinel_2/ndvi_result_writer_test.exs` um caso que crie um diretório no caminho final `ndvi.polyhok.f32`, force a falha da promoção do binário e comprove `{:error, reason}` e ausência de `metadata.json` final.
- **Verify**: repetir M3; a publicação antecipada de metadata deve fazer o novo teste falhar.
- **Done when**: M3 é morto e NDVI-25/26 permanecem verdes no Build gate.

### 2. NDVI-06: `-0.0f` não é exercitado — Major

- **Root cause**: o conjunto de seis pixels cobre cancelamento para zero, mas não constrói explicitamente denominador negativo zero.
- **Fix task**: adicionar caso GPU `1x1` com representação `float32` explícita que produza `-0.0f` no denominador e assertar `:nan`.
- **Verify**: o teste deve falhar se o branch de zero aceitar somente `+0.0f`.
- **Done when**: há asserções independentes para `+0.0f` e `-0.0f`.

### 3. NDVI-08: caso negativo não detecta clamp — Major

- **Root cause**: `-0.5` está dentro de `[-1,1]`; uma implementação com clamp indevido ainda passaria.
- **Fix task**: acrescentar um pixel finito cujo resultado literal fique fora de `[-1,1]`, por exemplo B04=`2.0`, B08=`-1.0`, e assertar `-3.0` sem calcular a expectativa em CPU.
- **Verify**: injetar clamp no kernel; o teste deve falhar.
- **Done when**: a ausência de clamp é discriminada por valor observável.

## Requirement Traceability Update

| Requirements | Previous status | Verification status |
| ------------ | --------------- | ------------------- |
| NDVI-01..05 | Implemented | ✅ Verified |
| NDVI-06 | Implemented | ❌ Needs Fix |
| NDVI-07 | Implemented | ✅ Verified |
| NDVI-08 | Implemented | ❌ Needs Fix |
| NDVI-09..24 | Implemented | ✅ Verified |
| NDVI-25 | Implemented | ❌ Needs Fix |
| NDVI-26..27 | Implemented | ✅ Verified |

O arquivo normativo `spec.md` não foi alterado porque o escopo do Verifier permite escrita apenas neste relatório.

## Lessons Distillation

Há sinais para `ac_gap` (NDVI-06 e NDVI-08), `surviving_mutant` (M3) e o marcador `SPEC_DEVIATION` em `ndvi.ex:42`. Nenhuma lição foi persistida porque a instrução explícita desta verificação restringe toda escrita na árvore real a `validation.md`.

Regras candidatas:

- Exercite separadamente classes IEEE nomeadas explicitamente no contrato.
- Para provar ausência de clamp, use um resultado esperado fora do intervalo de clamp.
- Teste publicação metadata-last com uma falha induzida entre os dois pontos de promoção.

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 24/27 outcomes matched; 0 spec-precision gaps.  
**Gate**: PASS, 74 Python + 53 CPU Elixir executados + 8 checks CUDA selecionados, 0 failures.  
**Sensor**: FAIL, 2/3 mutations killed.  
**Next step**: implementar os três fix tasks ranqueados e executar nova verificação independente.
