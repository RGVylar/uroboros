-- premium_usage
-- uroboros · ¿se usan de verdad las funciones Premium? (SOLO LECTURA)
--
-- Uso, desde el host de Proxmox:
--   pct exec 200 -- sudo -u postgres psql -d uroboros -f /opt/uroboros/backend/scripts/premium_usage.sql
--
-- "Activo" = al menos una entrada en el diario en los últimos 30 días.
-- La cohorte grandfathered tiene todo abierto: es el experimento natural de
-- qué haría alguien con Premium. La cohorte free nos dice quién choca con muros.

\pset border 2
\pset linestyle unicode

\echo ''
\echo '══════════════════════ COHORTES ══════════════════════'
SELECT
    grandfathered,
    subscription_status,
    COUNT(*) AS usuarios,
    COUNT(*) FILTER (WHERE id IN (
        SELECT user_id FROM diary_entries WHERE consumed_at >= NOW() - INTERVAL '30 days'
    )) AS activos_30d
FROM users
GROUP BY grandfathered, subscription_status
ORDER BY grandfathered DESC, subscription_status;

\echo ''
\echo '══════════ USO DE FUNCIONES PREMIUM (usuarios distintos) ══════════'
WITH activos AS (
    SELECT DISTINCT user_id FROM diary_entries
    WHERE consumed_at >= NOW() - INTERVAL '30 days'
),
uso AS (
    SELECT 'historial >90 días (no medible: lectura)' AS funcion, NULL::bigint AS alguna_vez, NULL::bigint AS ult_30d
    UNION ALL
    SELECT 'sesiones de ejercicio',
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT user_id) FILTER (WHERE session_date >= CURRENT_DATE - 30)
    FROM exercise_sessions
    UNION ALL
    SELECT 'medidas corporales',
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT user_id) FILTER (WHERE logged_at >= NOW() - INTERVAL '30 days')
    FROM body_measurement_logs
    UNION ALL
    SELECT 'cheat days',
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT user_id) FILTER (WHERE used_date >= CURRENT_DATE - 30)
    FROM cheat_day_logs
    UNION ALL
    SELECT 'despensa (personal)',
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT user_id) FILTER (WHERE updated_at >= NOW() - INTERVAL '30 days')
    FROM inventory_items
    UNION ALL
    SELECT 'despensa (compartida)',
        COUNT(DISTINCT added_by_user_id),
        COUNT(DISTINCT added_by_user_id) FILTER (WHERE updated_at >= NOW() - INTERVAL '30 days')
    FROM shared_inventory_items
    UNION ALL
    SELECT 'lista compra (personal)',
        COUNT(DISTINCT user_id),
        COUNT(DISTINCT user_id) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')
    FROM shopping_list_items
    UNION ALL
    SELECT 'lista compra (compartida)',
        COUNT(DISTINCT added_by_user_id),
        COUNT(DISTINCT added_by_user_id) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days')
    FROM shared_shopping_list_items
    UNION ALL
    SELECT 'más de 5 recetas',
        COUNT(*), NULL
    FROM (SELECT owner_id FROM recipes GROUP BY owner_id HAVING COUNT(*) > 5) r
    UNION ALL
    SELECT 'más de 15 productos propios',
        COUNT(*), NULL
    FROM (SELECT edited_by FROM products WHERE edited_by IS NOT NULL
          GROUP BY edited_by HAVING COUNT(*) > 15) p
    UNION ALL
    SELECT 'ajuste de macros (proporcional/rendimiento)',
        COUNT(*), NULL
    FROM user_goals WHERE macro_adjust_mode <> 'off'
)
SELECT
    funcion,
    alguna_vez,
    ult_30d,
    (SELECT COUNT(*) FROM activos) AS activos_30d_total
FROM uso;

\echo ''
\echo '══════════ FUNCIONES GRATIS (para comparar) ══════════'
-- (El diario no guarda quién registró la entrada: el uso real de "registrar
-- para la pareja" no es medible; solo el permiso concedido.)
SELECT 'permiso de registrar comida concedido' AS funcion,
       COUNT(*) AS cuenta
FROM friendships
WHERE status::text = 'accepted' AND (can_add_food OR can_add_food_requester)
UNION ALL
SELECT 'despensa compartida activa (ambos lados)', COUNT(*) FROM friendships
WHERE status::text = 'accepted' AND shared_inventory_requester AND shared_inventory_receiver
UNION ALL
SELECT 'peso', COUNT(DISTINCT user_id) FROM weight_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
UNION ALL
SELECT 'duelo (opt-in en alguna amistad)', COUNT(*) FROM friendships
WHERE status::text = 'accepted' AND (duel_opt_in_requester OR duel_opt_in_receiver)
UNION ALL
SELECT 'parejas aceptadas', COUNT(*) FROM friendships
WHERE status::text = 'accepted' AND kind::text = 'partner';

\echo ''
\echo '══════════ USUARIOS FREE QUE YA CHOCAN CON UN MURO ══════════'
SELECT
    u.id, u.name, u.created_at::date AS alta,
    (SELECT COUNT(*) FROM recipes r WHERE r.owner_id = u.id)        AS recetas,
    (SELECT COUNT(*) FROM products p WHERE p.edited_by = u.id)      AS productos_propios,
    (SELECT MIN(consumed_at)::date FROM diary_entries d WHERE d.user_id = u.id) AS primera_entrada
FROM users u
WHERE NOT u.grandfathered
  AND u.subscription_status = 'free'
  AND (
      (SELECT COUNT(*) FROM recipes r WHERE r.owner_id = u.id) >= 5
   OR (SELECT COUNT(*) FROM products p WHERE p.edited_by = u.id) >= 15
   OR (SELECT MIN(consumed_at) FROM diary_entries d WHERE d.user_id = u.id) < NOW() - INTERVAL '80 days'
  )
ORDER BY u.created_at;
