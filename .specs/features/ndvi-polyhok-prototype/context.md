# Contexto do Protótipo Inicial de NDVI via PolyHok

**Gathered:** 2026-09-02
**Spec:** `.specs/features/ndvi-polyhok-prototype/spec.md`
**Status:** Ready for design

---

## Feature Boundary

A feature recebe B04 e B08 como tensores Nx bidimensionais `float32` no host,
valida o contrato estrutural, transfere as entradas para a GPU, executa uma única
chamada de kernel NDVI via PolyHok, devolve o resultado ao host e permite
persisti-lo explicitamente como `ndvi.polyhok.f32` com metadata local. Ela não
implementa benchmark, execução em lote, referência CPU ou CUDA C/C++ direta.

---

## Implementation Decisions

### Contrato numérico

- A fórmula é `(B08 - B04) / (B08 + B04)` em `float32`.
- `NaN` em B04 ou B08 produz `NaN` na mesma posição.
- Denominador exatamente `+0.0f` ou `-0.0f` produz `NaN`.
- Todo denominador diferente de zero é dividido normalmente, sem epsilon.
- O resultado não sofre clamp, máscara, classificação ou tratamento temático.
- Cada thread processa no máximo um elemento dentro dos limites.
- O cálculo completo usa uma única chamada de kernel.

### Interface e erros

- A entrada pública são dois tensores Nx no host, no formato entregue pelo
  `PreparedReader`.
- O sucesso retorna diretamente o tensor Nx de NDVI no host.
- Entradas incompatíveis levantam `ArgumentError` antes da chamada ao PolyHok.
- Falhas nativas de PolyHok, NIF, CUDA ou alocação são propagadas sem wrappers.

### Simplicidade

- O código terá somente as funções e módulos exigidos pelo cálculo, pelas três
  fronteiras mensuráveis e pela persistência.
- A implementação reutilizará primitivas existentes do PolyHok quando elas
  cumprirem integralmente o contrato.
- Não haverá framework genérico de operações GPU, behaviors, configuração
  dinâmica da fórmula ou extensibilidade sem uso imediato.
- A separação H2D, kernel e D2H será explícita, mas não introduzirá instrumentação
  nem uma arquitetura de benchmark nesta feature.

### Persistência

- A persistência será uma operação explícita após o retorno do tensor ao host.
- O binário será salvo como `ndvi.polyhok.f32` em `float32`, little-endian,
  row-major e sem cabeçalho.
- `metadata.json` registrará dimensões, formato e checksum SHA-256 e será publicado
  por último.
- A escrita não será incluída no tempo de transferência ou execução GPU.

### Validação inicial

- O teste GPU usará uma única matriz sintética `2x3` com os seis pares aprovados.
- Os três resultados finitos usarão tolerância absoluta `1.0e-6` e relativa zero.
- As três posições inválidas serão verificadas como `NaN`.
- Testes de validação estrutural não implementarão uma versão CPU do NDVI.

### Agent's Discretion

- Nomes exatos dos módulos e funções internas, desde que permaneçam pequenos e
  reflitam as fronteiras aprovadas.
- Forma interna de representar as referências GPU retornadas pelo PolyHok.
- Mensagens de `ArgumentError`, desde que identifiquem tipo, forma ou
  incompatibilidade e ocorram antes da GPU.
- Estratégia mínima de arquivos temporários para publicar o metadata por último.

### Declined / Undiscussed Gray Areas → Assumptions

- Concorrência entre cálculos e persistências fica fora do protótipo; cada chamada
  será independente e sem coordenação global.
- Warm-up, cache JIT e tuning de bloco/grid ficam para o protocolo experimental.
- Resultados não terão expiração ou remoção automática.

---

## Specific References

- `docs/ndvi-numerical-contract.md` é a fonte normativa do cálculo e da validação.
- `/home/daniel/workspace/tcc-monografia/main.tex` define a separação futura das
  métricas e a comparação obrigatória posterior com CUDA C/C++ direta.
- `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/prepared_reader.ex` define
  o formato Nx entregue pela etapa anterior.

---

## Deferred Ideas

- Implementação CUDA C/C++ direta e comparação entre versões GPU.
- Referência CPU e comparação integral de recortes reais, somente se houver tempo.
- Instrumentação, warm-up, repetição, throughput e protocolo estatístico.
- Execução em lote, escolha de cenas e produtos visuais complementares.
