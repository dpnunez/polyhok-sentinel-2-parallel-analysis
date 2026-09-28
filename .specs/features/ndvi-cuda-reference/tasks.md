# Tarefas da referência NDVI em CUDA C/C++

**Spec:** `.specs/features/ndvi-cuda-reference/spec.md`
**Design:** `.specs/features/ndvi-cuda-reference/design.md`
**Status:** Draft para revisão; nenhuma tarefa executada

## Execution Protocol (MANDATORY -- do not skip)

Implementar estas tarefas com a skill `tlc-spec-driven`, seguindo seu fluxo Execute e suas Critical Rules. Cada tarefa concluída exige testes derivados dos ACs, gate verde, atualização deste arquivo e um commit Conventional Commits atômico. Após a última tarefa, um Verifier independente verifica todos os ACs e executa o discrimination sensor antes de `validation.md` receber PASS. Não publicar nem fazer push sem pedido explícito.

## Test Coverage Matrix

> Fonte: `README.md`, `docs/ndvi-numerical-contract.md`, `python/pyproject.toml`, `test/sentinel_2/ndvi_test.exs`, `test/sentinel_2/ndvi_result_writer_test.exs` e a spec desta feature. Não há padrão C++ preexistente. Os testes numéricos mantêm os valores literais do contrato; o comparador real usa os artefatos das duas implementações.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Build CUDA | smoke de compilação | Produzir executável com flags de precisão e configuração de arquitetura explícitas | `cuda/CMakeLists.txt` | `cmake -S cuda -B cuda/build -DCMAKE_CUDA_ARCHITECTURES=native && cmake --build cuda/build` |
| Kernel e fronteiras GPU | integração GPU CTest | Cobrir CUDA-01..09, 13..14, 21..26 com literais sintéticos, limites e falhas observáveis | `cuda/tests/*_gpu.cu` | `ctest --test-dir cuda/build -L gpu --output-on-failure` |
| Leitura e publicação binária | unidade CTest sem GPU | Tamanho, endianidade, sete campos, checksum e falha de promoção, cada AC aplicável | `cuda/tests/*_io.cpp` | `ctest --test-dir cuda/build -L cpu --output-on-failure` |
| CLI | integração por subprocesso | Argumentos inválidos sem GPU; sucesso JSON, caminho de saída e falha sem metadata com GPU | `cuda/tests/test_cli*.py` | `python/.venv/bin/python -m pytest cuda/tests/test_cli.py -q` e `python/.venv/bin/python -m pytest cuda/tests/test_cli_gpu.py -q` |
| Equivalência de recorte real | integração GPU + Elixir | Mesmos bytes de entrada, forma, posições NaN e diferença finita máxima `1.0e-6` | `cuda/tests/test_real_equivalence.py` | `python/.venv/bin/python -m pytest cuda/tests/test_real_equivalence.py -q` |

## Gate Check Commands

> Comandos novos propostos pelo design; devem ser executados na máquina Linux com Toolkit CUDA e GPU NVIDIA. O gate CPU também exige `nvcc` para compilar, embora seus testes não acessem a GPU. O checkout macOS atual não consegue executá-los.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Após tarefa de I/O ou parsing | `cmake -S cuda -B cuda/build -DCMAKE_CUDA_ARCHITECTURES=native && cmake --build cuda/build && ctest --test-dir cuda/build -L cpu --output-on-failure` |
| Full | Após kernel ou CLI GPU | `cmake -S cuda -B cuda/build -DCMAKE_CUDA_ARCHITECTURES=native && cmake --build cuda/build && ctest --test-dir cuda/build --output-on-failure && python/.venv/bin/python -m pytest cuda/tests/test_cli.py cuda/tests/test_cli_gpu.py -q` |
| Build | Fechamento da feature | `cmake -S cuda -B cuda/build -DCMAKE_CUDA_ARCHITECTURES=native && cmake --build cuda/build && ctest --test-dir cuda/build --output-on-failure && python/.venv/bin/python -m ruff check cuda/tests && python/.venv/bin/python -m pytest cuda/tests -q && mix test --exclude gpu && mix test --include gpu test/sentinel_2/ndvi_test.exs` |

O gate Build pressupõe que o recorte binário preparado e a dependência PolyHok estejam disponíveis na máquina CUDA. O teste de equivalência real deve falhar com diagnóstico claro se faltarem; não deve ser marcado como `skip` e a tarefa T6 permanece aberta até o ambiente permitir a validação.

## Execution Plan

Execução sequencial em três fases:

```text
Phase 1: T1 -> T2
Phase 2: T3 -> T4 -> T5
Phase 3: T6
```

## Task Breakdown

### Phase 1: Núcleo CUDA

#### T1: Criar build CUDA reproduzível

**What:** Configurar CMake e um `main.cpp` mínimo para compilar o alvo `ndvi_cuda` com CUDA C++17, CUDA Runtime, OpenSSL EVP e flags de precisão; ignorar `cuda/build/` no Git. O programa mínimo será substituído em T5.
**Where:** `cuda/CMakeLists.txt`
**Depends on:** None
**Reuses:** Requisitos do contrato numérico e convenção de build documentada no README.
**Requirement:** Pré-requisito para CUDA-01..26.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] Build produz `cuda/build/ndvi_cuda` na máquina CUDA com arquitetura configurada e sem `--use_fast_math`.
- [ ] `--ftz=false` e `--prec-div=true` são verificáveis na configuração de compilação.
- [ ] `cuda/build/` não aparece em `git status` após compilar.
- [ ] Gate de build de T1 passa; nenhum teste preexistente é removido ou desabilitado.

**Tests:** smoke de compilação do alvo mínimo.
**Gate:** build de T1: `cmake -S cuda -B cuda/build -DCMAKE_CUDA_ARCHITECTURES=native && cmake --build cuda/build`
**Commit:** `build(cuda): add direct CUDA target`

#### T2: Implementar o núcleo NDVI e suas três fronteiras

**What:** Implementar `to_device`, `run_kernel`, `to_host` e `compute`, com um kernel `float32`, validação de limites do dispositivo, checagem de erros e sincronização.
**Where:** `cuda/src/ndvi.cu`
**Depends on:** T1
**Reuses:** `Ndvi.compute/2`, contrato numérico e casos literais de `test/sentinel_2/ndvi_test.exs`.
**Requirement:** CUDA-01..09, CUDA-13..14, CUDA-21..26.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] Um kernel produz todos os casos sintéticos esperados, incluindo NaN, zero sinalizado, subnormal e `-3.0`.
- [ ] Contagem de seis elementos exercita threads excedentes sem acesso fora do buffer.
- [ ] Falhas de dispositivo/lançamento/sincronização retornam erro com etapa identificada.
- [ ] As funções GPU permanecem acionáveis separadamente e o gate GPU passa.

**Tests:** integração GPU co-localizada em `cuda/tests/test_ndvi_gpu.cu`, com ACs literais e casos de erro.
**Gate:** full, incluindo `ctest --test-dir cuda/build -L gpu --output-on-failure`
**Commit:** `feat(cuda): add NDVI GPU core`

### Phase 2: Interface e artefatos

#### T3: Ler as bandas preparadas com validação estrita

**What:** Ler cada arquivo `.f32` e rejeitar tamanho diferente de `width * height * 4`, host incompatível e falhas de leitura antes de alocar na GPU.
**Where:** `cuda/src/io.cpp`
**Depends on:** T2
**Reuses:** Contrato de `PreparedReader` e metadata dos recortes preparados.
**Requirement:** CUDA-10, CUDA-12 e parte de CUDA-21.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] Caso válido preserva os bytes e a ordem de posições esperada.
- [ ] Arquivo ausente, curto, longo ou ilegível retorna erro de leitura sem publicação.
- [ ] Testes de unidade co-localizados e gate Quick passam.

**Tests:** unidade sem GPU em `cuda/tests/test_ndvi_io.cpp`.
**Gate:** quick
**Commit:** `feat(cuda): read prepared float32 bands`

#### T4: Publicar o resultado e metadata por último

**What:** Gravar `ndvi.cuda.f32` e os sete campos de `metadata.json`, calcular SHA-256 e promover metadata após o binário.
**Where:** `cuda/src/io.cpp`
**Depends on:** T3
**Reuses:** `Ndvi.ResultWriter` e seus testes de bytes, checksum e falha de promoção.
**Requirement:** CUDA-15..18.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] Bytes, tamanho, sete campos e SHA-256 do caso sintético conferem com o contrato.
- [ ] Substituição remove metadata antigo antes de promover binário novo.
- [ ] Falha induzida na promoção do binário deixa ausência de metadata final válido.
- [ ] Testes de unidade co-localizados e gate Quick passam.

**Tests:** unidade sem GPU em `cuda/tests/test_ndvi_io.cpp`.
**Gate:** quick
**Commit:** `feat(cuda): publish NDVI result artifacts`

#### T5: Expor o executável de ponta a ponta

**What:** Interpretar os cinco argumentos obrigatórios, validar dimensões/overflow e compor leitura, GPU e publicação com JSON de sucesso e erro por etapa.
**Where:** `cuda/src/main.cpp`
**Depends on:** T4
**Reuses:** Contrato de saída do preparador e componentes de T2 a T4.
**Requirement:** CUDA-10..12, CUDA-14, CUDA-19, CUDA-21 e CUDA-27.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] Argumentos faltantes, dimensão inválida e overflow falham antes de acessar a GPU.
- [ ] Execução válida imprime uma linha JSON com status e caminhos e publica ambos os arquivos.
- [ ] Erro não imprime sucesso em stdout e não deixa metadata final válido.
- [ ] Erro imprime uma linha JSON em stderr com `status`, `stage` e `message`; sucesso informa caminhos absolutos.
- [ ] README documenta build, argumentos, arquivos de saída e necessidade de diretórios separados da saída PolyHok.
- [ ] Gate Full passa, incluindo CLI sem GPU e com GPU.

**Tests:** integração por subprocesso em `cuda/tests/test_cli.py` e `cuda/tests/test_cli_gpu.py`.
**Gate:** full
**Commit:** `feat(cuda): expose NDVI reference CLI`

### Phase 3: Equivalência observável

#### T6: Confrontar uma cena real com PolyHok

**What:** Executar as duas implementações no recorte `1024x1024` do mesmo fixture preparado e comparar forma, NaNs e valores finitos sem implementar NDVI em CPU.
**Where:** `cuda/tests/test_real_equivalence.py`
**Depends on:** T5
**Reuses:** `PreparedReader`, `Ndvi.compute/2`, `Ndvi.ResultWriter`, manifesto e metadata preparados.
**Requirement:** CUDA-20.

**Tools:** MCP NONE; skill `tlc-spec-driven`.

**Done when:**

- [ ] O teste lê os mesmos arquivos B04/B08 para as duas implementações e registra o identificador/checksum do recorte usado.
- [ ] As saídas têm forma e posições NaN idênticas; todos os pares finitos diferem no máximo `1.0e-6` em valor absoluto.
- [ ] O teste falha se os binários do fixture ou a GPU faltarem; não mascara ausência de evidência com skip.
- [ ] Gate Build passa na máquina CUDA; o Verifier independente conclui a validação da feature.

**Tests:** integração real GPU + Elixir em `cuda/tests/test_real_equivalence.py` com helper mínimo para invocar o cálculo PolyHok.
**Gate:** build
**Commit:** `test(cuda): verify real-scene parity with PolyHok`

## Phase Execution Map

```text
Phase 1: T1 -> T2
Phase 2: T3 -> T4 -> T5
Phase 3: T6
```

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1 | Um alvo de build e ignore associado | OK |
| T2 | Um núcleo GPU e seus testes | OK |
| T3 | Uma função de leitura e seus testes | OK |
| T4 | Uma função de escrita e seus testes | OK |
| T5 | Um CLI e seus testes | OK |
| T6 | Um teste de equivalência real | OK |

## Diagram-Definition Cross-Check

| Task | Depends On | Diagram Shows | Status |
| ---- | ---------- | ------------- | ------ |
| T1 | None | Sem entrada | Match |
| T2 | T1 | T1 -> T2 | Match |
| T3 | T2 | Phase 1 -> Phase 2 | Match |
| T4 | T3 | T3 -> T4 | Match |
| T5 | T4 | T4 -> T5 | Match |
| T6 | T5 | Phase 2 -> Phase 3 | Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1 | Build | smoke | smoke | OK |
| T2 | Kernel | integração GPU | integração GPU | OK |
| T3 | Leitura | unidade sem GPU | unidade sem GPU | OK |
| T4 | Publicação | unidade sem GPU | unidade sem GPU | OK |
| T5 | CLI | integração por subprocesso | integração por subprocesso | OK |
| T6 | Equivalência real | integração GPU + Elixir | integração GPU + Elixir | OK |

## Requirement Traceability

| Task | Requirements | Status |
| ---- | ------------ | ------ |
| T1 | Pré-requisito de todos | Pending |
| T2 | CUDA-01..09, CUDA-13..14, CUDA-21..26 | Pending |
| T3 | CUDA-10, CUDA-12, CUDA-21 | Pending |
| T4 | CUDA-15..18 | Pending |
| T5 | CUDA-10..12, CUDA-14, CUDA-19, CUDA-21, CUDA-27 | Pending |
| T6 | CUDA-20 | Pending |
