---
name: parecer-administrativo
description: Redige parecer jurídico curto de Direito Administrativo (ex.: nepotismo em cargo em comissão) citando SOMENTE fontes da ontologia validada pelo especialista (ontologia/fontes.json), no formato de citação padronizado. Use sempre que pedirem parecer, nota técnica ou manifestação jurídica neste projeto.
---

# Parecer administrativo (guia macio do HNV)

Esta skill é a camada **inferencial / macia** do Harness Neurossimbólico Vertical:
orienta o modelo. A camada **dura** é o hook `harness/verificar_citacoes.py`, que
roda automaticamente depois de cada Write/Edit em `saida/parecer*.md` e **bloqueia**
qualquer citação que não esteja na ontologia.

## Passo 1 - Ler a ontologia antes de escrever

Leia `ontologia/fontes.json`. Só podem ser citadas as instâncias listadas lá
(campo `citacao`). Use o campo `texto` para não distorcer o conteúdo da fonte.

## Passo 2 - Formato de citação (obrigatório)

Cite sempre entre colchetes, exatamente como no campo `citacao`:

- `[CF/88, art. 37, caput]`, `[CF/88, art. 37, II]`, `[CF/88, art. 37, V]`, `[CF/88, art. 37, § 4º]`
- `[STF, Súmula Vinculante 13]`
- `[STF, ADC 12]`, `[STF, RE 579.951]`
- `[Lei 8.429/1992, art. 11, caput]`, `[Lei 8.429/1992, art. 11, XI]`
- `[Decreto 7.203/2010, art. 1º]`, `[Decreto 7.203/2010, art. 2º, III]`, `[Decreto 7.203/2010, art. 3º, caput]`,
  `[Decreto 7.203/2010, art. 3º, I]`, `[Decreto 7.203/2010, art. 3º, § 1º]`, `[Decreto 7.203/2010, art. 4º, I]`

Regras:
1. **Nunca** cite fonte fora da ontologia, nem de memória (súmula, acórdão, REsp, lei, resolução, doutrina).
2. Evite mencionar números de normas ou artigos fora dos colchetes; o verificador também
   lê citações soltas ("art.", "Súmula nº", "RE", "ADI", "Lei nº") e bloqueia as que não reconhece.
3. Se a ontologia não cobrir um ponto, escreva: "ponto não coberto pelas fontes validadas;
   requer análise do especialista". Isso é melhor que inventar.
4. O Decreto 7.203/2010 vale para a **administração pública federal**; para município,
   use-o só como referência comparativa e diga isso.

## Passo 3 - Estrutura do parecer (curto, até ~1 página)

```
# Parecer nº XX/2026 - <assunto>

**Interessado:** ...  **Assunto:** ...

## 1. Relatório
(2-3 linhas com os fatos)

## 2. Fundamentação
(parágrafos curtos; cada afirmação jurídica com sua citação padronizada)

## 3. Conclusão
(resposta direta: permitido / vedado / depende de ...)

---
Status: minuta gerada com apoio de ferramenta - aguardando aprovação humana do especialista.
```

## Passo 4 - Gravar e reagir ao harness

- Grave em `saida/parecer.md` (ou `saida/parecer-<tema>.md`).
- Se o hook devolver **"HNV · BLOQUEIO"**, leia a lista de citações bloqueadas, corrija
  o arquivo e grave de novo. Repita até receber **"HNV · OK"**.
- Não tente desativar, contornar ou editar o hook, o verificador ou a ontologia.
- Ao final, informe o caminho do log de proveniência (`logs/prov-*.json`) e que o parecer
  está **aguardando aprovação humana** (liberação depende do especialista).
