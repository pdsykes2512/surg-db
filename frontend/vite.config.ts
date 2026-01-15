import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const env = loadEnv(mode, process.cwd(), '')

  // Get server hostname from env or use default
  const serverHostname = env.SERVER_HOSTNAME || 'impact.vps'
  const backendHost = env.BACKEND_HOST || '192.168.11.238'
  const backendPort = env.BACKEND_PORT || '8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src')
      }
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      strictPort: true,
      allowedHosts: [
        serverHostname,  // Configurable hostname from env
        'localhost',
	'impact.pdsykes.co.uk',
        '127.0.0.1'
      ],
      proxy: {
        '/api': {
          target: `http://${backendHost}:${backendPort}`,
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
  }
})
