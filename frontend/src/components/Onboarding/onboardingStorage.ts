// Respaldo local por usuario del tutorial visto: cubre el caso en que el PUT a
// /settings falle o tarde. Todo en try/catch: localStorage puede no estar
// disponible (modo privado, cookies bloqueadas) y no debe romper la app.
const key = (userId: string) => `cancen_onboarding_seen:${userId}`;

export function readOnboardingSeen(userId: string | undefined | null): number {
  if (!userId) return 0;
  try {
    const raw = window.localStorage.getItem(key(userId));
    const n = raw === null ? 0 : parseInt(raw, 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  } catch {
    return 0;
  }
}

export function writeOnboardingSeen(userId: string | undefined | null, version: number): void {
  if (!userId) return;
  try {
    const current = readOnboardingSeen(userId);
    window.localStorage.setItem(key(userId), String(Math.max(current, version)));
  } catch {
    // sin almacenamiento local: queda solo el valor del server
  }
}
