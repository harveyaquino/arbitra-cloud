"""
arbitra — Scanner Serverless (Vercel Cron)
Escanea The Odds API, detecta value bets, guarda en Supabase, alerta por Telegram.
Se ejecuta cada hora vía Vercel Cron o manualmente desde el dashboard.
"""

import os
import logging
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

logger = logging.getLogger("arbitra.scan")

# ─── Config ──────────────────────────────────────────────────────────────────
ODDS_API_KEY   = os.environ.get("ODDS_API_KEY", "")
SUPABASE_URL   = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY   = os.environ.get("SUPABASE_SERVICE_KEY", "")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHATS = [c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]
BANKROLL       = float(os.environ.get("BANKROLL", "300"))
CRON_SECRET    = os.environ.get("CRON_SECRET", "")

# ─── Scanner params ──────────────────────────────────────────────────────────
MIN_VALUE        = 0.03     # 3% minimum edge
MIN_ODDS         = 1.30
MAX_ODDS         = 5.00
KELLY_FRACTION   = 0.25     # quarter Kelly
MAX_STAKE_PCT    = 5.0      # max 5% of bankroll
MIN_BOOKMAKERS   = 3        # minimum bookmakers per event
SPORTS_PER_SCAN  = int(os.environ.get("SPORTS_PER_SCAN", "2"))

# ─── Sports (The Odds API keys) ─────────────────────────────────────────────
# Optimizados para value betting: alta liquidez + diversidad de bookmakers
DEFAULT_SPORTS = ",".join([
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_uefa_champs_league",
    "basketball_nba",
    "icehockey_nhl",
    "baseball_mlb",
    "americanfootball_nfl",
    "mma_mixed_martial_arts",
])
SPORTS = [s.strip() for s in os.environ.get("SCAN_SPORTS", DEFAULT_SPORTS).split(",") if s.strip()]

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"

# ─── Supabase ────────────────────────────────────────────────────────────────
_supabase: Client = None

def get_sb() -> Client:
    global _supabase
    if not _supabase:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="ARBITRA Scanner", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_sports_for_scan() -> list[str]:
    """Rota deportes para optimizar uso de API (free tier = 500 req/mes).
    Ej: con 10 deportes y SPORTS_PER_SCAN=2, cada deporte se escanea cada 5 horas.
    """
    if len(SPORTS) <= SPORTS_PER_SCAN:
        return SPORTS

    sb = get_sb()
    res = sb.table("scans").select("id", count="exact").execute()
    idx = res.count or 0

    selected = []
    for i in range(SPORTS_PER_SCAN):
        selected.append(SPORTS[(idx * SPORTS_PER_SCAN + i) % len(SPORTS)])
    return selected


def fetch_odds(client: httpx.Client, sport: str) -> tuple[list, dict]:
    """Fetch odds from The Odds API. Returns (events, headers_info)."""
    try:
        resp = client.get(
            f"{ODDS_API_BASE}/{sport}/odds",
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us,uk,eu,au",
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
            timeout=8.0,
        )
        resp.raise_for_status()
        headers = {
            "remaining": resp.headers.get("x-requests-remaining", "?"),
            "used": resp.headers.get("x-requests-used", "?"),
        }
        return resp.json(), headers
    except Exception as e:
        logger.error(f"Error fetching {sport}: {e}")
        return [], {}


def detect_value_bets(events: list) -> list[dict]:
    """Detecta value bets comparando cuota máxima vs probabilidad justa del mercado."""
    value_bets = []

    for event in events:
        bookmakers = event.get("bookmakers", [])
        if len(bookmakers) < MIN_BOOKMAKERS:
            continue

        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")

        # Recopilar cuotas por outcome
        outcomes: dict[str, list[dict]] = {}
        for bk in bookmakers:
            for market in bk.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for oc in market.get("outcomes", []):
                    outcomes.setdefault(oc["name"], []).append({
                        "bookmaker": bk["title"],
                        "odds": oc["price"],
                    })

        # Calcular probabilidades promedio por outcome (para overround)
        outcome_avg_probs = {}
        for name, entries in outcomes.items():
            odds_list = [e["odds"] for e in entries]
            outcome_avg_probs[name] = sum(1 / o for o in odds_list) / len(odds_list)
        overround = sum(outcome_avg_probs.values()) if outcome_avg_probs else 1.0

        # Analizar cada outcome
        for outcome_name, entries in outcomes.items():
            all_odds = [e["odds"] for e in entries]
            best_entry = max(entries, key=lambda e: e["odds"])
            best_odds = best_entry["odds"]
            best_bookmaker = best_entry["bookmaker"]

            if best_odds < MIN_ODDS or best_odds > MAX_ODDS:
                continue

            implied_prob = 1 / best_odds
            market_prob = outcome_avg_probs.get(outcome_name, implied_prob)
            model_prob = market_prob / overround if overround > 0 else market_prob

            value = model_prob - implied_prob
            if value < MIN_VALUE:
                continue

            # Kelly Criterion
            b = best_odds - 1
            p, q = model_prob, 1 - model_prob
            kelly = (b * p - q) / b if b > 0 else 0
            stake_pct = min(max(kelly * KELLY_FRACTION * 100, 0), MAX_STAKE_PCT)
            stake_amount = round(BANKROLL * stake_pct / 100, 2)
            if stake_amount < 1:
                continue

            # Mapear selección
            if outcome_name == home_team:
                selection, selection_label = "home", f"🏠 {outcome_name}"
            elif outcome_name == away_team:
                selection, selection_label = "away", f"✈️ {outcome_name}"
            elif outcome_name.lower() == "draw":
                selection, selection_label = "draw", "⚖️ Empate"
            else:
                selection, selection_label = outcome_name.lower(), outcome_name

            value_bets.append({
                "event_id":              event["id"],
                "home_team":             home_team,
                "away_team":             away_team,
                "commence_time":         event.get("commence_time"),
                "sport":                 event.get("sport_key", ""),
                "selection":             selection,
                "selection_label":       selection_label,
                "best_odds":             round(best_odds, 3),
                "best_bookmaker":        best_bookmaker,
                "implied_prob":          round(implied_prob, 4),
                "model_prob":            round(model_prob, 4),
                "value":                 round(value, 4),
                "overround":             round(overround, 4),
                "recommended_stake_pct": round(stake_pct, 3),
                "stake_amount":          stake_amount,
                "bookmaker_count":       len(entries),
            })

    return value_bets


def save_to_supabase(events_count: int, value_bets: list) -> tuple[int, int]:
    """Guarda scan + bets en Supabase. Retorna (scan_id, saved_count)."""
    sb = get_sb()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    scan_res = sb.table("scans").insert({
        "events": events_count,
        "value_bets": len(value_bets),
    }).execute()
    scan_id = scan_res.data[0]["id"]

    saved = 0
    for vb in value_bets:
        # Verificar duplicado (mismo evento + selección + día)
        existing = sb.table("bets") \
            .select("id") \
            .eq("event_id", vb["event_id"]) \
            .eq("selection", vb["selection"]) \
            .gte("detected_at", f"{today}T00:00:00") \
            .execute()

        if existing.data:
            continue

        sb.table("bets").insert({
            "scan_id": scan_id,
            "status":  "pending",
            **vb,
        }).execute()
        saved += 1

    return scan_id, saved


def send_telegram(value_bets: list, saved_count: int):
    """Envía alerta Telegram a todos los chat IDs configurados."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHATS or saved_count == 0:
        return

    lines = [f"🎯 *ARBITRA — {saved_count} value bet(s) nuevo(s)*\n"]
    for vb in value_bets[:5]:
        sport_label = vb["sport"].replace("soccer_", "⚽ ").replace("basketball_", "🏀 ") \
            .replace("americanfootball_", "🏈 ").replace("icehockey_", "🏒 ") \
            .replace("baseball_", "⚾ ").replace("mma_", "🥊 ").replace("_", " ").upper()
        lines.append(
            f"{sport_label}\n"
            f"  {vb['home_team']} vs {vb['away_team']}\n"
            f"  → {vb['selection_label']} @ *{vb['best_odds']}* ({vb['best_bookmaker']})\n"
            f"  → Value: *+{vb['value'] * 100:.1f}%* | Stake: *${vb['stake_amount']}*"
        )
    if len(value_bets) > 5:
        lines.append(f"\n_...y {len(value_bets) - 5} más_")

    text = "\n".join(lines)

    with httpx.Client(timeout=5.0) as client:
        for chat_id in TELEGRAM_CHATS:
            try:
                client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
            except Exception as e:
                logger.error(f"Telegram error ({chat_id}): {e}")


# ─── Endpoint ────────────────────────────────────────────────────────────────

@app.get("/api/scan")
def run_scan():
    """Ejecuta scanner de value bets. Llamado por Vercel Cron (cada hora) o manualmente."""
    if not ODDS_API_KEY:
        return {"status": "error", "message": "ODDS_API_KEY no configurada"}
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"status": "error", "message": "Supabase no configurado"}

    # Seleccionar deportes (rotación para optimizar API budget)
    scan_sports = get_sports_for_scan()
    all_events = []
    all_value_bets = []
    api_remaining = "?"

    with httpx.Client(timeout=8.0) as client:
        for sport in scan_sports:
            events, headers = fetch_odds(client, sport)
            all_events.extend(events)
            vbs = detect_value_bets(events)
            all_value_bets.extend(vbs)
            if headers.get("remaining"):
                api_remaining = headers["remaining"]

    # Guardar en Supabase
    scan_id, saved = save_to_supabase(len(all_events), all_value_bets)

    # Alertar por Telegram
    send_telegram(all_value_bets, saved)

    return {
        "status":           "ok",
        "scan_id":          scan_id,
        "sports_scanned":   scan_sports,
        "events_scanned":   len(all_events),
        "value_bets_found": len(all_value_bets),
        "new_bets_saved":   saved,
        "api_remaining":    api_remaining,
    }
