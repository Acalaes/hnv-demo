"""Gera a versão compacta (<16 KB) do replay HNV para o <x-embed> do slide 12."""
import json
import re
import sys

ORIGEM = r"C:\Users\acala\projetos\hnv-demo\replay\index.html"
DESTINO = r"C:\Users\acala\projetos\hnv-demo\replay\embed.html"

html = open(ORIGEM, encoding="utf-8").read()
dados = json.loads(re.search(r"const DADOS = (\{.*?\});\n", html, re.S).group(1))
ev = dados["eventos"]

# Remove o cartão de abertura (o slide já tem título) e encurta textos longos.
if ev[0]["k"] == "titulo" and ev[1]["k"] == "limpar":
    ev = ev[2:]
for e in ev:
    if e["k"] == "linha" and e["t"].startswith("Pedido:"):
        e["t"] = "Pedido: parecer curto — secretário quer nomear sobrinho da esposa para cargo em comissão. É permitido?"
    if e["k"] == "linha" and e["t"].startswith("Nas 3 rodadas:"):
        e["t"] = "Nas 3 rodadas: citação inexistente ou falsa; nenhuma citou a Súmula Vinculante 13."
    if e["k"] == "linha" and e["t"].startswith("Segundo o Artigo 37, inciso XXXIII"):
        e["t"] = "Segundo o Artigo 37, inciso XXXIII, da Constituição Federal de 1988, é vedado ao servidor público dar nomeação [...] a parente colateral até terceiro grau."
    if e["k"] == "linha" and e["t"].startswith("Corrija o parecer"):
        e["t"] = "Corrija: substitua cada citação bloqueada por fonte aceita. Não invente fontes."
    if e["k"] == "cmd" and len(e["t"]) > 70:
        e["t"] = e["t"][:67] + "..."
# Campos curtos para economizar bytes.
compacto = [[e["d"], e["k"], e.get("t", ""), e.get("c") or e.get("cor") or "", e.get("sub") or e.get("tag") or ""] for e in ev]
js_dados = json.dumps(compacto, ensure_ascii=False, separators=(",", ":"))

pagina = """<html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#070D18;color:#e2e8f0;overflow:hidden;font-family:"Segoe UI",system-ui,sans-serif}
#p{position:relative;width:100vw;height:100vh;container-type:inline-size}
#t{position:absolute;left:2cqw;right:2cqw;top:2cqw;bottom:16%;overflow:hidden;font-family:Consolas,"Cascadia Mono",monospace;font-size:1.45cqw;line-height:1.5}
.l{white-space:pre-wrap;margin:0}.cmd{color:#e2e8f0}.cmd:before{content:"$ ";color:#22d3ee}
.out{color:#cbd5e1}.dim,.json{color:#94a3b8}.ok{color:#22d3ee}.bloq{color:#f59e0b}.tool{color:#e2e8f0}
.alerta{color:#fde68a;background:rgba(245,158,11,.12);border-left:.3cqw solid #f59e0b;padding-left:.6cqw}
#g{position:absolute;left:2cqw;right:2cqw;bottom:2.5cqw;display:flex;align-items:center;gap:1.2cqw;font-size:2cqw;font-weight:500}
.tag{font-size:1.3cqw;font-weight:700;text-transform:uppercase;letter-spacing:.08em;padding:.3em .8em;border-radius:.4cqw;border:1px solid currentColor;color:#94a3b8}
.ciano{color:#22d3ee;background:rgba(34,211,238,.1)}.ambar{color:#f59e0b;background:rgba(245,158,11,.12)}
.c{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 8cqw;background:rgba(7,13,24,.94);opacity:0;transition:opacity .4s}
.c.on{opacity:1}.c h1{font-size:3.6cqw;margin:0 0 1.2cqw;font-weight:650}.c p{font-size:1.7cqw;color:#94a3b8;margin:0;font-family:Consolas,monospace}
#s h1{color:#22d3ee;border:.3cqw solid #22d3ee;border-radius:1cqw;padding:1cqw 3cqw;background:rgba(34,211,238,.1)}
#b{position:absolute;left:0;bottom:0;height:.4cqw;width:0;background:#22d3ee;transition:width .3s linear}
</style></head><body><div id="p"><div id="t"></div><div id="g"></div><div class="c" id="k"><h1></h1><p></p></div><div class="c" id="s"><h1></h1><p></p></div><div id="b"></div></div>
<script>
const E=__DADOS__;const $=i=>document.getElementById(i),T=$("t"),G=$("g"),K=$("k"),S=$("s");
const tot=E.reduce((a,e)=>a+e[0]+(e[1]=="cmd"?35*e[2].length:0),0);let gone=0;
const w=ms=>new Promise(r=>setTimeout(()=>{gone+=ms;$("b").style.width=Math.min(100,100*gone/tot)+"%";r()},ms));
function L(x,c){const p=document.createElement("p");p.className="l "+(c||"out");p.textContent=x||" ";T.appendChild(p);T.scrollTop=T.scrollHeight;return p}
async function play(){gone=0;T.innerHTML="";G.innerHTML="";
for(const [d,k,t,c,x] of E){await w(d);K.classList.remove("on");S.classList.remove("on");
if(k=="titulo"){K.querySelector("h1").textContent=t;K.querySelector("p").textContent=x;K.classList.add("on")}
else if(k=="fim")K.classList.add("on");
else if(k=="selo"){S.querySelector("h1").textContent=t;S.querySelector("p").textContent=x;S.classList.add("on")}
else if(k=="limpar")T.innerHTML="";
else if(k=="cmd"){const p=L("","cmd");for(let i=1;i<=t.length;i++){p.textContent=t.slice(0,i);await w(35)}}
else if(k=="linha")L(t,c);
else if(k=="legenda"){G.innerHTML="";const a=document.createElement("span");a.className="tag "+c;a.textContent=x;const b=document.createElement("span");b.textContent=t;G.append(a,b)}}
K.classList.add("on");await w(6000);play()}
play();
</script></body></html>"""

saida = pagina.replace("__DADOS__", js_dados)
open(DESTINO, "w", encoding="utf-8").write(saida)
tamanho = len(saida.encode("utf-8"))
print("bytes:", tamanho, "eventos:", len(compacto), "ok" if tamanho <= 16000 else "GRANDE DEMAIS")
sys.exit(0 if tamanho <= 16000 else 1)
