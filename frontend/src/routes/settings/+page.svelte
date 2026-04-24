<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import { pendingFriends } from '$lib/stores/friends.svelte';
	import type { Goals } from '$lib/types';
	if (!auth.isLoggedIn) goto('/login');

	let goals: Goals | null = $state(null);
	let savingCreatine = $state(false);
	let savingCheatDays = $state(false);
	let savingInventory = $state(false);

	async function loadGoals() {
		goals = await api.get<Goals>('/goals').catch(() => null);
	}

	loadGoals();

	async function toggleCreatine() {
		if (!goals) return;
		savingCreatine = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, track_creatine: !goals.track_creatine });
		} catch {
			// ignore
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
			// ignore
		} finally {
			savingCheatDays = false;
		}
	}

	async function toggleInventory() {
		if (!goals) return;
		savingInventory = true;
		try {
			goals = await api.put<Goals>('/goals', { ...goals, inventory_enabled: !goals.inventory_enabled });
		} catch {
			// ignore
		} finally {
			savingInventory = false;
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
		<!-- Creatina -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">💊</div>
			<div class="row-content">
				<div class="row-label">Trackear creatina</div>
				<div class="row-detail">{goals?.track_creatine ? 'Activo' : 'Inactivo'}</div>
			</div>
			{#if goals}
				<button
					onclick={toggleCreatine}
					disabled={savingCreatine}
					class="toggle-btn"
					style="background:{goals.track_creatine ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals.track_creatine ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
				>
					<span class="toggle-knob" style="left:{goals.track_creatine ? '18px' : '2px'};"></span>
				</button>
			{/if}
		</div>
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
		<!-- Inventario toggle + nav -->
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">🏠</div>
			<div class="row-content">
				<div class="row-label">Inventario doméstico</div>
				<div class="row-detail">{goals?.inventory_enabled ? 'Activo' : 'Inactivo'}</div>
			</div>
			{#if goals}
				<button
					onclick={toggleInventory}
					disabled={savingInventory}
					class="toggle-btn"
					style="background:{goals.inventory_enabled ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border-color:{goals.inventory_enabled ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'};"
				>
					<span class="toggle-knob" style="left:{goals.inventory_enabled ? '18px' : '2px'};"></span>
				</button>
			{/if}
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

<!-- ── Group: Cuenta ── -->
<div style="margin-bottom:1.125rem;">
	<div class="group-label">Cuenta</div>
	<div class="settings-group">
		<div class="settings-row" style="cursor:default;">
			<div class="icon-box">👤</div>
			<div class="row-content">
				<div class="row-label">{auth.user?.name ?? 'Usuario'}</div>
				<div class="row-detail">{auth.user?.email ?? ''}</div>
			</div>
		</div>
		<div class="row-divider"></div>
		<button class="settings-row" onclick={logout} style="cursor:pointer;">
			<div class="icon-box" style="background:oklch(55% 0.23 25 / 0.15);">→</div>
			<div class="row-content">
				<div class="row-label" style="color:oklch(75% 0.2 25);">Cerrar sesión</div>
			</div>
		</button>
	</div>
</div>

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
</style>
