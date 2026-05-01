import { createCanvas, loadImage } from 'canvas';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Colores de la app ──────────────────────────────────────────────────────
const BG = '#0a0d14';  // fondo oscuro

// Cargar el logo real
const logo = await loadImage(join(__dirname, 'src', 'logo.png'));

// ── 1. Icono 1024×1024 (foreground con fondo transparente) ─────────────────
{
  const SIZE = 1024;
  const canvas = createCanvas(SIZE, SIZE);
  const ctx = canvas.getContext('2d');

  // Fondo transparente
  ctx.clearRect(0, 0, SIZE, SIZE);

  // Logo centrado, con padding del 10% a cada lado
  const pad = SIZE * 0.1;
  ctx.drawImage(logo, pad, pad, SIZE - pad * 2, SIZE - pad * 2);

  writeFileSync(join(__dirname, 'assets', 'icon-only.png'), canvas.toBuffer('image/png'));
  console.log('✅ assets/icon-only.png');
}

// ── 2. Fondo del icono adaptativo ─────────────────────────────────────────
{
  const SIZE = 1024;
  const canvas = createCanvas(SIZE, SIZE);
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, SIZE, SIZE);

  writeFileSync(join(__dirname, 'assets', 'icon-background.png'), canvas.toBuffer('image/png'));
  console.log('✅ assets/icon-background.png');
}

// ── 3. Splash screen 2732×2732 ────────────────────────────────────────────
{
  const SIZE = 2732;
  const canvas = createCanvas(SIZE, SIZE);
  const ctx = canvas.getContext('2d');

  // Fondo oscuro
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, SIZE, SIZE);

  // Logo centrado (45% del ancho)
  const logoSize = SIZE * 0.45;
  const logoX = (SIZE - logoSize) / 2;
  const logoY = SIZE / 2 - logoSize / 2 - SIZE * 0.04;
  ctx.drawImage(logo, logoX, logoY, logoSize, logoSize);

  // Tagline debajo
  ctx.fillStyle = 'rgba(255,255,255,0.3)';
  ctx.font = `400 ${SIZE * 0.022}px Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('Come mejor. Juntos.', SIZE / 2, logoY + logoSize + SIZE * 0.06);

  writeFileSync(join(__dirname, 'assets', 'splash.png'), canvas.toBuffer('image/png'));
  console.log('✅ assets/splash.png');
}

console.log('\n✅ Imágenes generadas. Ahora ejecuta:');
console.log('   npx @capacitor/assets generate');
