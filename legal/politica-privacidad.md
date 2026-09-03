# Política de Privacidad — Vida Personal / FocusOS

**Última actualización:** [FECHA]
**Versión:** 1.0

> Borrador técnico basado en el funcionamiento real de la aplicación (no genérico) — revisalo con un abogado antes de publicarlo, en particular por el tratamiento de datos de salud (fitness/nutrición) y financieros.

## 1. Responsable del tratamiento

**[TU NOMBRE COMPLETO]**, con domicilio en Argentina, es responsable del tratamiento de tus datos personales. Contacto: **[TU EMAIL DE CONTACTO]**.

## 2. Qué datos recolectamos

### 2.1 Datos de cuenta
Email, nombre completo, contraseña (nunca en texto plano — ver sección 6), y, si iniciás sesión con Google, tu email y nombre verificados por Google.

### 2.2 Datos que vos cargás
Dependiendo de qué módulos uses:

| Categoría | Ejemplos |
|---|---|
| Hábitos y objetivos | Hábitos, registros diarios, metas |
| Financieros | Transacciones, categorías, presupuestos, cuentas bancarias que vos cargues |
| Salud y bienestar | Rutinas de entrenamiento, comidas y nutrición |
| Productividad | Tareas, notas, eventos de calendario, sesiones de concentración (Focus) |
| Módulos opcionales | Materias y exámenes (Estudio), libros (Biblioteca), películas/series (Películas), búsqueda laboral (Trabajo), viajes y equipaje (Viajes), vehículos y mantenimiento (Vehículo), proyectos y tareas (Proyectos) |
| Recordatorios | Mensaje, horario e ícono de las notificaciones que configurás |

Los datos de fitness y nutrición pueden considerarse **datos sensibles/de salud** en algunas normativas. Los tratamos con el mismo nivel de protección técnica que el resto de tus datos (ver sección 6), y nunca los usamos con fines distintos a mostrártelos a vos.

### 2.3 Datos de pago
Cuando comprás un módulo, Stripe procesa el pago. Nosotros guardamos: qué módulo compraste, cuánto pagaste y cuándo, y un identificador de cliente de Stripe — **nunca** el número de tu tarjeta ni datos de la tarjeta en sí.

### 2.4 Datos técnicos
Dirección IP (para limitar intentos de login fallidos y prevenir abuso), tipo de dispositivo/sesión, y registros de error técnico (ver Sentry, sección 4) sin datos personales asociados.

## 3. Para qué usamos tus datos

- Operar la Aplicación y mostrarte tu propia información.
- Autenticarte y mantener tu sesión activa.
- Procesar tus compras y darte acceso a los módulos que adquiriste.
- Enviarte emails transaccionales: verificación de cuenta, restablecimiento de contraseña.
- Enviarte las notificaciones push/locales que vos mismo configuraste (recordatorios) — estas se programan y disparan en tu propio dispositivo, no las enviamos nosotros desde un servidor.
- Prevenir abuso (rate limiting en intentos de login, límites de tamaño de datos).
- Corregir errores técnicos (mediante reportes de error que **no incluyen** tus datos personales — ver sección 4).

**No usamos tus datos para publicidad, no los vendemos, y no entrenamos modelos de inteligencia artificial con ellos.**

## 4. Con quién compartimos datos (terceros)

Usamos los siguientes proveedores para operar el Servicio. Cada uno procesa solo lo estrictamente necesario para su función:

| Proveedor | Para qué | Qué recibe |
|---|---|---|
| **Stripe** | Procesar pagos | Tu email, nombre, y los datos de pago que vos le das directamente a Stripe (nunca pasan por nuestros servidores) |
| **Resend** | Enviar emails de verificación y restablecimiento de contraseña | Tu email y el contenido del mail |
| **Google** (opcional) | Iniciar sesión con Google, sincronizar tu Google Calendar si lo conectás | Tu email/nombre (login), o tus eventos de calendario si activás la integración — solo si vos elegís conectarla |
| **Sentry** | Detectar y corregir errores técnicos | Información del error (stack trace, ruta), **explícitamente configurado para no recibir datos personales** |

No compartimos tus datos con ningún otro tercero, y no los transferimos fuera de estos proveedores salvo obligación legal.

## 5. Cuánto tiempo guardamos tus datos

Guardamos tus datos mientras tu cuenta esté activa. Si eliminás tu cuenta, borramos permanentemente todos tus datos personales de nuestra base de datos de forma inmediata (ver sección 7). Los registros de pago que Stripe requiere por normativa contable/fiscal pueden conservarse en los sistemas de Stripe según sus propias políticas, independientes de las nuestras.

## 6. Cómo protegemos tus datos

- Contraseñas guardadas con hash criptográfico (bcrypt), nunca en texto plano.
- Conexión cifrada (HTTPS) entre tu dispositivo y nuestros servidores.
- Cookies de sesión con protecciones estándar (`HttpOnly`, `Secure`, `SameSite`) que evitan que scripts maliciosos o sitios de terceros accedan a tu sesión.
- Límite de intentos de inicio de sesión para dificultar ataques de fuerza bruta.
- Cada usuario solo puede ver y modificar sus propios datos — verificado en cada operación del servidor, no solo en la app.
- Los identificadores internos de Stripe se excluyen de la exportación de datos que vos podés descargar, para no exponer información de nuestra cuenta comercial.

Ningún sistema es 100% seguro. Si detectamos una brecha de seguridad que afecte tus datos, te lo notificaremos según lo exija la normativa aplicable.

## 7. Tus derechos

Tenés derecho a:

- **Acceder** a tus datos: descargalos vos mismo en formato JSON desde Ajustes → Mis datos → Exportar mis datos, sin necesidad de pedirlo por email.
- **Rectificar** datos incorrectos: editables directamente desde la Aplicación.
- **Eliminar** tu cuenta y todos tus datos: Ajustes → Mis datos → Eliminar cuenta. Es inmediato y permanente.
- **Portabilidad**: la exportación en JSON te permite llevarte tus datos a otro servicio.
- Oponerte al procesamiento o pedir una copia por otra vía: escribinos a **[TU EMAIL DE CONTACTO]**.

Si estás en la Unión Europea, también tenés derecho a presentar un reclamo ante tu autoridad de protección de datos local. Si estás en Argentina, ante la Agencia de Acceso a la Información Pública (AAIP).

## 8. Menores de edad

El Servicio no está dirigido a menores de 16 años. Si tenés entre 16 y 18, necesitás el consentimiento de tu madre, padre o tutor. No recolectamos deliberadamente datos de menores de 16 años; si detectamos que ocurrió, eliminaremos esa cuenta.

## 9. Cookies

Usamos una única cookie técnica esencial para mantener tu sesión iniciada en la versión web. No usamos cookies de rastreo ni de publicidad de terceros.

## 10. Cambios a esta Política

Si hacemos cambios significativos, te avisaremos por email o dentro de la Aplicación antes de que entren en vigencia.

## 11. Contacto

Para cualquier consulta sobre esta Política o tus datos: **[TU EMAIL DE CONTACTO]**.
