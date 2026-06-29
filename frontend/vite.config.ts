import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/finanzas': apiTarget,
      '/anotaciones': apiTarget,
      '/eventos': apiTarget,
      '/metas': apiTarget,
      '/ajustes': apiTarget,
      '/auth': apiTarget,
      '/health': apiTarget,
    }
  }
})
