<script lang="ts">
	import { pushStore, isNativeApp } from '$lib/stores/push.svelte';
	import { api } from '$lib/api';

	let { onclose }: { onclose: () => void } = $props();

	let loading = $state(false);
	let denied = $state(false);

	async function activate() {
		loading = true;
		try {
			const ok = await pushStore.subscribe();
			if (ok) {
				// Mark as enabled in server prefs so scheduleNativeNotifications()
				// actually queues the daily alarms (default prefs have enabled=false).
				await api.put('/push/prefs', { enabled: true }).catch(() => {});
				onclose();
				return;
			}
			// subscribe() returned false — permission was denied
			const webDenied =
				!isNativeApp &&
				typeof Notification !== 'undefined' &&
				Notification.permission === 'denied';
			denied = isNativeApp || webDenied;
			if (!denied) onclose(); // user dismissed the web dialog without blocking
		} finally {
			loading = false;
		}
	}

	function dismiss() {
		// Won't ask again for 7 days
		localStorage.setItem('uro_notif_snoozed', String(Date.now() + 7 * 24 * 60 * 60 * 1000));
		onclose();
	}
</script>

<!-- Backdrop -->
<div class="backdrop" onclick={dismiss} role="presentation"></div>

<div class="modal" role="dialog" aria-modal="true" aria-label="Activar notificaciones">
	<div class="modal-icon">🔔</div>
	<h2 class="modal-title">Recordatorios inteligentes</h2>
	<p class="modal-sub">Solo te avisamos cuando tiene sentido</p>

	<ul class="feature-list">
		<li>
			<span class="feat-emoji">🍳</span>
			<div>
				<strong>Recordatorio de comida</strong>
				<span>Solo si esa comida no está registrada aún</span>
			</div>
		</li>
		<li>
			<span class="feat-emoji">🔥</span>
			<div>
				<strong>Racha en peligro</strong>
				<span>Si llevas ≥3 días y no has registrado nada hoy</span>
			</div>
		</li>
		<li>
			<span class="feat-emoji">🏆</span>
			<div>
				<strong>Hitos de racha</strong>
				<span>Al llegar a 7, 14, 30 días seguidos...</span>
			</div>
		</li>
		<li>
			<span class="feat-emoji">📊</span>
			<div>
				<strong>Resumen del día</strong>
				<span>Un vistazo rápido a tus macros al final del día</span>
			</div>
		</li>
	</ul>

	<p class="modal-fine">
		Sin spam. Sin marketing. Configurable en Ajustes.
	</p>

	{#if denied}
		<div class="denied-msg">
			{#if isNativeApp}
				Permiso denegado. Ve a Ajustes → Aplicaciones → Uroboros → Notificaciones para activarlas.
			{:else}
				El navegador bloqueó los permisos. Ve a los ajustes del navegador para activarlos.
			{/if}
		</div>
	{/if}

	<div class="modal-actions">
		<button class="btn-activate" onclick={activate} disabled={loading}>
			{loading ? 'Activando…' : '🔔 Activar recordatorios'}
		</button>
		<button class="btn-dismiss" onclick={dismiss}>Ahora no</button>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		backdrop-filter: blur(4px);
		z-index: 100;
		animation: fade-in 0.2s ease;
	}
	@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }

	.modal {
		position: fixed;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: min(480px, 100vw);
		background: oklch(18% 0.03 260);
		border: 1px solid oklch(35% 0.06 260 / 0.5);
		border-bottom: none;
		border-radius: 20px 20px 0 0;
		padding: 2rem 1.5rem 2.5rem;
		z-index: 101;
		animation: slide-up 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}
	@keyframes slide-up { from { transform: translateX(-50%) translateY(100%); } to { transform: translateX(-50%) translateY(0); } }

	.modal-icon {
		font-size: 2.5rem;
		margin-bottom: 0.25rem;
	}
	.modal-title {
		font-size: 1.2rem;
		font-weight: 800;
		color: #fff;
		margin: 0;
		text-align: center;
	}
	.modal-sub {
		font-size: 0.8rem;
		color: oklch(65% 0.05 260);
		margin: 0 0 0.75rem;
		text-align: center;
	}

	.feature-list {
		list-style: none;
		margin: 0;
		padding: 0;
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.feature-list li {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		background: oklch(22% 0.03 260);
		border: 1px solid oklch(35% 0.06 260 / 0.3);
		border-radius: 10px;
		padding: 0.6rem 0.875rem;
	}
	.feat-emoji {
		font-size: 1.25rem;
		flex-shrink: 0;
		margin-top: 1px;
	}
	.feature-list strong {
		display: block;
		font-size: 0.8rem;
		font-weight: 700;
		color: #fff;
	}
	.feature-list span {
		font-size: 0.72rem;
		color: oklch(65% 0.05 260);
	}

	.modal-fine {
		font-size: 0.7rem;
		color: oklch(55% 0.04 260);
		margin: 0.25rem 0;
		text-align: center;
	}

	.denied-msg {
		font-size: 0.75rem;
		color: oklch(75% 0.18 30);
		background: oklch(75% 0.18 30 / 0.1);
		border: 1px solid oklch(75% 0.18 30 / 0.25);
		border-radius: 8px;
		padding: 0.5rem 0.75rem;
		text-align: center;
	}

	.modal-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		width: 100%;
		margin-top: 0.5rem;
	}
	.btn-activate {
		width: 100%;
		padding: 0.875rem;
		background: linear-gradient(180deg, var(--primary), var(--primary-dim));
		color: var(--primary-ink);
		border: none;
		border-radius: 12px;
		font-size: 0.9rem;
		font-weight: 800;
		cursor: pointer;
		font-family: inherit;
		transition: opacity 0.15s;
	}
	.btn-activate:disabled { opacity: 0.6; cursor: wait; }
	.btn-dismiss {
		width: 100%;
		padding: 0.625rem;
		background: transparent;
		color: oklch(55% 0.04 260);
		border: none;
		font-size: 0.8rem;
		cursor: pointer;
		font-family: inherit;
	}
	.btn-dismiss:hover { color: oklch(70% 0.04 260); }
</style>
