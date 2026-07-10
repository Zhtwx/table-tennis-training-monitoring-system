-- ============================================================
-- 成员 2: 数据库约束、安全与高级对象补充脚本
-- 依赖脚本: sql/pingpang_db.sql
-- MySQL 5.5 兼容
-- 用法:
--   mysql -u root -p < sql/pingpang_db.sql
--   mysql -u root -p pingpang_db < sql/member2_advanced_database.sql
-- ============================================================

USE pingpang_db;


-- ============================================================
-- 第零部分: 约束增强（软删除字段）
-- 说明: 成员 8 伤病模块依赖 is_deleted；基础建表脚本尚未包含这些列。
-- ============================================================

ALTER TABLE injury_record
    ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 AFTER notes,
    ADD COLUMN deleted_at DATETIME NULL AFTER is_deleted,
    ADD COLUMN deleted_by VARCHAR(50) NULL AFTER deleted_at,
    ADD COLUMN delete_reason VARCHAR(200) NULL AFTER deleted_by;


-- ============================================================
-- 第一部分: 查询索引设计
-- 说明: 外键列在 InnoDB 中会自动建立辅助索引，本节主要补充业务查询索引。
-- ============================================================

-- 运动员档案: 支持按姓名、运动等级、伤病状态组合筛选。
CREATE INDEX idx_athlete_name ON athlete(name);
CREATE INDEX idx_athlete_level_status ON athlete(skill_level, injury_status);

-- 训练计划: 支持按运动员、日期区间、状态查询训练计划。
CREATE INDEX idx_training_plan_athlete_date ON training_plan(athlete_id, start_date, end_date);
CREATE INDEX idx_training_plan_coach_status ON training_plan(coach_id, status);

-- 专项技术记录: 支持按运动员和日期倒查技术评分。
CREATE INDEX idx_technical_record_athlete_date ON technical_record(athlete_id, record_date);
CREATE INDEX idx_technical_record_evaluator_date ON technical_record(evaluator_id, record_date);

-- 体能测试报告: 支持按运动员和测试日期查询历史体测。
CREATE INDEX idx_fitness_report_athlete_date ON fitness_report(athlete_id, test_date);
CREATE INDEX idx_fitness_report_tester_date ON fitness_report(tester_id, test_date);

-- 伤病记录: 支持康复跟踪、预警筛选，以及有效记录（未作废）查询。
CREATE INDEX idx_injury_record_athlete_status ON injury_record(athlete_id, recovery_status);
CREATE INDEX idx_injury_record_recovery_date ON injury_record(recovery_status, expected_recovery_date);
CREATE INDEX idx_injury_record_active ON injury_record(athlete_id, is_deleted, recovery_status);

-- 比赛记录: 支持按运动员、比赛日期和赛果统计。
CREATE INDEX idx_match_record_athlete_date ON match_record(athlete_id, match_date);
CREATE INDEX idx_match_record_result_date ON match_record(result, match_date);


-- ============================================================
-- 第二部分: 统计视图设计
-- ============================================================

DROP VIEW IF EXISTS v_athlete_comprehensive_profile;
DROP VIEW IF EXISTS v_monthly_training_summary;

-- 视图 1: 运动员综合档案视图
-- 用途: 运动员档案页、统计大屏、教练综合评估。
-- 说明: 伤病统计排除已软删除（is_deleted=1）的记录。
CREATE VIEW v_athlete_comprehensive_profile AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name,
    a.gender,
    a.team,
    a.skill_level,
    a.play_style,
    a.grip,
    a.injury_status,
    COUNT(DISTINCT tp.id) AS training_plan_count,
    COUNT(DISTINCT tr.id) AS technical_record_count,
    ROUND(AVG(tr.overall_score), 2) AS avg_technical_score,
    COUNT(DISTINCT fr.id) AS fitness_report_count,
    ROUND(AVG(fr.overall_score), 2) AS avg_fitness_score,
    COUNT(DISTINCT CASE WHEN ir.is_deleted = 0 THEN ir.id END) AS injury_record_count,
    COUNT(DISTINCT CASE
        WHEN ir.is_deleted = 0 AND ir.recovery_status IN ('治疗中','康复中')
        THEN ir.id
    END) AS active_injury_count,
    COUNT(DISTINCT mr.id) AS match_count,
    COUNT(DISTINCT CASE WHEN mr.result = '胜' THEN mr.id END) AS win_count
FROM athlete a
LEFT JOIN training_plan tp ON tp.athlete_id = a.id
LEFT JOIN technical_record tr ON tr.athlete_id = a.id
LEFT JOIN fitness_report fr ON fr.athlete_id = a.id
LEFT JOIN injury_record ir ON ir.athlete_id = a.id
LEFT JOIN match_record mr ON mr.athlete_id = a.id
GROUP BY
    a.id, a.student_no, a.name, a.gender, a.team,
    a.skill_level, a.play_style, a.grip, a.injury_status;

-- 视图 2: 月度技术训练汇总视图
-- 用途: 成员 9 统计分析与 ECharts 图表数据源。
-- 说明: 数据来源于 technical_record（专项技术评分），按月汇总。
CREATE VIEW v_monthly_training_summary AS
SELECT
    a.id AS athlete_id,
    a.student_no,
    a.name AS athlete_name,
    DATE_FORMAT(tr.record_date, '%Y-%m') AS training_month,
    COUNT(tr.id) AS technical_record_count,
    ROUND(AVG(tr.forehand_score), 2) AS avg_forehand_score,
    ROUND(AVG(tr.backhand_score), 2) AS avg_backhand_score,
    ROUND(AVG(tr.serve_score), 2) AS avg_serve_score,
    ROUND(AVG(tr.footwork_score), 2) AS avg_footwork_score,
    ROUND(AVG(tr.reaction_score), 2) AS avg_reaction_score,
    ROUND(AVG(tr.overall_score), 2) AS avg_overall_score
FROM athlete a
JOIN technical_record tr ON tr.athlete_id = a.id
GROUP BY
    a.id, a.student_no, a.name, DATE_FORMAT(tr.record_date, '%Y-%m');


-- ============================================================
-- 第三部分: 存储过程设计
-- ============================================================

DROP PROCEDURE IF EXISTS sp_filter_athletes_by_level;
DROP PROCEDURE IF EXISTS sp_get_monthly_training_summary;
DROP PROCEDURE IF EXISTS sp_refresh_athlete_injury_status;

DELIMITER $$

-- 存储过程 1: 按运动等级筛选运动员
-- 参数为空字符串时返回全部运动员。
CREATE PROCEDURE sp_filter_athletes_by_level(IN p_skill_level VARCHAR(20))
BEGIN
    SELECT
        id,
        student_no,
        name,
        gender,
        team,
        skill_level,
        play_style,
        injury_status
    FROM athlete
    WHERE p_skill_level IS NULL
       OR p_skill_level = ''
       OR skill_level = p_skill_level
    ORDER BY skill_level, name;
END$$

-- 存储过程 2: 查询指定月份训练技术汇总
-- p_training_month 格式: YYYY-MM，例如 2026-06。
CREATE PROCEDURE sp_get_monthly_training_summary(IN p_training_month VARCHAR(7))
BEGIN
    SELECT
        athlete_id,
        student_no,
        athlete_name,
        training_month,
        technical_record_count,
        avg_forehand_score,
        avg_backhand_score,
        avg_serve_score,
        avg_footwork_score,
        avg_reaction_score,
        avg_overall_score
    FROM v_monthly_training_summary
    WHERE p_training_month IS NULL
       OR p_training_month = ''
       OR training_month = p_training_month
    ORDER BY training_month DESC, avg_overall_score DESC;
END$$

-- 存储过程 3: 刷新单个运动员伤病状态
-- 由触发器复用，保证 athlete.injury_status 与 injury_record 保持一致。
-- 修复说明:
--   1. 无活跃伤病时，IFNULL 兜底为「健康」，避免把 NOT NULL 字段写成 NULL。
--   2. 仅统计未软删除（is_deleted=0）且未恢复的伤病记录。
CREATE PROCEDURE sp_refresh_athlete_injury_status(IN p_athlete_id INT)
BEGIN
    DECLARE v_status VARCHAR(20);

    SELECT
        CASE
            WHEN SUM(CASE WHEN recovery_status = '治疗中' AND severity = '严重' THEN 1 ELSE 0 END) > 0
                THEN '伤病中'
            WHEN SUM(CASE WHEN recovery_status = '治疗中' THEN 1 ELSE 0 END) > 0
                THEN '观察中'
            WHEN SUM(CASE WHEN recovery_status = '康复中' THEN 1 ELSE 0 END) > 0
                THEN '康复中'
            ELSE '健康'
        END
    INTO v_status
    FROM injury_record
    WHERE athlete_id = p_athlete_id
      AND is_deleted = 0
      AND recovery_status IN ('治疗中','康复中');

    UPDATE athlete
    SET injury_status = IFNULL(v_status, '健康')
    WHERE id = p_athlete_id;
END$$

DELIMITER ;


-- ============================================================
-- 第四部分: 触发器设计
-- ============================================================

DROP TRIGGER IF EXISTS trg_injury_after_insert;
DROP TRIGGER IF EXISTS trg_injury_after_update;
DROP TRIGGER IF EXISTS trg_injury_after_delete;

DELIMITER $$

-- 新增伤病记录后刷新运动员健康状态。
CREATE TRIGGER trg_injury_after_insert
AFTER INSERT ON injury_record
FOR EACH ROW
BEGIN
    CALL sp_refresh_athlete_injury_status(NEW.athlete_id);
END$$

-- 修改伤病记录后刷新运动员健康状态；若记录转移到其他运动员，同时刷新旧运动员。
-- 软删除（UPDATE is_deleted=1）也会走本触发器，从而自动回算健康状态。
CREATE TRIGGER trg_injury_after_update
AFTER UPDATE ON injury_record
FOR EACH ROW
BEGIN
    CALL sp_refresh_athlete_injury_status(NEW.athlete_id);
    IF OLD.athlete_id <> NEW.athlete_id THEN
        CALL sp_refresh_athlete_injury_status(OLD.athlete_id);
    END IF;
END$$

-- 物理删除伤病记录后刷新运动员健康状态。
CREATE TRIGGER trg_injury_after_delete
AFTER DELETE ON injury_record
FOR EACH ROW
BEGIN
    CALL sp_refresh_athlete_injury_status(OLD.athlete_id);
END$$

DELIMITER ;


-- ============================================================
-- 第五部分: 安全与备份补充说明 SQL
-- ============================================================

-- 只读账号: 用于统计大屏、答辩演示或数据审计，不能写入业务数据。
GRANT SELECT ON pingpang_db.* TO 'readonly_app'@'localhost' IDENTIFIED BY 'Readonly2026#';

-- 建议业务系统优先使用低权限账号，避免 Flask 应用直接使用 root。
FLUSH PRIVILEGES;


-- ============================================================
-- 验证语句
-- ============================================================

SELECT '>>> member2 advanced database objects setup complete! <<<' AS status;
SHOW COLUMNS FROM injury_record LIKE 'is_deleted';
SHOW INDEX FROM athlete;
SHOW INDEX FROM injury_record;
SHOW FULL TABLES WHERE Table_type = 'VIEW';
