import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.uroboros.app',
  appName: 'Uroboros',
  webDir: 'build',
  server: {
    // In production, the app loads from the built files but API calls
    // go to the configured server. Set VITE_API_URL at build time.
    androidScheme: 'https'
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1800,
      launchAutoHide: true,
      backgroundColor: '#0a0d14',
      androidSplashResourceName: 'splash',
      showSpinner: false
    }
  }
};

export default config;
