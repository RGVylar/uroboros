<script lang="ts">
	import { CHANGELOG_VERSION, changelogMarkSeen } from '$lib/changelog';

	type ChangeType = 'nuevo' | 'mejora' | 'fix';
	interface Change { type: ChangeType; title: string; desc: string; }

	const CHANGES: Change[] = [
		{
			type: 'nuevo',
			title: 'Modo sin conexión',
			desc: 'El diario, el agua, la creatina y los suplementos funcionan aunque haya fútbol. Se sincronizan solos al volver la conexión.',
		},
		{
			type: 'nuevo',
			title: 'Producto manual sin conexión',
			desc: 'Puedes crear un producto con sus macros y añadirlo al diario aunque no haya servidor.',
		},
		{
			type: 'mejora',
			title: 'Detección de caída más rápida',
			desc: 'El aviso de sin conexión aparece en menos de 6 segundos en vez de quedarse cargando indefinidamente.',
		},
		{
			type: 'fix',
			title: 'Editar y borrar entradas offline',
			desc: 'Los cambios se aplican al instante en local y se envían al servidor cuando vuelva la conexión.',
		},
	];

	const BADGE: Record<ChangeType, { label: string; cls: string }> = {
		nuevo:  { label: 'Nuevo',  cls: 'badge-new' },
		mejora: { label: 'Mejora', cls: 'badge-mejora' },
		fix:    { label: 'Fix',    cls: 'badge-fix' },
	};

	let { onclose }: { onclose: () => void } = $props();

	function dismiss() {
		changelogMarkSeen();
		onclose();
	}
</script>

<!-- Backdrop -->
<div class="backdrop" role="presentation" onclick={dismiss}></div>

<!-- Sheet -->
<div class="sheet" role="dialog" aria-modal="true" aria-label="Novedades de la versión">
	<div class="handle"></div>

	<div class="header">
		<div class="icon">🐍</div>
		<div class="header-text">
			<div class="eyebrow">Novedades</div>
			<div class="version-title">Versión {CHANGELOG_VERSION}</div>
		</div>
	</div>

	<div class="changes">
		{#each CHANGES as c}
			<div class="change">
				<span class="badge {BADGE[c.type].cls}">{BADGE[c.type].label}</span>
				<div class="change-text">
					<div class="change-title">{c.title}</div>
					<div class="change-desc">{c.desc}</div>
				</div>
			</div>
		{/each}
	</div>

	<div class="divider"></div>

	<div class="footer">
		<button class="btn-primary" onclick={dismiss}>¡Entendido!</button>
	</div>
</div>

<style>
	.backdrop {
		position: fixed; inset: 0; z-index: 900;
		background: rgba(0,0,0,0.55);
		backdrop-filter: blur(6px);
		-webkit-backdrop-filter: blur(6px);
	}

	.sheet {
		position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
		z-index: 901;
		width: 100%; max-width: 480px;
		background: oklch(16% 0.025 260);
		border: 1px solid rgba(255,255,255,0.1);
		border-bottom: none;
		border-radius: 24px 24px 0 0;
		padding: 0 0 2rem;
		animation: slide-up 0.32s cubic-bezier(0.34, 1.3, 0.64, 1);
	}
	@keyframes slide-up {
		from { transform: translateX(-50%) translateY(100%); opacity: 0; }
		to   { transform: translateX(-50%) translateY(0);    opacity: 1; }
	}

	.handle {
		width: 36px; height: 4px; border-radius: 99px;
		background: rgba(255,255,255,0.15);
		margin: 12px auto 0;
	}

	.header {
		padding: 1.25rem 1.5rem 0;
		display: flex; align-items: center; gap: 1rem;
	}
	.icon {
		width: 48px; height: 48px; border-radius: 14px; flex-shrink: 0;
		background: linear-gradient(135deg, oklch(75% 0.18 160 / 0.3), oklch(55% 0.2 200 / 0.15));
		border: 1px solid oklch(72% 0.18 160 / 0.3);
		display: flex; align-items: center; justify-content: center;
		font-size: 1.5rem;
	}
	.eyebrow {
		font-size: 0.625rem; letter-spacing: 0.12em; text-transform: uppercase;
		color: oklch(72% 0.18 160); font-weight: 700; margin-bottom: 0.2rem;
	}
	.version-title {
		font-size: 1.2rem; font-weight: 800; color: #fff; letter-spacing: -0.02em;
	}

	.changes {
		padding: 1.25rem 1.5rem 0;
		display: flex; flex-direction: column; gap: 0.75rem;
	}
	.change {
		display: flex; gap: 0.75rem; align-items: flex-start;
	}
	.badge {
		flex-shrink: 0; margin-top: 1px;
		font-size: 0.6rem; font-weight: 800; letter-spacing: 0.04em;
		padding: 0.2rem 0.45rem; border-radius: 99px; text-transform: uppercase;
	}
	.badge-new    { background: oklch(72% 0.18 160 / 0.18); border: 1px solid oklch(72% 0.18 160 / 0.35); color: oklch(82% 0.16 160); }
	.badge-mejora { background: oklch(72% 0.16 260 / 0.15); border: 1px solid oklch(72% 0.16 260 / 0.3);  color: oklch(82% 0.14 260); }
	.badge-fix    { background: oklch(72% 0.18 55  / 0.15); border: 1px solid oklch(72% 0.18 55  / 0.3);  color: oklch(82% 0.15 55);  }

	.change-title { font-size: 0.875rem; font-weight: 700; color: #fff; }
	.change-desc  { font-size: 0.75rem; color: rgba(255,255,255,0.45); margin-top: 0.15rem; line-height: 1.4; }

	.divider { height: 1px; background: rgba(255,255,255,0.06); margin: 1.25rem 1.5rem 0; }

	.footer { padding: 1.25rem 1.5rem 0; }
	.btn-primary {
		width: 100%; padding: 0.875rem; border-radius: 14px; border: none;
		background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
		color: #041010; font-family: inherit; font-weight: 800; font-size: 0.9375rem;
		cursor: pointer; letter-spacing: -0.01em;
	}
</style>
