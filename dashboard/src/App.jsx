import { useState, useEffect } from "react"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { Clock, CheckCircle, XCircle, RefreshCw, ChevronRight, TrendingUp, Zap } from "lucide-react"

// En Vercel la API está en el mismo dominio — /api
// En desarrollo local apunta a localhost:8000
const API = import.meta.env.VITE_API_URL || "/api"

const fmt    = (n) => n >= 0 ? `+$${Number(n).toFixed(2)}` : `-$${Math.abs(n).toFixed(2)}`
const fmtPct = (n) => `${n >= 0 ? "+" : ""}${Number(n).toFixed(1)}%`

function StatCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: "#0f0f0f",
      border: `1px solid ${color}22`,
      borderTop: `2px solid ${color}`,
      borderRadius: 8,
      padding: "20px 24px",
      flex: 1,
      minWidth: 150,
    }}>
      <div style={{ color: "#666", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ color, fontSize: 26, fontWeight: 700, fontFamily: "monospace" }}>{value}</div>
      {sub && <div style={{ color: "#555", fontSize: 12, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function BetRow({ bet, onResolve }) {
  const [resolving, setResolving] = useState(false)
  const [hg, setHg] = useState("")
  const [ag, setAg] = useState("")

  const statusColor = { won: "#22c55e", lost: "#ef4444", pending: "#f59e0b" }
  const statusIcon  = { won: <CheckCircle size={13}/>, lost: <XCircle size={13}/>, pending: <Clock size={13}/> }

  return (
    <div style={{
      background: "#0a0a0a", border: "1px solid #1a1a1a", borderRadius: 8,
      padding: "14px 18px", marginBottom: 8,
      display: "flex", alignItems: "center", gap: 14,
    }}>
      <div style={{ color: statusColor[bet.status] || "#666", display: "flex", alignItems: "center", gap: 4, minWidth: 72, fontSize: 12 }}>
        {statusIcon[bet.status]} {bet.status}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ color: "#e0e0e0", fontSize: 13, fontWeight: 500 }}>
          {bet.home_team} <span style={{ color: "#444" }}>vs</span> {bet.away_team}
        </div>
        <div style={{ color: "#555", fontSize: 11, marginTop: 2 }}>
          {bet.sport?.replace("soccer_", "").replace(/_/g, " ").toUpperCase()} · {bet.commence_time?.slice(0, 10)}
        </div>
      </div>

      <div style={{ textAlign: "center", minWidth: 110 }}>
        <div style={{ color: "#a78bfa", fontSize: 12, fontWeight: 600 }}>{bet.selection_label}</div>
        <div style={{ color: "#555", fontSize: 11 }}>@ {bet.best_odds} ({bet.best_bookmaker})</div>
      </div>

      <div style={{ textAlign: "right", minWidth: 88 }}>
        <div style={{ color: "#22c55e", fontSize: 13, fontWeight: 600 }}>+{(bet.value * 100).toFixed(1)}%</div>
        <div style={{ color: "#555", fontSize: 11 }}>${Number(bet.stake_amount).toFixed(2)}</div>
      </div>

      <div style={{ minWidth: 100, textAlign: "right" }}>
        {bet.status === "pending" ? (
          resolving ? (
            <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <input placeholder="L" value={hg} onChange={e => setHg(e.target.value)}
                style={{ width: 32, background: "#1a1a1a", border: "1px solid #333", borderRadius: 4, color: "#fff", padding: "2px 6px", fontSize: 12, textAlign: "center" }}/>
              <span style={{ color: "#444" }}>-</span>
              <input placeholder="V" value={ag} onChange={e => setAg(e.target.value)}
                style={{ width: 32, background: "#1a1a1a", border: "1px solid #333", borderRadius: 4, color: "#fff", padding: "2px 6px", fontSize: 12, textAlign: "center" }}/>
              <button onClick={() => { onResolve(bet.id, parseInt(hg), parseInt(ag)); setResolving(false) }}
                style={{ background: "#a78bfa", border: "none", borderRadius: 4, padding: "3px 8px", cursor: "pointer", color: "#000", fontSize: 11, fontWeight: 700 }}>OK</button>
            </div>
          ) : (
            <button onClick={() => setResolving(true)} style={{
              background: "transparent", border: "1px solid #333", borderRadius: 6,
              color: "#888", padding: "4px 10px", cursor: "pointer", fontSize: 11,
              display: "flex", alignItems: "center", gap: 4, marginLeft: "auto"
            }}>
              Resolver <ChevronRight size={12}/>
            </button>
          )
        ) : (
          <div style={{ color: bet.profit_loss >= 0 ? "#22c55e" : "#ef4444", fontSize: 14, fontWeight: 700, fontFamily: "monospace" }}>
            {fmt(bet.profit_loss || 0)}
          </div>
        )}
      </div>
    </div>
  )
}

function ScanToast({ result, onClose }) {
  if (!result) return null
  return (
    <div style={{
      position: "fixed", top: 20, right: 20, zIndex: 999,
      background: result.status === "ok" ? "#0a1a0a" : "#1a0a0a",
      border: `1px solid ${result.status === "ok" ? "#22c55e33" : "#ef444433"}`,
      borderRadius: 10, padding: "14px 20px", maxWidth: 340,
      boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      animation: "fadeIn 0.3s ease",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <div style={{ color: result.status === "ok" ? "#22c55e" : "#ef4444", fontSize: 13, fontWeight: 700 }}>
          {result.status === "ok" ? "✅ Scan completo" : "❌ Error en scan"}
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#555", cursor: "pointer", fontSize: 16 }}>×</button>
      </div>
      {result.status === "ok" && (
        <div style={{ color: "#888", fontSize: 11, lineHeight: 1.6 }}>
          📊 {result.events_scanned} eventos escaneados<br/>
          🎯 {result.value_bets_found} value bets encontrados<br/>
          💾 {result.new_bets_saved} nuevos guardados<br/>
          🔑 API restante: {result.api_remaining}
        </div>
      )}
      {result.message && <div style={{ color: "#ef4444", fontSize: 11 }}>{result.message}</div>}
    </div>
  )
}

export default function App() {
  const [stats,      setStats]      = useState(null)
  const [bets,       setBets]       = useState([])
  const [roiData,    setRoiData]    = useState([])
  const [lastScan,   setLastScan]   = useState(null)
  const [tab,        setTab]        = useState("all")
  const [loading,    setLoading]    = useState(true)
  const [error,      setError]      = useState(false)
  const [scanning,   setScanning]   = useState(false)
  const [scanResult, setScanResult] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [s, b, r, sc] = await Promise.all([
        fetch(`${API}/stats`).then(r => r.json()),
        fetch(`${API}/bets?limit=50`).then(r => r.json()),
        fetch(`${API}/bets/roi-over-time`).then(r => r.json()),
        fetch(`${API}/scans?limit=1`).then(r => r.json()),
      ])
      setStats(s)
      setBets(b.bets || [])
      setRoiData(r)
      if (sc?.length) setLastScan(sc[0])
      setError(false)
    } catch {
      setError(true)
    }
    setLoading(false)
  }

  const handleResolve = async (id, hg, ag) => {
    await fetch(`${API}/bets/${id}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ home_goals: hg, away_goals: ag }),
    })
    load()
  }

  const handleScan = async () => {
    setScanning(true)
    setScanResult(null)
    try {
      const res = await fetch(`/api/scan`)
      const data = await res.json()
      setScanResult(data)
      if (data.status === "ok") load()
    } catch {
      setScanResult({ status: "error", message: "No se pudo conectar al scanner" })
    }
    setScanning(false)
    setTimeout(() => setScanResult(null), 8000)
  }

  useEffect(() => { load() }, [])

  const filtered   = tab === "all" ? bets : bets.filter(b => b.status === tab)
  const roiColor   = (stats?.roi ?? 0) >= 0 ? "#22c55e" : "#ef4444"

  return (
    <div style={{ minHeight: "100vh", background: "#050505", color: "#e0e0e0", fontFamily: "'Inter',system-ui,sans-serif", padding: "32px 40px", maxWidth: 1100, margin: "0 auto" }}>

      <ScanToast result={scanResult} onClose={() => setScanResult(null)} />

      {/* Header */}
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, letterSpacing: "-0.03em", color: "#fff" }}>
            ARBITRA<span style={{ color: "#a78bfa" }}>.</span>
          </h1>
          <div style={{ color: "#444", fontSize: 12, marginTop: 2 }}>
            {lastScan
              ? `Último scan: ${lastScan.scanned_at?.slice(0, 16).replace("T", " ")} UTC · ${lastScan.value_bets} value bets`
              : "Sin scans aún — haz click en Escanear"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={handleScan} disabled={scanning} style={{
            background: scanning ? "#1a1a1a" : "linear-gradient(135deg, #7c3aed, #a78bfa)",
            border: "none", borderRadius: 8,
            color: scanning ? "#666" : "#fff",
            padding: "8px 16px", cursor: scanning ? "wait" : "pointer",
            fontSize: 13, fontWeight: 600,
            display: "flex", alignItems: "center", gap: 6,
            transition: "all 0.2s",
          }}>
            <Zap size={14} style={{ animation: scanning ? "pulse 1s infinite" : "none" }} />
            {scanning ? "Escaneando..." : "Escanear ahora"}
          </button>
          <button onClick={load} style={{ background: "#0f0f0f", border: "1px solid #222", borderRadius: 8, color: "#888", padding: "8px 16px", cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            <RefreshCw size={14}/> Actualizar
          </button>
        </div>
      </div>

      {error ? (
        <div style={{ color: "#ef4444", textAlign: "center", padding: 80 }}>
          Error conectando con la API.<br/>
          <span style={{ fontSize: 13, color: "#666" }}>Verifica las variables de entorno en Vercel.</span>
        </div>
      ) : loading && !stats ? (
        <div style={{ color: "#444", textAlign: "center", padding: 80 }}>Cargando...</div>
      ) : (
        <>
          {/* Stats */}
          <div style={{ display: "flex", gap: 12, marginBottom: 28, flexWrap: "wrap" }}>
            <StatCard label="ROI"         value={fmtPct(stats.roi)}        sub={`${stats.resolved} bets resueltos`}      color={roiColor}  />
            <StatCard label="P&L Total"   value={fmt(stats.total_pl)}       sub={`sobre $${stats.total_staked} apostado`} color={roiColor}  />
            <StatCard label="Win Rate"    value={`${Number(stats.win_rate).toFixed(0)}%`} sub={`${stats.won}W / ${stats.lost}L`}  color="#60a5fa" />
            <StatCard label="Value Medio" value={`+${stats.avg_value}%`}    sub={`cuota media ${stats.avg_odds}`}         color="#a78bfa"   />
            <StatCard label="Pendientes"  value={stats.pending}             sub="por resolver"                            color="#f59e0b"   />
          </div>

          {/* Chart */}
          {roiData.length > 0 && (
            <div style={{ background: "#0a0a0a", border: "1px solid #1a1a1a", borderRadius: 10, padding: "20px 24px", marginBottom: 28 }}>
              <div style={{ color: "#666", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>P&L Acumulado</div>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={roiData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#111"/>
                  <XAxis dataKey="date" tick={{ fill: "#444", fontSize: 11 }} axisLine={false} tickLine={false}/>
                  <YAxis tick={{ fill: "#444", fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`}/>
                  <Tooltip contentStyle={{ background: "#111", border: "1px solid #222", borderRadius: 6, fontSize: 12 }} formatter={v => [`$${Number(v).toFixed(2)}`, "P&L acum."]}/>
                  <Line type="monotone" dataKey="cumulative_pl" stroke="#a78bfa" strokeWidth={2} dot={false}/>
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Bets */}
          <div style={{ background: "#0a0a0a", border: "1px solid #1a1a1a", borderRadius: 10, padding: "20px 24px" }}>
            <div style={{ display: "flex", gap: 4, marginBottom: 18 }}>
              {["all", "pending", "won", "lost"].map(t => (
                <button key={t} onClick={() => setTab(t)} style={{
                  background: tab === t ? "#1a1a1a" : "transparent",
                  border: tab === t ? "1px solid #333" : "1px solid transparent",
                  borderRadius: 6, color: tab === t ? "#e0e0e0" : "#555",
                  padding: "5px 14px", cursor: "pointer", fontSize: 12,
                }}>
                  {t === "all"     ? `Todos (${bets.length})`          :
                   t === "pending" ? `Pendientes (${stats.pending})`   :
                   t === "won"     ? `Ganados (${stats.won})`          :
                                    `Perdidos (${stats.lost})`}
                </button>
              ))}
            </div>

            {filtered.length === 0 ? (
              <div style={{ color: "#444", textAlign: "center", padding: 40, fontSize: 13 }}>
                {tab === "pending"
                  ? "Sin pendientes — haz click en Escanear para buscar value bets"
                  : "Sin bets en esta categoría"}
              </div>
            ) : (
              filtered.map(b => <BetRow key={b.id} bet={b} onResolve={handleResolve}/>)
            )}
          </div>
        </>
      )}
    </div>
  )
}
