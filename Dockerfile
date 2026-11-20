FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements-lab-api.txt ./
RUN pip install --no-cache-dir -r requirements-lab-api.txt \
    && useradd --create-home --uid 10001 app \
    && mkdir /data && chown app:app /data
COPY --chown=app:app labs/ ./labs/
USER app
ENV LAB_DATABASE_PATH=/data/database.db LAB_SEED_DEMO=1
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
  CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["python", "-m", "uvicorn", "labs.lab_1_2.main:app", "--host", "0.0.0.0", "--port", "8000"]
