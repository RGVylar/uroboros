// Pasos desde Health Connect (solo la APK de Android).
//
// La web no puede leer la app de salud del móvil (ni Apple Health ni Health
// Connect), así que todo esto se apaga fuera de la APK: `supported` es false y
// ninguna llamada toca el plugin. En la APK el usuario lo activa en Ajustes;
// desde ahí, cada vez que la app arranca o vuelve a primer plano se suben los
// totales diarios de la última semana a /steps (idempotente en el backend).
import { Capacitor } from '@capacitor/core';
import { api } from '$lib/api';

const LS_KEY = 'uro_health_steps';
const SYNC_DAYS = 7;
// Volver a la app cada pocos segundos no debe disparar una consulta cada vez.
const MIN_SYNC_INTERVAL_MS = 5 * 60 * 1000;

export type ConnectResult = 'ok' | 'denied' | 'unavailable' | 'error';

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
	private lastSyncAt = 0;

	async connect(): Promise<ConnectResult> {
		if (!this.supported) return 'unavailable';
		try {
			const Health = await plugin();
			const { available } = await Health.isAvailable();
			if (!available) return 'unavailable';
			const status = await Health.requestAuthorization({ read: ['steps'] });
			if (!status.readAuthorized.includes('steps')) return 'denied';
			this.enabled = true;
			writeEnabled(true);
			await this.sync(true);
			return 'ok';
		} catch (e) {
			this.lastError = e instanceof Error ? e.message : String(e);
			return 'error';
		}
	}

	disconnect() {
		this.enabled = false;
		writeEnabled(false);
	}

	/** Abre Health Connect para que el usuario revise o retire el permiso. */
	async openSettings() {
		if (!this.supported) return;
		const Health = await plugin();
		await Health.openHealthConnectSettings();
	}

	async sync(force = false): Promise<void> {
		if (!this.enabled || this.syncing) return;
		if (!force && Date.now() - this.lastSyncAt < MIN_SYNC_INTERVAL_MS) return;
		this.syncing = true;
		try {
			const Health = await plugin();
			// Si el permiso se retiró desde Health Connect, no insistimos: se
			// queda activado aquí pero sin leer hasta que se vuelva a conceder.
			const status = await Health.checkAuthorization({ read: ['steps'] });
			if (!status.readAuthorized.includes('steps')) {
				this.lastError = 'denied';
				return;
			}
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
				await api.put('/steps', { days });
				this.version++;
			}
			this.lastSyncAt = Date.now();
			this.lastError = null;
		} catch (e) {
			this.lastError = e instanceof Error ? e.message : String(e);
		} finally {
			this.syncing = false;
		}
	}
}

export const health = new HealthStore();
