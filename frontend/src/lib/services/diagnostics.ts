/**
 * Diagnóstico de lo que solo existe en la APK (pasos de Health Connect,
 * recordatorios locales). El fallo pasa dentro del móvil y no deja rastro en
 * el servidor, así que la app manda en qué punto se quedó a /diagnostics, que
 * lo reenvía al Telegram de admin.
 *
 * Solo se manda cuando el resultado cambia respecto al último mandado desde
 * este móvil: cada mensaje en Telegram es un cambio de estado, no ruido.
 */
import { Capacitor } from '@capacitor/core';
import { api } from '$lib/api';
import { APP_VERSION } from '$lib/changelog';

export type DiagKind = 'health' | 'notifications';
export type DiagData = Record<string, string | number | boolean | null>;

const LS_PREFIX = 'uro_diag_';

function readLast(kind: DiagKind): string | null {
	try {
		return localStorage.getItem(LS_PREFIX + kind);
	} catch {
		return null;
	}
}

function writeLast(kind: DiagKind, outcome: string) {
	try {
		localStorage.setItem(LS_PREFIX + kind, outcome);
	} catch {}
}

function platform(): string {
	const native = Capacitor.getPlatform();
	if (native !== 'web') return native;
	return window.matchMedia('(display-mode: standalone)').matches ? 'pwa' : 'web';
}

/**
 * Fire-and-forget: un diagnóstico que no llega no debe romper nada.
 * @param force mandarlo aunque no haya cambiado; solo para acciones de la persona.
 */
export function reportDiagnostic(kind: DiagKind, outcome: string, data: DiagData, force = false) {
	const previous = readLast(kind);
	if (!force && previous === outcome) return;
	api
		// manual: lo ha provocado la persona (pulsar un interruptor o Diagnóstico).
		.post('/diagnostics', { kind, outcome, previous, manual: force, app_version: APP_VERSION, platform: platform(), data })
		// Solo se da por mandado si llegó: si no, se reintenta la próxima vez.
		.then(() => writeLast(kind, outcome))
		.catch(() => {});
}
