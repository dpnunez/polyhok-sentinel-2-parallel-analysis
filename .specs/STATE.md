# STATE

## Decisions

### AD-001
- **Decision**: O Elixir orquestrará a preparação em um processo Python externo, e os artefatos no sistema de arquivos serão a única fronteira para matrizes e metadados.
- **Reason**: A fronteira evita copiar matrizes de até 512 MiB pelo protocolo do processo e mantém o produtor Python e o consumidor Elixir testáveis de forma independente.
- **Trade-off**: O contrato de arquivos e sua validação precisam ser mantidos explicitamente nas duas linguagens.
- **Scope**: Preparação Sentinel-2 e futuras etapas locais que consumam os artefatos preparados.
- **Date**: 2026-08-20
- **Status**: active

### AD-002
- **Decision**: Uma cena só será observável como preparada depois da publicação atômica dos artefatos validados e da atualização final do manifesto.
- **Reason**: O manifesto funciona como ponto único de commit e impede que falhas parciais liberem entradas incompletas para a pipeline.
- **Trade-off**: Arquivos finais órfãos podem permanecer após uma interrupção, mas serão ignorados e substituídos na próxima preparação.
- **Scope**: Escrita, reutilização e leitura dos fixtures Sentinel-2.
- **Date**: 2026-08-20
- **Status**: active

## Handoff

- **Feature**: sentinel-2-data-preparation
- **Phase / Task**: execução e verificação concluídas
- **Completed**: T1-T15, correções ORCH-10/SAFE-07 e validação independente PASS
- **In-progress** (file:line): none
- **Next step**: integrar ou revisar a feature conforme o fluxo do projeto
- **Blockers**: none
- **Uncommitted files**: none after the validation commit
- **Branch**: feat/prepare-data-pipe
