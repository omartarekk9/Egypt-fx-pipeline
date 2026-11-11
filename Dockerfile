FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first: this layer is cached until requirements.txt changes.
# The container talks to Postgres only, so the SQL Server driver (pyodbc) is left out.
COPY requirements.txt .
RUN grep -iv '^pyodbc' requirements.txt > requirements-docker.txt \
 && pip install --no-cache-dir -r requirements-docker.txt

COPY run_pipeline.py .
COPY src ./src

# Do not run as root.
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENV FX_BACKEND=postgres

# Arguments after the image name go straight to run_pipeline.py, e.g. `--backfill 30`.
ENTRYPOINT ["python", "run_pipeline.py"]
