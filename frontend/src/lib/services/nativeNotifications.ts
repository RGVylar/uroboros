/**
 * Local notifications for the native Android/iOS app.
 * Schedules daily reminders based on the user's notification prefs (stored on the server).
 * No Firebase, no external service — everything runs on the device.
 */

import { api } from '$lib/api';
import { t } from '$lib/i18n/index.svelte';
import { reportDiagnostic } from '$lib/services/diagnostics';

interface NotifPrefs {
	enabled: boolean;
	breakfast_on: boolean; breakfast_time: string;
	lunch_on: boolean;     lunch_time: string;
	dinner_on: boolean;    dinner_time: string;
	water_on: boolean;     water_time: string;
	streak_on: boolean;    streak_time: string;
	summary_on: boolean;   summary_time: string;
}

// Fixed IDs so we can cancel + replace them cleanly
const IDS = {
	breakfast: 10,
	lunch:     11,
	dinner:    12,
	water:     13,
	streak:    14,
	summary:   15,
} as const;

/** Next Date when clock reaches HH:MM (today if still in the future, otherwise tomorrow). */
function nextAt(hhmm: string): Date {
	const [h, m] = hhmm.split(':').map(Number);
	const d = new Date();
	d.setSeconds(0, 0);
	d.setHours(h, m);
	if (d.getTime() <= Date.now()) d.setDate(d.getDate() + 1);
	return d;
}

/**
 * Request permission, fetch prefs, cancel old notifications and schedule fresh ones.
 * Call this on login and whenever prefs change.
 */
export async function scheduleNativeNotifications(): Promise<boolean> {
	try {
		const { LocalNotifications } = await import('@capacitor/local-notifications');

		const perm = await LocalNotifications.requestPermissions();
		if (perm.display !== 'granted') {
			reportDiagnostic('notifications', 'denied', { permission: perm.display });
			return false;
		}

		// Cancel all previously scheduled ones first
		await LocalNotifications.cancel({
			notifications: Object.values(IDS).map((id) => ({ id })),
		});

		const prefs = await api.get<NotifPrefs>('/push/prefs').catch(() => null);
		if (!prefs?.enabled) {
			// permission granted but user disabled notifs
			reportDiagnostic('notifications', prefs ? 'off' : 'prefs_error', { permission: perm.display });
			return true;
		}

		const notifications: Parameters<typeof LocalNotifications.schedule>[0]['notifications'] = [];

		const add = (id: number, title: string, body: string, hhmm: string) => {
			notifications.push({
				id,
				title,
				body,
				schedule: { at: nextAt(hhmm), repeats: true, every: 'day' },
				smallIcon: 'ic_stat_icon',
				sound: undefined,
				actionTypeId: '',
				extra: null,
			});
		};

		// Se programan con el idioma activo al llamar a esta función. Como se
		// reprograman al tocar cualquier preferencia de notificaciones, cambiar
		// de idioma en Ajustes también las regenera.
		if (prefs.breakfast_on) add(IDS.breakfast, t('notif.breakfast.title'), t('notif.breakfast.body'), prefs.breakfast_time);
		if (prefs.lunch_on)     add(IDS.lunch,     t('notif.lunch.title'),     t('notif.lunch.body'),     prefs.lunch_time);
		if (prefs.dinner_on)    add(IDS.dinner,    t('notif.dinner.title'),    t('notif.dinner.body'),    prefs.dinner_time);
		if (prefs.water_on)     add(IDS.water,     t('notif.water.title'),     t('notif.water.body'),     prefs.water_time);
		if (prefs.streak_on)    add(IDS.streak,    t('notif.streak.title'),    t('notif.streak.body'),    prefs.streak_time);
		if (prefs.summary_on)   add(IDS.summary,   t('notif.summary.title'),   t('notif.summary.body'),   prefs.summary_time);

		if (notifications.length > 0) {
			await LocalNotifications.schedule({ notifications });
		}

		// Comprobar que de verdad han quedado en cola, y si Android deja usar
		// alarmas exactas (sin ese permiso llegan con retraso o agrupadas).
		const { notifications: pending } = await LocalNotifications.getPending();
		const queued = pending.filter((n) => (Object.values(IDS) as number[]).includes(n.id)).length;
		const exact = await LocalNotifications.checkExactNotificationSetting()
			.then((r) => r.exact_alarm)
			.catch(() => 'unknown');
		reportDiagnostic('notifications', queued === notifications.length ? 'ok' : 'not_queued', {
			permission: perm.display,
			wanted: notifications.length,
			queued,
			exact_alarm: exact,
		});

		return true;
	} catch (e) {
		console.error('[nativeNotifications] schedule failed', e);
		reportDiagnostic('notifications', 'error', { error: e instanceof Error ? e.message : String(e) });
		return false;
	}
}

export interface NotifDiag {
	permission: string;
	exactAlarm: string;
	queued: number;
	serverEnabled: boolean | null;
}

/** Estado actual de los recordatorios, para Ajustes → Diagnóstico. */
export async function diagnoseNativeNotifications(): Promise<NotifDiag> {
	const { LocalNotifications } = await import('@capacitor/local-notifications');
	const perm = await LocalNotifications.checkPermissions();
	const exact = await LocalNotifications.checkExactNotificationSetting()
		.then((r) => r.exact_alarm as string)
		.catch(() => 'unknown');
	const { notifications: pending } = await LocalNotifications.getPending();
	const prefs = await api.get<NotifPrefs>('/push/prefs').catch(() => null);
	const d: NotifDiag = {
		permission: perm.display,
		exactAlarm: exact,
		queued: pending.filter((n) => (Object.values(IDS) as number[]).includes(n.id)).length,
		serverEnabled: prefs ? prefs.enabled : null,
	};
	reportDiagnostic(
		'notifications',
		d.permission !== 'granted' ? 'denied' : d.serverEnabled === false ? 'off' : d.queued ? 'ok' : 'not_queued',
		{ permission: d.permission, exact_alarm: d.exactAlarm, queued: d.queued, server_enabled: d.serverEnabled },
		true,
	);
	return d;
}

/** Cancel all scheduled local notifications (call on logout or when user disables notifs). */
export async function cancelNativeNotifications(): Promise<void> {
	try {
		const { LocalNotifications } = await import('@capacitor/local-notifications');
		await LocalNotifications.cancel({
			notifications: Object.values(IDS).map((id) => ({ id })),
		});
	} catch (e) {
		console.error('[nativeNotifications] cancel failed', e);
	}
}

/** Fire a test notification immediately (1 second delay). */
export async function testNativeNotification(): Promise<void> {
	try {
		const { LocalNotifications } = await import('@capacitor/local-notifications');
		const at = new Date(Date.now() + 1000);
		await LocalNotifications.schedule({
			notifications: [{
				id: 99,
				title: '🔔 uroboros',
				body: t('notif.test.body'),
				schedule: { at },
				smallIcon: 'ic_stat_icon',
				sound: undefined,
				actionTypeId: '',
				extra: null,
			}],
		});
	} catch (e) {
		console.error('[nativeNotifications] test failed', e);
	}
}
