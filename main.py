"""
APEX HUB — Backend v1.0
Deploy no Railway (railway.app) — arquivo único, sem configuração
"""

import os, json, sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="APEX HUB", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Banco de dados
DB = Path("apex.db")

def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS signals (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, asset TEXT, direction TEXT, score INTEGER,
        entry REAL, stop REAL, tp1 REAL, tp2 REAL, tp3 REAL,
        prob INTEGER, path_clear INTEGER, is_weekend INTEGER,
        analysis TEXT, payload TEXT
    )""")
    con.commit(); con.close()

def save_signal(payload, analysis):
    init_db()
    sig = payload.get("signal", {})
    lvl = payload.get("levels", {})
    con = sqlite3.connect(DB)
    con.execute("""INSERT INTO signals
        (timestamp,asset,direction,score,entry,stop,tp1,tp2,tp3,prob,path_clear,is_weekend,analysis,payload)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        payload.get("timestamp"), payload.get("asset"),
        sig.get("direction"),
        payload.get("score", {}).get("total", 0),
        lvl.get("entry"), lvl.get("stop"),
        lvl.get("tp1"), lvl.get("tp2"), lvl.get("tp3"),
        analysis.get("probabilidade", 0),
        1 if sig.get("path_clear") else 0,
        1 if payload.get("is_weekend") else 0,
        json.dumps(analysis, ensure_ascii=False),
        json.dumps(payload,  ensure_ascii=False)
    ))
    con.commit(); con.close()

def get_signals(limit=50, asset=None):
    init_db()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    if asset:
        rows = con.execute("SELECT * FROM signals WHERE asset=? ORDER BY id DESC LIMIT ?", (asset, limit)).fetchall()
    else:
        rows = con.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ── Prompt Apex 1.0
def build_prompt(p):
    tfs = p.get("timeframes", {})
    sig = p.get("signal", {})
    lvl = p.get("levels", {})
    fib = p.get("fibonacci", {})
    sd  = p.get("sd_zones", {})
    keo = p.get("keo", {})
    mm  = p.get("mm_kernel", {})
    osc = p.get("osc_matrix", {})
    st  = p.get("stoch_rsi", {})
    pr  = p.get("price", {})
    scr = p.get("score", {})
    wk  = p.get("is_weekend", False)
    direction = sig.get("direction","neutral").upper()
    path = sig.get("path_clear", False)

    weekend_note = "\n⚠ WEEKEND ATIVO: stops folgados +15%, priorizar TP1, evitar alvos distantes.\n" if wk else ""

    return f"""Você é o APEX 1.0 — Protocolo de Análise Profissional de Trading.
Analise o ativo {p.get("asset")} e gere análise técnica completa.

ATIVO: {p.get("asset")} | {tfs.get("principal")} / {tfs.get("confirmacao")} / {tfs.get("entrada")}
DIREÇÃO: {direction} {"⭐ caminho livre" if path else "⚠ obstruído"} | Score: {scr.get("total")}/5
{weekend_note}
PREÇO: close={pr.get("close")} high={pr.get("high")} low={pr.get("low")} atr={pr.get("atr14")}
NÍVEIS: entrada={lvl.get("entry")} stop={lvl.get("stop")} tp1={lvl.get("tp1")} tp2={lvl.get("tp2")} tp3={lvl.get("tp3")}
FIBONACCI: high={fib.get("high")} low={fib.get("low")} fib382={fib.get("fib382")} fib618={fib.get("fib618")}
SD ZONES: tipo={sd.get("zone_type")} dentro={sd.get("in_zone")} demand={sd.get("demand_btm")}-{sd.get("demand_top")} supply={sd.get("supply_btm")}-{sd.get("supply_top")}
KEO v7: sinal={sig.get("type")} er={keo.get("er_kaufman")} sigma={keo.get("sigma")} ema8={keo.get("ema8")} ema24={keo.get("ema24")}
MM KERNEL: status={mm.get("status")} val={mm.get("value")} adx={mm.get("adx")} slope={mm.get("ema24_slope")}%
OSC MATRIX: mf={osc.get("money_flow")} hw={osc.get("hyper_wave")} conf={osc.get("confluence")} overflow_bear={osc.get("overflow_bear")} overflow_bull={osc.get("overflow_bull")}
STOCH RSI: k={st.get("k")} d={st.get("d")} oversold={st.get("oversold")} overbought={st.get("overbought")}

Responda APENAS com JSON válido, sem texto fora do JSON:
{{
  "probabilidade": <0-100>,
  "vies": "<BULLISH|BEARISH|NEUTRO>",
  "estrutura_smc": "<análise ChoCh, IDM, BSL/SSL, liquidez>",
  "microestrutura": "<análise volume, momentum, fluxo>",
  "gestao_risco": "<análise stop, trailing, contexto>",
  "confluencias": ["<item1>", "<item2>", "<item3>"],
  "alertas": ["<risco1>", "<risco2>"],
  "tabela_alvos": {{
    "entrada": {lvl.get("entry")},
    "stop": {lvl.get("stop")},
    "tp1": {lvl.get("tp1")},
    "tp2": {lvl.get("tp2")},
    "tp3": {lvl.get("tp3")},
    "rr_ratio": "<calcule o R/R>"
  }},
  "resumo_telegram": "<mensagem pronta para o canal, máx 300 chars>"
}}"""

# ── Claude API
async def call_claude(prompt):
    import anthropic
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"error": "ANTHROPIC_API_KEY não configurada"}
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            system="Você é APEX 1.0, sistema de análise técnica profissional. Responda sempre em JSON válido.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "parse_error"}
    except Exception as e:
        return {"error": str(e)}

# ── Telegram
async def send_telegram(text):
    import httpx
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10
        )

def format_telegram(payload, analysis):
    # Prioriza o resumo gerado pelo Claude
    resumo = analysis.get("resumo_telegram", "")
    if resumo:
        return resumo
    # Fallback manual
    sig = payload.get("signal", {})
    lvl = payload.get("levels", {})
    tfs = payload.get("timeframes", {})
    d   = sig.get("direction","?").upper()
    emoji = "🟢" if d == "BUY" else "🔴"
    star  = " ⭐" if sig.get("path_clear") else ""
    wk    = "\n⚠ <b>Weekend Mode</b>" if payload.get("is_weekend") else ""
    scr   = payload.get("score",{}).get("total",0)
    prob  = analysis.get("probabilidade","?")
    asset = payload.get("asset","?")
    return (f"{emoji} <b>{d} — {asset}</b>{star}\n"
            f"⏱ {tfs.get('principal')} | Score: {scr}/5 | Prob: {prob}%\n\n"
            f"📍 Entrada: <b>{lvl.get('entry')}</b>\n"
            f"🛑 Stop: <b>{lvl.get('stop')}</b>\n"
            f"🎯 TP1: <b>{lvl.get('tp1')}</b> | TP2: <b>{lvl.get('tp2')}</b> | TP3: <b>{lvl.get('tp3')}</b>"
            f"{wk}\n#APEX #{asset.replace('/','')}")

# ── Processar sinal em background
async def process_signal(payload):
    asset = payload.get("asset","?")
    score = payload.get("score",{}).get("total",0)
    direction = payload.get("signal",{}).get("direction","?")
    print(f"[APEX] {asset} | {direction.upper()} | Score {score}/5")

    prompt   = build_prompt(payload)
    analysis = await call_claude(prompt)

    if os.getenv("TELEGRAM_ENABLED","false").lower() == "true":
        msg = format_telegram(payload, analysis)
        await send_telegram(msg)

    save_signal(payload, analysis)
    print(f"[APEX] {asset} processado.")

# ════════════════════════════
# ROTAS
# ════════════════════════════

@app.get("/")
async def root():
    return {"status": "APEX HUB online", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks):
    """Recebe o JSON do APEX Aggregator v1 via TradingView Alert."""
    try:
        payload = json.loads(await request.body())
    except Exception:
        return JSONResponse({"status": "error", "reason": "JSON inválido"}, status_code=400)

    score_total = payload.get("score", {}).get("total", 0)
    score_min   = int(os.getenv("SCORE_MINIMO", "3"))

    if score_total < score_min:
        return JSONResponse({"status": "ignored", "reason": f"Score {score_total} < mínimo {score_min}"})

    tf_aligned       = payload.get("signal", {}).get("tf_aligned", False)
    require_alignment = os.getenv("REQUIRE_TF_ALIGNMENT", "true").lower() == "true"

    if require_alignment and not tf_aligned:
        return JSONResponse({"status": "ignored", "reason": "TFs não alinhados"})

    bg.add_task(process_signal, payload)
    return JSONResponse({"status": "received", "asset": payload.get("asset"), "score": score_total})

@app.get("/signals")
async def list_signals(limit: int = 50, asset: Optional[str] = None):
    return {"signals": get_signals(limit=limit, asset=asset)}

@app.get("/signals/latest")
async def latest(asset: Optional[str] = None):
    signals = get_signals(limit=1, asset=asset)
    return {"signal": signals[0] if signals else None}
