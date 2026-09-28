# Contexto da referência NDVI em CUDA C/C++

**Gathered:** 2026-09-28
**Spec:** `.specs/features/ndvi-cuda-reference/spec.md`
**Status:** Draft para revisão

## Feature Boundary

Esta feature acrescenta uma referência CUDA direta para um par de bandas B04/B08 já preparadas. Ela produz o resultado numérico persistido e preserva etapas equivalentes às do módulo Elixir/PolyHok. O benchmark comparativo será implementado depois.

## Implementation Decisions

### Decisões expressas pelo usuário

- A versão direta usará C com CUDA, sem passar pelo PolyHok.
- O fluxo será o mais semelhante possível ao que já existe em Elixir, para permitir medir futuramente o overhead do PolyHok.
- A especificação deve definir a interface, a saída, as fronteiras de medição e a implementação do módulo.
- O desenvolvimento seguirá a skill `tlc-spec-driven`.

### Contrato existente que restringe esta feature

- `docs/ndvi-numerical-contract.md` define `float32`, fórmula, `NaN`, zero exato, um kernel e uma posição por thread.
- `Ndvi.compute/2` compõe `to_device/2`, `run_kernel/2` e `to_host/1`.
- `Ndvi.ResultWriter` grava resultado após D2H em binário little-endian e publica `metadata.json` por último.
- `PreparedReader` interpreta B04/B08 como tensores Nx de forma conhecida a partir dos binários preparados.

### Decisões propostas para revisão

- Usar CUDA C++ em arquivo `.cu` compilado por `nvcc`; essa é a interpretação operacional de “CUDA em C”.
- Expor um executável independente `ndvi_cuda` com caminhos B04/B08, largura, altura e diretório de saída.
- Gravar `ndvi.cuda.f32` e `metadata.json` em diretório próprio da execução CUDA.
- Manter uma chamada por processo, dispositivo 0, stream padrão e buffers host comuns.
- Adiar a coleta de tempos, mas deixar as fronteiras isoladas e a sincronização explícita.

### Agent's Discretion

Nomes de funções internas, técnica de parsing dos cinco argumentos, organização de arquivos fonte e biblioteca de SHA-256, desde que os contratos observáveis da spec sejam preservados.

### Declined / Undiscussed Gray Areas → Assumptions

Não houve discussão específica sobre parser de metadata Sentinel-2, seleção de GPU, concorrência, política de sobrescrita ou temporização nesta feature. Os defaults, com razões, estão na tabela **Assumptions & Open Questions** da spec.

## Specific References

- `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi.ex`
- `lib/polyhok_sentinel_2_parallel_analysis/sentinel_2/ndvi/result_writer.ex`
- `docs/ndvi-numerical-contract.md`
- `fixtures/sentinel-2/scenes/*/prepared/*/metadata.json`

## Deferred Ideas

- Runner comum para PolyHok e CUDA direta.
- Medição separada de tempos host e dispositivo, warm-up, repetições e estatística.
- Execução em lote sobre múltiplas cenas e tamanhos.
