# ARBITRA
### Probabilidad aplicada. Ventaja sistemática.

Motor de detección de value bets — 100% cloud (Supabase + Vercel).

---

## Stack

| Capa | Tecnología | Costo |
|---|---|---|
| Base de datos | Supabase (PostgreSQL) | Gratis |
| API | Vercel Serverless Functions (FastAPI) | Gratis |
| Dashboard | Vercel Static (React + Vite) | Gratis |
| Scanner | Vercel Cron + Serverless (Python) | Gratis |

---

## Setup paso a paso

### 1. Supabase

1. Crea proyecto en [supabase.com](https://supabase.com)
2. Ve a **SQL Editor** y ejecuta `supabase/schema.sql`
3. Ve a **Settings → API** y copia:
   - Project URL
   - `anon` key
   - `service_role` key

### 2. Variables de entorno

Configura las siguientes variables en **Vercel Dashboard → Settings → Environment Variables**:

| Variable | Descripción |
|---|---|
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_SERVICE_KEY` | service_role key |
| `SUPABASE_ANON_KEY` | anon key |
| `ODDS_API_KEY` | API key de [the-odds-api.com](https://the-odds-api.com) |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID(s) separados por coma |
| `BANKROLL` | Capital total (default: 300) |
| `SPORTS_PER_SCAN` | Deportes por escaneo (default: 2) |

### 3. Deploy en Vercel

1. Sube el repo a GitHub
2. Importa en [vercel.com](https://vercel.com)
3. Agrega las variables de entorno
4. Deploy automático en cada push
5. El scanner se ejecuta automáticamente cada hora vía Cron

---

## Estructura

```
arbitra-cloud/
├── api/
│   ├── index.py          ← API REST (FastAPI serverless)
│   ├── scan.py           ← Scanner de value bets (Vercel Cron)
│   └── requirements.txt
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── supabase/
│   └── schema.sql        ← ejecutar en Supabase SQL Editor
├── vercel.json            ← builds, routes, cron
└── .env.example
```

---

## Cómo funciona el Scanner

1. **Vercel Cron** ejecuta `GET /api/scan` cada hora
2. Obtiene cuotas de **The Odds API** (h2h markets, múltiples regiones)
3. Detecta **value bets** comparando la cuota máxima vs probabilidad justa del mercado
4. Calcula **stake óptimo** con Kelly Criterion fraccionario (25%)
5. Guarda en **Supabase** (con deduplicación por evento/día)
6. Envía **alertas Telegram** a todos los chat IDs configurados

### Rotación de deportes
Para optimizar el uso de la API (tier gratis = 500 req/mes), el scanner rota deportes automáticamente. Con `SPORTS_PER_SCAN=2` y 10 deportes configurados, cada deporte se escanea cada 5 horas.

### Deportes por defecto
EPL, La Liga, Bundesliga, Serie A, Champions League, NBA, NHL, MLB, NFL, MMA/UFC

### Escanear manualmente
Desde el dashboard, haz click en **"Escanear ahora"** para disparar un scan inmediato.

---

## Endpoints API

| Endpoint | Método | Descripción |
|---|---|---|
| `/api/scan` | GET | Ejecutar scanner (cron o manual) |
| `/api/stats` | GET | Estadísticas globales |
| `/api/bets` | GET | Lista paginada de bets |
| `/api/bets/pending` | GET | Bets pendientes |
| `/api/bets/roi-over-time` | GET | Datos para gráfico P&L |
| `/api/bets/{id}/resolve` | POST | Resolver bet con marcador |
| `/api/scans` | GET | Historial de scans |
| `/api/health` | GET | Health check |
