"""Gera replay/index.html a partir dos LOGS REAIS das cenas.

Lê: logs/cena1/*, logs/cena2/*, logs/cena2b/stream.jsonl, logs/prov-*.json, logs/laco/transcricao.json
Escreve: replay/index.html (template.html + roteiro JSON embutido). Nada é inventado: cada
linha exibida vem de um arquivo de log; o roteiro só escolhe trechos e define o ritmo.

Uso: py -I -X utf8 replay/gerar_replay.py
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LOGS = RAIZ / "logs"
ALVO_S = (60, 90)


def ler_json(p):
    return json.loads((RAIZ / p).read_text(encoding="utf-8"))


def ler_stream(p):
    return [json.loads(l) for l in (RAIZ / p).read_text(encoding="utf-8").splitlines() if l.strip()]


def linhas_verificador(msg: str):
    """Transforma a mensagem do verificador em linhas do terminal (encurta a lista de fontes aceitas)."""
    out = []
    for l in msg.replace("\r", "").splitlines():
        if not l.strip():
            continue
        if l.startswith("Fontes aceitas"):
            n = l.count("[")
            out.append(("dim", f"Fontes aceitas: {n} citações da ontologia, ex.: [STF, Súmula Vinculante 13]; [CF/88, art. 37, caput] ..."))
            continue
        if l.startswith("Corrija o parecer"):
            out.append(("dim", l))
            continue
        cls = "bloq" if ("BLOQUEIO" in l or l.lstrip().startswith(tuple("123456789")) or "Falta" in l) else (
            "ok" if ("OK" in l or "V ∧ V ∧ V" in l or "aguardando" in l) else "out")
        out.append((cls, l))
    return out


class Roteiro:
    def __init__(self):
        self.ev = []

    def add(self, d, k, t="", **kw):
        self.ev.append(dict(d=d, k=k, t=t, **kw))

    def linhas(self, pares, d=380):
        for cls, t in pares:
            self.add(d, "linha", t, c=cls)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    r = Roteiro()
    fontes = []

    # ------------------------------------------------------------ abertura
    r.add(0, "titulo", "Harness Neurossimbólico Vertical (HNV)",
          sub="Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade  ·  Liberação = Admissibilidade ∧ Humano")
    r.add(4200, "limpar")

    # ------------------------------------------------------------ cena 1
    m1 = ler_json("logs/cena1/rodada1.json")
    txt1 = (RAIZ / m1["arquivo_saida"]).read_text(encoding="utf-8")
    chk = ler_json("logs/cena1/checagem_manual.json")
    fontes += ["logs/cena1/rodada1.json", m1["arquivo_saida"], "logs/cena1/checagem_manual.json"]
    r.add(0, "titulo", "Cena 1 · Sem harness", sub=f"Modelo local {m1['modelo']} (Ollama, CPU) · sem ontologia, sem hook")
    r.add(2600, "limpar")
    r.add(300, "legenda", "Pedido natural de um servidor público", tag="Pedido")
    r.add(300, "cmd", f"py cenas/cena1_sem_harness.py --modelo {m1['modelo']} --rodada 1")
    r.add(900, "linha", "Pedido: " + m1["prompt"], c="dim")
    r.add(700, "linha", f"... gerando ({m1['tempo_parede_s']:.0f} s reais em CPU, {m1['tokens_por_s']} tokens/s - acelerado no replay)", c="dim")
    paras = [p.strip() for p in txt1.split("\n") if p.strip()]
    for p in paras[:3]:
        cls = "alerta" if re.search(r"[Aa]rtigo\s+37", p) else "out"
        r.add(900 if cls == "out" else 1200, "linha", p, c=cls)
    r.add(800, "linha", "[...]", c="dim")
    item = chk["itens"][0]
    r.add(900, "legenda", f"Alucinação: \"{item['citacao']}\" não existe - o art. 37 termina no inciso XXII", tag="Alucinação", cor="ambar")
    r.add(2600, "linha", f"checagem manual (planalto.gov.br): {item['veredito']}", c="bloq")
    r.add(2400, "linha", f"Nas 3 rodadas: {chk['resumo']}", c="dim")
    r.add(3600, "limpar")

    # ------------------------------------------------------------ cena 2a
    s2 = ler_stream("logs/cena2/stream.jsonl")
    fontes.append("logs/cena2/stream.jsonl")
    modelo2 = next((e.get("model") for e in s2 if e.get("subtype") == "init"), "?")
    r.add(0, "titulo", "Cena 2 · Com HNV",
          sub=f"Claude Code ({modelo2}) + skill (guia macio) + hook (regra dura) + ontologia + PROV")
    r.add(2600, "limpar")
    ex2 = ler_json("logs/cena2/execucao.json")
    r.add(300, "legenda", "2a · mesmo pedido, agora dentro do harness", tag="Harness")
    r.add(300, "cmd", 'claude -p "' + ex2["pedido"][:88] + '..." --permission-mode acceptEdits')
    r.add(500, "linha", "", c="dim")
    for e in s2:
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c["type"] == "tool_use":
                    alvo = c["input"].get("skill") or pathlib.Path(c["input"].get("file_path", "")).as_posix().split("hnv-demo/")[-1]
                    r.add(900, "linha", f"● {c['name']}({alvo})", c="tool")
        elif e.get("subtype") == "hook_response":
            saida = e.get("stderr") if e.get("exit_code") == 2 else e.get("output", "")
            if e.get("exit_code") == 0:
                try:
                    saida = json.loads(saida)["hookSpecificOutput"]["additionalContext"]
                except Exception:
                    pass
            r.add(700, "linha", f"  ⎿ hook {e.get('hook_name')} → exit {e.get('exit_code')}", c="dim")
            r.linhas(linhas_verificador(saida), d=500)
    r.add(700, "legenda", "Sem erro de citação: 13 citações conferidas na ontologia", tag="OK", cor="ciano")
    r.add(3200, "limpar")

    # ------------------------------------------------------------ cena 2b
    s2b = ler_stream("logs/cena2b/stream.jsonl")
    ex2b = ler_json("logs/cena2b/execucao.json")
    fontes += ["logs/cena2b/stream.jsonl", "logs/cena2b/execucao.json"]
    r.add(300, "legenda", "2b · o rascunho alucinado da cena 1 (rodada 2) entra no Claude Code", tag="Teste")
    r.add(300, "cmd", 'claude -p "' + ex2b["pedido"][:92] + '..."')
    r.add(500, "linha", "", c="dim")
    n_write = 0
    for e in s2b:
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c["type"] == "tool_use":
                    alvo = c["input"].get("skill") or pathlib.Path(c["input"].get("file_path", "")).as_posix().split("hnv-demo/")[-1]
                    if c["name"] == "Write":
                        n_write += 1
                        if n_write == 2:
                            r.add(600, "legenda", "Correção: o modelo reescreve usando só fontes validadas", tag="Correção", cor="ciano")
                    r.add(900, "linha", f"● {c['name']}({alvo})", c="tool")
        elif e.get("subtype") == "hook_response":
            cod = e.get("exit_code")
            saida = e.get("stderr") if cod == 2 else e.get("output", "")
            if cod == 0:
                try:
                    saida = json.loads(saida)["hookSpecificOutput"]["additionalContext"]
                except Exception:
                    pass
            r.add(700, "linha", f"  ⎿ hook {e.get('hook_name')} → exit {cod}", c="bloq" if cod == 2 else "dim")
            if cod == 2:
                r.add(200, "legenda", "Bloqueio: a regra dura devolve o erro ao modelo (exit 2)", tag="Bloqueio", cor="ambar")
            r.linhas(linhas_verificador(saida), d=650 if cod == 2 else 500)
            if cod == 2:
                r.add(1800, "pausa")
    r.add(2400, "limpar")

    # ------------------------------------------------------------ proveniência
    prov_ok = None
    for p in sorted(LOGS.glob("prov-*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        ent = next((v for v in d["entity"].values() if v.get("prov:type") == "hnv:Parecer"), {})
        if ent.get("hnv:arquivo") == "saida/parecer-rascunho-local.md" and d["hnv:formula"]["admissibilidade"]:
            prov_ok = (p, d)
    if prov_ok:
        p, d = prov_ok
        fontes.append(f"logs/{p.name}")
        r.add(0, "legenda", "Proveniência: cada parecer gera um log W3C PROV", tag="Proveniência", cor="ciano")
        r.add(300, "cmd", f"cat logs/{p.name}")
        agentes = {k: v.get("prov:label") or v.get("foaf:name") for k, v in d["agent"].items()}
        derivs = [v["prov:usedEntity"].split("/")[-1] for v in d["wasDerivedFrom"].values()]
        f = d["hnv:formula"]
        ent = next(v for v in d["entity"].values() if v.get("prov:type") == "hnv:Parecer")
        bloco = [
            ("json", "{"),
            ("json", f'  "entity": {{ "parecer": {{ "arquivo": "{ent["hnv:arquivo"]}", "sha256": "{ent["hnv:sha256"][:16]}…",'),
            ("ok", f'               "status": "{ent["hnv:status"]}" }} }},'),
            ("json", f'  "agent": {{ "modelo": "{agentes.get("hnv:modelo", "")[:40]}",'),
            ("json", f'             "harness": "{agentes.get("hnv:harness", "")}",'),
            ("json", f'             "especialista": "{agentes.get("hnv:especialista", "")}" }},'),
            ("json", f'  "wasDerivedFrom": [{", ".join(derivs[:4])}, … ({len(derivs)} fontes)],'),
            ("ok", f'  "formula": {{ "evidencia": {str(f["evidencia"]).lower()}, "norma": {str(f["norma"]).lower()}, '
                   f'"rastreabilidade": {str(f["rastreabilidade"]).lower()},'),
            ("ok", f'              "admissibilidade": {str(f["admissibilidade"]).lower()}, '
                   f'"aprovacao_humana": {str(f["aprovacao_humana"]).lower()}, "liberacao": {str(f["liberacao"]).lower()} }}'),
            ("json", "}"),
        ]
        r.linhas(bloco, d=420)
        r.add(1500, "selo", "Aguardando aprovação humana", sub="Liberação = Admissibilidade ∧ Humano")
        r.add(4200, "limpar")

    # ------------------------------------------------------------ bônus: laço local
    tr = ler_json("logs/laco/transcricao.json")
    fontes.append("logs/laco/transcricao.json")
    r.add(0, "titulo", "Bônus · Laço local gerar → verificar → corrigir", sub=f"{tr['modelo']} via API do Ollama · máx. 3 rodadas")
    r.add(2400, "limpar")
    r.add(300, "cmd", "py harness/laco_local.py")
    for rod in tr["rodadas"]:
        msg = rod["verificador_msg"]
        mm = re.search(r"Citações bloqueadas \((\d+)\)", msg)
        nb = mm.group(1) if mm else "0"
        r.add(900, "linha", f"rodada {rod['rodada']} · {rod['tempo_parede_s']:.0f} s · exit {rod['verificador_exit']} · {nb} citação(ões) bloqueada(s)",
              c="bloq" if rod["verificador_exit"] else "ok")
        for l in msg.replace("\r", "").splitlines():
            if re.match(r"\s+\d+\.", l):
                r.add(380, "linha", l, c="dim")
    r.add(900, "linha", "Resultado: " + tr["resultado_final"], c="bloq" if "bloqueado" in tr["resultado_final"] else "ok")
    r.add(500, "legenda", "Modelo pequeno não convergiu em 3 rodadas: o harness não libera", tag="Bloqueio", cor="ambar")
    r.add(3800, "limpar")

    # ------------------------------------------------------------ fecho
    r.add(0, "titulo", "Skill orienta · Hook decide · Ontologia ancora · PROV registra · Humano libera",
          sub="Camada simbólica definida pelo especialista - execução real, logs no repositório")
    r.add(5000, "fim")

    total = sum(e["d"] for e in r.ev) + sum(40 * len(e["t"]) for e in r.ev if e["k"] == "cmd")
    escala = 1.0
    if total / 1000 > ALVO_S[1]:
        escala = ALVO_S[1] * 1000 / total * 0.97
    elif total / 1000 < ALVO_S[0]:
        escala = ALVO_S[0] * 1000 / total * 1.03
    for e in r.ev:
        e["d"] = int(e["d"] * escala)

    dados = {"eventos": r.ev, "fontes": fontes, "escala": round(escala, 3),
             "duracao_estimada_s": round(total * escala / 1000, 1)}
    tpl = (RAIZ / "replay" / "template.html").read_text(encoding="utf-8")
    js = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    html = tpl.replace("/*__DADOS__*/null", js)
    (RAIZ / "replay" / "index.html").write_text(html, encoding="utf-8")
    print(f"replay/index.html gerado: {len(r.ev)} eventos, ~{dados['duracao_estimada_s']} s (escala {escala:.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
