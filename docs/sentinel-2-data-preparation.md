# Preparação mínima dos dados Sentinel-2 para cálculo posterior de NDVI

## 1. Objetivo

Esta etapa não calcula NDVI. Seu único objetivo é transformar um produto
Sentinel-2 Level-2A (`.SAFE`) em duas matrizes numéricas prontas para serem usadas,
posteriormente, pelo código que executará o NDVI na GPU:

```text
B04 preparada ─┐
               ├── entrada futura do cálculo de NDVI
B08 preparada ─┘
```

A preparação deve ser agnóstica à linguagem de programação. Não importa se ela for
implementada em Python ou outra linguagem, desde que produza as duas matrizes no
contrato descrito neste documento.

Nesta primeira versão não serão usados SCL, máscaras de nuvens, AOT, WVP, outras
bandas ou produtos derivados.

## 2. Entrada

A entrada é um produto Sentinel-2 **L2A** no formato `.SAFE`.

Para cada produto, somente quatro arquivos precisam ser lidos:

```text
<produto>.SAFE/
├── MTD_MSIL2A.xml
└── GRANULE/
    └── <granule>/
        ├── MTD_TL.xml
        └── IMG_DATA/R10m/
            ├── *_B04_10m.jp2
            └── *_B08_10m.jp2
```

Função de cada arquivo:

| Arquivo | Informação utilizada |
| --- | --- |
| `*_B04_10m.jp2` | valores da banda vermelha |
| `*_B08_10m.jp2` | valores da banda infravermelha próxima |
| `MTD_MSIL2A.xml` | identificação, quantificação, offsets e valores especiais |
| `MTD_TL.xml` | dimensões, resolução, CRS e posição da grade |

## 3. Arquivos usados no produto de exemplo

No sample fornecido, as duas bandas estão em:

```text
GRANULE/L2A_T22HCK_A009346_20260620T133149/IMG_DATA/R10m/
  T22HCK_20260620T133151_B04_10m.jp2
  T22HCK_20260620T133151_B08_10m.jp2
```

As duas imagens têm a mesma grade:

| Propriedade | Valor observado |
| --- | --- |
| tile | T22HCK |
| resolução | 10 m |
| largura | 10.980 pixels |
| altura | 10.980 pixels |
| CRS | EPSG:32722 — WGS 84 / UTM 22S |
| origem | 300000, 6500020 |
| tamanho do pixel | 10 m × -10 m |

Por isso, cada posição `[linha, coluna]` de B04 corresponde à mesma localização em
B08. Não é necessário reamostrar nenhuma das duas bandas.

## 4. Dados que devem ser extraídos

Extrair somente:

1. os valores de B04 em 10 m;
2. os valores de B08 em 10 m;
3. os metadados mínimos necessários para interpretar e reproduzir as matrizes.

Antes de salvar, confirmar que B04 e B08 possuem:

- a mesma largura e altura;
- o mesmo CRS;
- a mesma origem;
- o mesmo tamanho de pixel;
- a mesma extensão espacial.

Se alguma dessas propriedades for diferente, o produto não deve ser preparado
silenciosamente. A inconsistência deve ser registrada como erro.

## 5. Conversão dos valores

Os pixels armazenados nos JP2 são números digitais inteiros (`DN`), e não os valores
finais de refletância. A preparação deve convertê-los para refletância de superfície:

```text
refletância = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE
```

Os valores de `BOA_ADD_OFFSET` e `BOA_QUANTIFICATION_VALUE` devem ser lidos do
`MTD_MSIL2A.xml`, e não escritos como constantes da implementação.

No sample fornecido:

```text
BOA_ADD_OFFSET = -1000
BOA_QUANTIFICATION_VALUE = 10000

B04_preparada = (DN_B04 - 1000) / 10000
B08_preparada = (DN_B08 - 1000) / 10000
```

Essa conversão faz parte da preparação, não do cálculo de NDVI. Assim, o cenário
posterior na GPU receberá diretamente duas matrizes de refletância e executará apenas
a operação numérica que estiver sendo avaliada.

### 5.1 Valores sem dados ou saturados

No sample, os metadados declaram:

```text
NODATA = 0
SATURATED = 65535
```

Quando um desses valores ocorrer em B04 ou B08, a posição correspondente deve ser
gravada como `NaN` nas **duas** matrizes preparadas. Isso evita criar uma terceira
matriz de máscara e mantém as entradas com formas idênticas.

Exemplo:

```text
se DN_B04 ou DN_B08 for NODATA ou SATURATED:
    B04_preparada = NaN
    B08_preparada = NaN
senão:
    converter B04 e B08 para refletância
```

Não calcular NDVI, não substituir o pixel por zero e não limitar a refletância ao
intervalo `[0, 1]` durante esta etapa.

## 6. Recortes do benchmark

Para cada cena, a preparação deve produzir exatamente três tamanhos de entrada:

| Classe | Dimensões | Quantidade de pixels | Tamanho de B04 + B08 em `float32` |
| --- | ---: | ---: | ---: |
| pequena | 1.024 × 1.024 | 1.048.576 | 8 MiB |
| média | 4.096 × 4.096 | 16.777.216 | 128 MiB |
| grande | 8.192 × 8.192 | 67.108.864 | 512 MiB |

Os três tamanhos são recortes das bandas B04 e B08 de 10 m. Eles não correspondem
aos diretórios `R10m`, `R20m` e `R60m` do produto Sentinel-2. Não deve haver mudança
de resolução, redimensionamento ou reamostragem.

### 6.1 Posição dos recortes

Os recortes devem ser centralizados no tile e aninhados: a área de 1.024 × 1.024
fica dentro da área de 4.096 × 4.096, que fica dentro da área de 8.192 × 8.192. Isso
mantém uma região comum entre as três classes e torna a seleção determinística.

Considerando índices de linha e coluna iniciados em zero, o deslocamento é:

```text
row_offset    = floor((tile_height - crop_height) / 2)
column_offset = floor((tile_width  - crop_width)  / 2)
```

Para o sample, cuja grade possui 10.980 × 10.980 pixels:

| Dimensões | Linha inicial | Coluna inicial |
| ---: | ---: | ---: |
| 1.024 × 1.024 | 4.978 | 4.978 |
| 4.096 × 4.096 | 3.442 | 3.442 |
| 8.192 × 8.192 | 1.394 | 1.394 |

A mesma janela deve ser aplicada a B04 e B08. O deslocamento, a largura e a altura
devem ser registrados no `metadata.json`. Se uma cena não comportar algum dos três
tamanhos, a preparação deve falhar explicitamente para essa cena.

## 7. Organização dos dados no projeto

Todos os dados relacionados à preparação devem ficar sob
`fixtures/sentinel-2/`. A estrutura definida para a primeira versão é:

```text
fixtures/sentinel-2/
├── README.md                         # versionado
├── manifest.json                     # versionado: lista de cenas preparadas
└── scenes/
    └── <scene-id>/
        ├── source.json               # versionado: origem e identidade do .SAFE
        ├── source/                   # ignorado: produto .SAFE completo
        │   └── <product-id>.SAFE/
        └── prepared/
            ├── 1024x1024/
            │   ├── b04.f32           # ignorado: matriz binária
            │   ├── b08.f32           # ignorado: matriz binária
            │   ├── metadata.json     # versionado
            │   └── preview.png       # ignorado: visualização para debug
            ├── 4096x4096/
            │   ├── b04.f32           # ignorado
            │   ├── b08.f32           # ignorado
            │   ├── metadata.json     # versionado
            │   └── preview.png       # ignorado
            └── 8192x8192/
                ├── b04.f32           # ignorado
                ├── b08.f32           # ignorado
                ├── metadata.json     # versionado
                └── preview.png       # ignorado
```

O nome `<scene-id>` deve ser estável e derivado do ID do produto, sem depender do
caminho local. Por exemplo:

```text
s2c-t22hck-20260620t133151
```

`manifest.json` funciona como índice do dataset: identifica as cenas aceitas, seus
três recortes, os caminhos dos metadados e o estado da preparação. `source.json`
registra o ID integral do produto, a origem de download e o checksum do pacote-fonte.

### 7.1 Formato das matrizes preparadas

Para eliminar ambiguidade entre linguagens, `b04.f32` e `b08.f32` serão arquivos
binários sem cabeçalho com:

- valores IEEE 754 `float32`;
- ordem de bytes little-endian;
- armazenamento row-major: todos os valores da primeira linha, depois da segunda;
- exatamente `width × height` elementos;
- `NaN` nas posições inválidas, igualmente nas duas bandas.

O contrato da saída é:

| Campo | Requisito |
| --- | --- |
| B04 | matriz bidimensional de refletância `float32` |
| B08 | matriz bidimensional de refletância `float32` |
| forma | idêntica nas duas matrizes |
| ordem | linhas e colunas na mesma ordem dos JP2 |
| inválidos | `NaN` na mesma posição em ambas as matrizes |

### 7.2 Metadados mínimos da saída

O `metadata.json` deve registrar:

```text
product_id
tile_id
sensing_time_utc
size_class                # small, medium ou large
source_b04
source_b08
width
height
data_type                 # float32
byte_order
memory_order              # por exemplo: row-major
crs
pixel_size
origin
row_offset
column_offset
boa_offset_b04
boa_offset_b08
boa_quantification_value
source_nodata_value
source_saturated_value
checksum_b04_prepared
checksum_b08_prepared
```

Esses campos permitem que outra linguagem leia os arrays sem depender da ferramenta
que realizou a extração. Os caminhos registrados devem ser relativos à raiz do
projeto, nunca caminhos absolutos da máquina que preparou os dados.

### 7.3 PNG para inspeção visual

Cada um dos três recortes deve gerar um único `preview.png` para depuração visual.
Esse arquivo não é entrada do cálculo, não substitui as matrizes `.f32` e não deve
ser usado para obter valores numéricos.

O PNG deve apresentar dois painéis em escala de cinza:

```text
┌──────────────────┬──────────────────┐
│       B04        │       B08        │
│    vermelho      │ infravermelho    │
└──────────────────┴──────────────────┘
```

Regras da visualização:

- B04 à esquerda e B08 à direita;
- cada painel mantém a proporção quadrada do recorte;
- cada painel é reduzido para no máximo 1.024 × 1.024 pixels;
- os valores de cada banda são escalados independentemente apenas para exibição;
- usar os percentis 2 e 98 dos valores finitos como limites de contraste;
- valores `NaN` são exibidos em preto;
- a redução e o ajuste de contraste afetam somente o PNG, nunca os `.f32`.

Assim, inclusive para o recorte de 8.192², o `preview.png` terá no máximo
2.048 × 1.024 pixels. O PNG pode conter os rótulos `B04` e `B08`, mas não precisa
preservar georreferenciamento.

### 7.4 O que deve e não deve entrar no Git

Não faz sentido ignorar tudo. Os arquivos grandes são regeneráveis e devem ficar
fora do repositório; os arquivos pequenos que descrevem como reproduzi-los devem ser
versionados.

Deve ser **versionado**:

- esta documentação;
- `fixtures/sentinel-2/README.md`;
- `fixtures/sentinel-2/manifest.json`;
- cada `source.json`;
- cada `metadata.json`;
- futuramente, o código de preparação e seus testes.

Deve ser **ignorado pelo Git**:

- produtos `.SAFE` completos dentro de `source/`;
- imagens-fonte ou intermediárias JP2, TIFF/GeoTIFF;
- matrizes preparadas `.f32`;
- arquivos `preview.png` gerados para debug;
- arrays alternativos `.bin`, `.npy` ou `.npz`, caso sejam produzidos durante testes;
- arquivos parciais ou temporários dentro de `fixtures/sentinel-2/`;
- arquivos `.DS_Store` do macOS.

Bloco correspondente do `.gitignore`:

```gitignore
# macOS
.DS_Store

# Full local Sentinel-2 products
/fixtures/sentinel-2/**/source/

# Large source/intermediate raster files
/fixtures/sentinel-2/**/*.jp2
/fixtures/sentinel-2/**/*.tif
/fixtures/sentinel-2/**/*.tiff

# Generated numeric arrays
/fixtures/sentinel-2/**/*.f32
/fixtures/sentinel-2/**/*.bin
/fixtures/sentinel-2/**/*.npy
/fixtures/sentinel-2/**/*.npz

# Generated debug previews
/fixtures/sentinel-2/**/prepared/**/preview.png

# Incomplete preparation files
/fixtures/sentinel-2/**/*.tmp
/fixtures/sentinel-2/**/*.partial
```

Não ignorar o diretório `prepared/` inteiro, pois isso também esconderia os
`metadata.json`. Os metadados e checksums versionados permitem verificar e reconstruir
as matrizes que ficaram fora do Git.

## 8. Componentes do `.SAFE` que não serão extraídos

Na primeira versão, não copiar para o dataset preparado:

- SCL em 20 m ou 60 m;
- máscaras de nuvem, neve, qualidade ou detector;
- B01, B02, B03, B05, B06, B07, B09, B11, B12 e B8A;
- cópias de B04 em 20 m ou 60 m;
- AOT, WVP e TCI;
- previews, quicklooks e PVI fornecidos no `.SAFE`;
- `HTML/`, `DATASTRIP/`, `AUX_DATA/`, `rep_info/` e relatórios de qualidade.

Esses arquivos podem continuar no produto `.SAFE` original, mas não integram a saída
preparada para a GPU.

## 9. Fluxo completo da primeira versão

```text
1. localizar B04_10m e B08_10m
2. ler os metadados radiométricos e espaciais
3. confirmar que as duas bandas estão alinhadas
4. ler as duas imagens como matrizes
5. calcular as janelas centralizadas de 1024², 4096² e 8192²
6. aplicar cada janela igualmente a B04 e B08
7. substituir pares NoData/saturados por NaN
8. converter os demais DN para refletância float32
9. salvar b04.f32, b08.f32 e metadata.json para cada tamanho
10. gerar um preview.png de debug para cada tamanho
11. reler as saídas numéricas e validar dimensões, tipo e checksums
```

O processo termina nesse ponto. O cálculo de NDVI e a transferência das matrizes
para GPU pertencem a outra etapa do projeto.

## 10. Critérios de aceite

Uma preparação está correta quando:

- usa B04 e B08 de 10 m do mesmo produto e tile;
- produz exatamente os recortes 1.024², 4.096² e 8.192²;
- centraliza os recortes conforme a fórmula documentada;
- aplica a mesma janela a B04 e B08;
- não realiza cálculo de NDVI;
- não usa SCL ou máscaras de nuvem;
- B04 e B08 preparadas são `float32` e têm exatamente a mesma forma;
- os valores foram convertidos com offset e quantificação lidos dos metadados;
- pixels NoData ou saturados são `NaN` nas duas matrizes;
- nenhum redimensionamento ou reamostragem foi aplicado;
- cada recorte possui um `preview.png` apenas para inspeção visual;
- a geração do PNG não modifica os arquivos `.f32`;
- os metadados descrevem como os arquivos devem ser lidos;
- a releitura dos arquivos preserva valores, dimensões e ordem dos pixels.

## 11. Fontes técnicas

- [SentiWiki — Sentinel-2 Products](https://sentiwiki.copernicus.eu/web/s2-products): definição do L2A e fórmula de conversão para refletância BOA.
- [Copernicus Data Space — Sentinel-2 L2A](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html): bandas, resoluções e unidades.
- [Sentinel-2 Products Specification Document 15.1](https://sentinels.copernicus.eu/documents/d/sentinel/sentinel-2-products-specification-document-15_1): especificação formal dos produtos e metadados.

Os valores numéricos específicos do sample foram lidos de seus arquivos
`MTD_MSIL2A.xml` e `MTD_TL.xml`; eles não devem ser tratados como constantes para
outros produtos.
