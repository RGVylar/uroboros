<!--
  RecipeCardEditor.svelte
  La "ficha de cocina" de una receta: raciones, tiempos y pasos numerados.
  Se usa igual al crear y al editar; el padre enlaza los cuatro valores.

  Pegar un texto de varias líneas en un paso lo trocea en varios pasos: así se
  puede traer una receta copiada de otro sitio de un golpe.
-->
<script lang="ts">
	import { t } from '$lib/i18n/index.svelte';

	interface Props {
		steps: string[];
		servings: number | null;
		prepMinutes: number | null;
		cookMinutes: number | null;
		idPrefix: string;
	}
	let {
		steps = $bindable(),
		servings = $bindable(),
		prepMinutes = $bindable(),
		cookMinutes = $bindable(),
		idPrefix,
	}: Props = $props();

	function addStep() {
		steps = [...steps, ''];
	}

	function removeStep(idx: number) {
		steps = steps.filter((_, i) => i !== idx);
	}

	function moveStep(idx: number, dir: -1 | 1) {
		const to = idx + dir;
		if (to < 0 || to >= steps.length) return;
		const next = [...steps];
		[next[idx], next[to]] = [next[to], next[idx]];
		steps = next;
	}

	function onPaste(e: ClipboardEvent, idx: number) {
		const text = e.clipboardData?.getData('text') ?? '';
		const lines = text
			.split(/\r?\n/)
			// Quita la numeración que suelen traer las recetas copiadas ("1.", "2)", "- ").
			.map((l) => l.replace(/^\s*(?:\d+\s*[.)-]|[-•*])\s*/, '').trim())
			.filter(Boolean);
		if (lines.length < 2) return;
		e.preventDefault();
		const current = steps[idx].trim();
		const head = current ? [current, ...lines] : lines;
		steps = [...steps.slice(0, idx), ...head, ...steps.slice(idx + 1)];
	}
</script>

<div class="card-editor">
	<div class="meta-grid">
		<div class="form-group">
			<label for="{idPrefix}-servings">{t('recipes.servings')}</label>
			<input id="{idPrefix}-servings" type="number" min="1" max="100" step="1" inputmode="numeric" bind:value={servings} placeholder="—" />
		</div>
		<div class="form-group">
			<label for="{idPrefix}-prep">{t('recipes.prepMinutes')}</label>
			<input id="{idPrefix}-prep" type="number" min="0" step="1" inputmode="numeric" bind:value={prepMinutes} placeholder="min" />
		</div>
		<div class="form-group">
			<label for="{idPrefix}-cook">{t('recipes.cookMinutes')}</label>
			<input id="{idPrefix}-cook" type="number" min="0" step="1" inputmode="numeric" bind:value={cookMinutes} placeholder="min" />
		</div>
	</div>

	<div class="steps-label">{t('recipes.steps')}</div>
	{#each steps as _, idx (idx)}
		<div class="step-row">
			<span class="step-num">{idx + 1}</span>
			<textarea
				rows="2"
				bind:value={steps[idx]}
				onpaste={(e) => onPaste(e, idx)}
				placeholder={t('recipes.stepPlaceholder')}
				aria-label={t('recipes.stepAria', { n: idx + 1 })}
			></textarea>
			<div class="step-actions">
				<button type="button" class="mini" onclick={() => moveStep(idx, -1)} disabled={idx === 0} aria-label={t('recipes.stepUp')}>↑</button>
				<button type="button" class="mini" onclick={() => moveStep(idx, 1)} disabled={idx === steps.length - 1} aria-label={t('recipes.stepDown')}>↓</button>
				<button type="button" class="mini mini-danger" onclick={() => removeStep(idx)} aria-label={t('recipes.stepRemove')}>✕</button>
			</div>
		</div>
	{/each}
	<button type="button" class="add-step" onclick={addStep}>{t('recipes.addStep')}</button>
	{#if steps.length === 0}
		<div class="hint">{t('recipes.stepsHint')}</div>
	{/if}
</div>

<style>
	.card-editor {
		margin-top: 0.75rem;
	}
	.meta-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0.5rem;
		/* Las etiquetas largas ("Preparación (min)") parten en dos líneas: los
		   campos se alinean por abajo para que no queden a distinta altura. */
		align-items: end;
	}
	.meta-grid input {
		width: 100%;
	}
	.meta-grid label {
		font-size: 0.72rem;
	}
	.steps-label {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--text-muted);
		margin: 0.25rem 0 0.4rem;
	}
	.step-row {
		display: flex;
		gap: 0.5rem;
		align-items: flex-start;
		margin-bottom: 0.5rem;
	}
	.step-num {
		flex-shrink: 0;
		width: 1.6rem;
		height: 1.6rem;
		margin-top: 0.3rem;
		border-radius: 50%;
		display: grid;
		place-items: center;
		font-size: 0.75rem;
		font-weight: 800;
		background: oklch(75% 0.18 160 / 0.18);
		color: oklch(85% 0.15 160);
	}
	textarea {
		flex: 1;
		min-width: 0;
		resize: vertical;
		/* Crece con el texto donde se soporta; si no, se queda en 2 filas y scroll. */
		field-sizing: content;
		min-height: 2.6rem;
		font-family: inherit;
		font-size: 0.85rem;
	}
	.step-actions {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}
	.mini {
		padding: 0.1rem 0.4rem;
		font-size: 0.7rem;
		line-height: 1.2;
		background: rgba(255, 255, 255, 0.06);
		color: rgba(255, 255, 255, 0.7);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		cursor: pointer;
	}
	.mini:disabled {
		opacity: 0.3;
		cursor: default;
	}
	.mini-danger {
		color: oklch(75% 0.17 25);
	}
	.add-step {
		width: 100%;
		font-size: 0.8rem;
		padding: 0.45rem;
		background: rgba(255, 255, 255, 0.05);
		color: rgba(255, 255, 255, 0.75);
		border: 1px dashed rgba(255, 255, 255, 0.2);
		border-radius: 10px;
		cursor: pointer;
		font-family: inherit;
	}
	.hint {
		font-size: 0.72rem;
		color: var(--text-muted);
		margin-top: 0.3rem;
	}
</style>
