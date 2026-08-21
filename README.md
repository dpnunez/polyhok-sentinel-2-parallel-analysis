# PolyhokSentinel2ParallelAnalysis

Projeto Elixir iniciado com Mix.

O projeto usa a cópia local da PolyHok em `/home/daniel/poly_hok` como uma
dependência Mix por caminho.

## Requisitos

- Elixir 1.15 ou superior
- Erlang/OTP compatível com a versão do Elixir
- Python 3.11 ou superior
- um produto Sentinel-2 L2A `.SAFE` local com B04 e B08 de 10 m

## Instalação para CPU

```bash
python3 -m venv python/.venv
python/.venv/bin/python -m pip install -e "./python[dev]"
mix deps.get
MATREX_BLAS=noblas mix deps.compile
```

`MATREX_BLAS=noblas` evita exigir OpenBLAS quando o projeto usa a PolyHok com
`Nx`. Se operações BLAS do Matrex forem necessárias, instale
`libopenblas-dev` e compile com a implementação BLAS apropriada.

Execute os dois conjuntos de testes que não dependem de GPU:

```bash
python/.venv/bin/python -m pytest python/tests -q
mix test --exclude gpu
```

O gate de build local também verifica lint, formatação e warnings:

```bash
python/.venv/bin/python -m ruff check python
mix format --check-formatted
mix compile --warnings-as-errors
```

## Preparar uma cena

Coloque um produto em
`fixtures/sentinel-2/scenes/<scene-id>/source/<product-id>.SAFE/` e execute:

```bash
python/.venv/bin/sentinel2-prepare \
  --safe fixtures/sentinel-2/scenes/<scene-id>/source/<product-id>.SAFE \
  --root . \
  --source-uri <origem-do-produto>
```

`--safe` e `--root` são obrigatórios; `--source-uri` é opcional. Sucesso encerra
com status `0` e escreve em stdout um JSON com `status`, `scene_id` e `reused`.
Falhas encerram com status diferente de zero e escrevem um diagnóstico JSON em
stderr.

A publicação cria três diretórios sob
`fixtures/sentinel-2/scenes/<scene-id>/prepared/`: `1024x1024`, `4096x4096` e
`8192x8192`. Cada diretório contém `b04.f32`, `b08.f32`, `metadata.json` e
`preview.png`. O `manifest.json` é atualizado somente após a validação dos três
recortes.

## Orquestrar e ler pelo Elixir

Inicie a aplicação com `iex -S mix` e use a API componível:

```elixir
alias PolyhokSentinel2ParallelAnalysis.Sentinel2.Preparation
alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader

scene = %{
  scene_id: "s2a-t22jcp-20240830t132241",
  safe_path: "fixtures/sentinel-2/scenes/s2a-t22jcp-20240830t132241/source/product.SAFE"
}

{:ok, prepared_scene} = Preparation.prepare(scene, project_root: File.cwd!())
{:ok, %{b04: b04, b08: b08}} =
  PreparedReader.read_crop(File.cwd!(), hd(prepared_scene.crops))
```

`Preparation.prepare/2` retorna somente `{:ok, prepared_scene}` ou
`{:error, reason}`. Ela mantém matrizes no sistema de arquivos, aguarda o status
do processo Python e valida manifesto, metadados, tamanhos e checksums antes do
sucesso. Uma segunda chamada ativa para o mesmo `scene_id` retorna
`{:error, :already_running}`.

Uma saída existente só é reutilizada quando fonte, metadados, tamanhos e
checksums continuam válidos. Altere a fonte ou remova/corrompa um artefato para
forçar regeneração. Arquivos `.partial` e cenas sem entrada preparada no
manifesto são ignorados. Consulte
`fixtures/sentinel-2/README.md` para as regras de versionamento dos fixtures.

## Teste CUDA opcional

O teste `test/poly_hok_test.exs` envia um tensor Nx para a GPU com
`PolyHok.new_gnx/1`, copia o resultado de volta com `PolyHok.get_gnx/1` e
confirma seus valores, tipo e formato.

O teste precisa ser executado em um ambiente com acesso à GPU NVIDIA; sandboxes
ou contêineres sem acesso ao dispositivo CUDA não conseguem executá-lo. Ele não
faz parte dos gates de CPU e deve ser selecionado explicitamente:

```bash
mix test --include gpu test/poly_hok_test.exs
```
