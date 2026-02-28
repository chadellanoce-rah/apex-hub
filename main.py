"""
APEX HUB — Backend v3.0
Deploy no Railway (railway.app) — arquivo único
"""

import os, json, sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI(title="APEX HUB", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Banco de dados ─────────────────────────────────────────────────────────────
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
        payload.get("timestamp", datetime.utcnow().isoformat()),
        payload.get("asset"),
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

def get_signals(limit=50, asset=None, direction=None):
    init_db()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    where, params = [], []
    if asset:
        where.append("asset=?"); params.append(asset)
    if direction:
        where.append("direction=?"); params.append(direction)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    rows = con.execute(f"SELECT * FROM signals {clause} ORDER BY id DESC LIMIT ?", params).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_stats():
    init_db()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    total    = con.execute("SELECT COUNT(*) as n FROM signals").fetchone()["n"]
    buys     = con.execute("SELECT COUNT(*) as n FROM signals WHERE direction='buy'").fetchone()["n"]
    sells    = con.execute("SELECT COUNT(*) as n FROM signals WHERE direction='sell'").fetchone()["n"]
    avg_scr  = con.execute("SELECT AVG(score) as v FROM signals").fetchone()["v"] or 0
    avg_prob = con.execute("SELECT AVG(prob) as v FROM signals WHERE prob > 0").fetchone()["v"] or 0
    assets   = con.execute("SELECT DISTINCT asset FROM signals ORDER BY asset").fetchall()
    con.close()
    return {
        "total": total, "buys": buys, "sells": sells,
        "avg_score": round(avg_scr, 2),
        "avg_prob": round(avg_prob, 1),
        "assets": [r["asset"] for r in assets]
    }

# ── Prompt Apex 1.0 S-Tier ────────────────────────────────────────────────────
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
    direction = sig.get("direction", "neutral").upper()
    path = sig.get("path_clear", False)
    asset = p.get("asset", "?")
    weekend_note = "\n⚠ WEEKEND ATIVO: stops folgados +15%, priorizar TP1, evitar alvos distantes.\n" if wk else ""

    return f"""Voce e o APEX 1.0 - Protocolo de Analise Profissional de Trading (S-Tier).
Ative o Comando: $ {asset}

MISSAO: Analise profissional institucional com SMC avancado.

ATIVO: {asset} | TFs: {tfs.get("principal")} / {tfs.get("confirmacao")} / {tfs.get("entrada")}
DIRECAO: {direction} {"CAMINHO LIVRE" if path else "OBSTRUIDO"} | Score: {scr.get("total")}/5
{weekend_note}
PRECO: close={pr.get("close")} | high={pr.get("high")} | low={pr.get("low")} | atr14={pr.get("atr14")}
FIBONACCI KEO: high={fib.get("high")} | low={fib.get("low")} | fib382={fib.get("fib382")} | fib618={fib.get("fib618")}
SD ZONES: tipo={sd.get("zone_type")} | dentro_zona={sd.get("in_zone")} | demand={sd.get("demand_btm")}-{sd.get("demand_top")} | supply={sd.get("supply_btm")}-{sd.get("supply_top")}
KEO v7: sinal={sig.get("type")} | er_kaufman={keo.get("er_kaufman")} | er_ok={keo.get("er_ok")} | ema8={keo.get("ema8")} | ema24={keo.get("ema24")}
MM KERNEL: status={mm.get("status")} | valor={mm.get("value")} | adx={mm.get("adx")} | slope_ema24={mm.get("ema24_slope")}%
OSC MATRIX: money_flow={osc.get("money_flow")} | hyper_wave={osc.get("hyper_wave")} | confluencia={osc.get("confluence")}
STOCH RSI: k={st.get("k")} | d={st.get("d")} | oversold={st.get("oversold")} | overbought={st.get("overbought")}
NIVEIS: entrada={lvl.get("entry")} | stop={lvl.get("stop")} | tp1={lvl.get("tp1")} | tp2={lvl.get("tp2")} | tp3={lvl.get("tp3")}
SCORE: SD={scr.get("sd")}/1 | KEO={scr.get("keo")}/1 | MM={scr.get("mm_kernel")}/1 | OSC={scr.get("osc_matrix")}/1 | STOCH={scr.get("stoch_rsi")}/1 | TOTAL={scr.get("total")}/5

Analise:
1. Estrutura SMC: IDM, ChoCh anti-fake, PoL, BSL/SSL
2. Microestrutura: CVD, agressao, momentum, funding/OI se crypto
3. Gestao de risco: stop/trailing baseado no ATR {pr.get("atr14")}
{"4. Weekend: TR (Total Returns) e baixa liquidez" if wk else ""}

Responda APENAS com JSON valido, sem texto fora do JSON:
{{
  "probabilidade": <0-100>,
  "vies": "<BULLISH|BEARISH|NEUTRO>",
  "estrutura_smc": "<analise ChoCh, IDM, BSL/SSL, liquidez>",
  "microestrutura": "<analise volume, momentum, fluxo>",
  "gestao_risco": "<stop, trailing, contexto de risco>",
  "confluencias": ["<confluencia 1>", "<confluencia 2>", "<confluencia 3>"],
  "alertas": ["<risco 1>", "<risco 2>"],
  "tabela_alvos": {{
    "entrada": {lvl.get("entry", 0)},
    "stop": {lvl.get("stop", 0)},
    "tp1": {lvl.get("tp1", 0)},
    "tp2": {lvl.get("tp2", 0)},
    "tp3": {lvl.get("tp3", 0)},
    "rr_ratio": "<ex: 1:2.5>"
  }},
  "resumo_telegram": "<mensagem pronta para canal de sinais, max 300 chars, use emojis>"
}}"""

# ── Claude API ────────────────────────────────────────────────────────────────
async def call_claude(prompt: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {"error": "ANTHROPIC_API_KEY nao configurada no Railway"}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            system="Voce e APEX 1.0, protocolo de analise tecnica profissional S-Tier. Responda sempre com JSON valido sem texto fora do JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        return {"error": f"parse_error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

# ── Telegram ──────────────────────────────────────────────────────────────────
async def send_telegram(text: str):
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10
            )
    except Exception as e:
        print(f"[Telegram] Erro: {e}")

def format_telegram(payload: dict, analysis: dict) -> str:
    resumo = analysis.get("resumo_telegram", "")
    if resumo:
        return resumo
    sig   = payload.get("signal", {})
    lvl   = payload.get("levels", {})
    tfs   = payload.get("timeframes", {})
    d     = sig.get("direction", "?").upper()
    emoji = "🟢" if d == "BUY" else "🔴"
    star  = " ⭐" if sig.get("path_clear") else ""
    wk    = "\n⚠ <b>Weekend Mode</b>" if payload.get("is_weekend") else ""
    scr   = payload.get("score", {}).get("total", 0)
    prob  = analysis.get("probabilidade", "?")
    asset = payload.get("asset", "?")
    return (
        f"{emoji} <b>{d} — {asset}</b>{star}\n"
        f"⏱ {tfs.get('principal')} | Score: {scr}/5 | Prob: {prob}%\n\n"
        f"📍 Entrada: <b>{lvl.get('entry')}</b>\n"
        f"🛑 Stop: <b>{lvl.get('stop')}</b>\n"
        f"🎯 TP1: <b>{lvl.get('tp1')}</b> | TP2: <b>{lvl.get('tp2')}</b> | TP3: <b>{lvl.get('tp3')}</b>"
        f"{wk}\n#APEX #{asset.replace('/','')}"
    )

# ── Background task ───────────────────────────────────────────────────────────
async def process_signal(payload: dict):
    asset     = payload.get("asset", "?")
    score     = payload.get("score", {}).get("total", 0)
    direction = payload.get("signal", {}).get("direction", "?")
    print(f"[APEX] {asset} | {direction.upper()} | Score {score}/5")
    prompt   = build_prompt(payload)
    analysis = await call_claude(prompt)
    if os.getenv("TELEGRAM_ENABLED", "false").lower() == "true":
        msg = format_telegram(payload, analysis)
        await send_telegram(msg)
    save_signal(payload, analysis)
    print(f"[APEX] {asset} processado. Prob: {analysis.get('probabilidade', '?')}%")

# ════════════════════════════════════════════════════════
# ROTAS
# ════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse('<meta http-equiv="refresh" content="0; url=/hub">', status_code=302)

@app.get("/hub", response_class=HTMLResponse)
async def hub():
    hub_file = Path("hub.html")
    if not hub_file.exists():
        return HTMLResponse("<h1>hub.html nao encontrado</h1>", status_code=404)
    return HTMLResponse(hub_file.read_text(encoding="utf-8"))

@app.get("/health")
async def health():
    stats = get_stats()
    return {"status": "ok", "version": "3.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "signals_total": stats["total"]}

@app.get("/api/stats")
async def stats():
    return get_stats()

@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks):
    try:
        payload = json.loads(await request.body())
    except Exception:
        return JSONResponse({"status": "error", "reason": "JSON invalido"}, status_code=400)

    score_total = payload.get("score", {}).get("total", 0)
    score_min   = int(os.getenv("SCORE_MINIMO", "3"))
    if score_total < score_min:
        return JSONResponse({"status": "ignored", "reason": f"Score {score_total} < minimo {score_min}"})

    tf_aligned        = payload.get("signal", {}).get("tf_aligned", False)
    require_alignment = os.getenv("REQUIRE_TF_ALIGNMENT", "true").lower() == "true"
    if require_alignment and not tf_aligned:
        return JSONResponse({"status": "ignored", "reason": "TFs nao alinhados"})

    bg.add_task(process_signal, payload)
    return JSONResponse({
        "status": "received",
        "asset": payload.get("asset"),
        "score": score_total,
        "direction": payload.get("signal", {}).get("direction")
    })

@app.get("/signals")
async def list_signals(limit: int = 50, asset: Optional[str] = None, direction: Optional[str] = None):
    return {"signals": get_signals(limit=limit, asset=asset, direction=direction)}

@app.get("/signals/latest")
async def latest(asset: Optional[str] = None):
    signals = get_signals(limit=1, asset=asset)
    return {"signal": signals[0] if signals else None}

@app.delete("/signals/{signal_id}")
async def delete_signal(signal_id: int):
    init_db()
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM signals WHERE id=?", (signal_id,))
    con.commit(); con.close()
    return {"status": "deleted", "id": signal_id}
