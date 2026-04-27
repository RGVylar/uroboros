#!/bin/bash
# Generate Android icons from logo.png

SOURCE_LOGO="static/logo.png"
TEMP_ICON="temp_icon.png"

# Tamaños necesarios para Android
declare -A SIZES=(
    ["mdpi"]="48"
    ["hdpi"]="72"
    ["xhdpi"]="96"
    ["xxhdpi"]="144"
    ["xxxhdpi"]="192"
)

# Verificar que ImageMagick está instalado
if ! command -v convert &> /dev/null; then
    echo "ImageMagick no está instalado. Instálalo con: sudo apt-get install imagemagick"
    exit 1
fi

# Crear los iconos en cada resolución
for density in "${!SIZES[@]}"; do
    size=${SIZES[$density]}

    # Crear directorio si no existe
    mkdir -p "android/app/src/main/res/mipmap-$density"

    # Generar icono redondo (con fondo de color)
    convert "$SOURCE_LOGO" -resize "${size}x${size}" -extent "${size}x${size}" \
        -background "#4FFF99" -gravity Center \
        "android/app/src/main/res/mipmap-$density/ic_launcher.png"

    # Generar icono redondo (versión round)
    convert "$SOURCE_LOGO" -resize "${size}x${size}" -extent "${size}x${size}" \
        -background "#4FFF99" -gravity Center \
        -bordercolor "#4FFF99" -border 0 \
        "android/app/src/main/res/mipmap-$density/ic_launcher_round.png"

    echo "✓ Generado ic_launcher para $density (${size}x${size})"
done

echo "✓ Todos los iconos generados exitosamente"
