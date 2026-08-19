# Especificação da Preparação de Dados Sentinel-2

## Problem Statement

O projeto precisa transformar produtos Sentinel-2 L2A em matrizes binárias reproduzíveis antes do futuro cálculo de NDVI. A preparação será implementada em Python 3 e orquestrada pelo Elixir, que só poderá informar sucesso depois que o processo externo terminar e os artefatos forem validados.

## Goals

- [ ] Preparar B04 e B08 nos três tamanhos definidos em `docs/sentinel-2-data-preparation.md`.
- [ ] Disponibilizar uma API Elixir que aguarde a preparação e retorne um resultado explícito de sucesso ou erro.
- [ ] Comprovar que o Elixir consegue validar e ler os artefatos preparados sem transportar matrizes pelo Port.
- [ ] Tornar a preparação segura para repetição, interrupção e falha parcial.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Cálculo de NDVI | Pertence à etapa posterior da pipeline. |
| Transferência das matrizes para GPU | Será especificada com o cálculo de NDVI. |
| Implementação da pipeline completa | Ainda não existe; esta feature entrega apenas o contrato componível. |
| Download automático de produtos Sentinel-2 | A entrada será um produto L2A `.SAFE` já disponível localmente. |
| SCL, nuvens, AOT, WVP e outras bandas | Foram excluídos da primeira versão pela documentação de preparação. |
| Reamostragem, reprojeção ou redimensionamento | B04 e B08 devem permanecer na grade original de 10 m. |
| Migração da antiga estrutura de fixtures | O resquício foi excluído manualmente e não integra esta feature. |
| Fila persistente e retomada de jobs após reinício da BEAM | Um worker supervisionado local atende ao escopo do TCC. |
| Execução distribuída ou preparação paralela de várias cenas | A primeira versão executará cenas de forma sequencial. |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here; nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Organização dos componentes | Elixir e Python permanecerão no mesmo repositório, com um projeto Python isolado em `python/`. | O código pertence ao mesmo TCC e o contrato entre produtor e consumidor precisa evoluir junto. | yes |
| Contrato de preparação | `docs/sentinel-2-data-preparation.md` será a fonte normativa dos valores, recortes e artefatos. | A documentação existente já define o resultado esperado sem depender da linguagem. | yes |
| Estrutura antiga de fixtures | Não haverá migração nem compatibilidade com a tentativa anterior. | O usuário confirmou que os arquivos antigos foram excluídos manualmente. | yes |
| Forma de integração | O Elixir chamará um executável Python configurado por meio de processo externo e trocará somente status e diagnósticos. | Matrizes de até 512 MiB devem permanecer no sistema de arquivos. | yes |
| Timeout padrão | Cada preparação terá timeout configurável, com padrão de 60 minutos. | Evita espera ilimitada e oferece margem para processamento local dos três recortes. | no, chosen default |
| Reexecução | Uma saída existente será reutilizada somente quando identidade da fonte, metadados, tamanhos e checksums forem válidos. | Evita trabalho caro sem aceitar artefatos obsoletos ou corrompidos. | no, chosen default |
| Concorrência da mesma cena | Somente uma preparação por `scene-id` poderá estar ativa no mesmo nó Elixir. | Evita disputa na escrita do manifesto e dos arquivos finais. | no, chosen default |
| Versão mínima do Python | O projeto declarará Python `>=3.11`; a versão exata usada no ambiente será documentada. | Python 3.11 é uma base moderna e permite execução em versões mais novas sem vincular o projeto ao Python 3.14 local. | no, chosen default |
| Acesso Elixir | Esta feature validará e lerá as matrizes no host, mas não fará transferência para GPU. | Comprova o contrato entre linguagens sem antecipar a etapa de NDVI. | no, chosen default |
| Persistência de jobs | O estado durável será representado apenas pelos artefatos e pelo manifesto; não haverá banco ou fila. | A preparação é local e reexecutável no escopo atual. | no, chosen default |

**Open questions:** none; all resolved or logged above.

---

## User Stories

### P1: Preparar uma cena Sentinel-2 L2A ⭐ MVP

**User Story**: Como pesquisador, quero transformar uma cena `.SAFE` nas matrizes B04 e B08 padronizadas para que os benchmarks posteriores usem entradas reproduzíveis.

**Why P1**: Sem os binários preparados não existe entrada válida para a análise paralela.

**Acceptance Criteria**:

1. **PREP-01** — WHEN o CLI receber o caminho de um produto Sentinel-2 L2A `.SAFE` válido THEN o preparador SHALL localizar B04 10 m, B08 10 m, `MTD_MSIL2A.xml` e `MTD_TL.xml` pertencentes ao mesmo produto e tile.
2. **PREP-02** — IF B04 e B08 divergirem em largura, altura, CRS, origem, tamanho de pixel ou extensão espacial THEN o preparador SHALL encerrar com status diferente de zero sem publicar a cena como preparada.
3. **PREP-03** — WHEN uma grade comportar os três tamanhos do benchmark THEN o preparador SHALL produzir recortes centralizados de `1024x1024`, `4096x4096` e `8192x8192` usando a fórmula de deslocamento documentada.
4. **PREP-04** — The preparador SHALL aplicar exatamente a mesma janela de linhas e colunas a B04 e B08 em cada tamanho.
5. **PREP-05** — WHEN converter um DN válido THEN o preparador SHALL calcular `float32((DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE)` usando os valores da banda lidos de `MTD_MSIL2A.xml`.
6. **PREP-06** — IF B04 ou B08 contiver `NODATA` ou `SATURATED` em uma posição THEN o preparador SHALL gravar `NaN` nessa posição nas duas matrizes.
7. **PREP-07** — The preparador SHALL preservar a grade de 10 m sem calcular NDVI, reamostrar, reprojetar, redimensionar, limitar refletância ou aplicar máscaras não previstas.
8. **PREP-08** — The preparador SHALL gravar cada `b04.f32` e `b08.f32` como IEEE 754 `float32`, little-endian, row-major e sem cabeçalho, com exatamente `width × height × 4` bytes.
9. **PREP-09** — WHEN publicar um recorte THEN o preparador SHALL gravar um `metadata.json` contendo todos os campos mínimos definidos na seção 7.2 da documentação de preparação.
10. **PREP-10** — WHEN publicar um recorte THEN o preparador SHALL gerar um `preview.png` com B04 à esquerda, B08 à direita, percentis 2 e 98 independentes, `NaN` preto e dimensões máximas de `2048x1024`.
11. **PREP-11** — WHEN terminar a escrita de um recorte THEN o preparador SHALL reler os dois binários e validar dimensões, tipo, ordem, quantidade de bytes e checksums antes de marcá-lo como preparado.
12. **PREP-12** — WHEN os três recortes forem validados THEN o preparador SHALL publicar a cena sob `fixtures/sentinel-2/scenes/<scene-id>/prepared/` e atualizar `manifest.json` por último.
13. **PREP-13** — IF a cena não comportar qualquer um dos três recortes THEN o preparador SHALL encerrar com status diferente de zero sem publicar resultados finais parciais.
14. **PREP-14** — WHEN a preparação terminar com sucesso THEN o processo Python SHALL encerrar com status `0` e emitir um diagnóstico que identifique o `scene-id` preparado.

**Independent Test**: Executar o CLI contra uma fonte controlada e verificar os três pares de binários, metadados, previews, checksums e valores amostrados.

---

### P1: Orquestrar a preparação pelo Elixir ⭐ MVP

**User Story**: Como autor da futura pipeline, quero iniciar a preparação pelo Elixir e receber um resultado confiável para que a próxima etapa só seja liberada quando os dados estiverem prontos.

**Why P1**: O status do processo externo sozinho não comprova que os artefatos estão completos e legíveis.

**Acceptance Criteria**:

1. **ORCH-01** — WHEN a API de preparação receber uma cena THEN o orquestrador SHALL executar o interpretador e o entrypoint Python configurados com argumentos separados, sem interpolação por shell.
2. **ORCH-02** — WHILE o processo Python estiver ativo, o orquestrador SHALL manter a chamada da etapa pendente sem bloquear os demais processos da BEAM.
3. **ORCH-03** — WHEN o processo Python terminar THEN o orquestrador SHALL obter seu exit status antes de decidir o resultado da preparação.
4. **ORCH-04** — IF o processo Python terminar com status diferente de `0` THEN o orquestrador SHALL retornar `{:error, reason}` sem retornar sucesso.
5. **ORCH-05** — WHEN o processo Python terminar com status `0` THEN o orquestrador SHALL validar manifesto, metadados, presença, tamanhos e checksums de todos os seis arquivos `.f32` antes de retornar sucesso.
6. **ORCH-06** — IF qualquer validação posterior ao status `0` falhar THEN o orquestrador SHALL retornar `{:error, reason}` e não classificar a cena como preparada.
7. **ORCH-07** — WHEN processo e artefatos forem válidos THEN a API Elixir SHALL retornar `{:ok, prepared_scene}` com `scene-id`, caminhos relativos e metadados dos três recortes.
8. **ORCH-08** — WHEN o tempo configurado for excedido THEN o orquestrador SHALL retornar `{:error, :timeout}` e não liberar a próxima etapa.
9. **ORCH-09** — WHILE uma preparação estiver ativa, o orquestrador SHALL executá-la em um worker supervisionado separado do processo chamador da aplicação.
10. **ORCH-10** — WHEN houver sucesso, falha de processo, falha de validação ou timeout THEN o orquestrador SHALL registrar `scene-id`, duração, resultado e diagnóstico sem registrar o conteúdo das matrizes.
11. **ORCH-11** — The API Elixir SHALL expor somente os resultados `{:ok, prepared_scene}` e `{:error, reason}` como contrato de composição sequencial da futura pipeline.

**Independent Test**: Usar um executável Python controlado que simule sucesso, erro e demora; comprovar que apenas sucesso mais artefatos válidos produz `{:ok, prepared_scene}`.

---

### P1: Ler os dados preparados no Elixir ⭐ MVP

**User Story**: Como autor da análise numérica, quero abrir as matrizes preparadas pelo Elixir para comprovar que o contrato binário pode alimentar a etapa futura.

**Why P1**: A integração só está completa se o consumidor interpretar os bytes produzidos pelo Python sem ambiguidade.

**Acceptance Criteria**:

1. **READ-01** — WHEN o Elixir abrir um recorte preparado THEN o leitor SHALL resolver caminhos relativos a partir da raiz configurada do projeto.
2. **READ-02** — WHEN o Elixir ler uma banda válida THEN o leitor SHALL interpretar seus bytes como `float32` little-endian e row-major usando `width` e `height` do `metadata.json`.
3. **READ-03** — IF a quantidade de bytes não for exatamente `width × height × 4` THEN o leitor SHALL retornar `{:error, :invalid_byte_size}` antes de construir a matriz.
4. **READ-04** — WHEN o leitor abrir B04 e B08 do mesmo recorte THEN o leitor SHALL retornar duas estruturas numéricas com forma idêntica a `{height, width}` e `NaN` preservado nas posições inválidas.
5. **READ-05** — The integração Elixir–Python SHALL transportar pelo processo externo apenas argumentos, status e diagnósticos, mantendo matrizes e metadados no sistema de arquivos compartilhado.

**Independent Test**: Gerar um artefato pequeno e controlado com Python, lê-lo com Elixir e comparar forma, valores finitos e posições `NaN` esperadas.

---

### P1: Recuperar com segurança de repetição e falha parcial ⭐ MVP

**User Story**: Como pesquisador, quero repetir uma preparação interrompida sem aceitar arquivos incompletos para não contaminar os resultados do TCC.

**Why P1**: Uma execução longa pode falhar depois de escrever centenas de MiB.

**Acceptance Criteria**:

1. **SAFE-01** — WHILE uma cena estiver sendo preparada, o preparador SHALL escrever saídas novas com sufixo `.tmp` ou `.partial` no mesmo sistema de arquivos dos destinos finais.
2. **SAFE-02** — WHEN um artefato for validado THEN o preparador SHALL publicá-lo por renomeação atômica antes da atualização final do manifesto.
3. **SAFE-03** — IF uma execução terminar antes da validação completa THEN o sistema SHALL manter a cena fora do estado preparado e ignorar arquivos temporários em leituras posteriores.
4. **SAFE-04** — WHEN uma cena já possuir fonte, metadados, tamanhos e checksums válidos THEN o sistema SHALL retornar sucesso sem reescrever os seis binários.
5. **SAFE-05** — IF uma saída existente divergir da identidade ou checksum da fonte THEN o sistema SHALL refazer a preparação sem reutilizar o resultado divergente.
6. **SAFE-06** — WHILE uma preparação de um `scene-id` estiver ativa, uma segunda solicitação para o mesmo `scene-id` SHALL retornar `{:error, :already_running}`.
7. **SAFE-07** — The repositório SHALL versionar código, testes, manifesto e metadados e SHALL ignorar `.SAFE`, JP2/TIFF, `.f32`, previews, ambientes virtuais e arquivos temporários gerados.

**Independent Test**: Simular interrupção, repetição válida, saída corrompida e duas solicitações simultâneas da mesma cena; verificar estado, reutilização e erros retornados.

---

## Implicit-Requirement Dimensions

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | Coberta por PREP-01, PREP-02, PREP-03, PREP-13 e READ-03. |
| Failure / partial-failure states | Coberta por ORCH-04, ORCH-06, ORCH-08 e SAFE-01 a SAFE-03. |
| Idempotency / retry / duplicate handling | Coberta por SAFE-04 a SAFE-06. |
| Auth boundaries & rate limits | N/A porque a API é local ao processo Elixir e não será exposta por rede nesta feature. |
| Concurrency / ordering | Mesma cena é serializada por SAFE-06; múltiplas cenas em paralelo são N/A nesta versão. |
| Data lifecycle / expiry | N/A porque remoção e arquivamento dos datasets serão manuais no escopo do TCC. |
| Observability | Coberta por PREP-14 e ORCH-10. |
| External-dependency failure | Coberta por ORCH-04 e ORCH-08 para interpretador, dependências e processo Python. |
| State-transition integrity | Coberta por PREP-11, PREP-12, SAFE-02 e SAFE-03. |

## Edge Cases

- **EDGE-01** — IF qualquer arquivo obrigatório do `.SAFE` estiver ausente ou ambíguo THEN o preparador SHALL encerrar com status diferente de zero sem publicar a cena.
- **EDGE-02** — IF os offsets de B04 ou B08 ou o valor de quantificação estiverem ausentes ou inválidos THEN o preparador SHALL encerrar com status diferente de zero sem converter pixels.
- **EDGE-03** — IF o interpretador Python ou o entrypoint configurado não existir THEN o orquestrador SHALL retornar `{:error, :executable_not_found}`.
- **EDGE-04** — IF o destino não possuir espaço ou permissão de escrita THEN o sistema SHALL retornar erro e não atualizar o manifesto para preparado.
- **EDGE-05** — IF `metadata.json` for inválido ou não corresponder ao binário THEN o leitor SHALL retornar erro sem construir a matriz.
- **EDGE-06** — IF o processo externo terminar após o timeout já ter sido reportado THEN o sistema SHALL continuar classificando aquela chamada como erro e SHALL exigir validação antes de reutilizar qualquer saída produzida.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PREP-01 | P1: Preparar cena | Design | Pending |
| PREP-02 | P1: Preparar cena | Design | Pending |
| PREP-03 | P1: Preparar cena | Design | Pending |
| PREP-04 | P1: Preparar cena | Design | Pending |
| PREP-05 | P1: Preparar cena | Design | Pending |
| PREP-06 | P1: Preparar cena | Design | Pending |
| PREP-07 | P1: Preparar cena | Design | Pending |
| PREP-08 | P1: Preparar cena | Design | Pending |
| PREP-09 | P1: Preparar cena | Design | Pending |
| PREP-10 | P1: Preparar cena | Design | Pending |
| PREP-11 | P1: Preparar cena | Design | Pending |
| PREP-12 | P1: Preparar cena | Design | Pending |
| PREP-13 | P1: Preparar cena | Design | Pending |
| PREP-14 | P1: Preparar cena | Design | Pending |
| ORCH-01 | P1: Orquestrar | Design | Pending |
| ORCH-02 | P1: Orquestrar | Design | Pending |
| ORCH-03 | P1: Orquestrar | Design | Pending |
| ORCH-04 | P1: Orquestrar | Design | Pending |
| ORCH-05 | P1: Orquestrar | Design | Pending |
| ORCH-06 | P1: Orquestrar | Design | Pending |
| ORCH-07 | P1: Orquestrar | Design | Pending |
| ORCH-08 | P1: Orquestrar | Design | Pending |
| ORCH-09 | P1: Orquestrar | Design | Pending |
| ORCH-10 | P1: Orquestrar | Design | Pending |
| ORCH-11 | P1: Orquestrar | Design | Pending |
| READ-01 | P1: Ler dados | Design | Pending |
| READ-02 | P1: Ler dados | Design | Pending |
| READ-03 | P1: Ler dados | Design | Pending |
| READ-04 | P1: Ler dados | Design | Pending |
| READ-05 | P1: Ler dados | Design | Pending |
| SAFE-01 | P1: Recuperação segura | Design | Pending |
| SAFE-02 | P1: Recuperação segura | Design | Pending |
| SAFE-03 | P1: Recuperação segura | Design | Pending |
| SAFE-04 | P1: Recuperação segura | Design | Pending |
| SAFE-05 | P1: Recuperação segura | Design | Pending |
| SAFE-06 | P1: Recuperação segura | Design | Pending |
| SAFE-07 | P1: Recuperação segura | Design | Pending |
| EDGE-01 | Edge cases | Design | Pending |
| EDGE-02 | Edge cases | Design | Pending |
| EDGE-03 | Edge cases | Design | Pending |
| EDGE-04 | Edge cases | Design | Pending |
| EDGE-05 | Edge cases | Design | Pending |
| EDGE-06 | Edge cases | Design | Pending |

**Coverage:** 43 total, 0 mapped to tasks, 43 unmapped.

---

## Success Criteria

- [ ] Uma execução válida produz exatamente três recortes e seis binários conformes ao contrato documentado.
- [ ] Nenhum cenário de status Python não zero, timeout, arquivo ausente, tamanho incorreto ou checksum divergente retorna `{:ok, prepared_scene}`.
- [ ] Um teste cruzado escreve valores com Python e comprova no Elixir os mesmos valores, forma e posições `NaN`.
- [ ] Uma interrupção não deixa uma cena observável como preparada.
- [ ] Uma segunda execução com artefatos válidos não modifica os seis arquivos `.f32`.
- [ ] Testes Python e Elixir podem ser executados sem GPU e sem depender do produto Sentinel-2 real ignorado pelo Git.
