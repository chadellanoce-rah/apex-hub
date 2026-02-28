# APEX HUB v2.0

Sistema de análise técnica de trading com IA — TradingView → Railway → Dashboard web.

## Arquitetura

```
TradingView (Pine Script) 
    ↓ webhook JSON
Railway (FastAPI + SQLite)
    ↓ análise Claude AI
Dashboard Web (/hub)
    ↓ Telegram
Canal de sinais
```

## Rotas

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/hub` | Dashboard web |
| POST | `/webhook` | Recebe sinais do TradingView |
| GET | `/signals` | Lista sinais (`?limit=50&asset=BTC/USDT`) |
| GET | `/signals/latest` | Sinal mais recente |
| GET | `/api/stats` | Estatísticas globais |
| GET | `/health` | Status do servidor |

## Variáveis de ambiente (Railway)

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `ANTHROPIC_API_KEY` | Chave da API Claude | obrigatório |
| `SCORE_MINIMO` | Score mínimo para processar | `3` |
| `REQUIRE_TF_ALIGNMENT` | Exigir TFs alinhados | `true` |
| `TELEGRAM_ENABLED` | Ativar envio Telegram | `false` |
| `TELEGRAM_BOT_TOKEN` | Token do bot | opcional |
| `TELEGRAM_CHAT_ID` | ID do canal/chat | opcional |

## Deploy no Railway

1. Faça push dos 4 arquivos para o GitHub: `main.py`, `hub.html`, `requirements.txt`, `Procfile`
2. Railway detecta automaticamente e faz o deploy
3. Acesse `https://seu-dominio.up.railway.app/hub`

## Formato do Webhook (TradingView)

Configure o alerta com a mensagem JSON gerada pelo indicador **APEX HUB Aggregator v1.0**.
URL do webhook: `https://seu-dominio.up.railway.app/webhook`
