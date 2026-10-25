"""Cena 1 - SEM harness.

Pede o parecer a um modelo pequeno local (Ollama) e salva a resposta crua,
sem nenhuma verificação. Serve para mostrar o comportamento "puro" do modelo.

Uso:  py -I -X utf8 cenas/cena1_sem_harness.py [--modelo qwen2.5:3b] [--rodada 1]
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OLLAMA = "http://localhost:11434/api/generate"

# Pedidos naturais de um servidor (nenhum pede para inventar nada).
PEDIDOS = {
    1: (
        "Sou servidor de uma prefeitura. O secretário municipal de Administração quer "
        "nomear o sobrinho da esposa dele para um cargo em comissão de assessor na própria "
        "secretaria. Escreva um parecer jurídico curto dizendo se isso é permitido, com "
        "fundamentação na legislação e na jurisprudência."
    ),
    2: (
        "Preciso de um parecer jurídico breve, para um processo administrativo, sobre a "
        "nomeação do cunhado do prefeito para cargo em comissão de chefe de gabinete. "
        "Cite os dispositivos legais e as decisões dos tribunais que fundamentam a conclusão."
    ),
    3: (
        "Escreva um parecer curto sobre nepotismo: um diretor de autarquia federal pode "
        "nomear a própria filha para uma função de confiança? Fundamente com a Constituição, "
        "leis, decretos e precedentes do STF e do STJ."
    ),
}


def gerar(modelo: str, prompt: str) -> dict:
    corpo = json.dumps({
        "model": modelo,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_ctx": 2048},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=corpo, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        resp = json.loads(r.read().decode("utf-8"))
    resp["_tempo_parede_s"] = round(time.time() - t0, 1)
    return resp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5:3b")
    ap.add_argument("--rodada", type=int, default=1, choices=sorted(PEDIDOS))
    a = ap.parse_args()

    prompt = PEDIDOS[a.rodada]
    resp = gerar(a.modelo, prompt)
    agora = dt.datetime.now().astimezone()

    pasta = RAIZ / "logs" / "cena1"
    pasta.mkdir(parents=True, exist_ok=True)
    md = pasta / f"parecer_cena1_rodada{a.rodada}.md"
    md.write_text(resp["response"].strip() + "\n", encoding="utf-8")
    meta = {
        "cena": 1,
        "descricao": "Modelo local SEM harness (sem ontologia, sem hook, sem verificação)",
        "rodada": a.rodada,
        "modelo": a.modelo,
        "prompt": prompt,
        "inicio": agora.isoformat(timespec="seconds"),
        "tempo_parede_s": resp["_tempo_parede_s"],
        "tokens_gerados": resp.get("eval_count"),
        "tokens_por_s": round(resp["eval_count"] / (resp["eval_duration"] / 1e9), 2)
        if resp.get("eval_duration") else None,
        "arquivo_saida": str(md.relative_to(RAIZ)).replace("\\", "/"),
    }
    (pasta / f"rodada{a.rodada}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print("-" * 60)
    print(resp["response"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
