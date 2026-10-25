"""HNV - verificador de citações (regra dura / camada simbólica computacional).

Confere cada citação jurídica de um parecer (markdown) contra a ontologia do
especialista (ontologia/fontes.json) e aplica a fórmula do artigo:

    Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade
    Liberação       = Admissibilidade ∧ aprovação Humana

Saída:
  exit 0 -> admissível (fica "aguardando aprovação humana")
  exit 2 -> bloqueado; motivo detalhado no stderr (o Claude Code devolve ao modelo)
Sempre grava logs/prov-<timestamp>.json no estilo W3C PROV-JSON.

Modos:
  py -I -X utf8 harness/verificar_citacoes.py saida/parecer.md [--agente-gerador NOME]
  py -I -X utf8 harness/verificar_citacoes.py --hook      (lê o JSON do hook no stdin)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import unicodedata

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ONTOLOGIA = RAIZ / "ontologia" / "fontes.json"
LOGS = RAIZ / "logs"
PADRAO_ARQUIVO = re.compile(r"(^|[\\/])saida[\\/]parecer[^\\/]*\.md$", re.I)

ROMANO = r"[IVXLC]+"

# Normas reconhecidas pelo número -> id na ontologia (o resto é "não validado").
NORMAS_POR_NUMERO = {("LEI", "8429"): "LEI8429", ("DECRETO", "7203"): "DEC7203"}
NOMES_NORMA = {
    "LEI": "Lei", "DECRETO": "Decreto", "LC": "Lei Complementar", "RESOLUCAO": "Resolução",
    "PORTARIA": "Portaria", "IN": "Instrução Normativa", "MP": "Medida Provisória",
}

# ---------------------------------------------------------------- utilidades


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def so_digitos(s: str) -> str:
    return re.sub(r"\D", "", s)


def normalizar_citacao(s: str) -> str:
    s = sem_acento(s).lower()
    s = s.replace("º", "").replace("°", "").replace("ª", "")
    s = re.sub(r"\bn\.?\s*(?=\d)", "", s)          # "nº 13" -> "13"
    s = re.sub(r"(\d)o\b", r"\1", s)               # "1o" -> "1"
    s = re.sub(r"(\d)\.(\d{3})", r"\1\2", s)       # "8.429" -> "8429"
    s = re.sub(r"/19(\d\d)\b", r"/\1", s)          # "/1992" -> "/92"
    s = s.replace("constituicao federal", "cf/88")
    s = re.sub(r"\bcf(/88)?\b", "cf/88", s)
    s = re.sub(r"\s+", "", s)
    return s


def carregar_ontologia() -> dict:
    return json.loads(ONTOLOGIA.read_text(encoding="utf-8"))


class Indice:
    """Índice da ontologia para resolver citações."""

    def __init__(self, onto: dict):
        self.onto = onto
        self.por_id = {i["id"]: i for i in onto["instancias"]}
        self.canonicas: dict[str, str] = {}
        self.dispositivos: dict[tuple, str] = {}
        self.artigos: dict[tuple, list[str]] = {}
        self.sumulas: dict[tuple, str] = {}
        self.precedentes: dict[tuple, str] = {}
        self.temas: dict[str, str] = {}
        for i in onto["instancias"]:
            for c in [i["citacao"], *i.get("aliases", [])]:
                self.canonicas[normalizar_citacao(c.strip("[]"))] = i["id"]
            ch = i.get("chave", {})
            if i["classe"] == "Dispositivo":
                self.dispositivos[(ch["norma"], ch["art"], ch["unidade"])] = i["id"]
                self.artigos.setdefault((ch["norma"], ch["art"]), []).append(i["id"])
            elif i["classe"] == "Sumula":
                self.sumulas[(ch["tribunal"], ch["sumula"], ch["vinculante"])] = i["id"]
            elif i["classe"] == "Precedente":
                self.precedentes[(ch["classe_processual"], ch["numero"])] = i["id"]
                if ch.get("tema"):
                    self.temas[ch["tema"]] = i["id"]

    def lista_aceita(self) -> list[str]:
        return [i["citacao"] for i in self.onto["instancias"] if i["classe"] != "Norma"]


# ---------------------------------------------------------------- reconhecedores

RE_CF = re.compile(r"\bCF(?:\s*/\s*(?:88|1988))?\b|Constitui[cç][aã]o(?:\s+(?:Federal|da\s+Rep[uú]blica))?|Carta\s+Magna", re.I)
RE_NORMA_NUM = re.compile(
    r"\b(Lei\s+Complementar|Lei|Decreto(?:-Lei)?|Resolu[cç][aã]o|Portaria|Instru[cç][aã]o\s+Normativa|Medida\s+Provis[oó]ria)"
    r"(?:\s+(?:Federal|Municipal|Estadual|CNJ|do\s+CNJ|TCU))?\s*(?:n[º°o]?\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d{1,6})"
    r"(?:\s*/\s*(\d{2,4}))?", re.I)
RE_NORMA_NOME = re.compile(
    r"Lei\s+de\s+Improbidade(?:\s+Administrativa)?|C[oó]digo\s+Civil|C[oó]digo\s+Penal|\bCLT\b|"
    r"Estatuto\s+dos\s+Servidores[^,.;]*|Lei\s+Org[aâ]nica[^,.;]*|Lei\s+de\s+Licita[cç][oõ]es", re.I)
RE_ARTIGO = re.compile(
    r"\bart(?:igo)?s?\.?\s*(\d{1,2}(?:\.\d{3})+|\d+)\s*(?:[º°o](?![a-z]))?(?:-[A-Z])?"
    r"(?:\s*,?\s*(caput|par[aá]grafo\s+[uú]nico|§\s*(\d+)\s*[º°o]?|(?:inciso\s+)?(" + ROMANO + r"))\b)?", re.I)
RE_SUMULA = re.compile(
    r"\bS[uú]mula(?:s)?\s+(Vinculante\s+)?(?:n[º°o]?\.?\s*)?(\d+)(?:\s*(?:do|da)\s+(STF|STJ|TST|TCU|Supremo|Superior))?"
    r"|\bSV\s*-?\s*(\d+)", re.I)
RE_PRECEDENTE = re.compile(
    r"\b(RE|REsp|AREsp|ARE|ADI|ADIn|ADC|ADPF|MS|RMS|Rcl|HC|RHC|AI|AgRg|AgR|Pet|ACO|AC|AP|Inq)"
    r"\s*(?:n[º°o]?\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d{1,7})(?:\s*/\s*([A-Z]{2}))?")
RE_TEMA = re.compile(r"\bTema\s+(?:n[º°o]?\.?\s*)?(\d+)", re.I)
RE_COLCHETE = re.compile(r"\[([^\[\]\n]{2,160})\](?!\()")
GATILHO_COLCHETE = re.compile(
    r"\bart\b|art\.|s[uú]mula|\bSTF\b|\bSTJ\b|\bTCU\b|\bLei\b|Decreto|\bCF\b|Constitui|\bRE\b|\bADI|\bADC|Tema|Resolu|Parecer|Ac[oó]rd",
    re.I)


def resolver_norma_em(trecho: str):
    """Procura a primeira menção de norma no trecho. Devolve (id|None, rotulo) ou (None, None)."""
    cand = []
    m = RE_CF.search(trecho)
    if m:
        cand.append((m.start(), "CF88", "CF/88"))
    m = RE_NORMA_NUM.search(trecho)
    if m:
        tipo = sem_acento(m.group(1)).upper().split()[0]
        tipo = {"LEI": "LC" if "COMPLEMENTAR" in sem_acento(m.group(1)).upper() else "LEI",
                "INSTRUCAO": "IN", "MEDIDA": "MP", "RESOLUCAO": "RESOLUCAO"}.get(tipo, tipo)
        if tipo.startswith("DECRETO"):
            tipo = "DECRETO"
        num = so_digitos(m.group(2))
        cand.append((m.start(), NORMAS_POR_NUMERO.get((tipo, num)), m.group(0).strip()))
    m = RE_NORMA_NOME.search(trecho)
    if m:
        nome = m.group(0).strip()
        cand.append((m.start(), "LEI8429" if "improbidade" in nome.lower() else None, nome))
    if not cand:
        return None, None
    cand.sort(key=lambda c: c[0])
    return cand[0][1], cand[0][2]


def unidade_de(m: re.Match) -> str | None:
    if not m.group(2):
        return None
    u = m.group(2).lower()
    if u.startswith("caput"):
        return "caput"
    if u.startswith("par"):
        return "§unico"
    if m.group(3):
        return "§" + m.group(3)
    return m.group(4).upper()


# ---------------------------------------------------------------- verificação


def verificar_referencia(trecho: str, idx: Indice, contexto_depois: str = "") -> dict:
    """Resolve UMA referência (conteúdo de colchete ou trecho solto)."""
    r = {"trecho": trecho.strip(), "status": "bloqueado", "resolvido_para": [], "motivo": ""}

    # 1) formato padronizado exato
    can = idx.canonicas.get(normalizar_citacao(trecho))
    if can:
        r.update(status="ok", resolvido_para=[can], motivo="citação padronizada encontrada na ontologia")
        return r

    # 2) súmula
    m = RE_SUMULA.search(trecho)
    if m:
        vinc = bool(m.group(1)) or bool(m.group(4))
        num = m.group(2) or m.group(4)
        trib = (m.group(3) or ("STF" if vinc or re.search(r"\bSTF\b|Supremo", trecho + contexto_depois[:40]) else "?")).upper()
        trib = {"SUPREMO": "STF", "SUPERIOR": "STJ"}.get(trib, trib)
        if re.search(r"\bSTJ\b", trecho + contexto_depois[:30]):
            trib = "STJ"
        sid = idx.sumulas.get((trib, num, vinc))
        if sid:
            r.update(status="ok", resolvido_para=[sid], motivo="súmula encontrada na ontologia")
        else:
            rot = f"Súmula {'Vinculante ' if vinc else ''}{num}" + (f" do {trib}" if trib != "?" else "")
            r["motivo"] = f"{rot} não consta na ontologia validada pelo especialista"
        r["classe"] = "Sumula"
        return r

    # 3) precedente / tema
    m = RE_PRECEDENTE.search(trecho)
    if m:
        cls, num = m.group(1), so_digitos(m.group(2))
        cls_n = {"ADIn": "ADI"}.get(cls, cls)
        pid = idx.precedentes.get((cls_n, num))
        r["classe"] = "Precedente"
        if pid:
            r.update(status="ok", resolvido_para=[pid], motivo="precedente encontrado na ontologia")
        else:
            r["motivo"] = f"precedente {cls_n} {m.group(2)} não consta na ontologia validada pelo especialista"
        return r
    m = RE_TEMA.search(trecho)
    if m:
        pid = idx.temas.get(m.group(1))
        r["classe"] = "Precedente"
        if pid:
            r.update(status="ok", resolvido_para=[pid], motivo="tema de repercussão geral encontrado na ontologia")
        else:
            r["motivo"] = f"Tema {m.group(1)} não consta na ontologia validada pelo especialista"
        return r

    # 4) artigo (+ norma no próprio trecho ou logo depois)
    m = RE_ARTIGO.search(trecho)
    if m:
        art = so_digitos(m.group(1))
        uni = unidade_de(m)
        resto = trecho[m.end():] + " " + contexto_depois[:90]
        antes = trecho[:m.start()]
        nid, nrot = resolver_norma_em(antes) if resolver_norma_em(antes)[1] else resolver_norma_em(resto)
        r["classe"] = "Dispositivo"
        rot_disp = f"art. {m.group(1)}" + (f", {uni}" if uni else "")
        if not nrot:
            r["motivo"] = f"{rot_disp} sem norma identificável (não rastreável) - use o formato padronizado, ex.: [CF/88, art. 37, caput]"
            return r
        if not nid:
            r["motivo"] = f"{rot_disp} de \"{nrot}\": norma não consta na ontologia validada pelo especialista"
            return r
        if uni:
            did = idx.dispositivos.get((nid, art, uni))
            if did:
                r.update(status="ok", resolvido_para=[did], motivo="dispositivo encontrado na ontologia")
            else:
                r["motivo"] = f"{rot_disp} de {idx.por_id[nid]['citacao'].strip('[]')}: dispositivo não consta na ontologia validada"
            return r
        ids = idx.artigos.get((nid, art))
        if ids:
            r.update(status="ok", resolvido_para=ids, motivo="artigo encontrado na ontologia (nível de artigo)")
        else:
            r["motivo"] = f"{rot_disp} de {idx.por_id[nid]['citacao'].strip('[]')}: artigo não consta na ontologia validada"
        return r

    # 5) norma sem artigo
    nid, nrot = resolver_norma_em(trecho)
    if nrot:
        r["classe"] = "Norma"
        if nid:
            r.update(status="ok", resolvido_para=[nid], motivo="norma encontrada na ontologia")
        else:
            r["motivo"] = f"\"{nrot}\" não consta na ontologia validada pelo especialista"
        return r

    r["motivo"] = "citação em colchetes fora do formato padronizado e não reconhecida"
    return r


def extrair_e_verificar(texto: str, idx: Indice) -> list[dict]:
    resultados = []
    # (a) citações em colchetes (formato padronizado)
    for m in RE_COLCHETE.finditer(texto):
        conteudo = m.group(1)
        if not GATILHO_COLCHETE.search(conteudo):
            continue
        res = verificar_referencia(conteudo, idx)
        res["forma"] = "padronizada" if res["status"] == "ok" and idx.canonicas.get(normalizar_citacao(conteudo)) else "colchete"
        res["posicao"] = m.start()
        resultados.append(res)

    # (b) citações soltas no texto fora dos colchetes
    solto = RE_COLCHETE.sub(lambda m: " " * len(m.group(0)), texto)
    ocupados: list[tuple[int, int]] = []

    def livre(a, b):
        return all(b <= x or a >= y for x, y in ocupados)

    for rx in (RE_SUMULA, RE_PRECEDENTE, RE_TEMA, RE_ARTIGO, RE_NORMA_NUM):
        for m in rx.finditer(solto):
            if not livre(m.start(), m.end()):
                continue
            if rx is RE_PRECEDENTE and m.group(1) in ("AC", "AP", "MS", "AI", "Pet", "Inq") and not re.search(
                    r"STF|STJ|TCU|julg|Rel\.|rel\.|min\.", solto[max(0, m.start() - 60): m.end() + 60]):
                continue  # siglas ambíguas sem contexto judicial
            fim = m.end()
            ctx = solto[fim: fim + 120]
            res = verificar_referencia(m.group(0), idx, contexto_depois=ctx)
            # se o artigo puxou a norma do contexto, reserva também esse trecho
            if rx is RE_ARTIGO:
                mn = re.match(r"[^.;\n]{0,90}?(?:" + RE_CF.pattern + r"|" + RE_NORMA_NUM.pattern + r"|" + RE_NORMA_NOME.pattern + r")", ctx, re.I)
                if mn:
                    fim += mn.end()
            if rx is RE_TEMA:
                pass
            ocupados.append((m.start(), fim))
            res["forma"] = "solta"
            res["posicao"] = m.start()
            res["trecho"] = re.sub(r"\s+", " ", solto[m.start():fim]).strip()
            resultados.append(res)
    resultados.sort(key=lambda r: r["posicao"])
    return resultados


# ---------------------------------------------------------------- PROV


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gravar_prov(arquivo: pathlib.Path, conteudo: bytes, resultados: list[dict], formula: dict,
                agente_gerador: str, idx: Indice, inicio: dt.datetime, modo: str) -> pathlib.Path:
    LOGS.mkdir(parents=True, exist_ok=True)
    fim = dt.datetime.now().astimezone()
    carimbo = fim.strftime("%Y%m%dT%H%M%S") + f"-{fim.microsecond // 1000:03d}"
    h = sha256(conteudo)[:12]
    try:
        rel = str(arquivo.resolve().relative_to(RAIZ)).replace("\\", "/")
    except ValueError:
        rel = str(arquivo)
    ent_parecer = f"hnv:parecer-{h}"
    act_ger = f"hnv:geracao-{h}"
    act_ver = f"hnv:verificacao-{carimbo}"
    status = "aguardando aprovação humana" if formula["admissibilidade"] else "bloqueado pelo harness"
    fontes_ok = sorted({i for r in resultados if r["status"] == "ok" for i in r["resolvido_para"]})

    prov = {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "hnv": "https://github.com/Acalaes/hnv-demo#",
            "foaf": "http://xmlns.com/foaf/0.1/",
        },
        "entity": {
            ent_parecer: {
                "prov:type": "hnv:Parecer", "hnv:arquivo": rel, "hnv:sha256": sha256(conteudo),
                "hnv:status": status,
            },
            "hnv:ontologia": {
                "prov:type": "hnv:OntologiaDeFontes", "hnv:arquivo": "ontologia/fontes.json",
                "hnv:sha256": sha256(ONTOLOGIA.read_bytes()), "hnv:versao": idx.onto["meta"]["versao"],
                "hnv:statusValidacao": idx.onto["meta"]["status"],
            },
            f"hnv:relatorio-{carimbo}": {
                "prov:type": "hnv:RelatorioDeVerificacao",
                "hnv:citacoes": [{k: v for k, v in r.items() if k != "posicao"} for r in resultados],
            },
            **{f"hnv:fonte/{fid}": {
                "prov:type": f"hnv:{idx.por_id[fid]['classe']}", "prov:label": idx.por_id[fid]["rotulo"],
                "prov:location": idx.por_id[fid]["url"], "hnv:statusValidacao": idx.por_id[fid]["status"],
            } for fid in fontes_ok},
        },
        "activity": {
            act_ger: {"prov:type": "hnv:GeracaoDeTexto"},
            act_ver: {"prov:type": "hnv:VerificacaoSimbolica", "prov:startTime": inicio.isoformat(),
                      "prov:endTime": fim.isoformat(), "hnv:modo": modo},
        },
        "agent": {
            "hnv:modelo": {"prov:type": "prov:SoftwareAgent", "prov:label": agente_gerador},
            "hnv:harness": {"prov:type": "prov:SoftwareAgent", "prov:label": "HNV verificar_citacoes.py v0.1.0"},
            "hnv:especialista": {"prov:type": "prov:Person", "foaf:name": "Alexandre Pinto Calaes",
                                 "hnv:papel": "advogado - define e valida a ontologia"},
        },
        "wasGeneratedBy": {"_:g1": {"prov:entity": ent_parecer, "prov:activity": act_ger},
                           "_:g2": {"prov:entity": f"hnv:relatorio-{carimbo}", "prov:activity": act_ver}},
        "used": {"_:u1": {"prov:activity": act_ver, "prov:entity": ent_parecer},
                 "_:u2": {"prov:activity": act_ver, "prov:entity": "hnv:ontologia"}},
        "wasAssociatedWith": {"_:a1": {"prov:activity": act_ger, "prov:agent": "hnv:modelo"},
                              "_:a2": {"prov:activity": act_ver, "prov:agent": "hnv:harness"}},
        "wasAttributedTo": {"_:t1": {"prov:entity": "hnv:ontologia", "prov:agent": "hnv:especialista"}},
        "wasDerivedFrom": {f"_:d{n}": {"prov:generatedEntity": ent_parecer, "prov:usedEntity": f"hnv:fonte/{fid}"}
                           for n, fid in enumerate(fontes_ok, 1)},
        "hnv:formula": formula,
    }
    destino = LOGS / f"prov-{carimbo}.json"
    destino.write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


# ---------------------------------------------------------------- principal


def avaliar(arquivo: pathlib.Path, agente_gerador: str, modo: str) -> tuple[int, str, pathlib.Path]:
    inicio = dt.datetime.now().astimezone()
    idx = Indice(carregar_ontologia())
    conteudo = arquivo.read_bytes()
    texto = conteudo.decode("utf-8", errors="replace")
    resultados = extrair_e_verificar(texto, idx)

    bloq = [r for r in resultados if r["status"] != "ok"]
    oks = [r for r in resultados if r["status"] == "ok"]
    classes_ok = {idx.por_id[i]["classe"] for r in oks for i in r["resolvido_para"]}
    evidencia = bool(resultados) and not bloq
    norma = bool(classes_ok & {"Norma", "Dispositivo", "Sumula"})
    fontes_ok = {i for r in oks for i in r["resolvido_para"]}
    rastreab = all(idx.por_id[i].get("url", "").startswith("https://") for i in fontes_ok) and bool(fontes_ok)
    formula = {
        "evidencia": evidencia, "norma": norma, "rastreabilidade": rastreab,
        "admissibilidade": evidencia and norma and rastreab,
        "aprovacao_humana": False, "liberacao": False,
        "expressao": "Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade; Liberação = Admissibilidade ∧ Humano",
    }
    log = gravar_prov(arquivo, conteudo, resultados, formula, agente_gerador, idx, inicio, modo)
    rel_log = str(log.relative_to(RAIZ)).replace("\\", "/")
    V = lambda b: "V" if b else "F"  # noqa: E731

    if formula["admissibilidade"]:
        msg = (f"HNV · OK - {arquivo.name}: {len(oks)} citação(ões) conferida(s) na ontologia.\n"
               f"Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade = V ∧ V ∧ V\n"
               f"Status: aguardando aprovação humana (Liberação = Admissibilidade ∧ Humano).\n"
               f"Proveniência: {rel_log}")
        return 0, msg, log

    linhas = [f"HNV · BLOQUEIO (regra dura) - {arquivo.name} não é admissível.",
              f"Admissibilidade = Evidência ∧ Norma ∧ Rastreabilidade = {V(evidencia)} ∧ {V(norma)} ∧ {V(rastreab)}"]
    if bloq:
        linhas.append(f"Citações bloqueadas ({len(bloq)}):")
        for n, r in enumerate(bloq, 1):
            linhas.append(f"  {n}. \"{r['trecho']}\" -> {r['motivo']}")
    if not resultados:
        linhas.append("Nenhuma citação encontrada: parecer sem evidência rastreável.")
    if not norma:
        linhas.append("Falta ao menos uma fonte normativa (Norma, Dispositivo ou Súmula) da ontologia.")
    linhas.append("Fontes aceitas (use exatamente estes formatos): " + "; ".join(idx.lista_aceita()))
    linhas.append("Corrija o parecer: remova ou substitua cada citação bloqueada por uma fonte aceita. "
                  "Não invente fontes. Se faltar base, diga isso no texto.")
    linhas.append(f"Proveniência: {rel_log}")
    return 2, "\n".join(linhas), log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arquivo", nargs="?")
    ap.add_argument("--hook", action="store_true", help="modo hook do Claude Code (JSON no stdin)")
    ap.add_argument("--agente-gerador", default="modelo não informado")
    ap.add_argument("--json", action="store_true", help="imprime o relatório em JSON no stdout")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if a.hook:
        dados = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        caminho = (dados.get("tool_input") or {}).get("file_path", "")
        if not caminho or not PADRAO_ARQUIVO.search(caminho.replace("\\", "/")):
            return 0  # não é um parecer: o hook não interfere
        arq = pathlib.Path(caminho)
        if not arq.is_absolute():
            arq = pathlib.Path(dados.get("cwd") or RAIZ) / arq
        codigo, msg, log = avaliar(arq, "modelo do Claude Code (sessão " + str(dados.get("session_id", "?"))[:8] + ")", "hook PostToolUse")
        if codigo == 2:
            print(msg, file=sys.stderr)
            return 2
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}},
                         ensure_ascii=False))
        return 0

    if not a.arquivo:
        ap.error("informe o arquivo do parecer ou use --hook")
    codigo, msg, log = avaliar(pathlib.Path(a.arquivo), a.agente_gerador, "linha de comando")
    if a.json:
        print(log.read_text(encoding="utf-8"))
    print(msg, file=sys.stderr if codigo else sys.stdout)
    return codigo


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # falha fechada: erro no verificador também bloqueia
        print(f"HNV · BLOQUEIO (falha do verificador, bloqueio por segurança): {type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(2)
