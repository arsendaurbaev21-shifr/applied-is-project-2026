"""ЛР 1 қаңқасы: тауар маршруттары келесі кезеңде іске асырылады."""

from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])
