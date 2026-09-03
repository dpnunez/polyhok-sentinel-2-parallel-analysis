# Especificação do Protótipo Inicial de NDVI via PolyHok

**Status:** Approved on 2026-09-02

## Problem Statement

O projeto já produz matrizes B04 e B08 preparadas como tensores Nx `float32`, mas
ainda não possui o núcleo que calcula NDVI na GPU. O protótipo deve comprovar a
execução ponto a ponto via PolyHok, obedecer ao contrato numérico aprovado e
preservar as fronteiras necessárias para a futura avaliação de desempenho.

## Goals

- [ ] Disponibilizar uma operação Elixir que calcule NDVI em GPU a partir de duas
      matrizes Nx bidimensionais `float32` compatíveis.
- [ ] Aplicar em um único kernel a fórmula e todos os casos especiais definidos em
      `docs/ndvi-numerical-contract.md`.
- [ ] Retornar ao host um tensor Nx `float32` com a mesma forma e correspondência
      espacial das entradas.
- [ ] Comprovar o comportamento do kernel com os seis casos pequenos de resultado
      conhecido aprovados no contrato.
- [ ] Manter transferência host-GPU, execução do kernel e transferência GPU-host
      como fronteiras distintas para instrumentação posterior.
- [ ] Persistir opcionalmente o tensor retornado em um artefato binário simples e
      reproduzível, sem incluir a escrita no tempo do cálculo GPU.
- [ ] Implementar o menor núcleo necessário, reutilizando as primitivas do PolyHok
      e sem criar abstrações genéricas ou extensibilidade antecipada.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Implementação CUDA C/C++ direta | É uma etapa posterior e usará o mesmo contrato numérico. |
| Implementação ou referência CPU de NDVI | Foi adiada pelo usuário e não integra a pipeline final. |
| Comparação integral contra recortes reais | Foi adiada até haver necessidade ou tempo ao final do trabalho. |
| Benchmark, protocolo estatístico e coleta de métricas | O protótipo apenas preserva as fronteiras que serão instrumentadas depois. |
| Execução em lote e coordenação de cenas | Pertencem à pipeline experimental completa. |
| Leitura de manifesto ou escolha de recorte | `PreparedReader` e a preparação já possuem essa responsabilidade. |
| PNG, histograma, média ou classificação temática | São produtos complementares ou aplicações fora do núcleo numérico. |
| Máscara de nuvens e outros tratamentos geoespaciais | A entrada já está preparada e o kernel deve permanecer estritamente ponto a ponto. |
| Escolha definitiva de bloco e grid para os experimentos | O protótipo precisa apenas de uma configuração correta; tuning pertence ao benchmark. |
| Framework genérico para operações GPU | O protótipo implementa somente NDVI e deve permanecer simples. |
| Configuração dinâmica da fórmula ou da política numérica | O contrato aprovado é fixo e não precisa de extensibilidade. |
| Banco de dados, object storage ou manifesto global de resultados | A persistência inicial usará somente um binário e seu metadata local. |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here; nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Fonte normativa do comportamento | `docs/ndvi-numerical-contract.md` governa tipo, fórmula, casos especiais, execução e saída. | O usuário aprovou e documentou esse contrato antes da spec. | yes |
| Delimitação acadêmica | O protótipo seguirá as fronteiras e a decomposição futura de tempos descritas em `/home/daniel/workspace/tcc-monografia/main.tex`. | Mantém a implementação alinhada à metodologia da monografia. | yes |
| Simplicidade do código | A implementação usará o mínimo de módulos, funções e estruturas necessário para o núcleo NDVI e suas três fronteiras mensuráveis. | O usuário declarou simplicidade como objetivo explícito; abstrações genéricas e extensibilidade antecipada não pertencem ao protótipo. | yes |
| Interface de entrada | A operação pública receberá diretamente B04 e B08 como tensores Nx no host. | `PreparedReader.read_crop/2` já entrega esse formato e a seleção de cena não pertence ao núcleo NDVI. | yes |
| Resultado da operação | Uma entrada válida retornará diretamente o tensor Nx de NDVI; entrada incompatível levantará `ArgumentError` antes da GPU. | O núcleo é uma transformação numérica local; evitar tuplas e wrappers reduz código e mantém uso semelhante a operações Nx. | yes |
| Falha do runtime GPU | Erros do PolyHok, NIF, CUDA ou alocação serão propagados sem uma camada própria de normalização. | Preserva o diagnóstico original e evita tratamento especulativo no protótipo. | yes |
| Dimensões aceitas | Altura e largura deverão ser maiores que zero. | Os recortes preparados são matrizes não vazias e um kernel vazio não demonstra o protótipo. | yes |
| Ordem row-major | A operação preservará a ordem lógica do tensor Nx; não tentará inferir ou revalidar o layout binário original. | A ordem física já é validada na preparação e fica abstrata depois de `Nx.from_binary/2`. | yes |
| Domínio dos valores por pixel | As entradas preparadas conterão valores finitos ou `NaN`; o kernel verificará `NaN` nas entradas e denominador exatamente zero, e dividirá em todos os demais casos. | É o domínio produzido pela preparação e corresponde diretamente à política aprovada no contrato. | yes |
| Tolerância dos testes finitos | Os seis casos conhecidos usarão tolerância absoluta de `1.0e-6` e tolerância relativa zero nos três resultados finitos. | Literais decimais como `0.2` não têm representação binária exata em `float32`; a tolerância testa a fórmula sem alterar o cálculo. | yes |
| Comparação de zero | `+0.0f` e `-0.0f` serão tratados como denominador zero. | A igualdade IEEE 754 com `0.0f` considera ambos iguais e segue a comparação exata aprovada. | yes |
| Aquecimento e compilação JIT | Warm-up, cache de compilação e separação entre compilação e execução não serão medidos nesta feature. | São decisões do protocolo experimental, não da prova funcional inicial. | yes |
| Persistência do resultado | Uma operação explícita e separada gravará `ndvi.polyhok.f32` e `metadata.json` em um diretório de destino fornecido pelo chamador. | Mantém a API de cálculo pura, identifica a implementação PolyHok, evita misturar I/O com tempos GPU e produz um artefato que pode ser relido. | yes |

**Open questions:** none; all resolved or logged above.

---

## User Stories

### P1: Calcular NDVI em um único kernel GPU ⭐ MVP

**User Story**: Como pesquisador, quero calcular NDVI via PolyHok sobre B04 e B08
para comprovar o núcleo acelerado que será avaliado no estudo de caso.

**Why P1**: Sem um kernel correto não existe protótipo da etapa computacional nem
base para a futura comparação com CUDA C/C++ direta.

**Acceptance Criteria**:

1. **NDVI-01** — WHEN a operação receber dois tensores Nx bidimensionais, não vazios, de tipo `{:f, 32}` e mesma forma THEN o sistema SHALL transferir B04 e B08 do host para a GPU.
2. **NDVI-02** — WHEN as entradas válidas estiverem na GPU THEN o sistema SHALL executar exatamente uma chamada de kernel para produzir o NDVI.
3. **NDVI-03** — WHILE o kernel estiver em execução, cada thread SHALL processar no máximo uma posição linear dentro dos limites da matriz.
4. **NDVI-04** — WHEN uma posição válida contiver B04 e B08 finitos e `B08 + B04 != 0.0f` THEN o kernel SHALL escrever `(B08 - B04) / (B08 + B04)` usando aritmética `float32`.
5. **NDVI-05** — IF B04 ou B08 for `NaN` em uma posição THEN o kernel SHALL escrever `NaN` na posição correspondente.
6. **NDVI-06** — IF `B08 + B04` for exatamente `+0.0f` ou `-0.0f` em uma posição THEN o kernel SHALL escrever `NaN` na posição correspondente.
7. **NDVI-07** — IF `B08 + B04` for diferente de zero, ainda que próximo de zero, THEN o kernel SHALL executar a divisão sem epsilon e sem substituir o resultado.
8. **NDVI-08** — The kernel SHALL produce each position without clamp, thematic mask, classification or geospatial transformation.
9. **NDVI-09** — WHEN o kernel terminar com sucesso THEN o sistema SHALL transferir o resultado da GPU para o host exatamente uma vez.
10. **NDVI-10** — WHEN o resultado chegar ao host THEN o sistema SHALL retornar diretamente um tensor Nx `{:f, 32}`, com a mesma forma e correspondência linear das entradas.

**Independent Test**: Executar uma matriz sintética `2x3` contendo os seis pares
aprovados e verificar os três valores finitos e as três posições `NaN` depois do
retorno da GPU.

---

### P1: Rejeitar entradas incompatíveis antes da GPU ⭐ MVP

**User Story**: Como autor da pipeline, quero receber erros explícitos para entradas
incompatíveis para que uma execução inválida não seja confundida com falha do
kernel ou resultado científico.

**Why P1**: O contrato exige tipo e forma comuns, e essa condição precisa ser
garantida antes de alocar ou acionar a GPU.

**Acceptance Criteria**:

1. **NDVI-11** — IF B04 ou B08 não for um tensor Nx THEN o sistema SHALL levantar `ArgumentError` antes de qualquer chamada ao PolyHok.
2. **NDVI-12** — IF B04 ou B08 não tiver tipo `{:f, 32}` THEN o sistema SHALL levantar `ArgumentError` antes de qualquer chamada ao PolyHok.
3. **NDVI-13** — IF B04 ou B08 não for bidimensional ou possuir uma dimensão igual a zero THEN o sistema SHALL levantar `ArgumentError` antes de qualquer chamada ao PolyHok.
4. **NDVI-14** — IF B04 e B08 tiverem formas diferentes THEN o sistema SHALL levantar `ArgumentError` antes de qualquer chamada ao PolyHok.
5. **NDVI-15** — IF PolyHok, o NIF, CUDA ou uma alocação GPU falhar THEN o sistema SHALL propagar a falha original sem retornar um tensor parcial como sucesso.

**Independent Test**: Exercitar cada classe de entrada inválida e comprovar que
`ArgumentError` ocorre antes da execução GPU; falhas nativas permanecem observáveis
sem serem convertidas em resultado válido.

---

### P2: Preservar fronteiras para medições posteriores

**User Story**: Como pesquisador, quero que as etapas observáveis do protótipo
permaneçam separadas para instrumentar posteriormente os custos descritos na
monografia sem reescrever o núcleo numérico.

**Why P2**: A instrumentação completa não é necessária no protótipo, mas esconder
transferências e kernel numa fronteira indivisível impediria decompor os tempos do
experimento.

**Acceptance Criteria**:

1. **NDVI-16** — The system SHALL keep host-GPU transfer, kernel invocation and GPU-host transfer as distinct operations that Elixir code can invoke individually.
2. **NDVI-17** — The system SHALL keep data preparation outside the calculation operation and outside any future kernel duration.
3. **NDVI-18** — The public operation SHALL compose the three operations in host-GPU, kernel and GPU-host order without executing a CPU NDVI implementation.

**Independent Test**: Verificar por inspeção das interfaces que as três fronteiras
existem e executar a composição pública com o caso sintético sem passar por
preparação, persistência ou referência CPU.

---

### P1: Persistir o resultado numérico ⭐ MVP

**User Story**: Como pesquisador, quero salvar o NDVI retornado pela GPU para
inspecionar e reutilizar o resultado sem recalcular o protótipo.

**Why P1**: A escrita local é pequena, útil para validar o fluxo completo e foi
solicitada explicitamente para o protótipo inicial.

**Acceptance Criteria**:

1. **NDVI-23** — WHEN a operação de persistência receber um tensor NDVI bidimensional `{:f, 32}` e um diretório de destino THEN o sistema SHALL gravar `ndvi.polyhok.f32` como IEEE 754 `float32`, little-endian, row-major, sem cabeçalho e com exatamente `height * width * 4` bytes.
2. **NDVI-24** — WHEN o binário estiver completo THEN o sistema SHALL gravar `metadata.json` com largura, altura, tipo, byte order, organização, nome do arquivo e checksum SHA-256 de `ndvi.polyhok.f32`.
3. **NDVI-25** — WHEN publicar os artefatos THEN o sistema SHALL substituir `metadata.json` por último para que ele seja o ponto observável de conclusão da escrita.
4. **NDVI-26** — IF a escrita ou a validação do binário falhar THEN o sistema SHALL retornar um erro sem publicar um `metadata.json` que classifique o resultado incompleto como válido.
5. **NDVI-27** — The persistence operation SHALL remain explicit and separate from host-GPU transfer, kernel execution and GPU-host transfer.

**Independent Test**: Persistir um tensor `2x3` com valores finitos e `NaN`, reler
o binário usando o metadata e verificar tipo, forma, ordem, valores, tamanho e
checksum.

---

## Edge Cases

- **NDVI-19** — WHEN B04 e B08 forem iguais e finitos numa posição THEN o kernel SHALL escrever `0.0f` nessa posição.
- **NDVI-20** — WHEN B04 for maior que B08 e o denominador for não nulo numa posição THEN o kernel SHALL preservar o resultado negativo calculado, sem clamp.
- **NDVI-21** — WHEN o denominador for o menor valor `float32` não nulo representável pelo ambiente do kernel THEN o kernel SHALL executar a divisão normal, sem tratá-lo como zero por limiar.
- **NDVI-22** — WHEN o número de elementos não for múltiplo do tamanho do bloco THEN threads com índice fora da matriz SHALL terminar sem ler nem escrever posições de entrada ou saída.

---

## Implicit Requirement Dimensions

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | Coberta por NDVI-01, NDVI-03 e NDVI-11 a NDVI-14. |
| Failure / partial-failure states | Coberta por NDVI-15; nenhuma saída parcial é válida. |
| Idempotency / retry / duplicate handling | N/A because a operação não persiste estado e cada chamada calcula um novo resultado. |
| Auth boundaries & rate limits | N/A because esta é uma API Elixir local sem fronteira de rede ou usuários autenticados. |
| Concurrency / ordering | A ordem interna é coberta por NDVI-18; concorrência entre chamadas fica fora do protótipo e será tratada na execução em lote. |
| Data lifecycle / expiry | O tensor GPU é temporário; o resultado persistido é local e só é considerado completo após NDVI-25. Expiração e remoção ficam fora do protótipo. |
| Observability | Coberta pelas fronteiras individualmente acionáveis de NDVI-16 e pela ausência deliberada de métricas nesta etapa. |
| External-dependency failure | Coberta por NDVI-15 para PolyHok, NIF e CUDA. |
| State-transition integrity | Coberta por NDVI-25 e NDVI-26 para publicação completa ou falha sem metadata válido. |

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| NDVI-01 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-02 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-03 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-04 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-05 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-06 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-07 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-08 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-09 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-10 | P1: Calcular NDVI em um único kernel GPU | T1 | Pending |
| NDVI-11 | P1: Rejeitar entradas incompatíveis antes da GPU | T1 | Pending |
| NDVI-12 | P1: Rejeitar entradas incompatíveis antes da GPU | T1 | Pending |
| NDVI-13 | P1: Rejeitar entradas incompatíveis antes da GPU | T1 | Pending |
| NDVI-14 | P1: Rejeitar entradas incompatíveis antes da GPU | T1 | Pending |
| NDVI-15 | P1: Rejeitar entradas incompatíveis antes da GPU | T1 | Pending |
| NDVI-16 | P2: Preservar fronteiras para medições posteriores | T1 | Pending |
| NDVI-17 | P2: Preservar fronteiras para medições posteriores | T1 | Pending |
| NDVI-18 | P2: Preservar fronteiras para medições posteriores | T1 | Pending |
| NDVI-19 | Edge cases | T1 | Pending |
| NDVI-20 | Edge cases | T1 | Pending |
| NDVI-21 | Edge cases | T1 | Pending |
| NDVI-22 | Edge cases | T1 | Pending |
| NDVI-23 | P1: Persistir o resultado numérico | T2 | Pending |
| NDVI-24 | P1: Persistir o resultado numérico | T2 | Pending |
| NDVI-25 | P1: Persistir o resultado numérico | T2 | Pending |
| NDVI-26 | P1: Persistir o resultado numérico | T2 | Pending |
| NDVI-27 | P1: Persistir o resultado numérico | T2 | Pending |

**Coverage:** 27 total, 27 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] A operação pública executa os seis casos aprovados em uma única matriz GPU e
      retorna três resultados finitos dentro de tolerância absoluta `1.0e-6` e
      três resultados `NaN` nas posições corretas.
- [ ] O resultado preserva tipo `{:f, 32}`, forma `{2, 3}` e ordem dos seis pixels.
- [ ] Entradas de tipo, dimensionalidade ou forma inválidos falham antes do acesso
      à GPU com o motivo especificado.
- [ ] A implementação contém uma única chamada de kernel para o cálculo completo e
      mantém H2D, kernel e D2H como fronteiras distintas.
- [ ] O gate GPU do protótipo e o gate completo sem GPU terminam com zero falhas.
- [ ] Nenhuma implementação CPU de NDVI, benchmark, persistência ou produto
      complementar é introduzido nesta feature além da escrita binária explícita
      definida em NDVI-23 a NDVI-27.
- [ ] O resultado persistido pode ser relido com os mesmos valores, posições `NaN`,
      tipo e forma, e seu checksum corresponde ao metadata publicado.
- [ ] Nenhum framework genérico, comportamento, configuração dinâmica da fórmula
      ou abstração sem uso imediato é introduzido nesta feature.
