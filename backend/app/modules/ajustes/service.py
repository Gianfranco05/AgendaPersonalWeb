import asyncio
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.modules.ajustes.models import UserPreference
from app.modules.ajustes.repository import UserPreferenceRepository
from app.modules.ajustes.schemas import UserPreferenceUpdate
from app.modules.eventos.schemas import to_wall_clock


class SettingsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserPreferenceRepository(db)

    async def get_preferences(self, user_id: str) -> UserPreference:
        prefs = await self.repo.get_by_user(user_id)
        if prefs is None:
            prefs = await self.repo.upsert(user_id, {})
        return prefs

    async def update_preferences(
        self, user_id: str, data: UserPreferenceUpdate
    ) -> UserPreference:
        update_data = data.model_dump(exclude_unset=True)
        return await self.repo.upsert(user_id, update_data)

    async def disconnect_google(self, user_id: str) -> UserPreference:
        return await self.repo.upsert(
            user_id,
            {
                "google_access_token": None,
                "google_refresh_token": None,
                "google_token_expiry": None,
            },
        )

    async def sync_events_to_google(self, user_id: str, prefs: UserPreference) -> int:
        """Empuja (one-way, local -> Google) todos los eventos locales a Google Calendar.

        No dedupea contra eventos ya sincronizados: cada llamada re-inserta todo.
        """
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GRequest
        from googleapiclient.discovery import build
        from app.modules.eventos.models import Event

        creds = Credentials(
            token=prefs.google_access_token,
            refresh_token=prefs.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=app_settings.GOOGLE_CLIENT_ID,
            client_secret=app_settings.GOOGLE_CLIENT_SECRET,
        )

        if creds.expired and creds.refresh_token:
            await asyncio.to_thread(creds.refresh, GRequest())
            prefs.google_access_token = creds.token
            prefs.google_token_expiry = creds.expiry
            self.db.add(prefs)
            await self.db.commit()

        service = await asyncio.to_thread(build, "calendar", "v3", credentials=creds)

        events_result = await self.db.execute(
            select(Event).where(Event.user_id == user_id)
        )
        events = events_result.scalars().all()

        synced = 0
        for event in events:
            # Hora de pared sin offset: con el offset +00:00 de una columna
            # timestamptz, Google ignoraria timeZone y correria el evento.
            start_dt = to_wall_clock(event.start_datetime)
            end_dt = (
                to_wall_clock(event.end_datetime)
                if event.end_datetime
                else start_dt + timedelta(hours=1)
            )
            g_event = {
                "summary": event.title,
                "description": event.description or "",
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": "America/Argentina/Buenos_Aires",
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": "America/Argentina/Buenos_Aires",
                },
            }
            if event.location:
                g_event["location"] = event.location
            if event.is_all_day:
                date_str = start_dt.strftime("%Y-%m-%d")
                g_event["start"] = {"date": date_str}
                g_event["end"] = {"date": date_str}

            await asyncio.to_thread(
                service.events()
                .insert(calendarId=prefs.google_calendar_id, body=g_event)
                .execute
            )
            synced += 1

        return synced
