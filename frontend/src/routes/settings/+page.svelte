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
	let showDeleteModal = $state(false);
	let deletingAccount = $state(false);
	let deleteConfirmText = $state('');
	let allergies: Array<{id: number, ingredient: string}> = $state([]);
	let newAllergyInput = $state('');
	let addingAllergy = $state(false);

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
		}
	}

	async function loadGoals() {
		goals = await api.get<Goals>('/goals').catch(() => null);
	}

	async function loadAllergies() {
		allergies = await api.get<Array<{id: number, ingredient: string}>>('/allergies').catch(() => []);
	}

	async function addAllergy() {
		if (!newAllergyInput.trim()) return;
		addingAllergy = true;
		try {
			const newAllergy = await api.post<{id: number, ingredient: string}>('/allergies', {
				ingredient: newAllergyInput.trim()
			});
			allergies.push(newAllergy);
			newAllergyInput = '';
		} catch {
			// ignore
		} finally {
			addingAllergy = false;
		}
	}

	async function removeAllergy(id: number) {
		try {
			await api.del(`/allergies/${id}`);
			allergies = allergies.filter(a => a.id !== id);
		} catch {
			// ignore
		}
	}

	loadGoals();
	loadAllergies();

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
		savingInventory = true;
		try {
			const base = goals ?? { kcal: 2000, protein: 150, carbs: 250, fat: 65, water_ml: 2000, track_creatine: false, cheat_days_enabled: false, inventory_enabled: false };
			goals = await api.put<Goals>('/goals', { ...base, inventory_enabled: !base.inventory_enabled });
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
		<div class="settings-row" style="flex-direction:column; align-items:stretch; gap:0.5rem; cursor:default;">
			<div style="display:flex; align-items:center; gap:0.75rem;">
				<div class="icon-box">⚠️</div>
				<div class="row-content">
					<div class="row-label">Alergias e intolerancias</div>
					<div class="row-detail">Alertas al añadir productos</div>
				</div>
			</div>
			<div style="display:flex; gap:0.5rem; margin-left:2.75rem; margin-top:0.25rem;">
				<input
					type="text"
					bind:value={newAllergyInput}
					placeholder="p.ej. leche, cacahuetes"
					onkeydown={(e) => {
						if (e.key === 'Enter') {
							e.preventDefault();
							addAllergy();
						}
					}}
					style="flex:1; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.12); border-radius:8px; padding:0.5rem; color:#fff; font-family:inherit; font-size:0.8125rem; outline:none;"
				/>
				<button
					onclick={addAllergy}
					disabled={addingAllergy || !newAllergyInput.trim()}
					style="padding:0.5rem 0.75rem; border-radius:8px; border:1px solid rgba(255,255,255,0.1); background:{newAllergyInput.trim() ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.05)'}; color:{newAllergyInput.trim() ? '#fff' : 'rgba(255,255,255,0.3)'}; font-family:inherit; font-size:0.8125rem; font-weight:600; cursor:{newAllergyInput.trim() ? 'pointer' : 'not-allowed'}; transition:background 0.2s; flex-shrink:0;"
				>
					+
				</button>
			</div>
			{#if allergies.length > 0}
				<div style="margin-left:2.75rem; margin-top:0.5rem; display:flex; flex-wrap:wrap; gap:0.5rem;">
					{#each allergies as allergy (allergy.id)}
						<div style="display:inline-flex; align-items:center; gap:0.4rem; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); border-radius:99px; padding:0.35rem 0.75rem;">
							<span style="font-size:0.75rem; color:#fff;">{allergy.ingredient}</span>
							<button
								onclick={() => removeAllergy(allergy.id)}
								style="background:none; border:none; color:rgba(255,255,255,0.5); cursor:pointer; font-size:1rem; padding:0; margin-left:0.25rem; line-height:1; transition:color 0.2s;"
								onmouseover={(e) => e.currentTarget.style.color = '#fff'}
								onmouseout={(e) => e.currentTarget.style.color = 'rgba(255,255,255,0.5)'}
							>
								×
							</button>
						</div>
					{/each}
				</div>
			{/if}
		</div>
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
