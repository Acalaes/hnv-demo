# CONABOM 2026: HNV (harness) aplicado às automações n8n do CBMSC

Registro da conversa de 28/10/2026. Material-base para os slides da palestra no CONABOM
(26-27/11/2026, Balneário Camboriú/SC, palestras de 45 min).

## Ideia central
O Harness Neurossimbólico Vertical (HNV, artigo CIKI 2026) pode ser aplicado a um segundo domínio:
a construção de fluxos n8n do CBMSC. O domínio vertical deixa de ser o Direito Administrativo e passa
a ser "fluxo de automação do CBMSC".

Fórmula do HNV: `Liberação = (Evidência ∧ Norma ∧ Rastreabilidade) ∧ aprovação humana`.

## Dois usos (slide de 2ª camada: "O Cockpit é um harness?")

### Uso 1: harness para CONSTRUIR fluxos n8n (encaixe forte)
- Camada macia (já existe): regras obrigatórias escritas no replit.md do app "CBMSC Governança de Automação Inteligente".
- Camada dura (falta): verificador que lê o JSON do fluxo e bloqueia (`exit 2`) quando viola regra.
- Regras candidatas: sem token/segredo no JSON (só nome de credencial, doutrina F-X.B); sem URL no texto ao
  cidadão (anti-ban); sem Wait acima de 65 s; sem a palavra "UDESC"; "atestados" só como renovação de
  funcionamento; credencial e parâmetro DMN existentes; `modo_teste` com padrão seguro.
- Ganho: o modelo erra, o hook devolve o motivo, o modelo corrige. Menos erro chegando à revisão ou à produção.
  (Ganho de velocidade não medido.)

### Uso 2: o Cockpit como harness das automações (parcial)

| Peça do HNV | No seu Cockpit |
|---|---|
| Regra dura | Trava de aquecimento, teto diário, reserva atômica no banco, Porteiro DMN |
| Rastro | Diário de Bordo, logs de erro, Central de SQLs |
| Humano libera | O JSON gerado é "entregue ao motor" e o usuário importa à mão no n8n |
| Segredo fora | Credencial por nome |

**Diferença:** isso é governança de **execução** das automações. O harness do artigo cerca um **modelo de
linguagem**. O encaixe exato fica nos módulos **Captura** (BPMN por IA) e **Construção** (gerador de JSON).
Neles a IA age, e eles merecem a regra dura. Código desses dois módulos NÃO foi lido: não se sabe se já
validam o JSON de forma bloqueante.

## Cuidado de arquitetura
O Replit Agent não tem hooks. O verificador deve ser uma função independente (script Python ou TypeScript no
Express), chamada pelo hook do Claude Code, pelo gerador "Construção" e por um passo antes do commit.

## Próximo passo proposto (protótipo)
1. `regras_cbmsc.json` com ~8 regras.
2. `validar_fluxo_n8n.py` (lê o JSON, aplica regras, `exit 2` com o motivo).
3. Teste: fluxos SAINA reais devem passar; um fluxo sabotado deve ser barrado.

## Como usar nos slides
- Slide de 2ª camada (detalhe): a tabela acima + a frase "Diferença".
- Slide principal: "Regras viram código: o harness bloqueia o erro antes da produção".
- Ponte jurídica: princípio da legalidade (só se faz o que a regra autoriza), agora executável.
- Fio HKS: prova de generalização do HNV (Direito → automação pública de segurança).

## Fontes (onde conferir)
- Replit "CBMSC Governança de Automação Inteligente": replId 3ebf0d61-5203-4d04-8305-7d9c0d70c55d (replit.md, doutrina Cockpit + Motor).
- Replit "N8nCodeFlows": replId 7df01792-6c49-49d4-9733-22a196d35b0e.
- Repositório `Acalaes/hnv-demo` (demo executável do HNV) e `Acalaes/CBMSC-Portal`.
