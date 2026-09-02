# Contrato numérico do NDVI

**Status:** aprovado em 2 de setembro de 2026

## 1. Objetivo

Este documento define o comportamento numérico comum às implementações do cálculo
de NDVI usadas no projeto. Ele servirá como referência para uma especificação
posterior, mas não constitui uma especificação de feature nem define a arquitetura
completa da pipeline.

O contrato assegura que a implementação CUDA via PolyHok e a futura implementação
CUDA C/C++ direta executem a mesma operação sobre os mesmos dados. A pipeline final
usará exclusivamente a GPU para o cálculo de NDVI.

## 2. Entradas

O cálculo recebe duas matrizes bidimensionais:

- B04, correspondente à banda do vermelho;
- B08, correspondente à banda do infravermelho próximo.

As duas matrizes devem:

- conter valores de refletância de superfície já preparados;
- usar IEEE 754 `float32`;
- possuir exatamente a mesma forma `{altura, largura}`;
- manter a mesma ordem espacial dos pixels;
- usar organização row-major;
- representar pixels inválidos por `NaN`.

Tipo ou forma incompatível deve causar falha antes do acionamento da GPU. O cálculo
de NDVI não realiza conversão radiométrica, alinhamento, recorte, reamostragem ou
qualquer outra preparação geoespacial.

## 3. Operação numérica

Para cada posição correspondente das matrizes, o cálculo deve usar:

```text
denominador = B08 + B04
NDVI = (B08 - B04) / denominador
```

Toda a aritmética e a matriz de saída devem permanecer em `float32`. A implementação
não deve promover deliberadamente os operandos para `float64`.

## 4. Casos especiais

A política numérica aprovada é:

1. Se B04 ou B08 for `NaN`, o resultado da posição deve ser `NaN`.
2. Se `B08 + B04` for exatamente igual a `0.0f`, o resultado deve ser `NaN`.
3. Se o denominador for diferente de zero, ainda que muito próximo de zero, a
   divisão deve ser executada normalmente.
4. Nenhum epsilon deve ser adicionado ao denominador.
5. O resultado não deve ser limitado ao intervalo `[-1, 1]`.
6. Valores inválidos não devem ser substituídos por zero.
7. O cálculo não deve aplicar máscara de nuvens, classificação de vegetação ou
   outro tratamento temático.

A comparação com zero é exata em `float32`. Não existe, neste contrato, um limiar
para classificar denominadores pequenos como zero.

## 5. Execução na GPU

Cada thread deve processar no máximo uma posição da matriz. Em uma única execução
do kernel, a implementação deve:

1. verificar se o índice pertence aos limites da matriz;
2. ler B04 e B08;
3. calcular o denominador;
4. aplicar a política de `NaN` e denominador zero;
5. calcular e escrever o NDVI quando a posição for válida.

Não devem ser usados kernels separados para criar uma máscara, calcular o
denominador e calcular o NDVI. Transferências de memória não fazem parte do kernel
e permanecem etapas distintas da pipeline.

## 6. Saída

O resultado numérico deve ser uma matriz que:

- use IEEE 754 `float32`;
- tenha a mesma forma das matrizes de entrada;
- preserve a correspondência espacial de cada pixel;
- contenha `NaN` nas posições inválidas definidas neste contrato.

Ao final da pipeline, o resultado será transferido da GPU para o host. Imagens PNG,
histogramas, médias ou outros produtos derivados não fazem parte do resultado
numérico principal.

## 7. Fluxo delimitado

```text
B04 e B08 preparadas no host
            |
            v
transferência host -> GPU
            |
            v
kernel único de NDVI
            |
            v
transferência GPU -> host
            |
            v
matriz NDVI float32
```

A pipeline final não executará uma implementação CPU do NDVI e não comparará seus
resultados com a CPU durante o processamento normal.

## 8. Validação inicial

O protótipo será validado inicialmente com casos pequenos cujos resultados são
conhecidos previamente:

| B04 | B08 | Resultado esperado |
| ---: | ---: | ---: |
| `0.2` | `0.6` | `0.5` |
| `0.4` | `0.4` | `0.0` |
| `0.6` | `0.2` | `-0.5` |
| `-0.5` | `0.5` | `NaN` |
| `NaN` | `0.5` | `NaN` |
| `0.5` | `NaN` | `NaN` |

Esses casos não introduzem uma implementação CPU na pipeline. Eles apenas verificam
o comportamento observável do kernel contra resultados previamente determinados.

Uma implementação CPU de referência e a comparação integral dos recortes reais
ficam adiadas. Elas poderão ser acrescentadas ao final do trabalho se houver tempo,
mas não são requisito do protótipo inicial.

## 9. Compatibilidade com as medições futuras

Embora a instrumentação completa não faça parte deste contrato numérico, a
implementação posterior deve permitir medir separadamente:

- transferência host-GPU;
- chamada via PolyHok;
- execução do kernel de NDVI;
- transferência GPU-host;
- tempo total do fluxo.

O tempo de preparação dos dados deve continuar separado do tempo do kernel. A
implementação CUDA C/C++ direta deverá adotar este mesmo contrato numérico para que
as diferenças observadas sejam atribuíveis à forma de integração e execução, e não
a operações distintas.

## 10. Itens fora do escopo deste contrato

- implementação do kernel ou da pipeline;
- definição da API pública em Elixir;
- configuração de bloco e grid;
- execução em lote;
- persistência da matriz NDVI;
- geração de visualizações ou agregados;
- protocolo estatístico do benchmark;
- implementação CPU de referência;
- especificação formal da feature.
