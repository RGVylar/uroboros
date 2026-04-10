import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.uroboros.app',
  appName: 'Uroboros',
  webDir: 'build',
  server: {
    // In production, the app loads from the built files but API calls
    // go to the configured server. Set VITE_API_URL at build time.
    androidScheme: 'https'
  }
};

export default config;
