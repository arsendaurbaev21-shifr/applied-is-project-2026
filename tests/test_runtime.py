import os
from pathlib import Path
import subprocess
import sys
from fastapi.testclient import TestClient
from labs.lab_1_2.database.db import make_engine
from labs.lab_1_2.main import create_app
from labs.lab_1_2.test_crud import payload


def test_file_database_preserves_changes_across_restarts(tmp_path):
    path = tmp_path / 'volume' / 'database.db'
    first = make_engine(path)
    with TestClient(create_app(first, seed_on_start=True)) as client:
        created = client.post('/api/orders', json=payload()).json()
        assert client.delete('/api/orders/1').status_code == 204
    first.dispose()
    second = make_engine(path)
    try:
        with TestClient(create_app(second, seed_on_start=True)) as client:
            assert client.get(f"/api/orders/{created['id']}").json() == created
            assert client.get('/api/orders/1').status_code == 404
            assert client.get('/api/summary').json()['tables']['Orders'] == 3
    finally:
        second.dispose()


def test_database_path_can_point_to_container_volume(tmp_path):
    path = tmp_path / 'container-data' / 'database.db'
    env = {**os.environ, 'LAB_DATABASE_PATH': str(path)}
    result = subprocess.run([sys.executable, '-c',
                             'from labs.lab_1_2.database.db import DATABASE_PATH; print(DATABASE_PATH)'],
                            env=env, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
    assert Path(result.stdout.strip()) == path
