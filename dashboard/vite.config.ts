import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api/v1/machines': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/timeseries': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/summary': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/anomalies': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/v1/alerts': { target: 'http://localhost:8003', changeOrigin: true },
      // Health endpoints are unversioned on the individual services.
      '/api/v1/health': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace('/api/v1/health', '/health'),
      },
    },
  },
});
