# Fixtures Sentinel-2

Este diretório mantém o índice versionado e os metadados necessários para reproduzir as matrizes usadas pelos benchmarks. Produtos e artefatos grandes permanecem locais.

## Adicionar uma fonte

Coloque um único produto L2A em:

```text
scenes/<scene-id>/source/<product-id>.SAFE/
```

O `scene-id` é derivado da identidade do produto pelo preparador. O diretório `source/` e os arquivos JP2/TIFF são ignorados pelo Git.

## Preparar a cena

Com o ambiente Python instalado, execute a partir da raiz do projeto:

```bash
python/.venv/bin/sentinel2-prepare \
  --safe fixtures/sentinel-2/scenes/<scene-id>/source/<product-id>.SAFE \
  --root . \
  --source-uri <origem-do-produto>
```

O preparador grava três recortes em `scenes/<scene-id>/prepared/` e atualiza `manifest.json` somente depois de validar todos eles.

## Controle de versão

Versione:

- `README.md` e `manifest.json`;
- cada `source.json`;
- cada `prepared/<tamanho>/metadata.json`.

Não versione produtos `.SAFE`, JP2/TIFF, matrizes `.f32`, previews PNG, ambientes virtuais nem arquivos `.tmp`/`.partial`. Esses arquivos são gerados localmente e já estão cobertos pelo `.gitignore` do projeto.
