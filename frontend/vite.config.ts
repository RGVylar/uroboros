import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// API_PROXY permite apuntar a otro backend local (p. ej. uno en :8001 mientras
// otra sesión usa el de :8000).
const backend = process.env.API_PROXY || 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: Number(process.env.PORT) || 5173,
		proxy: {
			'/api': backend,
			// La landing la sirve el backend; sin esto SvelteKit devuelve su 404.
			'/unete': backend,
			// Receta compartida (/r/<código>), también del backend. Con regex: la
			// clave '/r' a secas casaría por prefijo con /recipes.
			'^/r/': backend
		}
	}
});
