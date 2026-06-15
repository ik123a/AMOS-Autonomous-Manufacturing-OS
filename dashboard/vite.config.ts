import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // TSDB Service — machines, telemetry, analytics
      '/api/machines': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/analytics': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      '/api/health': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Alert Service
      '/api/alerts': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      // Ingestion Service
      '/api/status': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      // MLOps Service
      '/api/models': {
        target: 'http://localhost:8004',
        changeOrigin: true,
      },
    },
  },
});