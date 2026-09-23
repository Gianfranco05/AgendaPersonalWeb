import LegalLayout from './LegalLayout';

/**
 * BORRADOR. Ver la nota de PrivacyPage: los marcadores [ENTRE CORCHETES] hay que
 * completarlos y el texto hay que hacerlo revisar antes de abrir el registro al
 * público.
 */
export default function TermsPage() {
  return (
    <LegalLayout title="Términos y Condiciones" updatedAt="7 de agosto de 2026">
      <p className="rounded-lg bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-xs text-amber-800 dark:text-amber-300">
        Borrador pendiente de revisión legal. Completá los campos entre corchetes
        antes de publicar.
      </p>

      <section>
        <h2>1. Qué es este servicio</h2>
        <p>
          Can_cen es una aplicación para organizar información personal:
          finanzas, tareas, notas, eventos, metas, entrenamientos y comidas. La
          presta [NOMBRE O RAZÓN SOCIAL]. Al crear una cuenta aceptás estos
          términos.
        </p>
      </section>

      <section>
        <h2>2. Tu cuenta</h2>
        <ul>
          <li>Necesitás una dirección de email válida y ser mayor de [EDAD MÍNIMA] años.</li>
          <li>
            Sos responsable de mantener tu contraseña en secreto y de la actividad
            que ocurra en tu cuenta. Si sospechás un acceso no autorizado, podés
            cerrar sesión en todos los dispositivos desde la aplicación.
          </li>
          <li>Una cuenta corresponde a una sola persona; no se comparte.</li>
        </ul>
      </section>

      <section>
        <h2>3. Tu contenido</h2>
        <p>
          Lo que cargás sigue siendo tuyo. No reclamamos ninguna propiedad sobre
          tus datos. Nos otorgás únicamente el permiso técnico necesario para
          almacenarlos y mostrártelos, que es lo que hace funcionar al servicio.
          Podés descargar todo tu contenido en cualquier momento desde
          Configuración.
        </p>
      </section>

      <section>
        <h2>4. Planes y pagos</h2>
        <ul>
          <li>Hay un plan gratuito y un plan Pro de suscripción periódica.</li>
          <li>
            Los pagos los procesa Stripe. Los precios y el período de facturación
            se muestran antes de confirmar la compra.
          </li>
          <li>
            La suscripción se renueva automáticamente hasta que la canceles. Podés
            cancelarla cuando quieras: conservás el acceso Pro hasta el final del
            período ya pagado.
          </li>
          <li>Política de reembolsos: [POLÍTICA DE REEMBOLSOS].</li>
        </ul>
      </section>

      <section>
        <h2>5. Uso aceptable</h2>
        <p>No se permite usar el servicio para:</p>
        <ul>
          <li>Actividades ilegales o que vulneren derechos de terceros.</li>
          <li>
            Intentar acceder a cuentas o datos ajenos, o vulnerar los mecanismos
            de seguridad de la aplicación.
          </li>
          <li>
            Sobrecargar la infraestructura de forma deliberada, con automatización
            abusiva o de cualquier otro modo.
          </li>
        </ul>
      </section>

      <section>
        <h2>6. Baja y cancelación</h2>
        <p>
          Podés eliminar tu cuenta cuando quieras desde Configuración. El borrado
          es inmediato e irreversible: descargá tus datos antes si querés
          conservarlos. Podemos suspender o cerrar una cuenta que incumpla estos
          términos, avisándote salvo que la gravedad del caso lo impida.
        </p>
      </section>

      <section>
        <h2>7. Garantías y responsabilidad</h2>
        <p>
          El servicio se ofrece «tal cual», sin garantía de disponibilidad
          ininterrumpida ni de ausencia de errores. No es asesoramiento financiero
          ni médico: la información que ves es la que vos cargaste. Mantené tus
          propias copias de lo que sea crítico. En la medida en que la ley lo
          permita, nuestra responsabilidad se limita a [LÍMITE DE RESPONSABILIDAD].
        </p>
      </section>

      <section>
        <h2>8. Cambios</h2>
        <p>
          Podemos modificar estos términos. Si el cambio es sustancial te
          avisaremos por email con antelación razonable; seguir usando el servicio
          después implica aceptarlos.
        </p>
      </section>

      <section>
        <h2>9. Ley aplicable</h2>
        <p>
          Estos términos se rigen por las leyes de [JURISDICCIÓN], y cualquier
          disputa se someterá a sus tribunales competentes. Consultas: [EMAIL DE
          CONTACTO].
        </p>
      </section>
    </LegalLayout>
  );
}
