<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { auth } from '$lib/stores/auth.svelte';
	import type { Friendship, FriendshipKind } from '$lib/types';
	import { Modal, Avatar } from '$lib/components';
	import { t } from '$lib/i18n/index.svelte';

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

	let addKind = $state<FriendshipKind>('friend');

	async function sendRequest() {
		addError = '';
		addSuccess = '';
		if (!addEmail.trim()) return;
		addLoading = true;
		try {
			await api.post('/friends', { email: addEmail.trim(), kind: addKind });
			addSuccess = `Solicitud enviada a ${addEmail.trim()}`;
			addEmail = '';
			addKind = 'friend';
			load();
		} catch (e: unknown) {
			addError = e instanceof Error ? e.message : 'Error al enviar solicitud';
		} finally {
			addLoading = false;
		}
	}

	// `kind` only ever lowers what was proposed — accepting as partner something
	// that wasn't offered is rejected by the API.
	async function accept(id: number, as?: FriendshipKind) {
		await api.patch(`/friends/${id}`, as ? { status: 'accepted', kind: as } : { status: 'accepted' });
		load();
	}

	async function proposePartner(f: Friendship) {
		try {
			await api.patch(`/friends/${f.id}`, { kind: 'partner' });
			load();
		} catch (e: unknown) {
			addError = e instanceof Error ? e.message : 'No se pudo proponer';
		}
	}

	let confirmBreakupId: number | null = $state(null);

	async function confirmBreakup() {
		if (!confirmBreakupId) return;
		await api.patch(`/friends/${confirmBreakupId}`, { kind: 'friend' });
		confirmBreakupId = null;
		load();
	}

	async function reject(id: number) {
		await api.patch(`/friends/${id}`, { status: 'rejected' });
		load();
	}

	async function togglePermission(f: Friendship) {
		const iAmReceiver = f.receiver.id === auth.user?.id;
		// Each controls their own flag: "allow partner to add to MY diary"
		const patch = iAmReceiver
			? { can_add_food: !f.can_add_food }
			: { can_add_food_requester: !f.can_add_food_requester };
		await api.patch(`/friends/${f.id}`, patch);
		load();
	}

	function myCanAddFlag(f: Friendship): boolean {
		// My flag = whether I allow the other person to add to MY diary
		return f.receiver.id === auth.user?.id ? f.can_add_food : f.can_add_food_requester;
	}

	function partnerName(f: Friendship): string {
		return f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name;
	}

	async function toggleSharedInventory(f: Friendship) {
		const iAmRequester = f.requester.id === auth.user?.id;
		const patch = iAmRequester
			? { shared_inventory_requester: !f.shared_inventory_requester }
			: { shared_inventory_receiver: !f.shared_inventory_receiver };
		await api.patch(`/friends/${f.id}`, patch);
		load();
	}

	function mySharedFlag(f: Friendship): boolean {
		return f.requester.id === auth.user?.id ? f.shared_inventory_requester : f.shared_inventory_receiver;
	}

	function theirSharedFlag(f: Friendship): boolean {
		return f.requester.id === auth.user?.id ? f.shared_inventory_receiver : f.shared_inventory_requester;
	}

	async function toggleDuel(f: Friendship) {
		const iAmRequester = f.requester.id === auth.user?.id;
		const patch = iAmRequester
			? { duel_opt_in_requester: !f.duel_opt_in_requester }
			: { duel_opt_in_receiver: !f.duel_opt_in_receiver };
		await api.patch(`/friends/${f.id}`, patch);
		load();
	}

	function myDuelFlag(f: Friendship): boolean {
		return f.requester.id === auth.user?.id ? f.duel_opt_in_requester : f.duel_opt_in_receiver;
	}

	function theirDuelFlag(f: Friendship): boolean {
		return f.requester.id === auth.user?.id ? f.duel_opt_in_receiver : f.duel_opt_in_requester;
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

	function friendAvatar(f: Friendship): string | null | undefined {
		return f.requester.id === auth.user?.id ? f.receiver.avatar_id : f.requester.avatar_id;
	}

	let activeTab = $state<'lista' | 'solicitudes'>('lista');
	let showAddForm = $state(false);

	// The partner is the one the relationship *says* is the partner. This used to
	// be `friends.find(f => f.can_add_food)` — a flag that defaulted to true on
	// every request sent, over a list the API returned unordered, so the badge
	// landed on whichever friend came back first.
	let partner = $derived(friends.find((f) => f.kind === 'partner'));
</script>

<!-- ── Header ── -->
<div style="display:flex; align-items:center; gap:0.75rem; padding:0.25rem 0 1rem;">
	<button onclick={() => goto('/settings')} style="width:36px; height:36px; border-radius:50%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; justify-content:center; color:#fff; cursor:pointer; font-family:inherit; font-size:1rem; flex-shrink:0;">←</button>
	<div style="flex:1; min-width:0;">
		<h1 style="font-size:1.875rem; font-weight:400; letter-spacing:-0.05em; color:#fff; line-height:1; margin:0; font-family:'Lora','Georgia',serif;">{t('friends.title')}</h1>
		<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.25rem;">{friends.length} conectad@s</div>
	</div>
	<button onclick={() => showAddForm = !showAddForm} style="padding:0.5625rem 0.875rem; border-radius:14px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.75rem; font-family:inherit; white-space:nowrap;">{t('friends.add')}</button>
</div>

<!-- ── Add friend form ── -->
{#if showAddForm}
	<div class="glass-card" style="margin-bottom:1rem;">
		<div style="font-size:0.6875rem; font-weight:700; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.625rem;">{t('friends.sendRequest')}</div>
		<input type="email" placeholder={t('friends.emailPlaceholder')} bind:value={addEmail}
			onkeydown={(e) => { if (e.key === 'Enter') sendRequest(); }} style="width:100%; margin-bottom:0.75rem;" />

		<!-- El tipo se elige, no se deduce de un permiso suelto -->
		<div style="display:flex; gap:0.5rem; margin-bottom:0.75rem;">
			<button
				onclick={() => { if (!partner) addKind = 'partner'; }}
				disabled={!!partner}
				aria-pressed={addKind === 'partner'}
				style="flex:1; text-align:left; padding:0.8125rem; border-radius:14px; cursor:{partner ? 'not-allowed' : 'pointer'}; opacity:{partner ? 0.4 : 1}; font-family:inherit; border:1px solid {addKind === 'partner' ? 'oklch(80% 0.17 165 / 0.55)' : 'rgba(255,255,255,0.1)'}; background:{addKind === 'partner' ? 'oklch(75% 0.15 160 / 0.1)' : 'rgba(255,255,255,0.03)'};">
				<div style="font-size:1.0625rem;">💚</div>
				<div style="font-size:0.8125rem; font-weight:700; margin-top:0.25rem; color:{addKind === 'partner' ? 'oklch(88% 0.15 160)' : '#fff'};">{t('friends.kindPartner')}</div>
				<div style="font-size:0.625rem; color:rgba(255,255,255,0.45); margin-top:0.3125rem; line-height:1.45;">{t('friends.kindPartnerSub')}</div>
				{#if partner}
					<div style="font-size:0.5938rem; color:oklch(80% 0.13 85); margin-top:0.4375rem; line-height:1.4;">🔒 Ya tienes a {friendName(partner)} como pareja</div>
				{/if}
			</button>
			<button
				onclick={() => (addKind = 'friend')}
				aria-pressed={addKind === 'friend'}
				style="flex:1; text-align:left; padding:0.8125rem; border-radius:14px; cursor:pointer; font-family:inherit; border:1px solid {addKind === 'friend' ? 'oklch(80% 0.17 165 / 0.55)' : 'rgba(255,255,255,0.1)'}; background:{addKind === 'friend' ? 'oklch(75% 0.15 160 / 0.1)' : 'rgba(255,255,255,0.03)'};">
				<div style="font-size:1.0625rem;">👋</div>
				<div style="font-size:0.8125rem; font-weight:700; margin-top:0.25rem; color:{addKind === 'friend' ? 'oklch(88% 0.15 160)' : '#fff'};">{t('friends.kindFriend')}</div>
				<div style="font-size:0.625rem; color:rgba(255,255,255,0.45); margin-top:0.3125rem; line-height:1.45;">{t('friends.kindFriendSub')}</div>
			</button>
		</div>

		<button onclick={sendRequest} disabled={addLoading || !addEmail.trim()} style="width:100%; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; border:none; padding:0.6875rem; border-radius:13px; font-family:inherit; cursor:pointer; font-size:0.8125rem;">
			{addLoading ? '...' : t('friends.sendRequest')}
		</button>
		{#if addError}<p style="color:oklch(75% 0.2 25); font-size:0.75rem; margin-top:0.375rem;">{addError}</p>{/if}
		{#if addSuccess}<p style="color:oklch(85% 0.17 160); font-size:0.75rem; margin-top:0.375rem;">{addSuccess}</p>{/if}
	</div>
{/if}

{#if loading}
	<p style="text-align:center; color:rgba(255,255,255,0.4); padding:3rem 0; font-size:0.85rem;">{t('friends.loading')}</p>
{:else}

<!-- ── Partner spotlight ── -->
{#if partner}
	{@const pName = friendName(partner)}
	<div class="glass-card" style="margin-bottom:0.875rem; display:flex; align-items:center; gap:0.875rem; border-color:oklch(75% 0.18 160 / 0.3); background:oklch(75% 0.15 160 / 0.07);">
		<div style="border-radius:50%; box-shadow:0 0 20px oklch(75% 0.2 165 / 0.4); flex-shrink:0; line-height:0;">
			<Avatar name={pName} avatarId={friendAvatar(partner)} size={52} ring="2px solid oklch(80% 0.17 165)" />
		</div>
		<div style="flex:1; min-width:0;">
			<div style="font-size:0.625rem; letter-spacing:0.075em; color:oklch(85% 0.15 160); text-transform:uppercase; font-weight:800;">{t('friends.pairUp')}</div>
			<div style="font-size:0.9375rem; font-weight:700; color:#fff; margin-top:0.125rem;">{pName}</div>
			<div style="font-size:0.6875rem; color:rgba(255,255,255,0.5); margin-top:0.125rem;">{friendEmail(partner)}</div>
		</div>
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
			<div style="font-size:0.875rem; font-weight:600;">{t('friends.empty')}</div>
			<div style="font-size:0.75rem; margin-top:0.25rem; color:rgba(255,255,255,0.35);">{t('friends.emptySub')}</div>
		</div>
	{:else}
		<div class="glass-card" style="padding:0.375rem;">
			{#each friends as f, i (f.id)}
				{@const iAmReceiver = f.receiver.id === auth.user?.id}
				{@const fName = friendName(f)}
				{@const fId = f.requester.id === auth.user?.id ? f.receiver.id : f.requester.id}
				<div style="padding:0.875rem; border-bottom:{i < friends.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<div style="display:flex; align-items:center; gap:0.75rem;">
						<!-- Avatar — toca para ver perfil -->
						<button onclick={() => goto(`/profile/${fId}`)} style="position:relative; flex-shrink:0; background:none; border:none; padding:0; cursor:pointer; box-shadow:none; border-radius:50%; line-height:0;">
							<Avatar name={fName} avatarId={friendAvatar(f)} size={46} />
							{#if f.kind === 'partner'}
								<div style="position:absolute; bottom:-2px; right:-2px; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, oklch(85% 0.17 160), oklch(72% 0.18 170)); border:2px solid #0a0d14; display:flex; align-items:center; justify-content:center; font-size:0.5rem; font-weight:800; color:#041010;">★</div>
							{/if}
						</button>
						<div style="flex:1; min-width:0;">
							{#if f.kind === 'partner'}
								<div style="font-size:0.5625rem; font-weight:800; letter-spacing:0.075em; text-transform:uppercase; color:oklch(85% 0.15 160);">{t('friends.kindPartner')}</div>
							{/if}
							<div style="font-size:0.8125rem; font-weight:700; color:#fff;">{fName}</div>
							<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45); margin-top:0.125rem;">{friendEmail(f)}</div>
						</div>
						{#if f.kind !== 'partner' && !partner}
							<button onclick={() => proposePartner(f)} style="font-size:0.625rem; padding:0.25rem 0.5rem; border-radius:8px; border:1px solid oklch(80% 0.17 165 / 0.4); background:oklch(75% 0.15 160 / 0.1); color:oklch(85% 0.15 160); cursor:pointer; font-family:inherit; white-space:nowrap;">
								{f.partner_proposed_by === auth.user?.id ? t('friends.partnerProposed') : f.partner_proposed_by ? t('friends.partnerWants') : t('friends.makePartner')}
							</button>
						{/if}
						<button onclick={() => removeFriend(f.id)} style="font-size:0.625rem; padding:0.25rem 0.5rem; border-radius:8px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.55); cursor:pointer; font-family:inherit;">{t('friends.remove')}</button>
					</div>
					{#if f.partner_proposed_by && f.partner_proposed_by !== auth.user?.id && f.kind !== 'partner'}
						<div style="font-size:0.625rem; color:oklch(85% 0.15 160); margin-top:0.5rem;">👆 {fName} quiere que seáis pareja. Toca para aceptar.</div>
					{/if}
					<!-- Shared inventory double-flag — partners only: a household is a 1:1 thing -->
					{#if f.kind === 'partner'}
					<div style="padding:0.5rem 0.625rem; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid rgba(255,255,255,0.06); margin-top:0.625rem;">
						<div style="display:flex; align-items:center; justify-content:space-between;">
							<div>
								<div style="font-size:0.75rem; font-weight:600; color:#fff;">{t('friends.sharedInventory')}</div>
								<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">
									{#if f.shared_inventory}
										Un inventario y lista de compra para los dos ✓
									{:else if mySharedFlag(f) && !theirSharedFlag(f)}
										Esperando a {f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name}...
									{:else if !mySharedFlag(f) && theirSharedFlag(f)}
										{f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name} quiere compartir
									{:else}
										Inventarios separados
									{/if}
								</div>
							</div>
							<button onclick={() => toggleSharedInventory(f)} role="switch" aria-checked={mySharedFlag(f)} aria-label={t('friends.shareAria', { name: partnerName(f) })} style="width:40px; height:24px; border-radius:99px; cursor:pointer; background:{mySharedFlag(f) ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border:1px solid {mySharedFlag(f) ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'}; position:relative; flex-shrink:0; transition:background 0.2s; padding:0;">
								<div style="position:absolute; top:2px; left:{mySharedFlag(f) ? '18px' : '2px'}; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #fff, oklch(85% 0.1 165)); box-shadow:0 2px 5px rgba(0,0,0,0.3); transition:left 0.2s;"></div>
							</button>
						</div>
						{#if theirSharedFlag(f) && !mySharedFlag(f)}
							<div style="font-size:0.625rem; color:oklch(85% 0.15 160); margin-top:0.375rem;">{t('friends.enableYourSide')}</div>
						{/if}
					</div>
					{/if}
					<!-- Weekly duel double-flag -->
					<div style="padding:0.5rem 0.625rem; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid rgba(255,255,255,0.06); margin-top:0.375rem;">
						<div style="display:flex; align-items:center; justify-content:space-between;">
							<div>
								<div style="font-size:0.75rem; font-weight:600; color:#fff;">{t('friends.duel')}</div>
								<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">
									{#if f.duel_active}
										Compitiendo en adherencia ✓
									{:else if myDuelFlag(f) && !theirDuelFlag(f)}
										Esperando a {f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name}...
									{:else if !myDuelFlag(f) && theirDuelFlag(f)}
										{f.requester.id === auth.user?.id ? f.receiver.name : f.requester.name} quiere competir
									{:else}
										Solo se comparte el %, nunca el diario
									{/if}
								</div>
							</div>
							<button onclick={() => toggleDuel(f)} role="switch" aria-checked={myDuelFlag(f)} aria-label={t('friends.duelAria', { name: partnerName(f) })} style="width:40px; height:24px; border-radius:99px; cursor:pointer; background:{myDuelFlag(f) ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border:1px solid {myDuelFlag(f) ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'}; position:relative; flex-shrink:0; transition:background 0.2s; padding:0;">
								<div style="position:absolute; top:2px; left:{myDuelFlag(f) ? '18px' : '2px'}; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #fff, oklch(85% 0.1 165)); box-shadow:0 2px 5px rgba(0,0,0,0.3); transition:left 0.2s;"></div>
							</button>
						</div>
						{#if theirDuelFlag(f) && !myDuelFlag(f)}
							<div style="font-size:0.625rem; color:oklch(85% 0.15 160); margin-top:0.375rem;">{t('friends.enableYourSideDuel')}</div>
						{/if}
					</div>
					<!-- Diary access is partner-only, like the household above -->
					{#if f.kind === 'partner'}
					<div style="display:flex; align-items:center; justify-content:space-between; padding:0.5rem 0.625rem; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid rgba(255,255,255,0.06); margin-top:0.375rem;">
						<div>
							<div style="font-size:0.75rem; font-weight:600; color:#fff;">{t('friends.allowDiary')}</div>
							<div style="font-size:0.625rem; color:rgba(255,255,255,0.4); margin-top:0.125rem;">
								{myCanAddFlag(f) ? `${partnerName(f)} puede registrar en tu diario` : 'Solo lectura para ellos'}
							</div>
						</div>
						<button onclick={() => togglePermission(f)} role="switch" aria-checked={myCanAddFlag(f)} aria-label={t('friends.allowDiaryAria', { name: partnerName(f) })} style="width:40px; height:24px; border-radius:99px; cursor:pointer; background:{myCanAddFlag(f) ? 'oklch(75% 0.18 165 / 0.35)' : 'rgba(255,255,255,0.08)'}; border:1px solid {myCanAddFlag(f) ? 'oklch(80% 0.17 165 / 0.5)' : 'rgba(255,255,255,0.1)'}; position:relative; flex-shrink:0; transition:background 0.2s; padding:0;">
							<div style="position:absolute; top:2px; left:{myCanAddFlag(f) ? '18px' : '2px'}; width:18px; height:18px; border-radius:50%; background:linear-gradient(135deg, #fff, oklch(85% 0.1 165)); box-shadow:0 2px 5px rgba(0,0,0,0.3); transition:left 0.2s;"></div>
						</button>
					</div>
						<button onclick={() => (confirmBreakupId = f.id)} style="width:100%; margin-top:0.375rem; padding:0.5rem; border-radius:10px; border:1px solid oklch(65% 0.18 25 / 0.3); background:oklch(60% 0.16 25 / 0.08); color:oklch(85% 0.12 25); font-weight:600; font-size:0.6875rem; font-family:inherit; cursor:pointer;">
							Ya no somos pareja
						</button>
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
			<div style="font-size:0.875rem; font-weight:600;">{t('friends.noPending')}</div>
		</div>
	{:else}
		<div class="glass-card" style="padding:0.375rem;">
			{#each pending as f, i (f.id)}
				<div style="padding:0.875rem; border-bottom:{i < pending.length-1 ? '1px solid rgba(255,255,255,0.05)' : 'none'};">
					<div style="display:flex; align-items:center; gap:0.75rem;">
						<Avatar name={f.requester.name} avatarId={f.requester.avatar_id} size={42} />
						<div style="flex:1; min-width:0;">
							<div style="font-size:0.8125rem; font-weight:700; color:#fff;">{f.requester.name}</div>
							<div style="font-size:0.6875rem; color:rgba(255,255,255,0.45);">
								te quiere añadir como <span style="font-weight:700; color:{f.kind === 'partner' ? 'oklch(85% 0.15 160)' : 'rgba(255,255,255,0.75)'};">{f.kind === 'partner' ? t('friends.asPartner') : t('friends.asFriend')}</span>
							</div>
						</div>
					</div>

					<!-- Qué implica, antes de decidir -->
					<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:12px; padding:0.6875rem 0.8125rem; margin-top:0.6875rem;">
						<div style="font-size:0.6563rem; color:rgba(255,255,255,0.5); line-height:1.7;">
							{#if f.kind === 'partner'}
								Si aceptáis como pareja podréis:<br>
								· juntar despensa y lista de la compra<br>
								· apuntaros comida el uno al otro<br>
								· veros las alergias<br>
								<span style="color:rgba(255,255,255,0.35);">{t('friends.eachSeparate')}</span>
							{:else}
								{f.requester.name} podrá:<br>
								· ver tu racha y cuántas recetas tienes<br>
								· ver las recetas que marques <em>{t('friends.forFriends')}</em><br>
								· proponerte duelo semanal (solo el %)<br>
								<span style="color:rgba(255,255,255,0.35);">{t('friends.wontSeeDiary')}</span>
							{/if}
						</div>
					</div>

					{#if f.kind === 'partner'}
						<button onclick={() => accept(f.id)} disabled={!!partner} style="width:100%; margin-top:0.6875rem; padding:0.6875rem; border-radius:13px; border:none; cursor:{partner ? 'not-allowed' : 'pointer'}; opacity:{partner ? 0.4 : 1}; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.8125rem; font-family:inherit;">
							Aceptar como pareja
						</button>
						{#if partner}
							<div style="font-size:0.5938rem; color:oklch(80% 0.13 85); margin-top:0.375rem; text-align:center;">🔒 Ya tienes a {friendName(partner)} como pareja</div>
						{/if}
						<div style="display:flex; gap:0.4375rem; margin-top:0.4375rem;">
							<button onclick={() => accept(f.id, 'friend')} style="flex:1; padding:0.5625rem; border-radius:11px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-size:0.7188rem; cursor:pointer; font-family:inherit;">Aceptar solo como amigo</button>
							<button onclick={() => reject(f.id)} aria-label="Rechazar" style="width:38px; padding:0.5625rem 0; border-radius:11px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-size:0.8125rem; cursor:pointer; font-family:inherit;">✕</button>
						</div>
					{:else}
						<button onclick={() => accept(f.id)} style="width:100%; margin-top:0.6875rem; padding:0.6875rem; border-radius:13px; border:none; cursor:pointer; background:linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170)); color:#041010; font-weight:800; font-size:0.8125rem; font-family:inherit;">
							Aceptar
						</button>
						<button onclick={() => reject(f.id)} style="width:100%; margin-top:0.4375rem; padding:0.5625rem; border-radius:11px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.05); color:rgba(255,255,255,0.7); font-size:0.7188rem; cursor:pointer; font-family:inherit;">Rechazar</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
{/if}

{/if}

<!-- Bottom spacing -->
<div style="height:6rem;"></div>

<!-- Breakup confirmation — the household splits, and that's worth saying first -->
{#if confirmBreakupId !== null}
	<Modal onClose={() => (confirmBreakupId = null)} title="¿Ya no sois pareja?" subtitle="Seguiréis siendo amigos.">
		<div style="background:oklch(60% 0.16 25 / 0.1); border:1px solid oklch(65% 0.18 25 / 0.3); border-radius:12px; padding:0.6875rem 0.8125rem; font-size:0.6875rem; color:oklch(85% 0.1 30); line-height:1.5;">
			<strong>Vuestra despensa se separará.</strong><br>
			Cada uno recupera lo que aportó. No se borran las recetas ni el historial del duelo.
		</div>
		<div style="display:flex; gap:0.5rem; margin-top:0.75rem;">
			<button class="btn-secondary" onclick={() => (confirmBreakupId = null)} style="flex:1;">Cancelar</button>
			<button class="btn-danger" onclick={confirmBreakup} style="flex:1;">Confirmar</button>
		</div>
	</Modal>
{/if}

<!-- Delete confirmation modal -->
{#if confirmDeleteId !== null}
	<Modal onClose={() => confirmDeleteId = null} title="¿Eliminar amigo?" subtitle="Se eliminará la amistad y los permisos asociados.">
		<div style="display:flex; gap:0.5rem; margin-top:0.5rem;">
			<button class="btn-secondary" onclick={() => confirmDeleteId = null} style="flex:1;">Cancelar</button>
			<button class="btn-danger" onclick={confirmRemove} style="flex:1;">{t('friends.remove')}</button>
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
