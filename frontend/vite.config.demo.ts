import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    outDir: 'dist-demo',
    rollupOptions: {
      input: 'demo.html',
    },
  },
})
