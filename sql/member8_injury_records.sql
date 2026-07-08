-- ============================================================
-- 成员 8: 伤病记录模块业务 SQL
-- 依赖脚本:
--   1. sql/pingpang_db.sql
--   2. sql/member2_advanced_database.sql
-- 说明:
--   成员 2 已提供 sp_refresh_athlete_injury_status 与伤病触发器。
--   本脚本补充伤病登记、历史追溯、异常校验与触发器联动验证语句。
-- MySQL 5.5 兼容
-- ============================================================

USE pingpang_db;


-- ============================================================
-- 第一部分: 伤病模块结构补充
-- ============================================================

-- 若基础 injury_record 表尚未包含软删除字段，可执行以下 ALTER。
-- MySQL 5.5 不支持 ADD COLUMN IF NOT EXISTS，重复执行前请先检查字段是否已存在。
-- ALTER TABLE injury_record
--     ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0,
--     ADD COLUMN deleted_by VARCHAR(50),
--     ADD COLUMN deleted_at DATETIME,
--     ADD COLUMN delete_reason VARCHAR(120);

CREATE TABLE IF NOT EXISTS injury_followup (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    injury_record_id    INT NOT NULL,
    followup_date       DATE NOT NULL,
    pain_score          INT NOT NULL,
    training_limit      VARCHAR(160) NOT NULL,
    advice              VARCHAR(160) NOT NULL,
    reviewer            VARCHAR(30) NOT NULL,
    created_by          VARCHAR(50),
    create_time         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_followup_injury
        FOREIGN KEY (injury_record_id) REFERENCES injury_record(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_followup_pain_score CHECK (pain_score BETWEEN 0 AND 10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE INDEX idx_injury_followup_record_date
    ON injury_followup(injury_record_id, followup_date);


-- ============================================================
-- 第二部分: 伤病记录明细视图
-- ============================================================

DROP VIEW IF EXISTS v_injury_record_detail;

CREATE VIEW v_injury_record_detail AS
SELECT
    ir.id,
    ir.athlete_id,
    a.student_no,
    a.name AS athlete_name,
    a.gender,
    a.team,
    a.skill_level,
    a.injury_status AS current_injury_status,
    ir.injury_date,
    ir.injury_location,
    ir.injury_type,
    ir.severity,
    ir.diagnosis,
    ir.treatment,
    ir.recovery_status,
    ir.expected_recovery_date,
    COALESCE(ir.is_deleted, 0) AS is_deleted,
    ir.deleted_by,
    ir.deleted_at,
    ir.delete_reason,
    COUNT(fu.id) AS followup_count,
    MAX(fu.followup_date) AS latest_followup_date,
    CASE
        WHEN ir.recovery_status <> '已恢复'
             AND ir.expected_recovery_date IS NOT NULL
             AND ir.expected_recovery_date < CURDATE()
            THEN 1
        ELSE 0
    END AS is_overdue,
    ir.notes,
    ir.create_time,
    ir.update_time
FROM injury_record ir
JOIN athlete a ON a.id = ir.athlete_id
LEFT JOIN injury_followup fu ON fu.injury_record_id = ir.id
GROUP BY
    ir.id, ir.athlete_id, a.student_no, a.name, a.gender, a.team,
    a.skill_level, a.injury_status, ir.injury_date, ir.injury_location,
    ir.injury_type, ir.severity, ir.diagnosis, ir.treatment,
    ir.recovery_status, ir.expected_recovery_date, ir.is_deleted,
    ir.deleted_by, ir.deleted_at, ir.delete_reason, ir.notes,
    ir.create_time, ir.update_time;


-- ============================================================
-- 第三部分: 历史追溯、登记、复诊与作废存储过程
-- ============================================================

DROP PROCEDURE IF EXISTS sp_get_athlete_injury_history;
DROP PROCEDURE IF EXISTS sp_register_injury_record;
DROP PROCEDURE IF EXISTS sp_add_injury_followup;
DROP PROCEDURE IF EXISTS sp_archive_injury_record;

DELIMITER $$

-- 历史伤病追溯: 按运动员倒序查看完整伤病时间线。
CREATE PROCEDURE sp_get_athlete_injury_history(IN p_athlete_id INT)
BEGIN
    SELECT
        id,
        athlete_id,
        student_no,
        athlete_name,
        current_injury_status,
        injury_date,
        injury_location,
        injury_type,
        severity,
        diagnosis,
        treatment,
        recovery_status,
        expected_recovery_date,
        followup_count,
        latest_followup_date,
        is_overdue,
        notes
    FROM v_injury_record_detail
    WHERE athlete_id = p_athlete_id
      AND is_deleted = 0
    ORDER BY injury_date DESC, id DESC;
END$$

-- 伤病登记: 做基础异常校验，并依赖成员 2 触发器联动刷新 athlete.injury_status。
CREATE PROCEDURE sp_register_injury_record(
    IN p_athlete_id INT,
    IN p_injury_date DATE,
    IN p_injury_location VARCHAR(100),
    IN p_injury_type VARCHAR(100),
    IN p_severity VARCHAR(20),
    IN p_diagnosis TEXT,
    IN p_treatment TEXT,
    IN p_recovery_status VARCHAR(20),
    IN p_expected_recovery_date DATE,
    IN p_notes TEXT
)
main_block: BEGIN
    DECLARE v_athlete_exists INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SELECT 'ERROR' AS status, '伤病登记失败，事务已回滚，请检查外键、枚举和字段长度。' AS message;
    END;

    START TRANSACTION;

    SELECT COUNT(*) INTO v_athlete_exists
    FROM athlete
    WHERE id = p_athlete_id;

    IF v_athlete_exists = 0 THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '运动员不存在，伤病记录未写入。' AS message;
        LEAVE main_block;
    END IF;

    IF p_injury_date IS NULL THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '伤病日期不能为空。' AS message;
        LEAVE main_block;
    END IF;

    IF p_injury_location IS NULL OR TRIM(p_injury_location) = '' THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '伤病部位不能为空。' AS message;
        LEAVE main_block;
    END IF;

    IF p_injury_type IS NULL OR TRIM(p_injury_type) = '' THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '伤病类型不能为空。' AS message;
        LEAVE main_block;
    END IF;

    IF p_severity NOT IN ('轻微','中度','严重') THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '伤病程度只能为轻微、中度、严重。' AS message;
        LEAVE main_block;
    END IF;

    IF p_recovery_status NOT IN ('治疗中','康复中','已恢复') THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '恢复状态只能为治疗中、康复中、已恢复。' AS message;
        LEAVE main_block;
    END IF;

    IF p_expected_recovery_date IS NOT NULL AND p_expected_recovery_date < p_injury_date THEN
        ROLLBACK;
        SELECT 'ERROR' AS status, '预计恢复日期不能早于伤病日期。' AS message;
        LEAVE main_block;
    END IF;

    INSERT INTO injury_record (
        athlete_id,
        injury_date,
        injury_location,
        injury_type,
        severity,
        diagnosis,
        treatment,
        recovery_status,
        expected_recovery_date,
        notes
    ) VALUES (
        p_athlete_id,
        p_injury_date,
        TRIM(p_injury_location),
        TRIM(p_injury_type),
        p_severity,
        p_diagnosis,
        p_treatment,
        p_recovery_status,
        p_expected_recovery_date,
        p_notes
    );

    COMMIT;

    SELECT
        'OK' AS status,
        LAST_INSERT_ID() AS injury_record_id,
        a.id AS athlete_id,
        a.name AS athlete_name,
        a.injury_status AS refreshed_injury_status
    FROM athlete a
    WHERE a.id = p_athlete_id;
END$$

-- 复诊跟踪: 记录疼痛评分、训练限制和复诊建议。
CREATE PROCEDURE sp_add_injury_followup(
    IN p_injury_record_id INT,
    IN p_followup_date DATE,
    IN p_pain_score INT,
    IN p_training_limit VARCHAR(160),
    IN p_advice VARCHAR(160),
    IN p_reviewer VARCHAR(30),
    IN p_created_by VARCHAR(50)
)
main_block: BEGIN
    DECLARE v_injury_date DATE;
    DECLARE v_deleted TINYINT DEFAULT 0;

    SELECT injury_date, COALESCE(is_deleted, 0)
    INTO v_injury_date, v_deleted
    FROM injury_record
    WHERE id = p_injury_record_id;

    IF v_injury_date IS NULL OR v_deleted = 1 THEN
        SELECT 'ERROR' AS status, '伤病记录不存在或已作废，不能新增复诊。' AS message;
        LEAVE main_block;
    END IF;

    IF p_followup_date < v_injury_date THEN
        SELECT 'ERROR' AS status, '复诊日期不能早于伤病日期。' AS message;
        LEAVE main_block;
    END IF;

    IF p_pain_score < 0 OR p_pain_score > 10 THEN
        SELECT 'ERROR' AS status, '疼痛评分必须介于 0 到 10。' AS message;
        LEAVE main_block;
    END IF;

    INSERT INTO injury_followup (
        injury_record_id, followup_date, pain_score,
        training_limit, advice, reviewer, created_by
    ) VALUES (
        p_injury_record_id, p_followup_date, p_pain_score,
        p_training_limit, p_advice, p_reviewer, p_created_by
    );

    SELECT 'OK' AS status, LAST_INSERT_ID() AS followup_id;
END$$

-- 作废归档: 不物理删除历史医疗信息，且重新刷新运动员健康状态。
CREATE PROCEDURE sp_archive_injury_record(
    IN p_injury_record_id INT,
    IN p_deleted_by VARCHAR(50),
    IN p_delete_reason VARCHAR(120)
)
main_block: BEGIN
    DECLARE v_athlete_id INT;

    SELECT athlete_id INTO v_athlete_id
    FROM injury_record
    WHERE id = p_injury_record_id
      AND COALESCE(is_deleted, 0) = 0;

    IF v_athlete_id IS NULL THEN
        SELECT 'ERROR' AS status, '伤病记录不存在或已作废。' AS message;
        LEAVE main_block;
    END IF;

    UPDATE injury_record
    SET is_deleted = 1,
        deleted_by = p_deleted_by,
        deleted_at = NOW(),
        delete_reason = p_delete_reason
    WHERE id = p_injury_record_id;

    CALL sp_refresh_athlete_injury_status(v_athlete_id);

    SELECT 'OK' AS status, p_injury_record_id AS archived_record_id;
END$$

DELIMITER ;


-- ============================================================
-- 第四部分: 常用业务查询
-- ============================================================

-- 伤病记录管理列表: 支持程度、恢复状态与运动员关键词筛选。
SELECT
    id,
    athlete_id,
    student_no,
    athlete_name,
    current_injury_status,
    injury_date,
    injury_location,
    injury_type,
    severity,
    recovery_status,
    expected_recovery_date,
    followup_count,
    latest_followup_date,
    is_overdue
FROM v_injury_record_detail
WHERE recovery_status IN ('治疗中','康复中','已恢复')
  AND is_deleted = 0
ORDER BY injury_date DESC, id DESC;

-- 康复跟踪预警: 未恢复且预计恢复日期临近或已逾期。
SELECT
    id,
    athlete_name,
    injury_location,
    severity,
    recovery_status,
    expected_recovery_date,
    is_overdue
FROM v_injury_record_detail
WHERE recovery_status IN ('治疗中','康复中')
  AND is_deleted = 0
ORDER BY is_overdue DESC, expected_recovery_date ASC, severity DESC;


-- ============================================================
-- 第五部分: 触发器联动验证
-- ============================================================

-- 验证 1: 登记严重治疗中伤病后，athlete.injury_status 应自动变为“伤病中”。
CALL sp_register_injury_record(
    1,
    CURDATE(),
    '右膝',
    '半月板损伤',
    '严重',
    '右膝疼痛伴活动受限，暂停对抗训练。',
    '制动休息，预约复查。',
    '治疗中',
    DATE_ADD(CURDATE(), INTERVAL 21 DAY),
    '触发器联动验证数据'
);
SELECT id, name, injury_status FROM athlete WHERE id = 1;

-- 验证 2: 运动员不存在时应返回错误，且不写入 injury_record。
CALL sp_register_injury_record(
    9999,
    CURDATE(),
    '左肩',
    '拉伤',
    '轻微',
    '无效运动员测试',
    '无',
    '治疗中',
    DATE_ADD(CURDATE(), INTERVAL 7 DAY),
    '异常处理验证数据'
);

-- 验证 3: 查询运动员历史伤病时间线。
CALL sp_get_athlete_injury_history(1);

-- 验证 4: 新增复诊跟踪。
CALL sp_add_injury_followup(
    1,
    CURDATE(),
    2,
    '控制发球训练量，不安排高强度对抗。',
    '三天后复查疼痛变化。',
    '陈指导',
    'admin'
);

SELECT '>>> member8 injury records module SQL ready! <<<' AS status;
