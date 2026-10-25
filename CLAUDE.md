# HNV demo - instruções do projeto

Este projeto é uma demonstração de Harness Neurossimbólico Vertical (HNV) para parecer
jurídico de Direito Administrativo.

- Para qualquer parecer, use a skill `parecer-administrativo`.
- Cite somente fontes de `ontologia/fontes.json`, no formato padronizado entre colchetes.
- Os pareceres vão para `saida/parecer*.md`. Um hook verifica cada gravação; se ele
  bloquear, corrija o arquivo e grave de novo.
- Não altere `harness/`, `ontologia/` nem `.claude/settings.json`.
- Nesta pasta, responda de forma curta e objetiva, sem blocos extras de estilo.
