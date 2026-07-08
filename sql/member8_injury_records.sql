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
-- 第一部分: 伤病记录明细视图
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
JOIN athlete a ON a.id = ir.athlete_id;


-- ============================================================
-- 第二部分: 历史追溯与登记存储过程
-- ============================================================

DROP PROCEDURE IF EXISTS sp_get_athlete_injury_history;
DROP PROCEDURE IF EXISTS sp_register_injury_record;

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
        is_overdue,
        notes
    FROM v_injury_record_detail
    WHERE athlete_id = p_athlete_id
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

DELIMITER ;


-- ============================================================
-- 第三部分: 常用业务查询
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
    is_overdue
FROM v_injury_record_detail
WHERE recovery_status IN ('治疗中','康复中','已恢复')
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
ORDER BY is_overdue DESC, expected_recovery_date ASC, severity DESC;


-- ============================================================
-- 第四部分: 触发器联动验证
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

SELECT '>>> member8 injury records module SQL ready! <<<' AS status;
