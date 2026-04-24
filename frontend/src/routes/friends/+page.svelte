<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Friendship } from '$lib/types';
	import { Modal } from '$lib/components';

	if (!auth.isLoggedIn) goto('/login');

	let friends: Friendship[] = $state([]);
	let pending: Friendship[] = $state([]);
	let loading = $state(true);
	let addEmail = $state('');
	let addError = $state('');
	let addLoading = $state(false);
	let addSuccess = $state('');
	let confirmDeleteId: number | null = $state(null);

	async function load() {
		loading = true;
		try {
			[friends, pending] = await Promise.all([
				api.get<Friendship[]>('/friends'),
				api.get<Friendship[]>('/friends/pending'),
			]);
		} catch {
			// ignore
		} finally {
			loading = false;
		}
	}

	$effect(() => { load(); });

	async function sendRequest() {
		addError = '';
		addSuccess = '';
		if (!addEmail.trim()) return;
		addLoading = true;
		try {
			await api.post('/friends', { email: addEmail.trim() });
			addSuccess = `Solicitud enviada a ${addEmail.trim()}`;
			addEmail = '';
			load();
		} catch (e: unknown) {
			addError = e instanceof Error ? e.message : 'Error al enviar solicitud';
		} finally {
			addLoading = false;
		}
	}

	async function accept(id: number) {
		await api.patch(`/friends/${id}`, { status: 'accepted' });
		load();
	}

	async function reject(id: number) {
		await api.patch(`/friends/${id}`, { status: 'rejected' });
		load();
	}

	async function togglePermission(f: Friendship) {
		const iAmReceiver = f.receiver.id === auth.user?.id;
		if (!iAmReceiver) return; // solo el receptor gestiona permisos
		await api.patch(`/friends/${f.id}`, { can_add_food: !f.can_add_food });
		load();
	}

	async function removeFriend(id: number) {
		confirmDeleteId = id;
	}

	async function confirmRemove() {
		if (!confirmDeleteId) return;
		await api.del(`/friends/${confirmDeleteId}`);
		confirmDeleteId = null;
		load();
	}

	function friendName(f: Friendship): string {
		return f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name;
	}

	function friendEmail(f: Friendship): string {
		return f.requester.id === auth.user?.id ? f.receiver.email : f.requester.email;
	}

	function nameHue(name: string): number {
		let h = 0;
		for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360;
		return h;
	}

	let activeTab = $state<'lista' | 'solicitudes'>('lista');
	let showAddForm = $state(false);
	let partner = $derived(friends.find(f => f.can_add_food));
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/settings')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">Amigos</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{friends.length} conectad@s</div>
	</div>
	<button onclick={() => showAddForm = !showAddForm} style="padding:0.5625rem 0.875rem; border-radius:14px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.75rem; font-family:inherit; white-space:nowrap;">＋ Añadir</button>
</div>

<!-- ── Add friend form ── -->
{#if showAddForm}
	<div class="glass-card" style="margin-bottom:1rem;">
		<div style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.625rem;">Enviar solicitud</div>
		<div style="display:flex; gap:0.5rem;">
			<input type="email" placeholder="Email del amigo..." bind:value={addEmail}
				onkeydown={(e) => { if (e.key === 'Enter') sendRequest(); }} style="flex:1;" />
			<button onclick={sendRequest} disabled={addLoading || !addEmail.trim()} style="white-space:nowrap; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; border:none; padding:0 1rem; border-radius:12px; font-family:inherit; cursor:pointer;">
				{addLoading ? '...' : 'Enviar'}
			</button>
		</div>
		{#if addError}<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin-top:0.375rem;">{addError}</p>{/if}
		{#if addSuccess}<p style="color:oklch(85% 0.17 160); font-size:0.75rem; margin-top:0.375rem;">{addSuccess}</p>{/if}
	</div>
{/if}

{#if loading}
	<p style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;">Cargando...</p>
{:else}

<!-- ── Partner spotlight ── -->
{#if partner}
	{@const pName = friendName(partner)}
	{@const pHue = nameHue(pName)}
	<div class="glass-card" style="margin-bottom:0.875rem; display:flex; align-items:center; gap:0.875rem; border-color:oklch(75% 0.18 160 / 0.3); background:oklch(75% 0.15 160 / 0.07);">
		<div style="width:52px; height:52px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {pHue}), oklch(55% 0.16 {(pHue+30) % 360})); display:flex; align-items:center; justify-content:center; font-size:1.375rem; font-weight:800; color:#fff; border:2px solid oklch(80% 0.17 165); box-shadow:0 0 20px oklch(75% 0.2 165 / 0.4); flex-shrink:0;">{pName[0].toUpperCase()}</div>
		<div style="flex:1; min-width:0;">
			<div style="font-size:0.625rem; letter-spacing:0.075em; color:oklch(85% 0.15 160); text-transform:uppercase; font-weight:800;">Empareja@</div>
			<div style="font-size:0.9375rem; font-weight:700; color:#fff; margin-top:0.125rem;">{pName}</div>
			<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.125rem;">{friendEmail(partner)}</div>
		</div>
		<div style="padding:0.25rem 0.625rem; border-radius:99px; background:oklch(75% 0.18 160 / 0.25); color:oklch(85% 0.15 160); font-size:0.625rem; font-weight:800; letter-spacing:0.03em; flex-shrink:0;">2× ACTIVO</div>
	</div>
{/if}

<!-- ── Tabs ── -->
<div style="display:flex; gap:0.375rem; margin-bottom:0.875rem;">
	{#each [['lista','Lista'],['solicitudes',`Solicitudes${pending.length > 0 ? ' · '+pending.length : ''}`]] as [id, label]}
		<button
			onclick={() => activeTab = id as 'lista'|'solicitudes'}
			style="flex:1; padding:0.5rem; border-radius:99px; border:1px solid {activeTab===id ? 'oklch(75% 0.18 160 / 0.4)' : 'rgba(255,255,255,0.1)'}; background:{activeTab===id ? 'oklch(75% 0.18 160 / 0.12)' : 'rgba(255,255,255,0.04)'}; color:{activeTab===id ? 'oklch(85% 0.15 160)' : 'rgba(255,255,255,0.55)'}; font-weight:700; font-size:0.75rem; font-family:inherit; cursor:pointer; text-align:center;">
			{label}
		</button>
	{/each}
</div>

<!-- ── Tab: Lista ── -->
{#if activeTab === 'lista'}
	{#if friends.length === 0}
		<div class="glass-card" style="text-align:center; color:rgba(255,255,255,0.4); padding:2.5rem 1rem;">
			<div style="font-size:2rem; margin-bottom:0.5rem;">👥</div>
			<div style="font-size:0.875rem; font-weight:600;">Sin amigos aún</div>
			<div style="font-size:0.75rem; margin-top:0.25rem; color:rgba(255,255,255,0.35);">Usa el botón ＋ Añadir para enviar una solicitud</div>
		</div>
	{:else}
		<div class="glass-card" style="padding:0.375rem;">
			{#each friends as f, i (f.id)}
				{@const iAmReceiver = f.receiver.id === auth.user?.id}
				{@const fName = friendName(f)}
				{@const fHue = nameHue(fName)}
				<div style="padding:0.875rem; border-bottom:{i < friends.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<div style="display:flex; align-items:center; gap:0.75rem;">
						<!-- Avatar -->
						<div style="position:relative; flex-shrink:0;">
							<div style="width:46px; height:46px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {fHue}), oklch(55% 0.16 {(fHue+30) % 360})); display:flex; align-items:center; justify-content:center; font-size:1.1875rem; font-weight:800; color:#fff;">{fName[0].toUpperCase()}</div>
							{#if f.can_add_food}
								<div style="position:absolute; bottom:-2px; right:-2px; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, oklch(85% 0.17 160), oklch(72% 0.18 170)); border:2px solid #0a0d14; display:flex; align-items:center; justify-content:center; font-size:0.5rem; font-weight:800; color:#041010;">★</div>
							{/if}
						</div>
						<div style="flex:1; min-width:0;">
							<div style="font-size:0.8125rem; font-weight:700; color:#fff;">{fName}</div>
							<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45); margin-top:0.125rem;">{friendEmail(f)}</div>
						</div>
						<button onclick={() => removeFriend(f.id)} style="font-size:0.625rem; padding:0.25rem 0.5rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.55); cursor:pointer; font-family:inherit;">Eliminar</button>
					</div>
					{#if iAmReceiver}
						<div style="display:flex; align-items:center; justify-content:space-between; padding:0.5rem 0.625rem; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid rgba(255,255,255,0.06); margin-top:0.625rem;">
							<div>
								<div style="font-size:0.75rem; font-weight:600; color:#fff;">Puede añadir comidas</div>
								<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">{f.can_add_food ? `${f.requester.name} registra en tu diario` : 'Solo lectura'}</div>
							</div>
							<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
							<div onclick={() => togglePermission(f)} style="width:40px; height:24px; border-radius:99px; cursor:pointer; background:{f.can_add_food ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border:1px solid {f.can_add_food ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'}; position:relative; flex-shrink:0; transition:background 0.2s;">
								<div style="position:absolute; top:2px; left:{f.can_add_food ? '18px' : '2px'}; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #fff, oklch(85% 0.1 165)); box-shadow:0 2px 5px rgba(0,0,0,0.3); transition:left 0.2s;"></div>
							</div>
						</div>
					{:else}
						<div style="font-size:0.6875rem; color:rgba(255,255,255,0.4); margin-top:0.375rem; padding-left:0.25rem;">
							{f.can_add_food ? '★ Puede registrar en tu diario' : 'Solo puede ver'}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}

<!-- ── Tab: Solicitudes ── -->
{#if activeTab === 'solicitudes'}
	{#if pending.length === 0}
		<div class="glass-card" style="text-align:center; color:rgba(255,255,255,0.4); padding:2.5rem 1rem;">
			<div style="font-size:2rem; margin-bottom:0.5rem;">✉️</div>
			<div style="font-size:0.875rem; font-weight:600;">Sin solicitudes pendientes</div>
		</div>
	{:else}
		<div class="glass-card" style="padding:0.375rem;">
			{#each pending as f, i (f.id)}
				{@const rHue = nameHue(f.requester.name)}
				<div style="display:flex; align-items:center; gap:0.75rem; padding:0.875rem; border-bottom:{i < pending.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<div style="width:42px; height:42px; border-radius:50%; background:linear-gradient(135deg, oklch(72% 0.18 {rHue}), oklch(55% 0.16 {(rHue+30) % 360})); display:flex; align-items:center; justify-content:center; font-size:1.125rem; font-weight:800; color:#fff; flex-shrink:0;">{f.requester.name[0].toUpperCase()}</div>
					<div style="flex:1; min-width:0;">
						<div style="font-size:0.8125rem; font-weight:700; color:#fff;">{f.requester.name}</div>
						<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45);">{f.requester.email}</div>
					</div>
					<div style="display:flex; gap:0.375rem; flex-shrink:0;">
						<button onclick={() => accept(f.id)} style="padding:0.5rem 0.875rem; border-radius:11px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:700; font-size:0.6875rem; font-family:inherit;">Aceptar</button>
						<button onclick={() => reject(f.id)} style="width:32px; padding:0.5rem 0; border-radius:11px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-size:0.8125rem; cursor:pointer; font-family:inherit;">✕</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
{/if}

{/if}

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<!-- Delete confirmation modal -->
{#if confirmDeleteId !== null}
	<Modal onClose={() => confirmDeleteId = null} title="¿Eliminar amigo?" subtitle="Se eliminará la amistad y los permisos asociados.">
		<div style="display:flex; gap:0.5rem; margin-top:0.5rem;">
			<button class="btn-secondary" onclick={() => confirmDeleteId = null} style="flex:1;">Cancelar</button>
			<button class="btn-danger" onclick={confirmRemove} style="flex:1;">Eliminar</button>
		</div>
	</Modal>
{/if}

<style>
	.glass-card {
		background: rgba(255,255,255,0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255,255,255,0.09);
		border-radius: 20px;
		padding: 1rem;
	}
</style>
