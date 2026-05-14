-- uroboros · dashboard stats
-- Usage: psql $DATABASE_URL -f stats.sql
-- or:    pct exec 200 -- bash -c "psql \$DATABASE_URL -f /opt/uroboros/backend/scripts/stats.sql"

\pset border 2
\pset linestyle unicode

-- ── 1. Resumen global ────────────────────────────────────────────────────────
\echo ''
\echo '══════════════════════ RESUMEN GLOBAL ══════════════════════'

SELECT
    (SELECT COUNT(*) FROM users)                                    AS usuarios_total,
    (SELECT COUNT(*) FROM users
        WHERE created_at >= NOW() - INTERVAL '7 days')             AS nuevos_7d,
    (SELECT COUNT(*) FROM users
        WHERE created_at >= NOW() - INTERVAL '30 days')            AS nuevos_30d,
    (SELECT COUNT(DISTINCT user_id) FROM diary_entries
        WHERE consumed_at >= NOW() - INTERVAL '7 days')            AS activos_7d,
    (SELECT COUNT(DISTINCT user_id) FROM diary_entries
        WHERE consumed_at >= NOW() - INTERVAL '30 days')           AS activos_30d,
    (SELECT COUNT(*) FROM push_subscriptions)                      AS push_suscritos;

-- ── 2. Usuarios más activos (por entradas en el diario) ──────────────────────
\echo ''
\echo '══════════════════ TOP 10 USUARIOS MÁS ACTIVOS ══════════════════'

SELECT
    u.id,
    u.name,
    u.email,
    COUNT(d.id)                                      AS entradas_totales,
    COUNT(CASE WHEN d.consumed_at >= NOW() - INTERVAL '7 days'  THEN 1 END) AS entradas_7d,
    COUNT(CASE WHEN d.consumed_at >= NOW() - INTERVAL '30 days' THEN 1 END) AS entradas_30d,
    ROUND(AVG(d.calories)::numeric, 0)               AS kcal_media_entrada,
    MIN(d.consumed_at)::date                         AS primera_entrada,
    MAX(d.consumed_at)::date                         AS ultima_entrada,
    MAX(d.consumed_at)::date - MIN(d.consumed_at)::date AS dias_de_vida
FROM users u
JOIN diary_entries d ON d.user_id = u.id
GROUP BY u.id, u.name, u.email
ORDER BY entradas_totales DESC
LIMIT 10;

-- ── 3. Registro de nuevos usuarios por semana (últimas 8 semanas) ─────────────
\echo ''
\echo '══════════════════ CRECIMIENTO SEMANAL (8 semanas) ══════════════'

SELECT
    DATE_TRUNC('week', created_at)::date  AS semana,
    COUNT(*)                              AS nuevos_usuarios,
    SUM(COUNT(*)) OVER (ORDER BY DATE_TRUNC('week', created_at)) AS acumulado
FROM users
WHERE created_at >= NOW() - INTERVAL '8 weeks'
GROUP BY 1
ORDER BY 1;

-- ── 4. Actividad diaria (últimos 14 días) ────────────────────────────────────
\echo ''
\echo '══════════════════ ACTIVIDAD DIARIA (14 días) ════════════════════'

SELECT
    consumed_at::date                     AS dia,
    COUNT(DISTINCT user_id)               AS usuarios_activos,
    COUNT(*)                              AS entradas,
    ROUND(SUM(calories)::numeric, 0)      AS kcal_total,
    ROUND(AVG(calories)::numeric, 0)      AS kcal_media_entrada
FROM diary_entries
WHERE consumed_at >= NOW() - INTERVAL '14 days'
GROUP BY 1
ORDER BY 1 DESC;

-- ── 5. Productos más registrados ─────────────────────────────────────────────
\echo ''
\echo '══════════════════ TOP 15 PRODUCTOS MÁS REGISTRADOS ═════════════'

SELECT
    p.name                                AS producto,
    p.brand,
    COUNT(d.id)                           AS veces_registrado,
    COUNT(DISTINCT d.user_id)             AS usuarios_distintos,
    ROUND(AVG(d.grams)::numeric, 0)       AS gramos_media
FROM diary_entries d
JOIN products p ON p.id = d.product_id
GROUP BY p.id, p.name, p.brand
ORDER BY veces_registrado DESC
LIMIT 15;

-- ── 6. Comidas más populares por franja horaria ──────────────────────────────
\echo ''
\echo '══════════════════ DISTRIBUCIÓN POR TIPO DE COMIDA ══════════════'

SELECT
    meal_type,
    COUNT(*)                               AS entradas,
    COUNT(DISTINCT user_id)                AS usuarios,
    ROUND(AVG(calories)::numeric, 0)       AS kcal_media
FROM diary_entries
GROUP BY meal_type
ORDER BY entradas DESC;

-- ── 7. Usuarios con racha activa (días consecutivos con entradas) ─────────────
\echo ''
\echo '══════════════════ TOP 10 RACHAS ACTUALES ════════════════════════'

WITH daily AS (
    SELECT user_id, consumed_at::date AS dia
    FROM diary_entries
    GROUP BY user_id, consumed_at::date
),
consecutive AS (
    SELECT
        user_id,
        dia,
        dia - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY dia)::int AS grp
    FROM daily
),
streaks AS (
    SELECT
        user_id,
        MIN(dia) AS inicio,
        MAX(dia) AS fin,
        COUNT(*) AS dias
    FROM consecutive
    GROUP BY user_id, grp
)
SELECT
    u.name,
    u.email,
    s.dias       AS racha_dias,
    s.inicio,
    s.fin
FROM streaks s
JOIN users u ON u.id = s.user_id
WHERE s.fin = CURRENT_DATE OR s.fin = CURRENT_DATE - 1  -- activa hoy o ayer
ORDER BY s.dias DESC
LIMIT 10;

-- ── 8. Retención: usuarios que volvieron después de su primera semana ─────────
\echo ''
\echo '══════════════════ RETENCIÓN (volvieron tras la 1ª semana) ══════'

WITH first_entry AS (
    SELECT user_id, MIN(consumed_at)::date AS primera
    FROM diary_entries
    GROUP BY user_id
),
returning AS (
    SELECT f.user_id
    FROM first_entry f
    JOIN diary_entries d ON d.user_id = f.user_id
    WHERE d.consumed_at::date > f.primera + 7
    GROUP BY f.user_id
)
SELECT
    COUNT(DISTINCT f.user_id)                                       AS usuarios_con_entradas,
    COUNT(DISTINCT r.user_id)                                       AS volvieron_semana_2,
    ROUND(
        100.0 * COUNT(DISTINCT r.user_id) / NULLIF(COUNT(DISTINCT f.user_id), 0),
        1
    )                                                               AS retencion_pct
FROM first_entry f
LEFT JOIN returning r ON r.user_id = f.user_id;

-- ── 9. Push notifications ────────────────────────────────────────────────────
\echo ''
\echo '══════════════════ PUSH NOTIFICATIONS ═══════════════════════════'

SELECT
    (SELECT COUNT(*) FROM push_subscriptions)                       AS subscripciones_activas,
    (SELECT COUNT(DISTINCT user_id) FROM push_subscriptions)        AS usuarios_suscritos,
    (SELECT COUNT(*) FROM notification_log
        WHERE sent_at >= NOW() - INTERVAL '24 hours')               AS notifs_ultimas_24h,
    (SELECT COUNT(*) FROM notification_log
        WHERE sent_at >= NOW() - INTERVAL '7 days')                 AS notifs_7d;

\echo ''
\echo '═══════════════════════════════════════════════════════════════'
\echo 'Fin del informe.'
\echo ''
