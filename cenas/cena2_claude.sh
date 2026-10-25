#!/usr/bin/env bash
# Cena 2 - COM HNV: Claude Code headless dentro do projeto (skill + hook + ontologia + PROV).
# Uso (terminal Git Bash, na raiz do projeto):  bash cenas/cena2_claude.sh [modelo]
set -u
cd "$(dirname "$0")/.."
MODELO="${1:-sonnet}"
mkdir -p logs/cena2/raw saida

PEDIDO='Sou servidor de uma prefeitura. O secretário municipal de Administração quer nomear o sobrinho da esposa dele para um cargo em comissão de assessor na própria secretaria. Escreva em saida/parecer.md um parecer jurídico curto dizendo se isso é permitido, com fundamentação na legislação e na jurisprudência.'

INICIO=$(date +%s)
# Variáveis da sessão "mãe" são removidas para o claude rodar como sessão nova e independente.
env -u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION \
    -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_CODE_ENTRYPOINT \
    -u CLAUDE_CODE_SESSION_ATTENDED -u CLAUDE_PID \
  claude -p "$PEDIDO" \
    --model "$MODELO" \
    --permission-mode acceptEdits \
    --setting-sources project,local \
    --strict-mcp-config \
    --max-turns 20 \
    --output-format stream-json --verbose --include-hook-events \
  > logs/cena2/raw/stream-raw.jsonl 2> logs/cena2/raw/stderr.txt
CODIGO=$?
FIM=$(date +%s)
echo "{\"modelo_pedido\": \"$MODELO\", \"exit\": $CODIGO, \"duracao_s\": $((FIM-INICIO)), \"pedido\": \"$PEDIDO\"}" > logs/cena2/execucao.json
py -I -X utf8 cenas/sanitizar_stream.py logs/cena2/raw/stream-raw.jsonl logs/cena2/stream.jsonl
echo "cena 2 terminou: exit=$CODIGO em $((FIM-INICIO)) s"
