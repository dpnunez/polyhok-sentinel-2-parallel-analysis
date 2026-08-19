# Contexto da Preparação de Dados Sentinel-2

**Gathered:** 2026-08-18
**Spec:** `.specs/features/sentinel-2-data-preparation/spec.md`
**Status:** Aguardando confirmação

---

## Feature Boundary

Esta feature implementa a preparação Sentinel-2 em Python 3, a execução supervisionada pelo Elixir, a validação dos artefatos antes do retorno de sucesso e uma leitura cruzada que comprova o acesso do Elixir. Ela termina antes do cálculo de NDVI e da transferência para GPU.

---

## Implementation Decisions

### Organização do repositório

- Elixir e Python permanecerão no mesmo repositório.
- O projeto Python ficará isolado sob `python/`, com manifesto de dependências, pacote em `src/` e testes próprios.
- As entradas e saídas continuarão sob `fixtures/sentinel-2/`, conforme a documentação existente.
- A estrutura antiga de fixtures foi removida e não terá migração nem compatibilidade.

### Fronteira entre Elixir e Python

- O Elixir será o orquestrador e o Python será o produtor dos artefatos.
- O processo externo transportará apenas argumentos, status e diagnósticos.
- Matrizes, previews e metadados serão compartilhados pelo sistema de arquivos.
- O Elixir aguardará o término do Python, validará os resultados e somente então retornará `{:ok, prepared_scene}`.
- Exit status `0` sem artefatos íntegros será tratado como erro.

### Continuidade da futura pipeline

- A API pública usará tagged tuples: `{:ok, prepared_scene}` ou `{:error, reason}`.
- A futura pipeline poderá compor essa API sequencialmente e só avançar no ramo `{:ok, ...}`.
- A pipeline completa, o NDVI e a GPU permanecem fora desta feature.

### Segurança operacional

- A escrita será temporária e a publicação será atômica.
- O manifesto será atualizado somente depois da validação dos três recortes.
- Uma saída existente será reutilizada apenas depois de validar fonte, metadados, tamanhos e checksums.
- Duas solicitações simultâneas para a mesma cena não escreverão os mesmos destinos.

### Agent's Discretion

- Escolha das bibliotecas Python para JP2/XML, arrays, checksums e PNG.
- Nomes exatos dos módulos Elixir e Python, mantendo as interfaces da especificação.
- Formato interno do descritor `prepared_scene`.
- Forma de injetar o executor de processo nos testes.
- Formatação dos logs e diagnósticos, sem incluir conteúdo das matrizes.

### Declined / Undiscussed Gray Areas → Assumptions

- Timeout padrão de 60 minutos, configurável.
- Python mínimo 3.11.
- Execução paralela de cenas diferentes não será implementada na primeira versão.
- Não haverá banco, fila persistente ou retomada automática após reinício da BEAM.
- O leitor Elixir comprovará acesso e interpretação, mas a estratégia final de memória/GPU será decidida com o NDVI.

---

## Specific References

- Contrato normativo: `docs/sentinel-2-data-preparation.md`.
- Arquitetura aprovada na conversa: mesmo repositório, Python chamado pelo Elixir e arquivos como fronteira de dados.

---

## Deferred Ideas

- Cálculo de NDVI e envio das matrizes para PolyHok/GPU.
- Progresso em tempo real pelo Port.
- Cancelamento forte da árvore de processos do sistema operacional.
- Preparação paralela de várias cenas.
- Download automático e catálogo de cenas.
