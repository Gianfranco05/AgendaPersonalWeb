import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'
import viteCompression from 'vite-plugin-compression'

const apiTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    ...(process.env.ANALYZE || process.env.VITE_ANALYZE
      ? [visualizer({ gzipSize: true, emitFile: true, filename: 'stats.html' })]
      : []),
    viteCompression({ algorithm: 'gzip', threshold: 1024 }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router')) {
            return 'vendor-react';
          }
          if (id.includes('node_modules/lucide-react') || id.includes('node_modules/recharts') || id.includes('node_modules/@uiw/react-md-editor')) {
            return 'vendor-ui';
          }
          if (id.includes('node_modules/axios') || id.includes('node_modules/swr') || id.includes('node_modules/zustand') || id.includes('node_modules/zod') || id.includes('node_modules/react-hook-form')) {
            return 'vendor-utils';
          }
        },
      },
    },
  },
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
      '/api/v1': apiTarget,
    }
  }
})
