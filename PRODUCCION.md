# 🚀 Plan de lanzamiento — uroboros

> Objetivo: subir uroboros a Google Play Store como app freemium para parejas.
> URL actual: https://comida.mugrelore.com

---

## 📊 Estado actual

- ✅ Backend FastAPI + PostgreSQL funcionando en casa (Proxmox, contenedor 200)
- ✅ Frontend SvelteKit + Capacitor
- ✅ Caddy con HTTPS
- ✅ Diario, recetas, inventario compartido, pareja, ejercicios, suplementos
- ✅ Sesión persistente (localStorage)
- ✅ Deploy via `git pull + alembic + systemctl`

---

## 🔴 FASE 1 — Crítico antes de cualquier lanzamiento

### 1.1 Recuperar contraseña (olvidé mi contraseña)
- Endpoint backend: `POST /auth/forgot-password` → genera token temporal
- Endpoint backend: `POST /auth/reset-password` → valida token y cambia contraseña
- Pantalla frontend en /login → "¿Olvidaste tu contraseña?"
- Servicio de email: **Resend** (gratis hasta 3000 emails/mes) o Gmail SMTP
- Sin esto: usuario que pierde contraseña pierde todos sus datos → reseña 1★

### 1.2 Ampliar duración del token JWT
- Actualmente: 7 días → el usuario tiene que loguearse cada semana
- Cambiar a: 90 días en `jwt_expire_minutes` (`config.py`)
- Archivo: `backend/app/config.py`

### 1.3 Política de privacidad
- Google Play la exige obligatoriamente para poder publicar
- Crear página `/privacy` en el frontend con texto legal
- Incluir: qué datos se recogen, cómo se usan, datos de contacto
- Alternativamente: página externa (Notion, GitHub Pages, etc.)

---

## 🟡 FASE 2 — Play Store

### 2.1 Cuenta de desarrollador
- Crear cuenta en [Google Play Console](https://play.google.com/console)
- Pago único: **$25**
- Usar cuenta de Google personal o crear una específica para la app

### 2.2 Icono y assets
- Icono de app: **512×512px** PNG (sin fondo transparente)
- Feature graphic: **1024×500px** (banner de la ficha)
- Capturas de pantalla: mínimo 2, idealmente 4-6
  - Pantalla de inicio / diario
  - Añadir comida
  - Inventario compartido con pareja
  - Recetas
- Splash screen para Capacitor

### 2.3 Build firmado
- Generar keystore: `keytool -genkey -v -keystore uroboros.jks ...`
- **⚠️ Guardar el keystore en lugar seguro — si se pierde, no puedes actualizar la app jamás**
- Build release: `cd frontend && npx cap build android --release`
- Firmar el AAB con el keystore
- Subir el `.aab` a Play Console

### 2.4 Ficha de la app (Play Store listing)
- Nombre: **uroboros** (o "Uroboros — Nutrición en pareja")
- Descripción corta (80 chars): *"Registra lo que coméis. Juntos."*
- Descripción larga: explicar diario, recetas, inventario compartido, pareja
- Categoría: Salud y bienestar
- Clasificación de contenido: completar cuestionario (sencillo)
- URL de política de privacidad: obligatoria

### 2.5 Prueba interna (antes de publicar)
- Subir como **Internal Testing** → hasta 100 testers
- Invitar por email: tu novia, amigos de confianza
- Probar en dispositivos reales
- Mínimo 1-2 semanas de beta antes de producción

---

## 🟢 FASE 3 — Monetización freemium

### 3.1 Modelo
| Plan | Precio | Features |
|------|--------|----------|
| **Gratis** | €0 | Diario básico, búsqueda productos, peso |
| **Premium** | €2.99/mes o €19.99/año | Recetas, pareja, inventario compartido, historial completo, ejercicios, suplementos, exportar CSV |

### 3.2 Implementación técnica
- Integrar **Google Play Billing** en Capacitor
- Backend: campo `is_premium` en modelo `User`
- Middleware que bloquea endpoints premium si no tiene suscripción activa
- Webhook de Google Play para sincronizar estado de suscripción

### 3.3 Gestión de suscripciones
- Crear producto de suscripción en Play Console
- Período de prueba gratuita: 14 días (recomendado para conversión)
- Precio familiar: descuento si ambos miembros de la pareja se suscriben

---

## 🔵 FASE 4 — Infraestructura (si crece)

### 4.1 Migrar a VPS (cuando superar ~30 usuarios de pago)
- **Hetzner CAX11**: €4.51/mes, 2 vCPU ARM, 4GB RAM, Alemania (GDPR)
- Migración de DB: `pg_dump` en casa → `psql` en VPS (< 1 hora)
- Mismo `docker-compose` / mismo `deploy.sh`
- Sin cambios en el código

### 4.2 Backups automáticos
- Actualmente: ninguno ⚠️
- Añadir cronjob: `pg_dump` diario → guardar en otro disco o cloud storage
- Script simple en el contenedor Proxmox

---

## 📋 Checklist de lanzamiento

### Antes de Internal Testing
- [ ] Recuperar contraseña implementado y probado
- [ ] Token JWT a 90 días
- [ ] Política de privacidad publicada con URL accesible
- [ ] Icono 512×512 listo
- [ ] Splash screen configurado en Capacitor
- [ ] Build firmado generado sin errores
- [ ] App funciona en dispositivo físico Android

### Antes de Producción pública
- [ ] Beta interna mínimo 2 semanas sin bugs críticos
- [ ] Capturas de pantalla preparadas (4-6)
- [ ] Descripción de la app escrita
- [ ] Cuestionario de clasificación de contenido completado
- [ ] Precio configurado en Play Console
- [ ] Monetización implementada (o decidir lanzar gratis primero)

### Antes de cobrar
- [ ] Google Play Billing integrado y probado en sandbox
- [ ] Flujo premium/gratis funcionando correctamente
- [ ] Período de prueba gratuita configurado

---

## 💡 Decisiones pendientes

- [ ] ¿Nombre definitivo de la app en Play Store?
- [ ] ¿Lanzar gratis primero para conseguir usuarios y luego freemium?
- [ ] ¿Verificación de email al registrarse? (recomendado para producción)
- [ ] ¿Notificaciones push? (recordatorios de registro diario)

---

## 🔑 Información importante

- **Servidor**: Proxmox contenedor 200, mini PC en casa
- **Deploy**: `pct exec 200 -- bash -c "cd /opt/uroboros && git pull && ..."`
- **Dominio**: comida.mugrelore.com
- **API nativa**: `VITE_API_URL=https://comida.mugrelore.com/api`
- **Keystore**: guardar en lugar seguro fuera del repo (nunca en git)
- **Play Console**: $25 pago único

---

*Última actualización: Mayo 2026*
