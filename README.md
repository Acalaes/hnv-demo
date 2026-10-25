# HNV demo: Harness Neurossimbólico Vertical

Esta é a demonstração executável do artigo apresentado no **CIKI 2026** (28/10/2026).
Autor: **Alexandre Pinto Calaes**, advogado, economista e doutorando em Engenharia do Conhecimento (UFSC).

Um *harness* de agente é o "arreio" em volta do modelo de linguagem: as instruções, as ferramentas,
os ganchos (*hooks*) e os registros que controlam o que o agente faz. Esta demo usa o **Claude Code**
como harness. Ela acrescenta uma **camada simbólica vertical**, ou seja, de um domínio específico
(Direito Administrativo / setor público). Quem define essa camada é o especialista.

```
Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade
Liberação       = Admissibilidade ∧ aprovação Humana
```

## Arquitetura

```
 pedido do servidor
        │
        ▼
┌──────────────────────────────┐   guia macio (inferencial)
│ Claude Code (modelo neural)  │◄── .claude/skills/parecer-administrativo/SKILL.md
│  lê a ontologia e escreve    │◄── CLAUDE.md
└──────────────┬───────────────┘
               │ Write/Edit saida/parecer*.md
               ▼
┌──────────────────────────────┐   regra dura (computacional)
│ hook PostToolUse             │   .claude/settings.json
│  harness/verificar_citacoes  │──► consulta ontologia/fontes.json
│  extrai e confere citações   │    (Norma, Dispositivo, Súmula, Precedente;
└──────┬────────────────┬──────┘     fundamenta / regulamenta / parteDe)
  exit 2 (stderr)    exit 0
  BLOQUEIO           OK
       │                │
       ▼                ▼
 volta ao modelo   logs/prov-*.json  (W3C PROV-JSON: entity, activity, agent,
 que corrige       wasDerivedFrom → cada fonte com URL oficial)
                        │
                        ▼
              "aguardando aprovação humana"
                        │
                        ▼
       harness/aprovar.py  (especialista)  →  Liberação
```

## Mapa harness ↔ neurossimbólico

| Peça do harness | Camada | Papel |
|---|---|---|
| `SKILL.md` + `CLAUDE.md` | guia **macio** (inferencial) | orienta o modelo: formato do parecer, citar só a ontologia |
| hook + `verificar_citacoes.py` | regra **dura** (computacional) | bloqueia, sem negociação, citação fora da ontologia (exit 2) |
| `ontologia/fontes.json` | conhecimento **simbólico** do especialista | fontes reais conferidas em planalto.gov.br e portal.stf.jus.br |
| `logs/prov-*.json` | **rastreabilidade** | quem gerou, o que foi usado, de que fontes o parecer deriva |
| `aprovar.py` (humano) | **liberação** | só o especialista libera; a máquina no máximo declara "admissível" |

## O que foi executado (25/10/2026, Windows 10, 8 GB RAM, sem GPU)

| Cena | O que roda | Resultado real |
|---|---|---|
| 1 · sem harness | `qwen2.5:3b` local (Ollama), 3 pedidos naturais | As 3 rodadas trazem citação inexistente ou com conteúdo falso. Exemplo: "art. 37, inciso XXXIII, da CF", que não existe, porque o art. 37 vai só até o inciso XXII. Detalhes em `logs/cena1/checagem_manual.json` |
| 2a · com HNV | `claude -p` (Sonnet) com skill + hook | O parecer cita 13 fontes, todas da ontologia; o hook respondeu **OK** de primeira |
| 2b · com HNV | Claude Code recebe o rascunho alucinado da cena 1 | Na 1ª gravação, o hook deu **exit 2 (BLOQUEIO)**. O modelo corrigiu e o hook deu **OK** |
| bônus · laço local | `harness/laco_local.py` (Ollama), até 3 rodadas | Citações bloqueadas por rodada: 3 → 3 → 1. Não convergiu, e o parecer **não foi liberado** |

Replay animado de ~87 s, gerado só a partir dos logs: `replay/index.html`. Abra no navegador.
Parâmetros: `?v=2` deixa 2x mais rápido; `?t=40` começa no segundo 40; espaço pausa; R reinicia.

## Como rodar

Requisitos: Python 3.11+ (`py`), Git Bash, [Ollama](https://ollama.com) e Claude Code.

```bash
# 1) modelo local
ollama pull qwen2.5:3b

# 2) cena 1 (sem harness)
py -I -X utf8 cenas/cena1_sem_harness.py --rodada 1

# 3) verificador sozinho (a mesma regra dura do hook)
py -I -X utf8 harness/verificar_citacoes.py logs/cena1/parecer_cena1_rodada1.md   # exit 2
py -I -X utf8 harness/verificar_citacoes.py saida/parecer.md                       # exit 0

# 4) cena 2 (Claude Code headless, grava stream-json com eventos de hook)
bash cenas/cena2_claude.sh a      # pedido natural
bash cenas/cena2_claude.sh b      # rascunho alucinado → bloqueio → correção

# 5) laço local gerar → verificar → corrigir
py -I -X utf8 harness/laco_local.py

# 6) aprovação humana (só o especialista; recusa se não for admissível ou se o arquivo mudou)
py -I -X utf8 harness/aprovar.py logs/prov-<...>.json --aprovador "Nome do especialista"

# 7) replay
py -I -X utf8 replay/gerar_replay.py
```

## Limitações (honestas)

- **Ontologia pendente de validação.** O texto de cada fonte foi conferido literalmente nas páginas
  oficiais em 25/10/2026. Mesmo assim, o campo `status` continua "pendente de validação" até o especialista revisar.
- **Fora da ontologia ≠ inexistente.** O verificador bloqueia fonte real não validada, como a Lei 8.112/1990
  ou a Resolução CNJ 7/2005. Isso é proposital (lista fechada), e a mensagem diz "não consta na ontologia".
  Ela não diz "é falsa".
- **Confere a citação, não o raciocínio.** No laço local, a rodada 3 aplica o Decreto 7.203/2010 (federal)
  a um município e fala em "cargos que exigem licitação". Nenhuma das duas falhas é de citação, e o
  verificador não as pega. É por isso que a liberação depende do humano.
- **Referências vagas escapam.** "Uma decisão do STJ", sem número, não é capturada pelos padrões de regex.
- **Regex, não parser jurídico.** Os padrões cobrem os formatos comuns ("art.", "Súmula nº", "RE", "ADI",
  "Lei nº", "Tema"), mas não todos.
- **Cena 2b é induzida.** Na 2a, o Claude não errou nenhuma citação. Para mostrar o bloqueio *dentro* do
  Claude Code, a 2b entrega ao agente o rascunho real (alucinado) da cena 1 e pede que ele seja gravado e
  corrigido. O bloqueio e a correção são execução real (`logs/cena2b/stream.jsonl`).
- Os logs do stream foram **sanitizados**: o evento `init` perde a lista de MCPs, plugins e skills pessoais.
  Mensagens, ferramentas e hooks ficam intactos.

## Estrutura

```
ontologia/fontes.json        classes, relações e instâncias reais com URL oficial
.claude/settings.json        hook PostToolUse (Write|Edit|MultiEdit) + deny para harness/ e ontologia/
.claude/skills/...           guia macio do parecer
harness/                     verificar_citacoes.py, laco_local.py, aprovar.py
cenas/                       cena1_sem_harness.py, cena2_claude.sh, sanitizar_stream.py
saida/                       pareceres gerados pelo Claude Code
logs/                        cena1/, cena2/, cena2b/, laco/, prov-*.json
replay/                      template.html, gerar_replay.py, index.html
testes/caso_misto.md         casos de borda do verificador
```
