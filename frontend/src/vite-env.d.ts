/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** Baked in by vite.config.ts at build time — see buildSha() there. */
declare const __BUILD_SHA__: string
declare const __BUILD_TIME__: string
