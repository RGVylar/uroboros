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
</script>

<!-- Header -->
<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:1rem;">
	<div style="flex:1;">
		<div style="font-size:0.625rem; letter-spacing:0.15em; color:rgba(255,255,255,0.45); text-transform:uppercase; font-weight:600;">Social</div>
		<div style="font-size:1.25rem; font-weight:800; color:#fff; letter-spacing:-0.02em;">Amigos</div>
	</div>
	<button onclick={() => goto('/settings')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.1); color:rgba(255,255,255,0.8); cursor:pointer; font-size:1rem; display:flex; align-items:center; justify-content:center; font-family:inherit;">←</button>
</div>

<!-- Añadir amigo -->
<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(24px); -webkit-backdrop-filter:blur(24px); border:1px solid rgba(255,255,255,0.09); border-radius:20px; padding:1rem; margin-bottom:1.25rem;">
	<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.75rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">
		Añadir amigo
	</div>
	<div style="display:flex; gap:0.5rem;">
		<input
			type="email"
			placeholder="Email del amigo..."
			bind:value={addEmail}
			onkeydown={(e) => { if (e.key === 'Enter') sendRequest(); }}
			style="flex:1;"
		/>
		<button onclick={sendRequest} disabled={addLoading || !addEmail.trim()} style="white-space:nowrap;">
			{addLoading ? '...' : 'Enviar'}
		</button>
	</div>
	{#if addError}
		<p style="color:var(--danger); font-size:0.8rem; margin-top:0.5rem;">{addError}</p>
	{/if}
	{#if addSuccess}
		<p style="color:var(--primary); font-size:0.8rem; margin-top:0.5rem;">{addSuccess}</p>
	{/if}
</div>

{#if loading}
	<p style="text-align:center; color:var(--text-muted); padding:2rem 0;">Cargando...</p>
{:else}

	<!-- Solicitudes pendientes -->
	{#if pending.length > 0}
		<div style="margin-bottom:1.25rem;">
			<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">
				Solicitudes recibidas
				<span style="background:var(--danger); color:#fff; border-radius:99px; padding:0.1rem 0.45rem; font-size:0.7rem; margin-left:0.3rem;">
					{pending.length}
				</span>
			</div>
			{#each pending as f (f.id)}
				<div class="glass-card" style="margin-bottom:0.5rem; display:flex; align-items:center; gap:0.75rem;">
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.9rem;">{f.requester.name}</div>
						<div style="font-size:0.75rem; color:var(--text-muted);">{f.requester.email}</div>
					</div>
					<button onclick={() => accept(f.id)} style="font-size:0.8rem; padding:0.35rem 0.7rem; background:var(--primary); color:#000; font-weight:700; border:none;">
						✓ Aceptar
					</button>
					<button onclick={() => reject(f.id)} class="btn-danger" style="font-size:0.8rem; padding:0.35rem 0.6rem;">
						✕
					</button>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Amigos aceptados -->
	<div style="font-weight:700; font-size:0.9rem; margin-bottom:0.6rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em;">
		Mis amigos
		{#if friends.length > 0}
			<span style="color:var(--primary); font-weight:600;">{friends.length}</span>
		{/if}
	</div>

	{#if friends.length === 0}
		<div class="glass-card" style="text-align:center; color:var(--text-muted); padding:2rem 1rem;">
			<div style="font-size:2rem; margin-bottom:0.5rem;">👥</div>
			<div style="font-size:0.9rem;">Aún no tienes amigos en la app.</div>
			<div style="font-size:0.8rem; margin-top:0.25rem;">Envía una solicitud con el email de alguien.</div>
		</div>
	{:else}
		{#each friends as f (f.id)}
			{@const iAmReceiver = f.receiver.id === auth.user?.id}
			<div class="glass-card" style="margin-bottom:0.6rem;">
				<div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:{iAmReceiver ? '0.75rem' : '0'};">
					<div style="flex:1; min-width:0;">
						<div style="font-weight:600; font-size:0.9rem;">{friendName(f)}</div>
						<div style="font-size:0.75rem; color:var(--text-muted);">{friendEmail(f)}</div>
					</div>
					<button onclick={() => removeFriend(f.id)} class="btn-danger" style="font-size:0.75rem; padding:0.3rem 0.5rem;">
						Eliminar
					</button>
				</div>

				{#if iAmReceiver}
					<!-- Permission toggle — only the receiver sees this -->
					<div style="display:flex; align-items:center; justify-content:space-between; padding:0.5rem 0.75rem; background:rgba(255,255,255,0.04); border-radius:8px; border:1px solid var(--border);">
						<div>
							<div style="font-size:0.8rem; font-weight:600;">Puede añadir comidas</div>
							<div style="font-size:0.7rem; color:var(--text-muted);">
								{f.can_add_food ? `${f.requester.name} puede registrar en tu diario` : 'Solo lectura'}
							</div>
						</div>
						<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
						<div
							onclick={() => togglePermission(f)}
							style="
								width:44px; height:24px; border-radius:99px; cursor:pointer;
								background:{f.can_add_food ? 'var(--primary)' : 'rgba(255,255,255,0.15)'};
								position:relative; transition:background 0.2s; flex-shrink:0;
							">
							<div style="
								position:absolute; top:3px;
								left:{f.can_add_food ? '23px' : '3px'};
								width:18px; height:18px; border-radius:50%;
								background:#fff; transition:left 0.2s;
							"></div>
						</div>
					</div>
				{:else}
					<div style="font-size:0.72rem; color:var(--text-muted); margin-top:0.1rem;">
						{f.can_add_food ? '✓ Puede añadir comidas en tu diario' : '✗ Solo puede ver'}
					</div>
				{/if}
			</div>
		{/each}
	{/if}
{/if}

<!-- Delete confirmation modal -->
{#if confirmDeleteId !== null}
	<Modal onClose={() => confirmDeleteId = null} title="¿Eliminar amigo?" subtitle="Se eliminará la amistad y los permisos asociados.">
		<div style="display:flex; gap:0.5rem; margin-top:0.5rem;">
			<button class="btn-secondary" onclick={() => confirmDeleteId = null} style="flex:1;">Cancelar</button>
			<button class="btn-danger" onclick={confirmRemove} style="flex:1;">Eliminar</button>
		</div>
	</Modal>
{/if}
