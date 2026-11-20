from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI
from sqlmodel import Session, select
from .database.db import engine, get_session, init_db
from .routers.orders import router


def create_app(database_engine=engine, *, seed_on_start=False):
    @asynccontextmanager
    async def lifespan(app):
        init_db(database_engine)
        if seed_on_start:
            from .seed import seed_demo
            seed_demo(database_engine)
        yield


    app = FastAPI(title="QazCargo зертханалық модулі", version="3.0.0", lifespan=lifespan,
                  description="Зертханалық жұмыстар 1–7. Оқу тапсырыстарының CRUD API-і. "
                              "Тек бөлек SQLite базасы; SQL Server-дегі негізгі сайтқа қосылмайды.")
    if database_engine is not engine:
        def local_session():
            with Session(database_engine) as session:
                yield session
        app.dependency_overrides[get_session] = local_session
    app.include_router(router)

    @app.get("/health", tags=["Health"])
    def health(session: Session = Depends(get_session)):
        session.exec(select(1)).one()
        return {"status": "ok"}


    @app.get("/")
    def home():
        return {"project": "QazCargo", "labs": [1, 2, 3, 4, 5, 6, 7], "docs": "/docs", "data": "synthetic"}
    return app


app = create_app(seed_on_start=os.getenv("LAB_SEED_DEMO", "0") == "1")
