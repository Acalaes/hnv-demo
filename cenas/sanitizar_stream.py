"""Remove do stream-json dados de configuração pessoal (lista de MCPs, plugins, skills
globais etc.) antes de versionar. Mantém tudo o que a demonstração precisa: mensagens,
chamadas de ferramenta, resultados e eventos de hook.

Uso: py -I -X utf8 cenas/sanitizar_stream.py entrada.jsonl saida.jsonl
"""
import json
import sys

MANTER_INIT = {"type", "subtype", "cwd", "session_id", "model", "permissionMode", "claude_code_version", "output_style"}


def main() -> int:
    ent, sai = sys.argv[1], sys.argv[2]
    n = 0
    with open(ent, encoding="utf-8") as f, open(sai, "w", encoding="utf-8") as g:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                ev = {k: v for k, v in ev.items() if k in MANTER_INIT}
            g.write(json.dumps(ev, ensure_ascii=False) + "\n")
            n += 1
    print(f"{n} eventos gravados em {sai}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
