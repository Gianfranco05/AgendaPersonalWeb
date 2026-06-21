import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/finanzas': 'http://localhost:8000',
      '/anotaciones': 'http://localhost:8000',
      '/eventos': 'http://localhost:8000',
      '/metas': 'http://localhost:8000',
      '/ajustes': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
