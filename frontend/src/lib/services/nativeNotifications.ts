/**
 * Local notifications for the native Android/iOS app.
 * Schedules daily reminders based on the user's notification prefs (stored on the server).
 * No Firebase, no external service — everything runs on the device.
 */

import { api } from '$lib/api';

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
		if (perm.display !== 'granted') return false;

		// Cancel all previously scheduled ones first
		await LocalNotifications.cancel({
			notifications: Object.values(IDS).map((id) => ({ id })),
		});

		const prefs = await api.get<NotifPrefs>('/push/prefs').catch(() => null);
		if (!prefs?.enabled) return true; // permission granted but user disabled notifs

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

		if (prefs.breakfast_on) add(IDS.breakfast, '🍳 Desayuno', '¿Has registrado el desayuno?',   prefs.breakfast_time);
		if (prefs.lunch_on)     add(IDS.lunch,     '🥗 Almuerzo', '¿Has registrado el almuerzo?',   prefs.lunch_time);
		if (prefs.dinner_on)    add(IDS.dinner,    '🍽 Cena',     '¿Has registrado la cena?',       prefs.dinner_time);
		if (prefs.water_on)     add(IDS.water,     '💧 Agua',     '¿Estás bebiendo suficiente agua?', prefs.water_time);
		if (prefs.streak_on)    add(IDS.streak,    '🔥 Racha',    '¡No pierdas tu racha! Registra algo hoy.', prefs.streak_time);
		if (prefs.summary_on)   add(IDS.summary,   '📊 Resumen',  'Revisa tu progreso de hoy.',     prefs.summary_time);

		if (notifications.length > 0) {
			await LocalNotifications.schedule({ notifications });
		}

		return true;
	} catch (e) {
		console.error('[nativeNotifications] schedule failed', e);
		return false;
	}
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
				body: 'Las notificaciones están funcionando correctamente.',
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
