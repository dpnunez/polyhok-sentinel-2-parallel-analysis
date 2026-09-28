# Especificação da referência NDVI em CUDA C/C++

**Status:** Draft para revisão em 2026-09-28

## Problem Statement

O projeto calcula NDVI via Elixir/PolyHok, mas ainda não possui uma implementação CUDA direta para executar sobre as mesmas matrizes. Sem essa referência, a comparação experimental prevista na monografia não consegue distinguir o custo do cálculo GPU dos custos introduzidos pela integração via PolyHok. Esta feature entrega uma execução CUDA independente e funcionalmente equivalente, com as mesmas fronteiras observáveis do protótipo Elixir.

## Goals

- [ ] Executar em CUDA direta a operação definida em `docs/ndvi-numerical-contract.md`, com um kernel e uma posição por thread.
- [ ] Consumir as matrizes B04/B08 preparadas como `float32` little-endian, row-major, sem recalcular a preparação geoespacial.
- [ ] Expor no código as etapas entrada no host, H2D, kernel, D2H e persistência, na mesma ordem do fluxo PolyHok.
- [ ] Produzir `ndvi.cuda.f32` e `metadata.json` compatíveis com o formato do `Ndvi.ResultWriter`.
- [ ] Validar os seis casos sintéticos do contrato e ao menos um recorte real contra a saída PolyHok, quando os dados e a GPU estiverem disponíveis.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Runner de benchmark, warm-up, repetição, métricas e análise estatística | A feature entrega a referência correta e as fronteiras que serão instrumentadas numa etapa posterior. |
| Integração Elixir que lance o executável CUDA | As duas implementações permanecem independentes nesta etapa; o runner futuro coordenará as execuções. |
| Referência CPU de NDVI | O contrato numérico atual adia essa implementação. |
| Leitura de `.SAFE`, recorte, escala radiométrica e máscara de nuvens | Os arquivos `b04.f32` e `b08.f32` já contêm as entradas preparadas. |
| Processamento de múltiplas cenas numa chamada | Cada execução trata um único par de matrizes. |
| Tuning de bloco/grid, streams concorrentes, memória pinned ou CUDA Graphs | Mudariam a configuração da referência antes da definição do protocolo experimental. |
| Igualdade byte a byte com a saída PolyHok | A correção numérica usa tolerância para valores finitos e igualdade de posições `NaN`. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Linguagem de implementação | Fonte `.cu` compilada por `nvcc`, usando CUDA C++ e um estilo direto. | O compilador e o lançamento de kernel CUDA usam a linguagem CUDA C++; “CUDA em C” foi entendido como CUDA direta sem PolyHok. | no — interpretação do pedido |
| Forma de execução | Executável local `ndvi_cuda`, chamado uma vez por par de bandas. | Permite provar a referência isoladamente e preserva a comparação futura com o fluxo PolyHok. | no — default proposto |
| Interface de entrada | `--b04`, `--b08`, `--width`, `--height` e `--output-dir` obrigatórios. | Equivale a receber dois tensores com forma conhecida; o chamador obtém esses valores do metadata preparado. | no — default proposto |
| Arquivos de saída | `ndvi.cuda.f32` e `metadata.json` no diretório indicado. | Espelha os sete campos e a publicação metadata-last do writer PolyHok. | no — default proposto |
| Fonte normativa | `docs/ndvi-numerical-contract.md`; esta spec fixa apenas as interfaces CUDA e de arquivos. | Evita duplicar ou alterar a política numérica já aprovada. | yes — contrato existente |
| Dispositivo e concorrência | GPU CUDA selecionada pelo runtime como dispositivo 0; uma execução e um stream padrão, sem sobreposição. | Define um fluxo simples; seleção de dispositivo e concorrência ficam para o runner experimental. | no — default proposto |
| Memória host | Buffers host comuns (pageable), alocados pelo processo. | Os tensores Nx atuais não estabelecem uso de memória pinned; evita uma otimização exclusiva da referência. | no — default proposto |
| Tempos | A execução inicial não publica tempos; as funções H2D, kernel e D2H terão fronteiras explícitas. | Tempos do dispositivo e tempos de chamada host medem coisas diferentes; o protocolo comparativo deve instrumentar ambos os lados. | no — default proposto |
| Requisitos de ambiente | Toolkit CUDA, compilador C++ compatível, CMake e GPU NVIDIA para os testes funcionais. | O checkout macOS atual não possui `mix`, `nvcc` nem dados binários preparados. | no — pressuposto operacional |
| Persistência repetida | Cada execução substitui os arquivos do destino; metadata final é removido antes da troca do binário e publicado por último. | Evita que metadata antigo valide um binário novo ou incompleto. | no — default proposto |

**Open questions:** none; as escolhas ainda não confirmadas estão identificadas acima para revisão.

## User Stories

### P1: Calcular NDVI diretamente na GPU ⭐ MVP

**User Story:** Como pesquisador, quero uma execução CUDA direta sobre as mesmas entradas para comparar futuramente seu custo com a execução via PolyHok.

**Why P1:** A referência é a segunda implementação exigida pelos objetivos do TCC.

**Acceptance Criteria:**

1. **CUDA-01** — WHEN B04 e B08 válidos forem carregados no host THEN o programa SHALL executar duas transferências H2D, uma por banda, antes de lançar o kernel.
2. **CUDA-02** — WHEN as duas bandas estiverem disponíveis na GPU THEN o programa SHALL lançar exatamente um kernel para produzir uma matriz NDVI de `width * height` elementos `float32`.
3. **CUDA-03** — WHILE o kernel executar, cada thread SHALL calcular no máximo uma posição linear e SHALL acessar as matrizes somente se `index < width * height`.
4. **CUDA-04** — WHEN B04 e B08 forem finitos e `B08 + B04` for diferente de `0.0f` THEN o kernel SHALL escrever `(B08 - B04) / (B08 + B04)` com operações `float32`.
5. **CUDA-05** — IF B04 ou B08 for `NaN` THEN o kernel SHALL escrever `NaN` na mesma posição.
6. **CUDA-06** — IF `B08 + B04` for exatamente `+0.0f` ou `-0.0f` THEN o kernel SHALL escrever `NaN` na mesma posição.
7. **CUDA-07** — WHEN o denominador for diferente de zero, inclusive o menor subnormal positivo `float32`, THEN o kernel SHALL dividir sem epsilon, flush-to-zero deliberado ou clamp.
8. **CUDA-08** — WHEN o kernel concluir com sucesso THEN o programa SHALL transferir a matriz NDVI da GPU para o host uma vez.
9. **CUDA-09** — The kernel SHALL preserve the row-major linear correspondence and SHALL omit radiometric conversion, geospatial operations, cloud masking and CPU NDVI calculation.

**Independent Test:** Executar os seis pares sintéticos aprovados e verificar `0.5`, `0.0`, `-0.5` e três `NaN` em posições exatas.

### P1: Ler entradas preparadas e rejeitar entradas inválidas ⭐ MVP

**User Story:** Como operador do experimento, quero apontar os mesmos binários usados pelo PolyHok e receber um erro explícito quando os argumentos ou arquivos não satisfizerem o contrato.

**Why P1:** Entradas distintas ou mal interpretadas invalidam a comparação.

**Acceptance Criteria:**

1. **CUDA-10** — WHEN `--b04`, `--b08`, `--width`, `--height` e `--output-dir` forem fornecidos THEN o programa SHALL interpretar cada banda como `width * height` valores IEEE 754 `float32` little-endian em ordem row-major.
2. **CUDA-11** — IF faltar argumento obrigatório, uma dimensão não for inteira positiva ou a multiplicação `width * height * 4` exceder `size_t` THEN o programa SHALL sair com código diferente de zero antes de qualquer alocação GPU.
3. **CUDA-12** — IF qualquer banda não puder ser lida ou seu tamanho não for exatamente `width * height * 4` bytes THEN o programa SHALL sair com código diferente de zero antes de qualquer alocação GPU.
4. **CUDA-13** — IF a contagem de blocos exceder o limite `maxGridSize.x` do dispositivo escolhido THEN o programa SHALL sair com código diferente de zero antes de lançar o kernel.
5. **CUDA-14** — IF uma chamada CUDA, alocação, lançamento ou sincronização falhar THEN o programa SHALL sair com código diferente de zero, identificar a etapa que falhou e não publicar metadata da tentativa falha.

**Independent Test:** Exercitar argumentos faltantes, dimensões inválidas, arquivo ausente e tamanho incorreto; nenhum caso deverá iniciar cálculo GPU ou publicar resultado válido.

### P1: Publicar resultado verificável ⭐ MVP

**User Story:** Como pesquisador, quero reler a saída CUDA e confrontá-la com a saída PolyHok sem depender da memória do processo que a produziu.

**Why P1:** A comparação de correção precisa de um artefato estável e rastreável.

**Acceptance Criteria:**

1. **CUDA-15** — WHEN a cópia D2H terminar THEN o programa SHALL escrever `ndvi.cuda.f32` sem cabeçalho, em `float32` little-endian, row-major, com exatamente `width * height * 4` bytes.
2. **CUDA-16** — WHEN o binário estiver completo THEN o programa SHALL publicar `metadata.json` com exatamente os campos `width`, `height`, `dtype`, `byte_order`, `order`, `path` e `sha256`, usando os mesmos valores semânticos do writer PolyHok e `path = "ndvi.cuda.f32"`.
3. **CUDA-17** — WHEN substituir uma saída existente THEN o programa SHALL invalidar o metadata anterior antes de promover o novo binário e SHALL promover o novo metadata por último.
4. **CUDA-18** — IF a escrita, validação de tamanho, checksum ou promoção falhar THEN o programa SHALL sair com código diferente de zero sem deixar metadata final que valide um resultado incompleto.
5. **CUDA-19** — WHEN a publicação for concluída THEN o programa SHALL imprimir uma linha JSON em stdout com `status = "ok"`, `path` e `metadata_path` como caminhos absolutos, e SHALL terminar com código zero.

**Independent Test:** Reler o binário e o JSON de um caso `2x3`, verificar bytes, forma e SHA-256; induzir falha na promoção do binário e confirmar ausência de metadata final.

### P2: Manter a equivalência observável com PolyHok

**User Story:** Como pesquisador, quero executar ambas as implementações sobre o mesmo recorte para demonstrar correção antes de medir diferenças de desempenho.

**Why P2:** Uma diferença numérica confundiria a análise de overhead com uma diferença de algoritmo.

**Acceptance Criteria:**

1. **CUDA-20** — WHEN as duas implementações processarem os mesmos bytes B04/B08 THEN a validação SHALL exigir forma e posições `NaN` idênticas, infinitos com o mesmo sinal e diferença absoluta de até `1.0e-6` para cada par de valores finitos.
2. **CUDA-21** — The implementation SHALL expose distinct code boundaries for input reading, H2D, kernel launch/completion, D2H and result publication, in that order.
3. **CUDA-22** — WHEN o kernel for lançado THEN o programa SHALL verificar erro imediato de lançamento e SHALL sincronizar antes de considerar a etapa concluída, para detectar falhas assíncronas.

**Independent Test:** Comparar um recorte real preparado, quando disponível, e verificar por inspeção e teste que o cálculo não é considerado concluído antes da sincronização.

## Edge Cases

- **CUDA-23** — WHEN B04 e B08 forem iguais e finitos THEN o kernel SHALL produzir `0.0f`.
- **CUDA-24** — WHEN os operandos finitos produzirem NDVI fora de `[-1, 1]` THEN o kernel SHALL preservar esse valor sem clamp.
- **CUDA-25** — WHEN a quantidade de pixels não for múltipla de 256 THEN as threads excedentes SHALL terminar sem ler ou escrever fora dos buffers.
- **CUDA-26** — IF o dispositivo não estiver disponível ou não suportar blocos de 256 threads THEN o programa SHALL terminar com erro identificado sem publicar metadata.
- **CUDA-27** — IF qualquer etapa da execução falhar THEN o CLI SHALL emitir uma linha JSON em stderr com `status = "error"`, `stage` e `message`, sem emitir JSON de sucesso em stdout.

## Implicit Requirement Dimensions

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | CUDA-10 a CUDA-13, CUDA-25 e CUDA-26. |
| Failure / partial-failure states | CUDA-14, CUDA-17 e CUDA-18. |
| Idempotency / retry / duplicate handling | Reexecução no mesmo destino substitui a saída; CUDA-17. |
| Auth boundaries & rate limits | N/A because o executável é local e não expõe serviço de rede. |
| Concurrency / ordering | Uma execução por processo e um stream; concorrência entre processos não é coordenada por esta feature. |
| Data lifecycle / expiry | Artefatos permanecem no diretório escolhido até remoção externa; nenhuma expiração automática. |
| Observability | Etapas de código separadas por CUDA-21; erro por etapa em CUDA-14 e CUDA-27; tempos pertencem ao runner futuro. |
| External-dependency failure | CUDA-14 e CUDA-26 cobrem runtime/dispositivo; CUDA-12 cobre sistema de arquivos. |
| State-transition integrity | Metadata publicado por último segundo CUDA-17 e CUDA-18. |

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| CUDA-01 | Cálculo GPU | T2 | In Tasks |
| CUDA-02 | Cálculo GPU | T2 | In Tasks |
| CUDA-03 | Cálculo GPU | T2 | In Tasks |
| CUDA-04 | Cálculo GPU | T2 | In Tasks |
| CUDA-05 | Cálculo GPU | T2 | In Tasks |
| CUDA-06 | Cálculo GPU | T2 | In Tasks |
| CUDA-07 | Cálculo GPU | T2 | In Tasks |
| CUDA-08 | Cálculo GPU | T2 | In Tasks |
| CUDA-09 | Cálculo GPU | T2 | In Tasks |
| CUDA-10 | Entrada | T3 | In Tasks |
| CUDA-11 | Entrada | T3 | In Tasks |
| CUDA-12 | Entrada | T3 | In Tasks |
| CUDA-13 | Entrada | T2 | In Tasks |
| CUDA-14 | Falhas | T2, T3 | In Tasks |
| CUDA-15 | Publicação | T4 | In Tasks |
| CUDA-16 | Publicação | T4 | In Tasks |
| CUDA-17 | Publicação | T4 | In Tasks |
| CUDA-18 | Publicação | T4 | In Tasks |
| CUDA-19 | Publicação | T5 | In Tasks |
| CUDA-20 | Equivalência | T6 | In Tasks |
| CUDA-21 | Fronteiras | T2, T3, T4 | In Tasks |
| CUDA-22 | Sincronização | T2 | In Tasks |
| CUDA-23 | Edge cases | T2 | In Tasks |
| CUDA-24 | Edge cases | T2 | In Tasks |
| CUDA-25 | Edge cases | T2 | In Tasks |
| CUDA-26 | Edge cases | T2 | In Tasks |
| CUDA-27 | Edge cases | T5 | In Tasks |

**Coverage:** 27 total, 27 mapped to tasks, 0 unmapped.

## Success Criteria

- [ ] O executável CUDA produz a saída esperada para os seis casos sintéticos, signed zero, denominador subnormal e resultado fora de `[-1, 1]`.
- [ ] Entradas inválidas e falhas de CUDA/I/O não publicam metadata da tentativa falha.
- [ ] Um recorte real reproduz forma, posições `NaN` e valores finitos da implementação PolyHok dentro de `1.0e-6`.
- [ ] O gate de build e os testes CUDA da feature passam num ambiente com GPU NVIDIA.
- [ ] As fronteiras H2D, kernel e D2H são identificáveis sem misturar leitura ou persistência.
