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

// Puntuación 0–100 de un día registrado: la misma regla que el duelo y el
// ranking (backend/app/services/duel_service.py → day_score). 70 puntos por
// kcal (completos a ±100 del objetivo, a 0 a ±500, simétrico) y 30 por llegar
// a la proteína.
export const HIT_SCORE = 50;
export function dayScore(kcal: number, protein: number, goals: Goals, burned: number): number {
	if (!goals.kcal) return 100;
	const g = adjustGoalsForExercise(goals, burned);
	const over = Math.max(0, Math.abs(kcal - g.kcal) - 100);
	const kcalPts = Math.round(70 * Math.max(0, 1 - over / 400));
	const protPts = g.protein > 0 ? Math.round(30 * Math.min(1, protein / g.protein)) : 30;
	return kcalPts + protPts;
}
