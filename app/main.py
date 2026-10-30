"""ЛР 1: FastAPI жобасының іске қосылатын бастапқы қаңқасы."""

from fastapi import FastAPI
from app.routers.items import router

app = FastAPI(title="Қойма ақпараттық жүйесі", version="0.1.0")
app.include_router(router)


@app.get("/")
def root():
    return {"system": "warehouse", "status": "ok", "labs": [1, 2]}
