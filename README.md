# PolyhokSentinel2ParallelAnalysis

Projeto Elixir iniciado com Mix.

O projeto usa a cópia local da PolyHok em `/home/daniel/poly_hok` como uma
dependência Mix por caminho.

## Requisitos

- Elixir 1.15 ou superior
- Erlang/OTP compatível com a versão do Elixir

## Uso

```bash
mix deps.get
MATREX_BLAS=noblas mix deps.compile
mix test
iex -S mix
```

`MATREX_BLAS=noblas` evita exigir OpenBLAS quando o projeto usa a PolyHok com
`Nx`. Se operações BLAS do Matrex forem necessárias, instale
`libopenblas-dev` e compile com a implementação BLAS apropriada.

> TODO: revisar o uso de `MATREX_BLAS=noblas`; avaliar a instalação do
> OpenBLAS e validar as operações BLAS do Matrex antes de depender delas.

O teste `test/poly_hok_test.exs` envia um tensor Nx para a GPU com
`PolyHok.new_gnx/1`, copia o resultado de volta com `PolyHok.get_gnx/1` e
confirma seus valores, tipo e formato.

O teste precisa ser executado em um ambiente com acesso à GPU NVIDIA; sandboxes
ou contêineres sem acesso ao dispositivo CUDA não conseguem executá-lo.
