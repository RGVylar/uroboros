// Pasos desde Health Connect (solo la APK de Android).
//
// La web no puede leer la app de salud del móvil (ni Apple Health ni Health
// Connect), así que todo esto se apaga fuera de la APK: `supported` es false y
// ninguna llamada toca el plugin. En la APK el usuario lo activa en Ajustes;
// desde ahí, cada vez que la app arranca o vuelve a primer plano se suben los
// totales diarios de la última semana a /steps (idempotente en el backend).
import { Capacitor } from '@capacitor/core';
import { api } from '$lib/api';
import { reportDiagnostic, type DiagData } from '$lib/services/diagnostics';

const LS_KEY = 'uro_health_steps';
const SYNC_DAYS = 7;
// Volver a la app cada pocos segundos no debe disparar una consulta cada vez.
const MIN_SYNC_INTERVAL_MS = 5 * 60 * 1000;

export type ConnectResult = 'ok' | 'denied' | 'unavailable' | 'error';

/**
 * Qué ha pasado en la última conexión o sincronización. Lo ve la persona en
 * Ajustes → Diagnóstico y llega a Telegram cuando cambia. Sin valores de
 * pasos: solo datos técnicos, que Telegram está fuera de la UE.
 */
export interface HealthDiag {
	/** 'ok' | 'no_data' | 'denied' | 'unavailable' | 'error' | 'off' */
	outcome: string;
	/** En qué paso se quedó: availability, permission, query, upload. */
	stage: string;
	available: boolean | null;
	reason: string | null;
	authorized: boolean | null;
	/** Días de la última semana con algún paso en Health Connect. */
	daysWithSteps: number | null;
	error: string | null;
	at: string;
}

function readEnabled(): boolean {
	try {
		return localStorage.getItem(LS_KEY) === '1';
	} catch {
		return false;
	}
}

function writeEnabled(on: boolean) {
	try {
		if (on) localStorage.setItem(LS_KEY, '1');
		else localStorage.removeItem(LS_KEY);
	} catch {}
}

/** YYYY-MM-DD en hora local: los pasos son "del día" tal como lo vive el usuario. */
function localDay(d: Date): string {
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function plugin() {
	const { Health } = await import('@capgo/capacitor-health');
	return Health;
}

class HealthStore {
	readonly supported = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android';
	enabled = $state(this.supported && readEnabled());
	syncing = $state(false);
	/** Sube cada vez que una sincronización guarda algo: la portada lo escucha para recargar. */
	version = $state(0);
	lastError = $state<string | null>(null);
	diag = $state<HealthDiag | null>(null);
	private lastSyncAt = 0;

	/** Apunta el resultado y lo manda a Telegram si cambia (o siempre, con force). */
	private record(d: Omit<HealthDiag, 'at'>, force = false) {
		this.diag = { ...d, at: new Date().toISOString() };
		const data: DiagData = {
			stage: d.stage,
			enabled: this.enabled,
			available: d.available,
			reason: d.reason,
			authorized: d.authorized,
			days_with_steps: d.daysWithSteps,
			error: d.error,
		};
		reportDiagnostic('health', d.outcome, data, force);
	}

	async connect(): Promise<ConnectResult> {
		if (!this.supported) return 'unavailable';
		const base = { available: null, reason: null, authorized: null, daysWithSteps: null, error: null };
		let stage = 'availability';
		try {
			const Health = await plugin();
			const { available, reason } = await Health.isAvailable();
			if (!available) {
				this.record({ ...base, outcome: 'unavailable', stage, available, reason: reason ?? null }, true);
				return 'unavailable';
			}
			stage = 'permission';
			const status = await Health.requestAuthorization({ read: ['steps'] });
			if (!status.readAuthorized.includes('steps')) {
				this.record({ ...base, outcome: 'denied', stage, available, authorized: false }, true);
				return 'denied';
			}
			this.enabled = true;
			writeEnabled(true);
			// sync() apunta el resultado final (ok / no_data / error).
			await this.sync(true, true);
			return 'ok';
		} catch (e) {
			this.lastError = e instanceof Error ? e.message : String(e);
			this.record({ ...base, outcome: 'error', stage, error: this.lastError }, true);
			return 'error';
		}
	}

	disconnect() {
		this.enabled = false;
		writeEnabled(false);
	}

	/**
	 * Para Ajustes → Diagnóstico: comprueba el estado ahora mismo y, si está
	 * activado, sincroniza; manda el resultado aunque no haya cambiado.
	 */
	async diagnose(): Promise<void> {
		if (!this.supported) return;
		if (this.enabled) return this.sync(true, true);
		const base = { authorized: null, daysWithSteps: null, error: null };
		try {
			const Health = await plugin();
			const { available, reason } = await Health.isAvailable();
			this.record({ ...base, outcome: available ? 'off' : 'unavailable', stage: 'availability', available, reason: reason ?? null }, true);
		} catch (e) {
			const error = e instanceof Error ? e.message : String(e);
			this.record({ ...base, outcome: 'error', stage: 'availability', available: null, reason: null, error }, true);
		}
	}

	/** Abre Health Connect para que el usuario revise o retire el permiso. */
	async openSettings() {
		if (!this.supported) return;
		const Health = await plugin();
		await Health.openHealthConnectSettings();
	}

	/** @param report true = mandar el diagnóstico aunque no haya cambiado. */
	async sync(force = false, report = false): Promise<void> {
		if (!this.enabled || this.syncing) return;
		if (!force && Date.now() - this.lastSyncAt < MIN_SYNC_INTERVAL_MS) return;
		this.syncing = true;
		const base = { available: true, reason: null, daysWithSteps: null, error: null };
		let stage = 'permission';
		try {
			const Health = await plugin();
			// Si el permiso se retiró desde Health Connect, no insistimos: se
			// queda activado aquí pero sin leer hasta que se vuelva a conceder.
			const status = await Health.checkAuthorization({ read: ['steps'] });
			if (!status.readAuthorized.includes('steps')) {
				this.lastError = 'denied';
				this.record({ ...base, outcome: 'denied', stage, authorized: false }, report);
				return;
			}
			stage = 'query';
			const start = new Date();
			start.setHours(0, 0, 0, 0);
			start.setDate(start.getDate() - (SYNC_DAYS - 1));
			const { samples } = await Health.queryAggregated({
				dataType: 'steps',
				startDate: start.toISOString(),
				endDate: new Date().toISOString(),
				bucket: 'day',
				aggregation: 'sum',
			});
			const days = samples
				.filter((s) => s.value > 0)
				.map((s) => ({ day: localDay(new Date(s.startDate)), steps: Math.round(s.value) }));
			if (days.length) {
				stage = 'upload';
				await api.put('/steps', { days });
				this.version++;
			}
			this.lastSyncAt = Date.now();
			this.lastError = null;
			// Sin un solo paso en una semana casi seguro que ninguna app (Samsung
			// Health, Google Fit…) está escribiendo en Health Connect.
			this.record(
				{ ...base, outcome: days.length ? 'ok' : 'no_data', stage, authorized: true, daysWithSteps: days.length },
				report,
			);
		} catch (e) {
			this.lastError = e instanceof Error ? e.message : String(e);
			this.record({ ...base, outcome: 'error', stage, authorized: null, error: this.lastError }, report);
		} finally {
			this.syncing = false;
		}
	}
}

export const health = new HealthStore();
