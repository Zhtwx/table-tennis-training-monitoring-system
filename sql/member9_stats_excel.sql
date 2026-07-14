-- ============================================================
-- 成员9：统计分析与 Excel 数据导入导出增量脚本
-- 依赖脚本（按顺序执行）：
--   1. sql/pingpang_db.sql
--   2. sql/member2_advanced_database.sql（为 injury_record 增加 is_deleted）
--   3. sql/fitness_training_redesign.sql（体能训练新指标记录）
-- 用法: mysql -u root -p pingpang_db < sql/member9_stats_excel.sql
-- ============================================================

USE pingpang_db;

-- Excel 导入暂存表：用于批量导入专项技术记录。
CREATE TABLE IF NOT EXISTS temp_import_technical_record (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    student_no          VARCHAR(20) NOT NULL,
    record_date         DATE NOT NULL,
    footwork_duration   INT DEFAULT 0,
    hit_score           DECIMAL(5,2) DEFAULT 0,
    multi_ball_duration INT DEFAULT 0,
    intensity           ENUM('低','中','高','极高') DEFAULT '中',
    import_batch_no     VARCHAR(50) NOT NULL,
    create_time         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    KEY idx_member9_import_batch (import_batch_no),
    KEY idx_member9_import_student_date (student_no, record_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 按运动员、月份统计训练时长与训练强度。
DROP VIEW IF EXISTS v_member9_monthly_training_stats;

CREATE VIEW v_member9_monthly_training_stats AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name AS athlete_name,
    DATE_FORMAT(tp.start_date, '%Y-%m') AS training_month,
    COUNT(tp.id) AS plan_count,
    SUM(IFNULL(tp.hours, 0)) AS total_hours,
    ROUND(AVG(
        CASE tp.intensity
            WHEN '低' THEN 1
            WHEN '中' THEN 2
            WHEN '高' THEN 3
            WHEN '极高' THEN 4
            ELSE 0
        END
    ), 2) AS avg_intensity_level,
    SUM(CASE WHEN tp.intensity IN ('高','极高') THEN 1 ELSE 0 END) AS high_intensity_count
FROM athlete a
JOIN training_plan tp ON tp.athlete_id = a.id
GROUP BY a.id, a.student_no, a.name, DATE_FORMAT(tp.start_date, '%Y-%m');

-- 按运动员、ISO 周统计训练时长与训练强度。
DROP VIEW IF EXISTS v_member9_weekly_training_stats;

CREATE VIEW v_member9_weekly_training_stats AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name AS athlete_name,
    YEARWEEK(tp.start_date, 1) AS training_week,
    MIN(tp.start_date) AS week_start_date,
    MAX(tp.end_date) AS week_end_date,
    COUNT(tp.id) AS plan_count,
    SUM(IFNULL(tp.hours, 0)) AS total_hours,
    SUM(CASE WHEN tp.intensity IN ('高','极高') THEN 1 ELSE 0 END) AS high_intensity_count
FROM athlete a
JOIN training_plan tp ON tp.athlete_id = a.id
GROUP BY a.id, a.student_no, a.name, YEARWEEK(tp.start_date, 1);

-- 全队伤病部位分布。
DROP VIEW IF EXISTS v_member9_injury_distribution_stats;

CREATE VIEW v_member9_injury_distribution_stats AS
SELECT
    injury_location,
    COUNT(id) AS injury_count,
    ROUND(
        COUNT(id) / (
            SELECT GREATEST(COUNT(*), 1)
            FROM injury_record
            WHERE IFNULL(is_deleted, 0) = 0
        ) * 100,
        2
    ) AS rate,
    SUM(CASE WHEN severity = '严重' THEN 1 ELSE 0 END) AS severe_count,
    SUM(CASE WHEN severity = '中度' THEN 1 ELSE 0 END) AS medium_count,
    SUM(CASE WHEN severity = '轻微' THEN 1 ELSE 0 END) AS light_count
FROM injury_record
WHERE IFNULL(is_deleted, 0) = 0
GROUP BY injury_location;

-- 专项技术月度汇总，用于统计看板趋势分析。
DROP VIEW IF EXISTS v_member9_technical_monthly_stats;

CREATE VIEW v_member9_technical_monthly_stats AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name AS athlete_name,
    DATE_FORMAT(tr.record_date, '%Y-%m') AS record_month,
    COUNT(tr.id) AS record_count,
    ROUND(AVG(IFNULL(tr.overall_score, 0)), 2) AS avg_overall_score,
    ROUND(AVG(IFNULL(tr.footwork_score, 0)), 2) AS avg_footwork_score
FROM athlete a
JOIN technical_record tr ON tr.athlete_id = a.id
GROUP BY a.id, a.student_no, a.name, DATE_FORMAT(tr.record_date, '%Y-%m');

-- 新体能训练模块月度统计。旧体测报告仍保留在 fitness_report 中，
-- 不与新的 0-10 体能训练评分混合计算。
DROP VIEW IF EXISTS v_member9_fitness_training_monthly_stats;

CREATE VIEW v_member9_fitness_training_monthly_stats AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name AS athlete_name,
    DATE_FORMAT(ftr.test_date, '%Y-%m') AS training_month,
    COUNT(ftr.id) AS record_count,
    ROUND(AVG(ftr.overall_score), 2) AS avg_overall_score,
    ROUND(AVG(ftr.sprint_30m), 2) AS avg_sprint_30m,
    ROUND(AVG(ftr.standing_long_jump), 2) AS avg_standing_long_jump,
    SUM(ftr.training_hours) AS total_training_hours
FROM fitness_training_record ftr
JOIN athlete a ON a.id = ftr.athlete_id
GROUP BY a.id, a.student_no, a.name, DATE_FORMAT(ftr.test_date, '%Y-%m');

DROP PROCEDURE IF EXISTS sp_member9_import_technical_records;
DROP PROCEDURE IF EXISTS sp_member9_export_monthly_full_data;

DELIMITER $$

CREATE PROCEDURE sp_member9_import_technical_records(
    IN p_batch_no VARCHAR(50),
    IN p_evaluator_id INT
)
main_block: BEGIN
    DECLARE v_error_count INT DEFAULT 0;
    DECLARE v_success_count INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, '专项技术批量导入失败，事务已回滚。' AS message;
    END;

    START TRANSACTION;

    UPDATE temp_import_technical_record
    SET student_no = TRIM(student_no)
    WHERE import_batch_no = p_batch_no;

    SELECT COUNT(*) INTO v_error_count
    FROM temp_import_technical_record t
    LEFT JOIN athlete a ON a.student_no = t.student_no
    WHERE t.import_batch_no = p_batch_no
      AND a.id IS NULL;

    IF v_error_count > 0 THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, CONCAT('存在 ', v_error_count, ' 条无效运动员编号，导入终止。') AS message;
        LEAVE main_block;
    END IF;

    INSERT INTO technical_record (
        athlete_id,
        record_date,
        evaluator_id,
        forehand_score,
        backhand_score,
        serve_score,
        footwork_score,
        reaction_score,
        overall_score,
        notes
    )
    SELECT
        a.id,
        t.record_date,
        p_evaluator_id,
        t.hit_score,
        t.hit_score,
        t.hit_score,
        LEAST(t.footwork_duration, 100),
        t.hit_score,
        t.hit_score,
        CONCAT('Excel批量导入；多球时长：', t.multi_ball_duration, '分钟；训练强度：', t.intensity)
    FROM temp_import_technical_record t
    JOIN athlete a ON a.student_no = t.student_no
    WHERE t.import_batch_no = p_batch_no;

    SET v_success_count = ROW_COUNT();

    DELETE FROM temp_import_technical_record
    WHERE import_batch_no = p_batch_no;

    COMMIT;

    SELECT 'OK' AS status, CONCAT('批量导入成功，共写入 ', v_success_count, ' 条专项技术记录。') AS message;
END$$

CREATE PROCEDURE sp_member9_export_monthly_full_data(IN p_month VARCHAR(7))
BEGIN
    SELECT
        a.student_no,
        a.name AS athlete_name,
        c.name AS coach_name,
        tp.plan_name,
        tp.start_date,
        tp.end_date,
        tp.training_content,
        tp.intensity,
        tp.hours,
        tp.status
    FROM training_plan tp
    JOIN athlete a ON a.id = tp.athlete_id
    JOIN coach c ON c.id = tp.coach_id
    WHERE DATE_FORMAT(tp.start_date, '%Y-%m') = p_month
    ORDER BY a.student_no, tp.start_date;

    SELECT
        a.student_no,
        a.name AS athlete_name,
        tr.record_date,
        tr.forehand_score,
        tr.backhand_score,
        tr.serve_score,
        tr.footwork_score,
        tr.reaction_score,
        tr.overall_score,
        tr.notes
    FROM technical_record tr
    JOIN athlete a ON a.id = tr.athlete_id
    WHERE DATE_FORMAT(tr.record_date, '%Y-%m') = p_month
    ORDER BY a.student_no, tr.record_date;

    SELECT
        a.student_no,
        a.name AS athlete_name,
        fr.test_date,
        fr.upper_strength,
        fr.lower_strength,
        fr.flexibility,
        fr.endurance,
        fr.speed,
        fr.overall_score,
        fr.notes
    FROM fitness_report fr
    JOIN athlete a ON a.id = fr.athlete_id
    WHERE DATE_FORMAT(fr.test_date, '%Y-%m') = p_month
    ORDER BY a.student_no, fr.test_date;

    SELECT
        a.student_no,
        a.name AS athlete_name,
        c.name AS coach_name,
        ftr.test_date,
        ftr.plan_name,
        ftr.training_hours,
        ftr.training_intensity,
        ftr.plan_status,
        ftr.sprint_30m,
        ftr.abdominal_endurance,
        ftr.back_endurance,
        ftr.lateral_slide,
        ftr.a_footwork,
        ftr.double_under,
        ftr.seated_rotation_throw,
        ftr.standing_long_jump,
        ftr.overall_score,
        ftr.notes
    FROM fitness_training_record ftr
    JOIN athlete a ON a.id = ftr.athlete_id
    JOIN coach c ON c.id = ftr.tester_id
    WHERE DATE_FORMAT(ftr.test_date, '%Y-%m') = p_month
    ORDER BY a.student_no, ftr.test_date;
END$$

DELIMITER ;
