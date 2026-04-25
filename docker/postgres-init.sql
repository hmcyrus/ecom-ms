-- Runs once on first container start via /docker-entrypoint-initdb.d/
-- Creates isolated DB + user per service (no cross-service DB access).

CREATE USER ecom WITH PASSWORD 'ecom';
CREATE DATABASE ecom_db OWNER ecom;

CREATE USER inventory WITH PASSWORD 'inventory';
CREATE DATABASE inventory_db OWNER inventory;
