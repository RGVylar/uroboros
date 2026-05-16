<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import { pushStore } from '$lib/stores/push.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import type { Goals } from '$lib/types';
	if (!auth.isLoggedIn) goto('/login');

	// ── Notification prefs ─────────────────────────────────────────────────────
	interface NotifPrefs {
		enabled: boolean;
		quiet_start: number; quiet_end: number;
		breakfast_on: boolean; breakfast_time: string;
		lunch_on: boolean; lunch_time: string;
		dinner_on: boolean; dinner_time: string;
		streak_on: boolean; streak_time: string; streak_min_days: number;
		summary_on: boolean; summary_time: string;
		water_on: boolean; water_time: string;
		timezone: string;
	}

	// Common IANA timezones for the selector
	const TIMEZONES = [
		{ value: 'Europe/Madrid',      label: 'Madrid / España' },
		{ value: 'Europe/London',      label: 'Londres' },
		{ value: 'Europe/Paris',       label: 'París / Europa Central' },
		{ value: 'America/Mexico_City',label: 'Ciudad de México' },
		{ value: 'America/Bogota',     label: 'Bogotá / Lima / Quito' },
		{ value: 'America/Caracas',    label: 'Caracas' },
		{ value: 'America/Santiago',   label: 'Santiago de Chile' },
		{ value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires' },
		{ value: 'America/Sao_Paulo',  label: 'São Paulo / Brasil' },
		{ value: 'America/New_York',   label: 'Nueva York' },
		{ value: 'America/Los_Angeles',label: 'Los Ángeles' },
		{ value: 'UTC',                label: 'UTC' },
	];
	let prefs: NotifPrefs | null = $state(null);
	let savingPrefs = $state(false);
	let testSent = $state(false);

	async function loadPrefs() {
		prefs = await api.get<NotifPrefs>('/push/prefs').catch(() => null);
	}
	loadPrefs();

	async function savePrefs(patch: Partial<NotifPrefs>) {
		if (!prefs) return;
		prefs = { ...prefs, ...patch };
		savingPrefs = true;
		try {
			prefs = await api.put<NotifPrefs>('/push/prefs', patch);
			// Re-schedule local notifications on native whenever prefs change
			await pushStore.reschedule();
		} catch { toast.error('No se pudo guardar la preferencia'); } finally {
			savingPrefs = false;
		}
	}

	async function enableNotifs() {
		const ok = await pushStore.subscribe();
		if (ok) await savePrefs({ enabled: true });
	}

	async function disableNotifs() {
		await savePrefs({ enabled: false });
		await pushStore.unsubscribe();
	}

	async function sendTestNotif() {
		await pushStore.sendTest();
		testSent = true;
		setTimeout(() => testSent = false, 3000);
	}

	let goals: Goals | null = $state(null);
	let savingCreatine = $state(false);
	let savingCheatDays = $state(false);
	let savingInventory = $state(false);
	let showDeleteModal = $state(false);
	let deletingAccount = $state(false);
	let deleteConfirmText = $state('');
	let allergyCount = $state(0);

	async function deleteAccount() {
		if (deleteConfirmText !== 'ELIMINAR') return;
		deletingAccount = true;
		try {
			await api.del('/users/me');
			auth.logout();
			goto('/login');
		} catch {
			deletingAccount = false;
			showDeleteModal = false;
			toast.error('No se pudo eliminar la cuenta. Inténtalo de nuevo.');
		}
	}

	async function loadGoals() {
		goals = await api.get<Goals>('/goals').catch(() => null);
	}

	async function loadAllergyCount() {
		const rows = await api.get<Array<{id: number, ingredient: string}>>('/allergies').catch(() => []);
		allergyCount = rows.length;
	}

	loadGoals();
	loadAllergyCount();

	async function toggleCreatine() {
		if (!goals) return;
		savingCreatine = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, track_creatine: !goals.track_creatine });
		} catch {
			toast.error('No se pudo actualizar la configuración');
		} finally {
			savingCreatine = false;
		}
	}

	async function toggleCheatDays() {
		if (!goals) return;
		savingCheatDays = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, cheat_days_enabled: !goals.cheat_days_enabled });
		} catch {
			toast.error('No se pudo actualizar la configuración');
		} finally {
			savingCheatDays = false;
		}
	}

	async function toggleInventory() {
		savingInventory = true;
		try {
			const base = goals ?? { kcal: 2000, protein: 150, carbs: 250, fat: 65, water_ml: 2000, track_creatine: false, cheat_days_enabled: false, inventory_enabled: false, macro_adjust_mode: 'off' as const };
			goals = await api.put<Goals>('/goals', { ...base, inventory_enabled: !base.inventory_enabled });
		} catch {
			toast.error('No se pudo actualizar la configuración');
		} finally {
			savingInventory = false;
		}
	}

	let savingMacroMode = $state(false);
	async function setMacroAdjustMode(mode: 'off' | 'proportional' | 'performance') {
		if (!goals || goals.macro_adjust_mode === mode) return;
		savingMacroMode = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, macro_adjust_mode: mode });
		} catch {
			toast.error('No se pudo actualizar la configuración');
		} finally {
			savingMacroMode = false;
		}
	}

	function logout() {
		auth.logout();
		goto('/login');
	}
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Ajustes</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">Configuración y cuenta</div>
	</div>
</div>

<!-- ── Group: Objetivos ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Objetivos</div>
	<div class="settings-group">
		<!-- Kcal y macros -->
		<button class="settings-row" onclick={() => goto('/goals')}>
			<div class="icon-box">🎯</div>
			<div class="row-content">
				<div class="row-label">Kcal y macros</div>
				{#if goals}
					<div class="row-detail">{Math.round(goals.kcal)} kcal · P{Math.round(goals.protein ?? 0)} / C{Math.round(goals.carbs ?? 0)} / G{Math.round(goals.fat ?? 0)}</div>
				{/if}
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Suplementos -->
		<button class="settings-row" onclick={() => goto('/supplements')}>
			<div class="icon-box">💊</div>
			<div class="row-content">
				<div class="row-label">Suplementos</div>
				<div class="row-detail">Gestiona tu lista diaria</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Cheat day -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🍕</div>
			<div class="row-content">
				<div class="row-label">Cheat days</div>
				<div class="row-detail">{goals?.cheat_days_enabled ? 'Activo' : 'Inactivo'}</div>
			</div>
			{#if goals}
				<button
					onclick={toggleCheatDays}
					disabled={savingCheatDays}
					class="toggle-btn"
					style="background:{goals.cheat_days_enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals.cheat_days_enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
				>
					<span class="toggle-knob" style="left:{goals.cheat_days_enabled ? '18px' : '2px'};"></span>
				</button>
			{/if}
		</div>
		<div class="row-divider"></div>
		<!-- Macro adjust mode -->
		<div class="settings-row" style="cursor:default; flex-direction:column; align-items:flex-start; gap:0.625rem;">
			<div style="display:flex; align-items:center; gap:0.75rem; width:100%;">
				<div class="icon-box">⚡</div>
				<div class="row-content">
					<div class="row-label">Ajuste por ejercicio</div>
					<div class="row-detail">Cómo subir objetivos al quemar calorías</div>
				</div>
			</div>
			{#if goals}
				<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:0.375rem; width:100%; padding-left:2.75rem;">
					{#each [
						{ value: 'off',          label: 'Fijo',           note: 'Sin ajuste' },
						{ value: 'proportional', label: 'Proporcional',   note: 'Sube todo' },
						{ value: 'performance',  label: 'Rendimiento',    note: 'Solo carbs' },
					] as opt}
						<button
							onclick={() => setMacroAdjustMode(opt.value as 'off' | 'proportional' | 'performance')}
							disabled={savingMacroMode}
							style="
								padding:0.5rem 0.25rem;
								border-radius:0.625rem;
								border:1px solid {goals.macro_adjust_mode === opt.value ? 'oklch(80% 0.17 165 / 0.6)' : 'rgba(255,255,255,0.1)'};
								background:{goals.macro_adjust_mode === opt.value ? 'oklch(75% 0.18 165 / 0.15)' : 'rgba(255,255,255,0.04)'};
								color:{goals.macro_adjust_mode === opt.value ? 'oklch(85% 0.17 165)' : 'rgba(255,255,255,0.55)'};
								font-size:0.6875rem;
								font-weight:{goals.macro_adjust_mode === opt.value ? '700' : '400'};
								text-align:center;
								cursor:pointer;
								transition:all 0.15s;
								line-height:1.3;
							"
						>
							{opt.label}<br>
							<span style="font-size:0.5625rem; opacity:0.7;">{opt.note}</span>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</div>

<!-- ── Group: Pareja ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Pareja</div>
	<div class="settings-group">
		<button class="settings-row" onclick={() => goto('/friends')}>
			<div class="icon-box">💑</div>
			<div class="row-content">
				<div class="row-label" style="display:flex; align-items:center; gap:0.4rem;">
					Amigos y pareja
					{#if pendingFriends.count > 0}
						<span style="background:oklch(55% 0.23 25); color:#fff; border-radius:99px; padding:0.05rem 0.4rem; font-size:0.625rem; font-weight:800; line-height:1.5;">{pendingFriends.count}</span>
					{/if}
				</div>
				<div class="row-detail">Gestiona amigos y permisos</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Group: Salud ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Salud</div>
	<div class="settings-group">
		<!-- Alergias -->
		<button class="settings-row" onclick={() => goto('/allergies')}>
			<div class="icon-box" style="background:oklch(35% 0.15 40 / 0.3); border:1px solid oklch(60% 0.2 40 / 0.3);">⚠️</div>
			<div class="row-content">
				<div class="row-label">Alergias e intolerancias</div>
				<div class="row-detail">{allergyCount > 0 ? `${allergyCount} registrada${allergyCount > 1 ? 's' : ''}` : 'Alertas al añadir productos'}</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>
<!-- ── Group: Datos ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Datos</div>
	<div class="settings-group">
		<button class="settings-row" onclick={() => goto('/weight')}>
			<div class="icon-box">⚖️</div>
			<div class="row-content">
				<div class="row-label">Registro de peso</div>
				<div class="row-detail">Seguimiento de evolución</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/measurements')}>
			<div class="icon-box">📏</div>
			<div class="row-content">
				<div class="row-label">Medidas corporales</div>
				<div class="row-detail">Contornos y gráfica por zona</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/exercises')}>
			<div class="icon-box">💪</div>
			<div class="row-content">
				<div class="row-label">Ejercicios</div>
				<div class="row-detail">Biblioteca y rutinas de entreno</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<!-- Inventario toggle + nav -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🏠</div>
			<div class="row-content">
				<div class="row-label">Inventario doméstico</div>
				<div class="row-detail">{goals?.inventory_enabled ? 'Activo' : 'Inactivo'}</div>
			</div>
			<button
				onclick={toggleInventory}
				disabled={savingInventory}
				class="toggle-btn"
				style="background:{goals?.inventory_enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals?.inventory_enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
			>
				<span class="toggle-knob" style="left:{goals?.inventory_enabled ? '18px' : '2px'};"></span>
			</button>
		</div>
		{#if goals?.inventory_enabled}
			<div class="row-divider"></div>
			<button class="settings-row" onclick={() => goto('/inventory')}>
				<div class="icon-box">📦</div>
				<div class="row-content">
					<div class="row-label">Ver inventario</div>
					<div class="row-detail">Stock, precios y alertas</div>
				</div>
				<span class="chevron">›</span>
			</button>
			<div class="row-divider"></div>
			<button class="settings-row" onclick={() => goto('/shopping-list')}>
				<div class="icon-box">🛒</div>
				<div class="row-content">
					<div class="row-label">Lista de la compra</div>
					<div class="row-detail">Generada desde recetas</div>
				</div>
				<span class="chevron">›</span>
			</button>
		{/if}
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => goto('/history')}>
			<div class="icon-box">📤</div>
			<div class="row-content">
				<div class="row-label">Exportar datos</div>
				<div class="row-detail">CSV · Historial completo</div>
			</div>
			<span class="chevron">›</span>
		</button>
	</div>
</div>

<!-- ── Group: Notificaciones ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Notificaciones</div>
	<div class="settings-group">
		{#if !pushStore.isSupported}
			<div class="settings-row" style="cursor:default; opacity:0.5;">
				<div class="icon-box">🔔</div>
				<div class="row-content">
					<div class="row-label">No disponible</div>
					<div class="row-sub">Tu navegador no soporta notificaciones push</div>
				</div>
			</div>
		{:else if pushStore.permission === 'denied'}
			<div class="settings-row" style="cursor:default;">
				<div class="icon-box">🔕</div>
				<div class="row-content">
					<div class="row-label">Bloqueadas por el navegador</div>
					<div class="row-sub">Actívalas en los ajustes del navegador</div>
				</div>
			</div>
		{:else}
			<!-- Master toggle -->
			<div class="settings-row" style="cursor:default;">
				<div class="icon-box">🔔</div>
				<div class="row-content">
					<div class="row-label">Activar notificaciones</div>
					<div class="row-sub">
						{prefs?.enabled ? 'Activadas · Solo cuando tiene sentido' : 'Desactivadas'}
					</div>
				</div>
				<button
					class="toggle-btn"
					class:toggle-on={prefs?.enabled}
					onclick={() => prefs?.enabled ? disableNotifs() : enableNotifs()}
					disabled={savingPrefs}
					aria-label="Toggle notificaciones"
				>
					<span class="toggle-thumb"></span>
				</button>
			</div>

			{#if prefs?.enabled}
				<!-- Meal reminders -->
				<div class="notif-subsection">
					<div class="notif-sub-label">Recordatorios de comida</div>
					{#each [
						{ key: 'breakfast', label: 'Desayuno', emoji: '🍳', on: prefs.breakfast_on, time: prefs.breakfast_time },
						{ key: 'lunch',     label: 'Almuerzo', emoji: '🥗', on: prefs.lunch_on,     time: prefs.lunch_time     },
						{ key: 'dinner',    label: 'Cena',     emoji: '🍽️', on: prefs.dinner_on,    time: prefs.dinner_time    },
					] as meal}
						<div class="notif-row">
							<span class="notif-emoji">{meal.emoji}</span>
							<span class="notif-meal-label">{meal.label}</span>
							<input
								type="time"
								class="time-input"
								value={meal.time}
								disabled={!meal.on}
								onchange={(e) => savePrefs({ [`${meal.key}_time`]: (e.target as HTMLInputElement).value } as Partial<NotifPrefs>)}
							/>
							<button
								class="toggle-btn toggle-sm"
								class:toggle-on={meal.on}
								onclick={() => savePrefs({ [`${meal.key}_on`]: !meal.on } as Partial<NotifPrefs>)}
								aria-label="Toggle {meal.label}"
							><span class="toggle-thumb"></span></button>
						</div>
					{/each}
				</div>

				<!-- Streak alert -->
				<div class="notif-subsection">
					<div class="notif-sub-label">Racha</div>
					<div class="notif-row">
						<span class="notif-emoji">🔥</span>
						<span class="notif-meal-label">Racha en peligro</span>
						<input type="time" class="time-input" value={prefs.streak_time} disabled={!prefs.streak_on}
							onchange={(e) => savePrefs({ streak_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.streak_on}
							onclick={() => savePrefs({ streak_on: !prefs.streak_on })}
							aria-label="Toggle racha"><span class="toggle-thumb"></span></button>
					</div>
					<div class="notif-row">
						<span class="notif-emoji">🏆</span>
						<span class="notif-meal-label">Hitos de racha</span>
						<span class="notif-hint">3, 7, 14, 30... días</span>
						<span class="notif-always">Siempre</span>
					</div>
				</div>

				<!-- Summary + water -->
				<div class="notif-subsection">
					<div class="notif-sub-label">Resumen y agua</div>
					<div class="notif-row">
						<span class="notif-emoji">📊</span>
						<span class="notif-meal-label">Resumen del día</span>
						<input type="time" class="time-input" value={prefs.summary_time} disabled={!prefs.summary_on}
							onchange={(e) => savePrefs({ summary_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.summary_on}
							onclick={() => savePrefs({ summary_on: !prefs.summary_on })}
							aria-label="Toggle resumen"><span class="toggle-thumb"></span></button>
					</div>
					<div class="notif-row">
						<span class="notif-emoji">💧</span>
						<span class="notif-meal-label">Recordatorio agua</span>
						<input type="time" class="time-input" value={prefs.water_time} disabled={!prefs.water_on}
							onchange={(e) => savePrefs({ water_time: (e.target as HTMLInputElement).value })} />
						<button class="toggle-btn toggle-sm" class:toggle-on={prefs.water_on}
							onclick={() => savePrefs({ water_on: !prefs.water_on })}
							aria-label="Toggle agua"><span class="toggle-thumb"></span></button>
					</div>
				</div>

				<!-- Quiet hours + Timezone -->
				<div class="notif-subsection">
					<div class="notif-sub-label">Horas de silencio</div>
					<div class="notif-row" style="gap:0.5rem;">
						<span class="notif-emoji">🌙</span>
						<span class="notif-meal-label">Sin molestar de</span>
						<input type="number" min="0" max="23" class="hour-input" value={prefs.quiet_start}
							onchange={(e) => savePrefs({ quiet_start: Number((e.target as HTMLInputElement).value) })} />
						<span style="color:var(--text-muted); font-size:0.8rem;">a</span>
						<input type="number" min="0" max="23" class="hour-input" value={prefs.quiet_end}
							onchange={(e) => savePrefs({ quiet_end: Number((e.target as HTMLInputElement).value) })} />
						<span style="color:var(--text-muted); font-size:0.75rem;">h</span>
					</div>
					<div class="notif-row" style="gap:0.5rem; margin-top:0.25rem;">
						<span class="notif-emoji">🌍</span>
						<span class="notif-meal-label">Zona horaria</span>
						<select
							class="tz-select"
							value={prefs.timezone}
							onchange={(e) => savePrefs({ timezone: (e.target as HTMLSelectElement).value })}
						>
							{#each TIMEZONES as tz}
								<option value={tz.value}>{tz.label}</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Test button -->
				<button class="settings-row" onclick={sendTestNotif} style="border-top:1px solid rgba(255,255,255,0.06);">
					<div class="icon-box">📨</div>
					<div class="row-content">
						<div class="row-label">{testSent ? '✅ Enviada' : 'Enviar notificación de prueba'}</div>
						<div class="row-sub">Comprueba que todo funciona</div>
					</div>
					<div class="row-arrow">›</div>
				</button>
			{/if}
		{/if}
	</div>
</div>

<!-- ── Group: Cuenta ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Cuenta</div>
	<div class="settings-group">
		<button class="settings-row" onclick={() => goto('/profile')}>
			<div class="icon-box">👤</div>
			<div class="row-content">
				<div class="row-label">{auth.user?.name ?? 'Usuario'}</div>
				<div class="row-detail">{auth.user?.email ?? ''}</div>
			</div>
			<span class="chevron">›</span>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={logout} style="cursor:pointer;">
			<div class="icon-box" style="background:oklch(55% 0.23 25 / 0.15);">→</div>
			<div class="row-content">
				<div class="row-label" style="color:oklch(75% 0.2 25);">Cerrar sesión</div>
			</div>
		</button>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={() => { showDeleteModal = true; deleteConfirmText = ''; }} style="cursor:pointer;">
			<div class="icon-box" style="background:oklch(40% 0.2 25 / 0.2);">🗑️</div>
			<div class="row-content">
				<div class="row-label" style="color:oklch(65% 0.2 25);">Eliminar cuenta</div>
				<div class="row-detail">Borra todos tus datos permanentemente</div>
			</div>
		</button>
	</div>
</div>

<!-- ── Modal eliminar cuenta ── -->
{#if showDeleteModal}
	<div style="position:fixed; inset:0; background:rgba(0,0,0,0.75); z-index:1000; display:flex; align-items:center; justify-content:center; padding:1.5rem;" onclick={() => showDeleteModal = false}>
		<div style="background:#0f1520; border:1px solid rgba(255,255,255,0.1); border-radius:20px; padding:1.5rem; width:100%; max-width:360px;" onclick={(e) => e.stopPropagation()}>
			<div style="font-size:2rem; text-align:center; margin-bottom:0.75rem;">⚠️</div>
			<h2 style="font-size:1.125rem; font-weight:700; color:#fff; margin:0 0 0.5rem; text-align:center;">Eliminar cuenta</h2>
			<p style="font-size:0.8125rem; color:rgba(255,255,255,0.6); margin:0 0 1.25rem; text-align:center; line-height:1.5;">
				Esta acción es <strong style="color:#fff;">irreversible</strong>. Se borrarán todos tus datos: diario, recetas, inventario, peso y medidas.
			</p>
			<p style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin:0 0 0.5rem;">Escribe <strong style="color:#fff;">ELIMINAR</strong> para confirmar:</p>
			<input
				bind:value={deleteConfirmText}
				placeholder="ELIMINAR"
				style="width:100%; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:0.75rem; color:#fff; font-family:inherit; font-size:0.875rem; box-sizing:border-box; margin-bottom:1rem; outline:none;"
			/>
			<div style="display:flex; gap:0.75rem;">
				<button onclick={() => showDeleteModal = false}
					style="flex:1; padding:0.75rem; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.06); color:rgba(255,255,255,0.7); font-family:inherit; font-size:0.875rem; cursor:pointer;">
					Cancelar
				</button>
				<button onclick={deleteAccount}
					disabled={deleteConfirmText !== 'ELIMINAR' || deletingAccount}
					style="flex:1; padding:0.75rem; border-radius:12px; border:none; background:{deleteConfirmText === 'ELIMINAR' ? 'oklch(50% 0.22 25)' : 'rgba(255,255,255,0.05)'}; color:{deleteConfirmText === 'ELIMINAR' ? '#fff' : 'rgba(255,255,255,0.3)'}; font-family:inherit; font-size:0.875rem; font-weight:700; cursor:{deleteConfirmText === 'ELIMINAR' ? 'pointer' : 'not-allowed'}; transition:background 0.2s;">
					{deletingAccount ? 'Eliminando...' : 'Eliminar'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Ko-fi -->
<div style="text-align:center; margin-top:1rem; padding-bottom:0.5rem;">
	<a href="https://ko-fi.com/Z8Z81OW7UV" target="_blank" rel="noopener noreferrer"
		style="display:inline-flex; align-items:center; gap:0.4rem; font-size:0.75rem; color:rgba(255,255,255,0.45); text-decoration:none; padding:0.35rem 0.875rem; border-radius:99px; border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.03);">
		☕ Invítame una
	</a>
</div>
<div style="text-align:center; margin-top:0.5rem; color:rgba(255,255,255,0.25); font-size:0.6875rem; padding-bottom:6rem;">v0.3.0</div>

<style>
	
	.group-label {
		font-size: 0.625rem;
		letter-spacing: 0.12em;
		color: rgba(255,255,255,0.45);
		text-transform: uppercase;
		font-weight: 700;
		padding: 0 0.375rem 0.5rem;
	}
	.settings-group {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 18px;
		overflow: hidden;
	}
	.settings-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.875rem;
		width: 100%;
		background: none;
		border: none;
		color: #fff;
		font-family: inherit;
		text-align: left;
	}
	.row-divider {
		height: 1px;
		background: rgba(255,255,255,0.05);
		margin: 0 0.875rem;
	}
	.icon-box {
		width: 32px;
		height: 32px;
		border-radius: 10px;
		background: rgba(255,255,255,0.05);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.row-content {
		flex: 1;
		min-width: 0;
	}
	.row-label {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #fff;
	}
	.row-detail {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
	}
	.chevron {
		color: rgba(255,255,255,0.3);
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.row-sub {
		font-size: 0.6875rem;
		color: rgba(255,255,255,0.45);
		margin-top: 0.125rem;
	}
	.row-arrow {
		color: rgba(255,255,255,0.3);
		font-size: 0.875rem;
		flex-shrink: 0;
	}
	.toggle-btn {
		position: relative;
		width: 40px;
		height: 24px;
		border-radius: 99px;
		border: 1px solid;
		cursor: pointer;
		flex-shrink: 0;
		padding: 0;
		transition: background 0.2s, border-color 0.2s;
	}
	.toggle-knob {
		position: absolute;
		top: 2px;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
		box-shadow: 0 2px 5px rgba(0,0,0,0.3);
		transition: left 0.2s;
		display: block;
	}
	/* Toggle-thumb variant (CSS-driven, no inline style needed) */
	.toggle-thumb {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
		box-shadow: 0 2px 5px rgba(0,0,0,0.3);
		transition: left 0.2s;
		display: block;
	}
	.toggle-on .toggle-thumb { left: 18px; }
	.toggle-btn:not(.toggle-on) { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.15); }
	.toggle-btn.toggle-on { background: var(--primary); border-color: var(--primary); }
	.toggle-sm { width: 34px; height: 20px; }
	.toggle-sm .toggle-thumb { width: 14px; height: 14px; top: 2px; }
	.toggle-sm.toggle-on .toggle-thumb { left: 16px; }

	/* Notification rows */
	.notif-subsection {
		border-top: 1px solid rgba(255,255,255,0.06);
		padding: 0.625rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.notif-sub-label {
		font-size: 0.65rem;
		font-weight: 700;
		color: oklch(55% 0.05 260);
		text-transform: uppercase;
		letter-spacing: 0.07em;
		margin-bottom: 0.1rem;
	}
	.notif-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.notif-emoji { font-size: 1rem; flex-shrink: 0; width: 1.25rem; text-align: center; }
	.notif-meal-label { flex: 1; font-size: 0.8rem; color: rgba(255,255,255,0.85); min-width: 0; }
	.notif-hint { font-size: 0.7rem; color: oklch(55% 0.05 260); }
	.notif-always {
		font-size: 0.68rem;
		font-weight: 700;
		color: oklch(65% 0.15 160);
		background: oklch(65% 0.15 160 / 0.1);
		border: 1px solid oklch(65% 0.15 160 / 0.2);
		border-radius: 99px;
		padding: 0.1rem 0.4rem;
	}
	.time-input {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.75rem;
		padding: 0.2rem 0.4rem;
		width: 5.5rem;
		flex-shrink: 0;
	}
	.time-input:disabled { opacity: 0.35; }
	.time-input::-webkit-calendar-picker-indicator { filter: invert(1); opacity: 0.5; }
	.hour-input {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.8rem;
		padding: 0.2rem 0.4rem;
		width: 3rem;
		text-align: center;
		flex-shrink: 0;
	}
	.tz-select {
		background: rgba(255,255,255,0.06);
		border: 1px solid rgba(255,255,255,0.12);
		border-radius: 8px;
		color: #fff;
		font-family: inherit;
		font-size: 0.75rem;
		padding: 0.2rem 0.4rem;
		flex: 1;
		min-width: 0;
		cursor: pointer;
	}
	.tz-select option { background: #1a1f2e; color: #fff; }
</style>
