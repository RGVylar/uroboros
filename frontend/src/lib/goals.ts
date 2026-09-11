import type { Goals } from './types';

// Objetivos del día ajustados por el ejercicio registrado. Es la misma regla
// que pinta el diario: en 'proportional' todo sube en la misma proporción que
// las kcal; en 'performance' las kcal quemadas van íntegras a carbohidratos.
// Con 'off' (o sin ejercicio) devuelve los objetivos tal cual.
export function adjustGoalsForExercise(goals: Goals, burned: number): Goals {
	const mode = goals.macro_adjust_mode ?? 'off';
	if (burned <= 0 || mode === 'off') return goals;

	if (mode === 'proportional') {
		const ratio = (goals.kcal + burned) / goals.kcal;
		return {
			...goals,
			kcal:    goals.kcal + burned,
			protein: Math.round(goals.protein * ratio * 10) / 10,
			carbs:   Math.round(goals.carbs   * ratio * 10) / 10,
			fat:     Math.round(goals.fat     * ratio * 10) / 10,
		};
	}

	if (mode === 'performance') {
		const extraCarbs = burned / 4;
		return {
			...goals,
			kcal:  goals.kcal + burned,
			carbs: Math.round((goals.carbs + extraCarbs) * 10) / 10,
			// protein and fat stay fixed
		};
	}

	return goals;
}
