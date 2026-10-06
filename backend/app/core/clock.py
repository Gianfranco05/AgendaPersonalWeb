from datetime import date, datetime, timedelta, timezone
from typing import Optional


def local_today(tz_offset_minutes: Optional[int] = None) -> date:
    """"Hoy" en la zona del cliente.

    El server corre en UTC y no conoce la zona del usuario: con `date.today()`
    el dia cambia a las 21:00 en Argentina. `tz_offset_minutes` son los minutos
    al este de UTC (Buenos Aires = -180), el mismo contrato que focus. Sin el
    parametro (clientes viejos) queda el comportamiento de siempre.
    """
    if tz_offset_minutes is None:
        return date.today()
    return (datetime.now(timezone.utc) + timedelta(minutes=tz_offset_minutes)).date()
