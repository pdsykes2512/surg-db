import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: [
      'surg-db.vps',
      'impact.vps',
      'localhost',
      '127.0.0.1'
    ],
    proxy: {
      '/api': {
        target: 'http://192.168.11.238:8000',
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  },
  build: {
    // Ensure service worker and manifest are included in build
    rollupOptions: {
      input: {
        main: './index.html'
      }
    }
  }
})
