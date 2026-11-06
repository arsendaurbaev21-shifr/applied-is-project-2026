"""Temporary seeded SQLite for manual Swagger exercises; removed on exit."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
import uvicorn
from labs.lab_1_2.database.db import make_engine
from labs.lab_1_2.main import create_app
from labs.lab_1_2.seed import seed_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="QazCargo_Lab34_") as folder:
        engine = make_engine(Path(folder) / "sandbox.db")
        try:
            seed_demo(engine)
            uvicorn.run(create_app(engine), host="127.0.0.1", port=args.port)
        finally:
            engine.dispose()
