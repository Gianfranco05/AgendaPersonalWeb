from datetime import date, timedelta
from typing import Any, Optional, Sequence

from sqlalchemy import and_, case, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inversiones.models import Investment


class InvestmentRepository:
    """Toda consulta filtra por `user_id`: un id ajeno responde "no existe"."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, investment_id: str, user_id: str) -> Optional[Investment]:
        result = await self.db.execute(
            select(Investment).where(
                and_(Investment.id == investment_id, Investment.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: str,
        status: str = "active",
        asset_type: Optional[str] = None,
    ) -> Sequence[Investment]:
        query = select(Investment).where(Investment.user_id == user_id)
        if status != "all":
            query = query.where(Investment.status == status)
        if asset_type:
            query = query.where(Investment.asset_type == asset_type)
        # Por tipo, vencimiento mas cercano primero (los que no vencen, al
        # final) y nombre. El CASE evita depender de NULLS LAST, que SQLite
        # recien soporta desde 3.30.
        query = query.order_by(
            Investment.asset_type,
            case((Investment.maturity_date.is_(None), 1), else_=0),
            Investment.maturity_date,
            Investment.name,
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, investment: Investment) -> Investment:
        self.db.add(investment)
        await self.db.commit()
        await self.db.refresh(investment)
        return investment

    async def update(self, investment: Investment, data: dict[str, Any]) -> Investment:
        for key, value in data.items():
            setattr(investment, key, value)
        await self.db.commit()
        await self.db.refresh(investment)
        return investment

    async def renewal_map(self, user_id: str) -> dict[str, str]:
        """{id de la renovada: id de su renovacion} de todas las del usuario."""
        result = await self.db.execute(
            select(Investment.renewed_from_id, Investment.id).where(
                and_(Investment.user_id == user_id, Investment.renewed_from_id.is_not(None))
            )
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_many(self, user_id: str, ids: Sequence[str]) -> dict[str, Investment]:
        if not ids:
            return {}
        result = await self.db.execute(
            select(Investment).where(and_(Investment.user_id == user_id, Investment.id.in_(ids)))
        )
        return {inv.id: inv for inv in result.scalars().all()}

    async def delete(self, investment: Investment) -> None:
        # La renovacion de este plazo fijo (si la hay) queda sin "renovado desde":
        # las FK no tienen ON DELETE y en Postgres borrar el anterior fallaria.
        await self.db.execute(
            update(Investment)
            .where(
                and_(
                    Investment.renewed_from_id == investment.id,
                    Investment.user_id == investment.user_id,
                )
            )
            .values(renewed_from_id=None)
        )
        await self.db.execute(
            delete(Investment).where(
                and_(Investment.id == investment.id, Investment.user_id == investment.user_id)
            )
        )
        await self.db.commit()

    async def list_due_for_alerts(self, utc_today: date) -> Sequence[Investment]:
        """Activos con aviso encendido cuyo vencimiento puede caer hoy o
        manana en algun huso horario (UTC-12 a UTC+14 corre el "hoy" local
        entre un dia antes y uno despues del de UTC)."""
        result = await self.db.execute(
            select(Investment).where(
                and_(
                    Investment.status == "active",
                    Investment.notify_maturity.is_(True),
                    Investment.maturity_date.is_not(None),
                    Investment.maturity_date >= utc_today - timedelta(days=1),
                    Investment.maturity_date <= utc_today + timedelta(days=2),
                )
            )
        )
        return result.scalars().all()

    async def claim_notice(self, investment_id: str, kind: str, maturity: date) -> bool:
        """Marca persistente y atomica del aviso (`eve` o `day`): True solo si
        esta llamada fue la que cambio la fila. Guardar la fecha de vencimiento
        (no un booleano) hace que mover el vencimiento rehabilite el aviso."""
        column = Investment.eve_notice_for if kind == "eve" else Investment.day_notice_for
        result = await self.db.execute(
            update(Investment)
            .where(
                and_(
                    Investment.id == investment_id,
                    Investment.maturity_date == maturity,
                    (column.is_(None)) | (column != maturity),
                )
            )
            .values({column.key: maturity})
        )
        await self.db.commit()
        return result.rowcount == 1
