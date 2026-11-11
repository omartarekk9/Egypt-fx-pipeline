-- A separate database for Airflow's own metadata, kept apart from the FX data.
-- Runs automatically on a FRESH volume, before 01_schema.sql.
CREATE DATABASE airflow;
