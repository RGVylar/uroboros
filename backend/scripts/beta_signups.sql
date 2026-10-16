-- beta_signups
-- uroboros · quién se ha apuntado en /beta y falta por meter en Play Console
--
-- Uso, desde el host de Proxmox:
--   pct exec 200 -- sudo -u postgres psql -d uroboros -f /opt/uroboros/backend/scripts/beta_signups.sql
--
-- La última línea son los emails pendientes separados por comas: se pegan tal
-- cual en Play Console → Prueba cerrada → Testers → lista "Testers" → Detalles.
--
-- Una vez añadidos, márcalos para que no vuelvan a salir:
--   pct exec 200 -- sudo -u postgres psql -d uroboros -c "UPDATE beta_signups SET added = true WHERE added = false;"
--
-- Al acabar la beta, bórralos (la página promete hacerlo):
--   pct exec 200 -- sudo -u postgres psql -d uroboros -c "DELETE FROM beta_signups;"

\pset border 2
\pset linestyle unicode

\echo ''
\echo '══════════════════════ PENDIENTES ══════════════════════'
SELECT id, email, name, lang, created_at::date AS dia
FROM beta_signups
WHERE added = false
ORDER BY created_at;

\echo ''
\echo '══════════════════════ PARA PEGAR EN PLAY CONSOLE ══════════════════════'
\pset format unaligned
\pset tuples_only on
SELECT COALESCE(string_agg(email, ', ' ORDER BY created_at), '(nadie pendiente)')
FROM beta_signups
WHERE added = false;
