from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database.db import init_db
from .routers.orders import router


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="QazCargo зертханалық модулі", version="1.0.0", lifespan=lifespan,
              description="Зертханалық жұмыстар 1–2. Тек бөлек SQLite базасындағы оқу деректері.")
app.include_router(router)


@app.get("/")
def home():
    return {"project": "QazCargo", "labs": [1, 2], "docs": "/docs", "data": "synthetic"}
