import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: './', // relative base -> works on a GitHub Pages project site
  plugins: [react()],
  test: { environment: 'node', globals: true },
});
