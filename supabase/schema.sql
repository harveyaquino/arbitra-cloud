-- ARBITRA — Schema Supabase
-- Ejecuta esto en Supabase → SQL Editor → New Query

-- Tabla de scans
CREATE TABLE IF NOT EXISTS scans (
    id          BIGSERIAL PRIMARY KEY,
    scanned_at  TIMESTAMPTZ DEFAULT NOW(),
    events      INTEGER DEFAULT 0,
    value_bets  INTEGER DEFAULT 0
);

-- Tabla de bets
CREATE TABLE IF NOT EXISTS bets (
    id                      BIGSERIAL PRIMARY KEY,
    scan_id                 BIGINT REFERENCES scans(id),
    detected_at             TIMESTAMPTZ DEFAULT NOW(),

    -- Evento
    event_id                TEXT NOT NULL,
    home_team               TEXT NOT NULL,
    away_team               TEXT NOT NULL,
    commence_time           TIMESTAMPTZ,
    sport                   TEXT NOT NULL,

    -- Selección
    selection               TEXT NOT NULL,
    selection_label         TEXT NOT NULL,

    -- Cuotas
    best_odds               NUMERIC(6,3) NOT NULL,
    best_bookmaker          TEXT NOT NULL,
    implied_prob            NUMERIC(6,4),
    model_prob              NUMERIC(6,4),
    value                   NUMERIC(6,4),
    overround               NUMERIC(6,4),

    -- Stake
    recommended_stake_pct   NUMERIC(6,3),
    stake_amount            NUMERIC(10,2),

    -- Resultado
    status                  TEXT DEFAULT 'pending'
                            CHECK (status IN ('pending','won','lost','void','skipped')),
    result_home_goals       INTEGER,
    result_away_goals       INTEGER,
    profit_loss             NUMERIC(10,2),
    resolved_at             TIMESTAMPTZ,

    -- Metadata
    bookmaker_count         INTEGER,
    notes                   TEXT,

    -- Evitar duplicados
    UNIQUE(event_id, selection, detected_at::DATE)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_bets_status   ON bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_sport    ON bets(sport);
CREATE INDEX IF NOT EXISTS idx_bets_detected ON bets(detected_at);
CREATE INDEX IF NOT EXISTS idx_bets_event    ON bets(event_id);

-- Row Level Security (RLS) — necesario en Supabase
ALTER TABLE bets  ENABLE ROW LEVEL SECURITY;
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;

-- Política: el service_role key puede hacer todo (para el scanner)
CREATE POLICY "service_role_all_bets"  ON bets  FOR ALL USING (true);
CREATE POLICY "service_role_all_scans" ON scans FOR ALL USING (true);

-- Vista de estadísticas (útil para el dashboard)
CREATE OR REPLACE VIEW bet_stats AS
SELECT
    COUNT(*)                                            AS total_bets,
    COUNT(*) FILTER (WHERE status = 'pending')          AS pending,
    COUNT(*) FILTER (WHERE status = 'won')              AS won,
    COUNT(*) FILTER (WHERE status = 'lost')             AS lost,
    COUNT(*) FILTER (WHERE status IN ('won','lost'))    AS resolved,
    COALESCE(SUM(stake_amount) FILTER (WHERE status IN ('won','lost')), 0) AS total_staked,
    COALESCE(SUM(profit_loss)  FILTER (WHERE status IN ('won','lost')), 0) AS total_pl,
    CASE
        WHEN SUM(stake_amount) FILTER (WHERE status IN ('won','lost')) > 0
        THEN ROUND(
            SUM(profit_loss) FILTER (WHERE status IN ('won','lost')) /
            SUM(stake_amount) FILTER (WHERE status IN ('won','lost')) * 100, 2)
        ELSE 0
    END AS roi,
    CASE
        WHEN COUNT(*) FILTER (WHERE status IN ('won','lost')) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE status = 'won')::NUMERIC /
            COUNT(*) FILTER (WHERE status IN ('won','lost')) * 100, 2)
        ELSE 0
    END AS win_rate,
    ROUND(AVG(value) * 100, 2)  AS avg_value,
    ROUND(AVG(best_odds), 2)    AS avg_odds
FROM bets;
