import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: Number(process.env.PORT) || 5173,
		proxy: {
			'/api': 'http://127.0.0.1:8000',
			// La landing la sirve el backend; sin esto SvelteKit devuelve su 404.
			'/unete': 'http://127.0.0.1:8000'
		}
	}
});
