-- Fitness training redesign schema for MySQL 5.5.
-- Run after sql/pingpang_db.sql and before sql/member9_stats_excel.sql.
-- Legacy fitness_report rows remain unchanged because their 0-100 assessment
-- values are not equivalent to the redesigned 0-10 training scores.

USE pingpang_db;

CREATE TABLE IF NOT EXISTS fitness_training_record (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    athlete_id              INT NOT NULL,
    test_date               DATETIME NOT NULL,
    tester_id               INT NOT NULL,
    plan_name               VARCHAR(100) NOT NULL,
    training_hours          DECIMAL(5,1) NOT NULL DEFAULT 0.0,
    training_intensity      VARCHAR(20) NOT NULL,
    plan_status             VARCHAR(20) NOT NULL,
    sprint_30m              DECIMAL(5,2) NOT NULL,
    abdominal_endurance     DECIMAL(6,2) NOT NULL,
    back_endurance          DECIMAL(6,2) NOT NULL,
    lateral_slide           DECIMAL(5,2) NOT NULL,
    a_footwork              DECIMAL(5,2) NOT NULL,
    double_under            DECIMAL(6,2) NOT NULL,
    seated_rotation_throw   DECIMAL(7,2) NOT NULL,
    standing_long_jump      DECIMAL(6,2) NOT NULL,
    overall_score           DECIMAL(4,2) NOT NULL,
    notes                   VARCHAR(120) DEFAULT NULL,
    created_by              VARCHAR(50) DEFAULT NULL,
    create_time             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time             TIMESTAMP NULL,

    CONSTRAINT fk_fitness_training_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_fitness_training_tester
        FOREIGN KEY (tester_id) REFERENCES coach(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    INDEX idx_fitness_training_athlete_date (athlete_id, test_date),
    INDEX idx_fitness_training_tester_date (tester_id, test_date),
    INDEX idx_fitness_training_plan_status (plan_status, training_intensity)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT '>>> fitness training redesign schema ready <<<' AS status;
