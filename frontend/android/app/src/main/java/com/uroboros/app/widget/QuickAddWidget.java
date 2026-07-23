package com.uroboros.app.widget;

import com.uroboros.app.R;

/** Widget "Añadir": abre directamente la pantalla de registro. */
public class QuickAddWidget extends LinkWidgetProvider {

    @Override
    protected int getLayoutId() {
        return R.layout.widget_quick_add;
    }

    @Override
    protected String getTargetUri() {
        return "uroboros://add";
    }
}
