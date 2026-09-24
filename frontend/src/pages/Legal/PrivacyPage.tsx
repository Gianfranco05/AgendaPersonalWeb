import LegalLayout from './LegalLayout';

/**
 * BORRADOR. Describe lo que la app hace hoy, pero no fue revisado por nadie con
 * matrícula. Faltan completar [EMAIL DE CONTACTO] y [PROVEEDOR DE HOSTING], y
 * el texto hay que hacerlo revisar antes de abrir el registro al público — la
 * app maneja datos financieros y de salud, que en la mayoría de las
 * jurisdicciones son categorías especiales con obligaciones extra.
 */
export default function PrivacyPage() {
  return (
    <LegalLayout title="Política de Privacidad" updatedAt="7 de agosto de 2026">
      <p className="rounded-lg bg-amber-50 dark:bg-amber-900/20 px-4 py-3 text-xs text-amber-800 dark:text-amber-300">
        Borrador pendiente de revisión legal. Completá los campos entre corchetes
        antes de publicar.
      </p>

      <section>
        <h2>Quién es responsable de tus datos</h2>
        <p>
          El responsable del tratamiento es Gianfranco Canciani, con
          domicilio en la Provincia de Mendoza, Argentina. Para cualquier
          consulta sobre esta política podés escribir a [EMAIL DE CONTACTO].
        </p>
      </section>

      <section>
        <h2>Qué datos guardamos</h2>
        <ul>
          <li>
            <strong>Datos de cuenta:</strong> tu email y tu nombre. La contraseña
            se guarda únicamente como hash: no la almacenamos ni podemos leerla.
          </li>
          <li>
            <strong>Contenido que cargás:</strong> transacciones y presupuestos,
            tareas, notas y etiquetas, eventos, metas y hábitos, entrenamientos y
            comidas. Los datos financieros y de salud son los más sensibles que
            maneja la app.
          </li>
          <li>
            <strong>Datos de sesión:</strong> tokens de sesión asociados a tus
            dispositivos, para mantenerte con la sesión iniciada y permitirte
            cerrarla en forma remota.
          </li>
          <li>
            <strong>Datos de compras:</strong> qué módulo comprás, cuánto
            pagás y cuándo, y un identificador de cliente de Mercado Pago. Los
            datos de tu tarjeta los procesa Mercado Pago: no pasan por
            nuestros servidores ni los almacenamos.
          </li>
        </ul>
      </section>

      <section>
        <h2>Para qué los usamos</h2>
        <p>
          Para prestarte el servicio: mostrarte tu información, autenticarte,
          enviarte los emails imprescindibles (verificación de cuenta y
          recuperación de contraseña) y, si corresponde, gestionar el cobro de la
          suscripción. No vendemos tus datos ni los usamos para publicidad, y no
          los cedemos a terceros salvo a los proveedores listados abajo.
        </p>
      </section>

      <section>
        <h2>Con quién los compartimos</h2>
        <ul>
          <li>
            <strong>Mercado Pago</strong> — procesamiento de pagos de los
            módulos que comprás.
          </li>
          <li>
            <strong>Resend</strong> — envío de los emails transaccionales.
          </li>
          <li>
            <strong>[PROVEEDOR DE HOSTING]</strong> — infraestructura donde corre
            la aplicación y su base de datos.
          </li>
        </ul>
      </section>

      <section>
        <h2>Cuánto tiempo los conservamos</h2>
        <p>
          Mientras tengas la cuenta abierta. Si la eliminás, borramos tus datos de
          la base de forma inmediata e irreversible. Pueden persistir hasta
          [PLAZO DE RETENCIÓN DE BACKUPS] en copias de seguridad, que se sobrescriben
          por rotación.
        </p>
      </section>

      <section>
        <h2>Tus derechos</h2>
        <p>
          Podés ejercer estos dos directamente desde{' '}
          <strong>Configuración</strong>, sin escribirnos ni esperar respuesta:
        </p>
        <ul>
          <li>
            <strong>Acceso y portabilidad:</strong> descargar un archivo JSON con
            todo lo que guardamos sobre vos.
          </li>
          <li>
            <strong>Supresión:</strong> eliminar tu cuenta y todos sus datos.
          </li>
        </ul>
        <p>
          Para rectificar datos, oponerte al tratamiento o limitarlo, escribinos a
          [EMAIL DE CONTACTO]. También podés reclamar ante la Agencia de Acceso
          a la Información Pública (AAIP), órgano de control de la Ley 25.326.
        </p>
      </section>

      <section>
        <h2>Seguridad</h2>
        <p>
          Las contraseñas se almacenan con hash bcrypt. El tráfico viaja cifrado
          por HTTPS. Las sesiones usan tokens de acceso de vida corta con tokens
          de refresco rotativos y revocables. Ningún sistema es infalible: si
          detectamos una brecha que te afecte, te avisaremos a tu email.
        </p>
      </section>

      <section>
        <h2>Cambios</h2>
        <p>
          Si modificamos esta política, actualizaremos la fecha del encabezado y,
          cuando el cambio sea sustancial, te avisaremos por email.
        </p>
      </section>
    </LegalLayout>
  );
}
