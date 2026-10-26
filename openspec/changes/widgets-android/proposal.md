## Why

Para tildar una tarea o un hábito hoy hay que abrir la app, esperar el arranque y navegar: es justo la fricción que hace que el registro diario se abandone. Un widget en la pantalla de inicio de Android que muestre "lo de hoy" y deje marcarlo con un toque baja ese costo a cero, y es el punto de contacto diario más barato que tiene la app con el usuario.

## What Changes

- **Dos widgets de pantalla de inicio en Android** (solo Android; iOS fuera de alcance):
  - **"Tareas de hoy"**: tareas pendientes (`pending` o `in_progress`) que vencen hoy o ya vencieron, primero las vencidas, hasta un máximo según el tamaño del widget (tope 8). Tocar el círculo de una tarea la marca como completada sin abrir la app; tocar el título o el encabezado abre la app en Tareas. Muestra "+N más" si no entran todas, y "Nada para hoy" si no hay.
  - **"Hábitos de hoy"**: hábitos (`binary` y `metric`) con su emoji y color. Tocar un hábito de sí/no lo marca o desmarca para hoy reutilizando la lógica idempotente de `setHabitDoneToday` (extraída a una función sin SWR). Los hábitos métricos muestran el valor de hoy y al tocarlos abren la app en Hábitos (cargar un número no entra en un widget). Encabezado con "2/5 hechos".
- **Datos sin la app abierta**: el widget corre en una tarea headless de JS (librería `react-native-android-widget`, render con JSX a RemoteViews/bitmap) que llama al backend con el token de `expo-secure-store` a través del mismo `apiClient` (refresh single-flight incluido). Sin conexión muestra la última foto guardada con la leyenda "Sin conexión · hace X"; con la sesión vencida o cerrada muestra "Iniciá sesión en Can_cen".
- **Nuevo endpoint liviano `GET /api/v1/widgets/today`** (backend): devuelve en una sola respuesta las tareas del día y los hábitos con su estado de hoy, calculados en la fecha local del usuario (`tz_offset_minutes`). Evita que el widget haga 2 + N pedidos (lista de tareas, lista de metas y registros de cada hábito) cada vez que se refresca.
- **Cuándo se refresca**: periódico cada 30 minutos (mínimo de Android), al tocar el botón ↻, después de cada marcado desde el widget, y cuando la app cambia tareas/hábitos, inicia o cierra sesión o pasa a segundo plano. Al cambiar el día se descartan los datos de ayer.
- **Escrituras sin conexión desde el widget**: se aplican de forma optimista a la foto del widget y se encolan en la cola offline existente (sin toast), que la app o el próximo refresco del widget reenvían.
- **Privacidad**: nueva opción en Ajustes del celular "Contenido de los widgets": *Completo* (títulos y acciones) o *Solo conteos* ("3 tareas para hoy · 1 vencida", "2/5 hábitos"; tocar abre la app). Cuando el bloqueo con huella/PIN del change `app-bloqueo-y-bienvenida` está activo, el default pasa a *Solo conteos*. Finanzas no tiene widget. Los widgets se declaran solo para la pantalla de inicio (no para la pantalla de bloqueo).
- **Temas claro y oscuro** con los tokens Stitch, siguiendo el tema del sistema.
- **Build nativo nuevo en EAS** (todos los perfiles, incluido el dev client): el config plugin se agrega en `app.config.js`; `index.ts` registra el task handler.

### Fuera de alcance

- iOS (WidgetKit / `expo-widgets`).
- Widgets de Finanzas, Eventos, Focus o Notas.
- Widgets configurables por instancia (elegir área de tareas o qué hábitos mostrar): queda como mejora.
- Crear tareas o hábitos desde el widget.
- Widgets en la pantalla de bloqueo.
- Actualización por push silenciosa desde el server (cambios hechos en la web aparecen en el próximo refresco periódico o al abrir la app).

## Capabilities

### New Capabilities
- `widgets-today-api`: endpoint `GET /api/v1/widgets/today` con la selección de tareas del día (vencen hoy o vencidas, orden y tope) y los hábitos con su estado de hoy en la fecha local del usuario, aislado por usuario.
- `android-home-widgets`: widgets "Tareas de hoy" y "Hábitos de hoy" en Android: registro y tamaños, obtención de datos en segundo plano, sesión vencida, caché y modo sin conexión, acciones de marcado idempotentes, disparadores de refresco, temas, y modo de privacidad.

### Modified Capabilities
<!-- Ninguna: las specs vigentes en openspec/specs/ describen la web; tareas y hábitos no cambian de comportamiento, solo se suma un endpoint de lectura. -->

## Impact

- **Backend** (`C:\Proyectos\Proyecto_desarrollo personal\backend`): nuevo módulo `app/modules/widgets/` (`schemas.py`, `service.py`, `api_routes.py`) usando `app/core/clock.py::local_today`; router incluido en `app/api/v1/router.py`. Sin tablas nuevas ni migración (no toca `OWNED_TABLES`). Tests nuevos `tests/test_widgets_today.py` y caso en `tests/test_tenant_isolation.py`.
- **Mobile** (`C:\Proyectos\vida-personal-mobile`): dependencia nueva `react-native-android-widget` (0.24.x); `app.config.js` (plugin con los dos widgets), `index.ts` (registro del handler solo en Android), nuevo `src/widgets/` (componentes, task handler, selección/estado puro, snapshot en AsyncStorage, `refreshWidgets()`), `src/api/endpoints.ts` (`fetchWidgetsToday`), `src/api/client.ts` (opción `silent` de la cola offline), `src/hooks/useGoals.ts` y `src/hooks/useTasks.ts` (extraer la lógica de marcado y avisar a los widgets), `src/store/authStore.ts` (login/logout refrescan y limpian widgets), `src/screens/SettingsScreen.tsx` (opción de privacidad), `App.tsx` (revalidar al volver al frente si el widget cambió datos), `assets/widget-preview/*.png`. Se agrega Jest (`jest-expo`) para tests unitarios de la lógica pura.
- **Web** (`frontend/`): sin cambios.
- **Build**: requiere build nativo nuevo en EAS para todos los perfiles; impacto estimado en el APK de +0,5 a +1,5 MB por ABI (librería nativa + WorkManager + previews), a medir en la verificación.
- **Dependencias con changes hermanos**: `app-bloqueo-y-bienvenida` (default de privacidad y restricción de no proteger los tokens con autenticación del Keystore); `habitos-recordatorios-inteligentes` (si cambia la forma de marcar un hábito, el widget debe usar la misma función compartida).
