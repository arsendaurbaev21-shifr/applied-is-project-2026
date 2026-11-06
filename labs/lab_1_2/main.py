from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Session
from .database.db import engine, get_session, init_db
from .routers.orders import router


def create_app(database_engine=engine):
    @asynccontextmanager
    async def lifespan(app):
        init_db(database_engine)
        yield


    app = FastAPI(title="QazCargo зертханалық модулі", version="2.0.0", lifespan=lifespan,
                  description="Зертханалық жұмыстар 1–4. Оқу тапсырыстарының CRUD API-і. "
                              "Тек бөлек SQLite базасы; SQL Server-дегі негізгі сайтқа қосылмайды.")
    if database_engine is not engine:
        def local_session():
            with Session(database_engine) as session:
                yield session
        app.dependency_overrides[get_session] = local_session
    app.include_router(router)


    @app.get("/")
    def home():
        return {"project": "QazCargo", "labs": [1, 2, 3, 4], "docs": "/docs", "data": "synthetic"}
    return app


app = create_app()
