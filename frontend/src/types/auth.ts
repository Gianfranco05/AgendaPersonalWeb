export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  // null = todavía no aceptó la versión vigente de los Términos (ver
  // CURRENT_TERMS_VERSION en authStore.ts). Cubre cuentas nuevas creadas por
  // Google (no pasan por el checkbox del registro normal) y usuarios
  // existentes cuando sube la versión.
  terms_accepted_version: string | null;
}
