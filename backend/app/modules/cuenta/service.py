"""Export y borrado de la cuenta completa de un usuario.

Las dos operaciones recorren el mismo inventario de tablas (`OWNED_TABLES`), asi
que agregar un modelo nuevo con `user_id` solo requiere sumarlo ahi una vez y
queda cubierto por el export y por el borrado a la vez. `test_account.py` tiene
un test que recorre los mapeadores de SQLAlchemy y falla si aparece una tabla
con `user_id` que no este en la lista — sin eso, un modulo nuevo se filtraria
del export y dejaria filas huerfanas al borrar la cuenta.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ajustes.models import UserPreference
from app.modules.anotaciones.models import Note, Tag, note_tags
from app.modules.arrepentimiento.models import WithdrawalRequest
from app.modules.auth.models import RefreshToken, User, VerificationToken
from app.modules.billing.models import StripeCustomer
from app.modules.eventos.models import Event
from app.modules.finanzas.models import BankAccount, Budget, Category, Transaction
from app.modules.finanzas.transfer.models import ImportBatch
from app.modules.inversiones.models import Investment
from app.modules.recurrentes.models import RecurringOccurrence, RecurringTransaction
from app.modules.fitness.models import Exercise, WorkoutSession
from app.modules.habitos_recordatorios.models import (
    HabitReminderDispatch,
    HabitReminderSettings,
)
from app.modules.biblioteca.models import Book
from app.modules.estudio.models import Exam, Subject
from app.modules.peliculas.models import MediaItem
from app.modules.proyectos.models import Project, ProjectTask
from app.modules.trabajo.models import WorkOpportunity
from app.modules.vehiculo.models import MaintenanceRecord, Vehicle
from app.modules.viajes.models import PackingItem, Trip
from app.modules.focus.models import FocusSession
from app.modules.recordatorios.models import Reminder
from app.modules.metas.models import Goal, HabitRecord
from app.modules.modulos.models import EnabledModule, ModulePurchase
from app.modules.nutricion.models import Meal
from app.modules.push.models import PushToken
from app.modules.tareas.models import Task

logger = logging.getLogger(__name__)


# Tablas con `user_id` propio. El orden es el de borrado: una tabla se borra
# antes que cualquier otra a la que apunte por FK.
#
# El orden importa de verdad. SQLite no aplica FKs salvo que se active
# `PRAGMA foreign_keys=ON` (no esta activo), asi que un orden mal puesto no
# falla en los tests pero deja filas huerfanas en Postgres — o al reves, revienta
# en prod y pasa en CI. Por eso el orden es explicito y no depende de cascades.
OWNED_TABLES: list[tuple[str, Any]] = [
    # Hijos primero: apuntan a categories / goals / notes.
    # Las ocurrencias apuntan a transactions y a su plantilla: van antes que ambas.
    ("recurring_occurrences", RecurringOccurrence),
    ("transactions", Transaction),
    # El lote lo referencian las transacciones (import_batch_id) y el lote
    # referencia a bank_accounts (account_id): va despues de las primeras y
    # antes de la segunda.
    ("import_batches", ImportBatch),
    # La plantilla apunta a categories y bank_accounts: va antes que ellas.
    ("recurring_transactions", RecurringTransaction),
    ("budgets", Budget),
    ("habit_records", HabitRecord),
    # Sin FKs hacia otras tablas del usuario: el orden entre ellas no importa.
    ("habit_reminder_dispatches", HabitReminderDispatch),
    ("habit_reminder_settings", HabitReminderSettings),
    ("exams", Exam),
    ("packing_items", PackingItem),
    ("maintenance_records", MaintenanceRecord),
    ("project_tasks", ProjectTask),
    # Padres.
    ("subjects", Subject),
    ("books", Book),
    ("media_items", MediaItem),
    ("work_opportunities", WorkOpportunity),
    ("trips", Trip),
    ("vehicles", Vehicle),
    ("projects", Project),
    ("categories", Category),
    ("goals", Goal),
    ("bank_accounts", BankAccount),
    ("investments", Investment),
    ("notes", Note),
    ("tags", Tag),
    ("events", Event),
    ("tasks", Task),
    ("meals", Meal),
    ("workout_sessions", WorkoutSession),
    ("user_preferences", UserPreference),
    ("stripe_customers", StripeCustomer),
    ("module_purchases", ModulePurchase),
    ("enabled_modules", EnabledModule),
    ("focus_sessions", FocusSession),
    ("reminders", Reminder),
    ("push_tokens", PushToken),
    ("refresh_tokens", RefreshToken),
    ("verification_tokens", VerificationToken),
]

# Tablas con `user_id` que se CONSERVAN al borrar la cuenta: se desvincula al
# usuario (user_id = NULL) pero la fila queda. Son registros legales — la
# solicitud del Boton de arrepentimiento tiene que poder responderse aunque la
# persona haya cerrado su cuenta. Salen en el export como cualquier otra tabla.
RETAINED_TABLES: list[tuple[str, Any]] = [
    ("withdrawal_requests", WithdrawalRequest),
]

# Nunca salen en el export: son credenciales, material de sesion, o
# identificadores de dispositivo sin valor para el usuario fuera de la app.
NEVER_EXPORTED: set[str] = {"refresh_tokens", "verification_tokens", "push_tokens"}

# Columnas que se omiten aunque su tabla se exporte.
REDACTED_COLUMNS: dict[str, set[str]] = {
    "users": {"password_hash"},
    # Identificadores internos de Stripe: no son datos personales del usuario y
    # exponerlos solo sirve para enumerar la cuenta de Stripe del negocio.
    "stripe_customers": {"stripe_customer_id"},
    "module_purchases": {"stripe_session_id"},
    # Celdas del archivo subido: transitorias (maximo 24 h) y pueden pesar MB.
    "import_batches": {"raw_table"},
}


def _serialize_value(value: Any) -> Any:
    """Convierte un valor de columna a algo que `json` sepa escribir.

    `Numeric(12, 2)` devuelve `Decimal` en Postgres y `float` en SQLite, asi que
    el export tiene que aceptar los dos o el mismo codigo funciona en tests y
    falla en prod.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _serialize_row(model: Any, row: Any, table_key: str) -> dict[str, Any]:
    redacted = REDACTED_COLUMNS.get(table_key, set())
    return {
        column.key: _serialize_value(getattr(row, column.key))
        for column in model.__table__.columns
        if column.key not in redacted
    }


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export(self, user: User) -> dict[str, Any]:
        """Arma el volcado completo de los datos del usuario."""
        data: dict[str, Any] = {
            "exported_at": datetime.now().astimezone().isoformat(),
            "format_version": 1,
            "user": _serialize_row(User, user, "users"),
        }

        for table_key, model in [*OWNED_TABLES, *RETAINED_TABLES]:
            if table_key in NEVER_EXPORTED:
                continue
            result = await self.db.execute(
                select(model).where(model.user_id == str(user.id))
            )
            data[table_key] = [
                _serialize_row(model, row, table_key) for row in result.scalars().all()
            ]

        # Exercise no tiene user_id: cuelga de WorkoutSession, asi que se escopa
        # por las sesiones del usuario en vez de por columna propia.
        session_ids = [row["id"] for row in data["workout_sessions"]]
        if session_ids:
            result = await self.db.execute(
                select(Exercise).where(Exercise.session_id.in_(session_ids))
            )
            data["exercises"] = [
                _serialize_row(Exercise, row, "exercises")
                for row in result.scalars().all()
            ]
        else:
            data["exercises"] = []

        # note_tags es una tabla de asociacion sin modelo propio: sin esto el
        # export perderia que etiquetas tenia cada nota.
        note_ids = [row["id"] for row in data["notes"]]
        if note_ids:
            result = await self.db.execute(
                select(note_tags).where(note_tags.c.note_id.in_(note_ids))
            )
            data["note_tags"] = [
                {"note_id": r.note_id, "tag_id": r.tag_id} for r in result.all()
            ]
        else:
            data["note_tags"] = []

        return data

    async def delete_account(self, user: User) -> None:
        """Borra al usuario y todo lo que le pertenece, en una sola transaccion.

        No se apoya en cascades de la base: ver el comentario de OWNED_TABLES.
        """
        user_id = str(user.id)

        # Exercise y note_tags no tienen user_id — se resuelven por subquery
        # sobre la tabla padre, y antes de que esa tabla padre desaparezca.
        session_ids = select(WorkoutSession.id).where(WorkoutSession.user_id == user_id)
        await self.db.execute(
            delete(Exercise).where(Exercise.session_id.in_(session_ids))
        )

        note_ids = select(Note.id).where(Note.user_id == user_id)
        await self.db.execute(delete(note_tags).where(note_tags.c.note_id.in_(note_ids)))
        tag_ids = select(Tag.id).where(Tag.user_id == user_id)
        await self.db.execute(delete(note_tags).where(note_tags.c.tag_id.in_(tag_ids)))

        for _table_key, model in RETAINED_TABLES:
            await self.db.execute(
                update(model).where(model.user_id == user_id).values(user_id=None)
            )

        for _table_key, model in OWNED_TABLES:
            await self.db.execute(delete(model).where(model.user_id == user_id))

        await self.db.execute(delete(User).where(User.id == user_id))
        await self.db.commit()

