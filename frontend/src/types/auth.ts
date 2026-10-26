export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  // null = todavía no aceptó `current_terms_version`. Cubre cuentas nuevas
  // creadas por Google (no pasan por el checkbox del registro normal) y
  // usuarios existentes cuando sube la versión.
  terms_accepted_version: string | null;
  // Versión vigente de Términos/Privacidad, la manda el backend
  // (settings.CURRENT_TERMS_VERSION) para no duplicarla como constante en
  // cada cliente.
  current_terms_version: string;
  // false = todavía no declaró tener 16 años o más (cuenta nueva de Google,
  // o cuenta anterior a la declaración de edad). Se pide en el mismo gate.
  age_confirmed: boolean;
}
