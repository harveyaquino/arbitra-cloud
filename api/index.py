"""
arbitra — API Serverless para Vercel
Conecta con Supabase en lugar de SQLite local.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from supabase import create_client, Client

# ─── Supabase client ─────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]  # service_role key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="ARBITRA API", version="4.0")
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "traceback": traceback.format_exc()}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ──────────────────────────────────────────────────────────────────
class ResolveRequest(BaseModel):
    home_goals: int
    away_goals: int


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/stats")
def stats():
    res = supabase.table("bet_stats").select("*").execute()
    s = res.data[0] if res.data else {}
    
    # Defaults in case the view returns null because there are no resolved bets
    s["roi"] = s.get("roi") or 0
    s["total_pl"] = s.get("total_pl") or 0
    s["win_rate"] = s.get("win_rate") or 0
    s["avg_value"] = s.get("avg_value") or 0
    s["avg_odds"] = s.get("avg_odds") or 0
    s["resolved"] = s.get("resolved") or 0
    s["total_staked"] = s.get("total_staked") or 0
    s["won"] = s.get("won") or 0
    s["lost"] = s.get("lost") or 0
    s["pending"] = s.get("pending") or 0
    
    by_sport = supabase.rpc("stats_by_sport").execute()
    s["by_sport"] = by_sport.data if by_sport.data else []
    return s


@app.get("/api/bets")
def get_bets(
    status: Optional[str] = None,
    sport:  Optional[str] = None,
    limit:  int = Query(50, le=200),
    offset: int = 0,
):
    q = supabase.table("bets").select("*", count="exact")

    if status:
        q = q.eq("status", status)
    if sport:
        q = q.ilike("sport", f"%{sport}%")

    res = q.order("detected_at", desc=True).range(offset, offset + limit - 1).execute()
    return {"bets": res.data, "total": res.count}


@app.get("/api/bets/pending")
def pending_bets():
    res = supabase.table("bets").select("*").eq("status", "pending").order("commence_time").execute()
    return res.data


@app.get("/api/bets/roi-over-time")
def roi_over_time():
    res = supabase.rpc("roi_over_time").execute()
    return res.data or []


@app.post("/api/bets/{bet_id}/resolve")
def resolve(bet_id: int, body: ResolveRequest):
    # Obtener bet
    res = supabase.table("bets").select("*").eq("id", bet_id).single().execute()
    if not res.data:
        raise HTTPException(404, f"Bet {bet_id} no encontrado")

    bet = res.data
    hg, ag = body.home_goals, body.away_goals

    if hg > ag:     actual = "home"
    elif hg == ag:  actual = "draw"
    else:           actual = "away"

    won = (actual == bet["selection"])
    stake = bet["stake_amount"]
    profit_loss = round(stake * (bet["best_odds"] - 1), 2) if won else round(-stake, 2)
    status = "won" if won else "lost"

    supabase.table("bets").update({
        "status": status,
        "result_home_goals": hg,
        "result_away_goals": ag,
        "profit_loss": profit_loss,
        "resolved_at": "now()",
    }).eq("id", bet_id).execute()

    return {"status": status, "profit_loss": profit_loss}


@app.get("/api/scans")
def get_scans(limit: int = 20):
    res = supabase.table("scans").select("*").order("scanned_at", desc=True).limit(limit).execute()
    return res.data


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "4.0"}
