<!--
  Módulos: qué partes de la app ve cada usuario. Apagar uno lo quita del
  diario, de la navegación y de Ajustes; los datos se quedan donde estaban.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth.svelte';
	import { modules, type ModuleKey } from '$lib/stores/modules.svelte';
	import { subscription } from '$lib/stores/subscription.svelte';
	import { toast } from '$lib/stores/toast.svelte';
	import Aurora from '$lib/components/uro/Aurora.svelte';
	import ScreenHeader from '$lib/components/uro/ScreenHeader.svelte';
	import { t } from '$lib/i18n/index.svelte';

	if (!auth.isLoggedIn) goto('/login');

	type Item = { key: ModuleKey; icon: string; pro?: boolean };

	// `pro` solo en lo que el servidor no deja *encender* sin Premium. Medidas y
	// ejercicio son de pago al entrar, pero enseñarlos o no es libre.
	const GROUPS: { label: 'modules.group.tracking' | 'modules.group.home' | 'modules.group.extras'; items: Item[] }[] = [
		{
			label: 'modules.group.tracking',
			items: [
				{ key: 'water', icon: '💧' },
				{ key: 'weight', icon: '⚖️' },
				{ key: 'measurements', icon: '📏' },
				{ key: 'exercise', icon: '💪' },
				{ key: 'supplements', icon: '💊' },
				{ key: 'creatine', icon: '🧪' },
				{ key: 'mood', icon: '🫥' },
			],
		},
		{ label: 'modules.group.home', items: [{ key: 'inventory', icon: '🏠' }] },
		{ label: 'modules.group.extras', items: [{ key: 'cheat_days', icon: '🍕', pro: true }] },
	];

	let busy = $state<ModuleKey | null>(null);

	async function toggle(key: ModuleKey) {
		if (busy) return;
		busy = key;
		try {
			await modules.set(key, !modules.on(key));
		} catch {
			toast.error(t('settings.errSaveConfig'));
		} finally {
			busy = null;
		}
	}
</script>

<Aurora />

<div class="page">
	<ScreenHeader title={t('modules.title')} sub={t('modules.sub')} onBack={() => goto('/settings')} />

	{#each GROUPS as group}
		<div class="group-label">{t(group.label)}</div>
		<div class="group">
			{#each group.items as item, i (item.key)}
				{@const on = modules.on(item.key)}
				{@const locked = item.pro && !on && !subscription.is_premium}
				{#if i > 0}<div class="divider"></div>{/if}
				<div class="row">
					<div class="icon" class:on>{item.icon}</div>
					<div class="texts">
						<div class="name">{t(`modules.${item.key}`)}</div>
						<div class="desc">{t(`modules.${item.key}.desc`)}</div>
					</div>
					{#if locked}
						<!-- El servidor rechaza encenderlo sin Premium (402) -->
						<button class="pro" onclick={() => goto('/premium')}>PRO</button>
					{:else}
						<button
							class="switch"
							class:on
							onclick={() => toggle(item.key)}
							disabled={busy === item.key}
							aria-label={t(`modules.${item.key}`)}
							aria-pressed={on}
						>
							<span class="knob"></span>
						</button>
					{/if}
				</div>
			{/each}
		</div>
	{/each}

	<p class="foot">{t('modules.foot')}</p>
</div>

<style>
	.page {
		position: relative;
		z-index: 1;
		max-width: 560px;
		margin: 0 auto;
		padding: 8px 16px 120px;
	}
	.group-label {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: rgba(255, 255, 255, 0.45);
		margin: 18px 4px 8px;
	}
	.group {
		border-radius: 18px;
		background: rgba(255, 255, 255, 0.05);
		backdrop-filter: blur(24px) saturate(160%);
		-webkit-backdrop-filter: blur(24px) saturate(160%);
		border: 1px solid rgba(255, 255, 255, 0.09);
		overflow: hidden;
	}
	.divider { height: 1px; background: rgba(255, 255, 255, 0.06); margin-left: 62px; }
	.row { display: flex; align-items: center; gap: 12px; padding: 12px 14px; }
	.icon {
		width: 36px; height: 36px; border-radius: 12px;
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.08);
		display: flex; align-items: center; justify-content: center;
		font-size: 16px;
		flex-shrink: 0;
		opacity: 0.6;
		transition: all 0.15s;
	}
	.icon.on {
		opacity: 1;
		background: linear-gradient(135deg, oklch(78% 0.18 165 / 0.3), oklch(60% 0.2 200 / 0.15));
		border-color: oklch(75% 0.18 165 / 0.35);
	}
	.texts { flex: 1; min-width: 0; color: #fff; }
	.name { font-size: 13px; font-weight: 700; }
	.desc { font-size: 11px; color: rgba(255, 255, 255, 0.5); margin-top: 2px; line-height: 1.35; }

	.switch {
		width: 40px; height: 24px; border-radius: 99px;
		position: relative; flex-shrink: 0;
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.1);
		box-shadow: none;
		cursor: pointer;
		padding: 0;
	}
	.switch.on {
		background: oklch(75% 0.18 165 / 0.35);
		border-color: oklch(80% 0.17 165 / 0.5);
	}
	.knob {
		position: absolute; top: 2px; left: 2px;
		width: 18px; height: 18px; border-radius: 50%;
		background: #d0d4d8;
		box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
		transition: all 0.15s;
	}
	.switch.on .knob {
		left: 18px;
		background: linear-gradient(135deg, #fff, oklch(85% 0.1 165));
	}
	.pro {
		flex-shrink: 0;
		padding: 4px 10px;
		border-radius: 99px;
		border: none;
		box-shadow: none;
		font: inherit;
		font-size: 10px;
		font-weight: 800;
		letter-spacing: 0.05em;
		color: #1a1a1a;
		background: linear-gradient(135deg, oklch(88% 0.15 85), oklch(78% 0.17 60));
		cursor: pointer;
	}
	.foot {
		font-size: 11px;
		color: rgba(255, 255, 255, 0.45);
		text-align: center;
		margin: 18px 12px 0;
		line-height: 1.45;
	}
</style>
