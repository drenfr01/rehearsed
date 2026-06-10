import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: '../backend/openapi.json',
  output: 'src/app/core/api',
  plugins: ['@hey-api/typescript'],
});
