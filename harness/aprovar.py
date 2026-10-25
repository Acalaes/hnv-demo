"""HNV - registro da aprovação humana (Liberação = Admissibilidade ∧ Humano).

Só aprova se o log PROV indicado for admissível E o parecer não tiver mudado
desde a verificação (mesmo SHA-256). Grava um novo log PROV com a atividade de
aprovação, ligada ao especialista.

Uso: py -I -X utf8 harness/aprovar.py logs/prov-XXXX.json --aprovador "Alexandre Pinto Calaes"
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log_prov")
    ap.add_argument("--aprovador", required=True)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    prov = json.loads(pathlib.Path(a.log_prov).read_text(encoding="utf-8"))
    if not prov["hnv:formula"]["admissibilidade"]:
        print("Recusado: o parecer não é admissível; não pode ser liberado.", file=sys.stderr)
        return 2
    ent_id, ent = next((k, v) for k, v in prov["entity"].items() if v.get("prov:type") == "hnv:Parecer")
    arq = RAIZ / ent["hnv:arquivo"]
    atual = hashlib.sha256(arq.read_bytes()).hexdigest()
    if atual != ent["hnv:sha256"]:
        print("Recusado: o parecer mudou depois da verificação. Verifique de novo.", file=sys.stderr)
        return 2

    agora = dt.datetime.now().astimezone()
    carimbo = agora.strftime("%Y%m%dT%H%M%S")
    formula = dict(prov["hnv:formula"], aprovacao_humana=True, liberacao=True)
    novo = {
        "prefix": prov["prefix"],
        "entity": {ent_id: dict(ent, **{"hnv:status": "liberado"})},
        "activity": {f"hnv:aprovacao-{carimbo}": {"prov:type": "hnv:AprovacaoHumana",
                                                  "prov:startTime": agora.isoformat()}},
        "agent": {"hnv:especialista": {"prov:type": "prov:Person", "foaf:name": a.aprovador}},
        "used": {"_:u1": {"prov:activity": f"hnv:aprovacao-{carimbo}", "prov:entity": ent_id}},
        "wasAssociatedWith": {"_:a1": {"prov:activity": f"hnv:aprovacao-{carimbo}", "prov:agent": "hnv:especialista"}},
        "wasInfluencedBy": {"_:i1": {"prov:influencee": f"hnv:aprovacao-{carimbo}",
                                     "prov:influencer": str(pathlib.Path(a.log_prov).name)}},
        "hnv:formula": formula,
    }
    destino = RAIZ / "logs" / f"prov-aprovacao-{carimbo}.json"
    destino.write_text(json.dumps(novo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Liberado por {a.aprovador}. Proveniência: {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
