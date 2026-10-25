"""Cena bônus - laço gerar -> verificar -> corrigir com modelo LOCAL (Ollama).

Rodada 1: pedido natural (igual à cena 1), sem guia.
Rodadas seguintes: o modelo recebe a mensagem real do verificador (stderr) e o texto
das fontes validadas, e reescreve. Máximo de 3 rodadas.

Uso: py -I -X utf8 harness/laco_local.py [--modelo qwen2.5:3b] [--max 3]
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OLLAMA = "http://localhost:11434/api/generate"
VERIFICADOR = RAIZ / "harness" / "verificar_citacoes.py"

PEDIDO = (
    "Sou servidor de uma prefeitura. O secretário municipal de Administração quer "
    "nomear o sobrinho da esposa dele para um cargo em comissão de assessor na própria "
    "secretaria. Escreva um parecer jurídico curto dizendo se isso é permitido, com "
    "fundamentação na legislação e na jurisprudência."
)


def gerar(modelo: str, prompt: str) -> dict:
    corpo = json.dumps({"model": modelo, "prompt": prompt, "stream": False,
                        "options": {"temperature": 0.3, "num_ctx": 4096}}).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=corpo, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        resp = json.loads(r.read().decode("utf-8"))
    resp["_tempo_parede_s"] = round(time.time() - t0, 1)
    return resp


def fontes_validadas() -> str:
    onto = json.loads((RAIZ / "ontologia" / "fontes.json").read_text(encoding="utf-8"))
    linhas = []
    for i in onto["instancias"]:
        if i["classe"] == "Norma":
            continue
        linhas.append(f"- {i['citacao']}: {i.get('texto', '')[:260]}")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="qwen2.5:3b")
    ap.add_argument("--max", type=int, default=3)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    pasta = RAIZ / "logs" / "laco"
    pasta.mkdir(parents=True, exist_ok=True)
    transcricao = {"cena": "bonus", "descricao": "Laço gerar -> verificar -> corrigir com modelo local",
                   "modelo": a.modelo, "inicio": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
                   "rodadas": []}
    prompt = PEDIDO
    resultado_final = "bloqueado após o limite de rodadas"
    for n in range(1, a.max + 1):
        resp = gerar(a.modelo, prompt)
        texto = resp["response"].strip()
        arq = pasta / f"parecer_laco_rodada{n}.md"
        arq.write_text(texto + "\n", encoding="utf-8")
        ver = subprocess.run(
            [sys.executable, "-I", "-X", "utf8", str(VERIFICADOR), str(arq),
             "--agente-gerador", f"{a.modelo} (Ollama, laço local, rodada {n})"],
            capture_output=True, text=True, encoding="utf-8")
        msg = (ver.stderr or ver.stdout).strip()
        rodada = {"rodada": n, "prompt": prompt, "resposta": texto, "tempo_parede_s": resp["_tempo_parede_s"],
                  "tokens_gerados": resp.get("eval_count"), "verificador_exit": ver.returncode,
                  "verificador_msg": msg, "arquivo": str(arq.relative_to(RAIZ)).replace("\\", "/")}
        transcricao["rodadas"].append(rodada)
        print(f"--- rodada {n}: exit {ver.returncode} ({resp['_tempo_parede_s']} s)\n{msg}\n", flush=True)
        if ver.returncode == 0:
            resultado_final = f"admissível na rodada {n} - aguardando aprovação humana"
            break
        prompt = (
            f"{PEDIDO}\n\nSua versão anterior do parecer foi BLOQUEADA pelo verificador de citações. "
            f"Mensagem do verificador:\n{msg}\n\n"
            "Reescreva o parecer completo. Use SOMENTE as fontes abaixo, citadas exatamente no formato "
            "entre colchetes mostrado (ex.: [STF, Súmula Vinculante 13]). Não cite nenhuma outra lei, "
            "artigo, súmula ou decisão. Fontes validadas:\n" + fontes_validadas() +
            f"\n\nParecer anterior (para corrigir):\n{texto}\n"
        )
    transcricao["resultado_final"] = resultado_final
    transcricao["fim"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (pasta / "transcricao.json").write_text(json.dumps(transcricao, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Resultado final:", resultado_final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
