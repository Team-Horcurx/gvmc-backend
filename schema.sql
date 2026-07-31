-- GVMC Change Detection Schema — matches the live RDS DB
-- This file documents the actual schema. For fresh installs:
--   mysql -h HOST -u USER -p gvmcdb < schema.sql

CREATE DATABASE IF NOT EXISTS gvmcdb;
USE gvmcdb;

CREATE TABLE IF NOT EXISTS wards (
  id          VARCHAR(10) PRIMARY KEY,
  name        VARCHAR(100),
  bbox_north  DECIMAL(10,6),
  bbox_south  DECIMAL(10,6),
  bbox_east   DECIMAL(10,6),
  bbox_west   DECIMAL(10,6),
  geojson_s3  VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS properties (
  id                   VARCHAR(36) PRIMARY KEY,
  ward_id              VARCHAR(10),
  lat                  DECIMAL(10,7),
  lng                  DECIMAL(10,7),
  area_sqm             DECIMAL(10,2),
  detection_type       ENUM('new_build','change_of_use'),
  confidence           DECIMAL(5,4),
  confidence_breakdown JSON,
  detected_at          DATETIME,
  s3_geojson_key       VARCHAR(500),
  status               ENUM('pending','verified','underassessed','false_positive','already_assessed') DEFAULT 'pending',
  notes                TEXT,
  updated_by           VARCHAR(100),
  updated_at           DATETIME,
  ai_explanation       TEXT,
  FOREIGN KEY (ward_id) REFERENCES wards(id)
);

CREATE TABLE IF NOT EXISTS verification_status (
  property_id  VARCHAR(36) PRIMARY KEY,
  status       ENUM('pending','verified','underassessed','false_positive','already_assessed'),
  updated_by   VARCHAR(100),
  updated_at   DATETIME,
  notes        TEXT,
  FOREIGN KEY (property_id) REFERENCES properties(id)
);

CREATE TABLE IF NOT EXISTS admin_config (
  key_name   VARCHAR(100) PRIMARY KEY,
  value      TEXT,
  updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS alerts (
  id         VARCHAR(36) PRIMARY KEY,
  ward_id    VARCHAR(10),
  severity   ENUM('danger','warning','info'),
  text       TEXT,
  created_at DATETIME,
  FOREIGN KEY (ward_id) REFERENCES wards(id)
);

-- ── Default admin config ───────────────────────────────────────────────────────
INSERT INTO admin_config (key_name, value, updated_at) VALUES
  ('data_mode',       'demo',                    NOW()),
  ('pipeline_status', 'idle',                    NOW()),
  ('last_refresh',    '2026-07-30T04:00:00.000Z',NOW()),
  ('ndbi_threshold',  '0.15',                    NOW())
ON DUPLICATE KEY UPDATE updated_at = NOW();

-- ── Seed wards ────────────────────────────────────────────────────────────────
INSERT INTO wards VALUES
  ('1','Seethammadhara',17.745,17.715,83.315,83.280,'geojson/ward-1.json'),
  ('2','Gopalapatnam',  17.778,17.748,83.278,83.245,'geojson/ward-2.json'),
  ('3','Maddilapalem',  17.728,17.700,83.302,83.270,'geojson/ward-3.json'),
  ('4','Asilmetta',     17.710,17.685,83.230,83.200,'geojson/ward-4.json'),
  ('5','Dwaraka Nagar', 17.695,17.668,83.220,83.190,'geojson/ward-5.json')
ON DUPLICATE KEY UPDATE name = VALUES(name);
