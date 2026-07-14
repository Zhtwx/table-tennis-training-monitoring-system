-- Workflow refactor schema contract for MySQL 5.5.
-- This script only adds workflow tables. It does not delete or rewrite legacy tables.
-- Keep this file limited to MySQL 5.5 compatible DDL.
-- Run after sql/pingpang_db.sql.

USE pingpang_db;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS tactical_standard_version (
  id INT NOT NULL AUTO_INCREMENT,
  standard_name VARCHAR(120) NOT NULL,
  method_code VARCHAR(40) NOT NULL,
  source_title VARCHAR(200) NOT NULL,
  source_location VARCHAR(255) NOT NULL,
  applicable_group VARCHAR(120) NOT NULL DEFAULT '',
  singles_doubles VARCHAR(20) NOT NULL DEFAULT '',
  verification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
  verified_by VARCHAR(80) DEFAULT NULL,
  verified_at DATETIME DEFAULT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 0,
  note VARCHAR(500) DEFAULT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_standard_method_status (method_code, verification_status),
  KEY idx_standard_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS match_tactical_analysis (
  id INT NOT NULL AUTO_INCREMENT,
  match_id INT NOT NULL,
  standard_version_id INT DEFAULT NULL,
  analysis_method VARCHAR(40) NOT NULL,
  version_no INT NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  coach_summary VARCHAR(1000) DEFAULT NULL,
  confirmed_by VARCHAR(80) DEFAULT NULL,
  confirmed_at DATETIME DEFAULT NULL,
  created_by VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_analysis_version (match_id, version_no),
  KEY idx_analysis_match_status (match_id, status),
  KEY idx_analysis_standard (standard_version_id),
  CONSTRAINT fk_analysis_match
    FOREIGN KEY (match_id)
    REFERENCES match_record (id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_analysis_standard_version
    FOREIGN KEY (standard_version_id)
    REFERENCES tactical_standard_version (id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS match_phase_stat (
  id INT NOT NULL AUTO_INCREMENT,
  analysis_id INT NOT NULL,
  phase_code VARCHAR(40) NOT NULL,
  points_won INT NOT NULL DEFAULT 0,
  points_lost INT NOT NULL DEFAULT 0,
  scoring_rate DECIMAL(6,2) DEFAULT NULL,
  usage_rate DECIMAL(6,2) DEFAULT NULL,
  usage_denominator_source VARCHAR(120) NOT NULL DEFAULT '',
  evaluation_level VARCHAR(40) DEFAULT NULL,
  coach_note VARCHAR(500) DEFAULT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_analysis_phase (analysis_id, phase_code),
  KEY idx_phase_analysis (analysis_id),
  CONSTRAINT fk_phase_analysis
    FOREIGN KEY (analysis_id)
    REFERENCES match_tactical_analysis (id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS training_plan_source (
  id INT NOT NULL AUTO_INCREMENT,
  plan_id INT NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  match_analysis_id INT DEFAULT NULL,
  injury_record_id INT DEFAULT NULL,
  source_summary VARCHAR(1000) NOT NULL,
  created_by VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_plan_source_plan (plan_id),
  KEY idx_plan_source_analysis (match_analysis_id),
  KEY idx_plan_source_injury (injury_record_id),
  CONSTRAINT fk_plan_source_plan
    FOREIGN KEY (plan_id)
    REFERENCES training_plan (id)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT fk_plan_source_analysis
    FOREIGN KEY (match_analysis_id)
    REFERENCES match_tactical_analysis (id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT,
  CONSTRAINT fk_plan_source_injury
    FOREIGN KEY (injury_record_id)
    REFERENCES injury_record (id)
    ON UPDATE CASCADE
    ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS training_plan_item (
  id INT NOT NULL AUTO_INCREMENT,
  plan_id INT NOT NULL,
  module_type VARCHAR(40) NOT NULL,
  item_title VARCHAR(160) NOT NULL,
  target_description VARCHAR(1000) NOT NULL,
  planned_sessions INT NOT NULL DEFAULT 1,
  planned_minutes INT NOT NULL DEFAULT 30,
  intensity VARCHAR(20) NOT NULL DEFAULT '中',
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  sort_order INT NOT NULL DEFAULT 1,
  created_by VARCHAR(80) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  PRIMARY KEY (id),
  KEY idx_plan_item_plan (plan_id),
  KEY idx_plan_item_module_status (module_type, status),
  CONSTRAINT fk_plan_item_plan
    FOREIGN KEY (plan_id)
    REFERENCES training_plan (id)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP VIEW IF EXISTS v_training_execution_feedback;

CREATE VIEW v_training_execution_feedback AS
SELECT
  NULL AS execution_id,
  'fitness' AS module_type,
  NULL AS plan_item_id,
  NULL AS plan_id,
  NULL AS athlete_id,
  NULL AS coach_id,
  NULL AS executed_at,
  NULL AS execution_status,
  NULL AS feedback_summary,
  NULL AS updated_at
FROM DUAL
WHERE 1 = 0;
