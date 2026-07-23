package com.uroboros.app.widget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;

import com.uroboros.app.R;

/**
 * Widget de acceso directo: un solo toque abre la app en una ruta concreta
 * mediante un deep link (uroboros://...). No muestra datos, así que no necesita
 * refrescos ni acceso a red — sólo lanza el intent.
 *
 * Cada widget concreto define su layout y su URI destino.
 */
public abstract class LinkWidgetProvider extends AppWidgetProvider {

    /** Layout del widget (contiene un contenedor con id widget_root). */
    protected abstract int getLayoutId();

    /** Deep link que abre la pantalla, p. ej. "uroboros://add?scan=1". */
    protected abstract String getTargetUri();

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            RemoteViews views = new RemoteViews(context.getPackageName(), getLayoutId());

            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(getTargetUri()));
            // Restringir al propio paquete para que resuelva a MainActivity y no a un navegador.
            intent.setPackage(context.getPackageName());
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);

            PendingIntent pendingIntent = PendingIntent.getActivity(
                context,
                appWidgetId, // requestCode distinto por instancia para no colisionar
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );

            views.setOnClickPendingIntent(R.id.widget_root, pendingIntent);
            manager.updateAppWidget(appWidgetId, views);
        }
    }
}
