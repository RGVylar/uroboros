package com.uroboros.app.widget;

import com.uroboros.app.R;

/** Widget "Escanear": abre la pantalla de añadir con el escáner QR/barras activo. */
public class ScanWidget extends LinkWidgetProvider {

    @Override
    protected int getLayoutId() {
        return R.layout.widget_scan;
    }

    @Override
    protected String getTargetUri() {
        return "uroboros://add?scan=1";
    }
}
