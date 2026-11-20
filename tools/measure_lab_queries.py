"""Reproducible ORM query count against a fresh in-memory teaching database."""
import json
from fastapi.testclient import TestClient
from sqlalchemy import event
from labs.lab_1_2.database.db import make_engine
from labs.lab_1_2.main import create_app
from labs.lab_1_2.seed import seed_demo
from labs.lab_1_2.test_crud import payload


def measure():
    engine=make_engine(':memory:')
    seed_demo(engine)
    statements=[]
    def record(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT'): statements.append(statement)
    event.listen(engine,'before_cursor_execute',record)
    results={}
    try:
        with TestClient(create_app(engine)) as client:
            for size in (3,30):
                if size==30:
                    for _ in range(27):
                        response=client.post('/api/orders',json=payload())
                        response.raise_for_status()
                statements.clear()
                response=client.get('/api/orders',params={'limit':200})
                response.raise_for_status()
                results[str(size)]={'orders':len(response.json()),'selects':len(statements)}
    finally:
        event.remove(engine,'before_cursor_execute',record)
        engine.dispose()
    return results


if __name__=='__main__':
    print(json.dumps(measure(),indent=2))
