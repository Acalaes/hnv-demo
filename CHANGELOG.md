# Changelog

## v0.1.0 - 2026-10-25

- Ontologia mínima com fontes reais conferidas em fonte oficial: CF/88 art. 37 (caput, II, V, § 4º),
  STF Súmula Vinculante 13, ADC 12, RE 579.951 (Tema 66), Lei 8.429/1992 art. 11 (caput e XI) e
  Decreto 7.203/2010 (arts. 1º, 2º III, 3º caput, I e § 1º, 4º I).
- Verificador de citações (padronizadas e soltas) com a fórmula Evidência ∧ Norma ∧ Rastreabilidade,
  saída exit 2 para bloqueio, falha fechada e log W3C PROV-JSON.
- Hook PostToolUse no Claude Code e skill `parecer-administrativo`.
- Cena 1 (qwen2.5:3b sem harness), cena 2a/2b (Claude Code com hook real), laço local e aprovação humana.
- Replay animado a partir dos logs reais (`replay/index.html`).
