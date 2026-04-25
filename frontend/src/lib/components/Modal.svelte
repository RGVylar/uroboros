<!--
  Modal.svelte
  Modal bottom-sheet (móvil) / centrado (desktop) con backdrop, cierre Escape,
  y animación de entrada. Reemplaza los modales inline ad-hoc del código actual.

  Uso:
    {#if showModal}
      <Modal onClose={() => showModal = false} title="Editar">
        ...contenido...
      </Modal>
    {/if}
-->
<script lang="ts">
	interface Props {
		onClose: () => void;
		title?: string;
		subtitle?: string;
		maxWidth?: number;
		dismissable?: boolean;
		children: import('svelte').Snippet;
	}
	let {
		onClose,
		title,
		subtitle,
		maxWidth = 480,
		dismissable = true,
		children,
	}: Props = $props();

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape' && dismissable) onClose();
	}

	// Teleport: mueve el nodo a document.body para escapar del stacking context
	// del .container (z-index:1), que quedaba por debajo del nav (z-index:100).
	function teleport(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() { node.remove(); }
		};
	}
</script>

<svelte:window onkeydown={onKey} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	use:teleport
	class="backdrop"
	onclick={(e) => { if (dismissable && e.target === e.currentTarget) onClose(); }}
	role="dialog"
	aria-modal="true"
	aria-label={title ?? 'Modal'}
>
	<div class="sheet" style="max-width:{maxWidth}px;">
		{#if title}
			<div class="head">
				<div>
					<div class="t">{title}</div>
					{#if subtitle}<div class="s">{subtitle}</div>{/if}
				</div>
				{#if dismissable}
					<button class="close" aria-label="Cerrar" onclick={onClose}>✕</button>
				{/if}
			</div>
		{/if}
		<div class="body">
			{@render children()}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.55);
		backdrop-filter: blur(8px);
		-webkit-backdrop-filter: blur(8px);
		z-index: 300;
		display: flex;
		align-items: flex-end;
		justify-content: center;
		padding: 0;
		animation: bd 0.18s ease;
	}
	@media (min-width: 600px) {
		.backdrop { align-items: center; padding: 1rem; }
	}
	.sheet {
		width: 100%;
		background: rgba(14, 16, 22, 0.88);
		backdrop-filter: var(--blur);
		-webkit-backdrop-filter: var(--blur);
		border: 1px solid var(--border);
		border-radius: var(--r-xl) var(--r-xl) 0 0;
		padding: 1rem 1.25rem 1.5rem;
		box-shadow: 0 -20px 60px -10px rgba(0, 0, 0, 0.8);
		max-height: 90dvh;
		overflow-y: auto;
		animation: up 0.26s cubic-bezier(0.22, 1, 0.36, 1);
	}
	@media (min-width: 600px) {
		.sheet { border-radius: var(--r-xl); animation: pop 0.2s cubic-bezier(0.22, 1, 0.36, 1); }
	}
	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
		margin-bottom: 1rem;
	}
	.t {
		font-size: 1.05rem;
		font-weight: 800;
		letter-spacing: -0.01em;
	}
	.s {
		font-size: 0.8rem;
		color: var(--text-muted);
		margin-top: 0.2rem;
	}
	.close {
		background: var(--surface2);
		color: var(--text-muted);
		border: 1px solid var(--border);
		box-shadow: none;
		font-size: 0.85rem;
		padding: 0.35rem 0.6rem;
		line-height: 1;
	}
	.close:hover { background: var(--surface-hover); color: var(--text); filter: none; }

	/* Grab handle on mobile */
	@media (max-width: 599px) {
		.sheet::before {
			content: '';
			display: block;
			width: 40px;
			height: 4px;
			border-radius: 2px;
			background: rgba(255, 255, 255, 0.2);
			margin: -0.5rem auto 0.75rem;
		}
	}

	@keyframes bd { from { opacity: 0; } to { opacity: 1; } }
	@keyframes up { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
	@keyframes pop { from { transform: scale(0.96); opacity: 0; } to { transform: scale(1); opacity: 1; } }
</style>
