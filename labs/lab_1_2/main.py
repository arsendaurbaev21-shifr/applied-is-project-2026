from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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


    app = FastAPI(title="QazCargo зертханалық модулі", version="4.0.0", lifespan=lifespan,
                  description="Зертханалық жұмыстар 1–8. Оқу тапсырыстарының CRUD API-і. "
                              "Тек бөлек SQLite базасы; SQL Server-дегі негізгі сайтқа қосылмайды.")
    if database_engine is not engine:
        def local_session():
            with Session(database_engine) as session:
                yield session
        app.dependency_overrides[get_session] = local_session
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo input values (including unknown password/token fields) to the response.
        details = [{key: item[key] for key in ("type", "loc", "msg")} for item in error.errors()]
        status = 400 if any(item["type"] == "json_invalid" for item in details) else 422
        return JSONResponse(status_code=status, content={"detail": details})

    @app.get("/health", tags=["Health"])
    def health(session: Session = Depends(get_session)):
        session.exec(select(1)).one()
        return {"status": "ok"}


    @app.get("/")
    def home():
        return {"project": "QazCargo", "labs": list(range(1, 9)), "docs": "/docs", "data": "synthetic"}
    return app


app = create_app(seed_on_start=os.getenv("LAB_SEED_DEMO", "0") == "1")
