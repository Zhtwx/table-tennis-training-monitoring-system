-- ============================================================
-- 乒乓球运动员综合训练管理系统 · 完整数据库脚本
-- MySQL 5.5 兼容
-- 用法: mysql -u root -p < pingpang_db.sql
-- ============================================================

-- ============================================================
-- 第一部分: 建库
-- ============================================================
DROP DATABASE IF EXISTS pingpang_db;
CREATE DATABASE pingpang_db
    DEFAULT CHARACTER SET utf8
    DEFAULT COLLATE utf8_general_ci;

USE pingpang_db;


-- ============================================================
-- 第二部分: 建表（8 张表）
-- 命名规范: 全小写+下划线, 主键 id, 外键 关联表名_id
-- 评分 DECIMAL(5,2), 状态 ENUM, 时间 TIMESTAMP
-- ============================================================

-- 表 1: athlete  运动员
CREATE TABLE athlete (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    student_no      VARCHAR(20)     NOT NULL UNIQUE,
    name            VARCHAR(50)     NOT NULL,
    gender          ENUM('男','女') NOT NULL,
    birth_date      DATE,
    team            VARCHAR(100),
    skill_level     ENUM('二级运动员','一级运动员','国家级','健将级','青年队') NOT NULL,
    play_style      VARCHAR(100),
    grip            VARCHAR(50),
    contact_phone   VARCHAR(20),
    primary_coach_id INT,
    injury_status   ENUM('健康','观察中','康复中','伤病中')
                        NOT NULL DEFAULT '健康',
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    update_time     TIMESTAMP,
    INDEX idx_athlete_primary_coach (primary_coach_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 2: coach  教练员
CREATE TABLE coach (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL,
    gender          ENUM('男','女'),
    specialty       VARCHAR(100),
    contact_phone   VARCHAR(20),
    email           VARCHAR(100)    UNIQUE,
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

ALTER TABLE athlete
    ADD CONSTRAINT fk_athlete_primary_coach
        FOREIGN KEY (primary_coach_id) REFERENCES coach(id)
        ON DELETE RESTRICT ON UPDATE CASCADE;

-- 表 3: training_plan  训练计划
CREATE TABLE training_plan (
    id               INT            AUTO_INCREMENT  PRIMARY KEY,
    athlete_id       INT            NOT NULL,
    coach_id         INT            NOT NULL,
    plan_name        VARCHAR(100)   NOT NULL,
    start_date       DATE           NOT NULL,
    end_date         DATE           NOT NULL,
    training_content TEXT,
    intensity        ENUM('低','中','高','极高') NOT NULL,
    hours            DECIMAL(4,1),
    status           ENUM('进行中','已完成','已取消') DEFAULT '进行中',
    create_time      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    update_time      TIMESTAMP,

    CONSTRAINT fk_training_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_training_coach
        FOREIGN KEY (coach_id) REFERENCES coach(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 4: technical_record  专项技术记录
CREATE TABLE technical_record (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    athlete_id      INT             NOT NULL,
    record_date     DATE            NOT NULL,
    evaluator_id    INT,
    forehand_score  DECIMAL(5,2),
    backhand_score  DECIMAL(5,2),
    serve_score     DECIMAL(5,2),
    footwork_score  DECIMAL(5,2),
    reaction_score  DECIMAL(5,2),
    overall_score   DECIMAL(5,2),
    notes           TEXT,
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_tech_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tech_evaluator
        FOREIGN KEY (evaluator_id) REFERENCES coach(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 5: fitness_report  体能测试报告
CREATE TABLE fitness_report (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    athlete_id      INT             NOT NULL,
    test_date       DATE            NOT NULL,
    tester_id       INT,
    upper_strength  DECIMAL(5,2),
    lower_strength  DECIMAL(5,2),
    flexibility     DECIMAL(5,2),
    endurance       DECIMAL(5,2),
    speed           DECIMAL(5,2),
    overall_score   DECIMAL(5,2),
    notes           TEXT,
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_fitness_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_fitness_tester
        FOREIGN KEY (tester_id) REFERENCES coach(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 6: injury_record  伤病记录
CREATE TABLE injury_record (
    id                      INT          AUTO_INCREMENT  PRIMARY KEY,
    athlete_id              INT          NOT NULL,
    injury_date             DATE         NOT NULL,
    injury_location         VARCHAR(100) NOT NULL,
    injury_type             VARCHAR(100),
    severity                ENUM('轻微','中度','严重') NOT NULL,
    diagnosis               TEXT,
    treatment               TEXT,
    recovery_status         ENUM('治疗中','康复中','已恢复') DEFAULT '治疗中',
    expected_recovery_date  DATE,
    notes                   TEXT,
    create_time             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    update_time             TIMESTAMP,

    CONSTRAINT fk_injury_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 7: user_account  用户账号
CREATE TABLE user_account (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    username        VARCHAR(50)     NOT NULL UNIQUE,
    password_hash   VARCHAR(255)    NOT NULL,
    role            ENUM('管理员','教练员') NOT NULL,
    coach_id        INT             UNIQUE,
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_user_coach
        FOREIGN KEY (coach_id) REFERENCES coach(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- 表 8: match_record  比赛成绩记录
CREATE TABLE match_record (
    id              INT             AUTO_INCREMENT  PRIMARY KEY,
    athlete_id      INT             NOT NULL,
    match_date      DATE            NOT NULL,
    match_name      VARCHAR(100)    NOT NULL,
    opponent        VARCHAR(100),
    result          ENUM('胜','负','平') NOT NULL,
    score           VARCHAR(50),
    notes           TEXT,
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_match_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


-- ============================================================
-- 第三部分: 初始测试数据
-- ============================================================

INSERT INTO athlete (student_no, name, gender, birth_date, team, skill_level, play_style, grip, contact_phone) VALUES
('2026001', '王一鸣', '男', '2001-05-12', '校乒乓球队', '一级运动员', '右手横板快攻结合弧圈', '右手横板', '13800001001'),
('2026002', '李清扬', '女', '2002-08-23', '校乒乓球队', '二级运动员', '左手横板两面弧圈',     '左手横板', '13800001002'),
('2026003', '陈昊然', '男', '1999-11-03', '省青年队',   '国家级',     '右手直板近台快攻',       '右手直板', '13800001003'),
('2026004', '赵若溪', '女', '2002-02-17', '校乒乓球队', '一级运动员', '右手横板反手快拨',       '右手横板', '13800001004'),
('2026005', '孙旋球', '男', '2000-09-30', '省青年队',   '一级运动员', '右手横板削球打法',       '右手横板', '13800001005'),
('2026006', '刘扣杀', '男', '2001-06-08', '校乒乓球队', '二级运动员', '左手直板快攻结合弧圈',   '左手直板', '13800001006');

INSERT INTO coach (name, gender, specialty, contact_phone, email) VALUES
('陈指导', '男', '技术训练', '13900002001', 'chen@pingpang.cn'),
('刘指导', '女', '体能训练', '13900002002', 'liu@pingpang.cn'),
('马指导', '男', '战术分析', '13900002003', 'ma@pingpang.cn');

UPDATE athlete
SET primary_coach_id = CASE id
    WHEN 1 THEN 1
    WHEN 2 THEN 2
    WHEN 3 THEN 3
    WHEN 4 THEN 1
    WHEN 5 THEN 2
    WHEN 6 THEN 3
END
WHERE id BETWEEN 1 AND 6;

INSERT INTO training_plan (athlete_id, coach_id, plan_name, start_date, end_date, training_content, intensity, hours, status) VALUES
(1, 1, '正手暴冲特训',  '2026-06-01', '2026-06-14', '正手位发力优化 + 连续拉球',                '高', 28.0, '已完成'),
(1, 3, '战术演练',      '2026-06-15', '2026-06-28', '发抢战术套路 + 第三板进攻',                 '中', 21.0, '已完成'),
(2, 1, '反手强化',      '2026-06-01', '2026-06-14', '反手拧拉 + 弹击衔接',                       '中', 24.0, '已完成'),
(2, 2, '体能储备期',    '2026-06-15', '2026-07-05', '下肢力量 + 核心稳定性',                     '高', 30.0, '已完成'),
(3, 1, '大赛前集训',    '2026-07-01', '2026-07-14', '模拟对抗 + 关键分处理',                     '高', 28.0, '进行中'),
(4, 2, '基础体能提升',  '2026-06-20', '2026-07-10', '入门体能训练 + 柔韧性基础',                 '低', 18.0, '进行中'),
(5, 3, '发球旋转特训',  '2026-06-05', '2026-06-25', '下旋/侧旋/逆旋转发球专项',                  '中', 20.0, '已完成'),
(6, 1, '入门技术训练',  '2026-07-01', '2026-07-12', '正反手基本功 + 步法入门',                   '低', 16.0, '进行中');

INSERT INTO technical_record (athlete_id, record_date, evaluator_id, forehand_score, backhand_score, serve_score, footwork_score, reaction_score, overall_score) VALUES
(1, '2026-06-14', 1, 92.5, 88.0, 90.0, 85.0, 91.0, 89.3),
(1, '2026-06-28', 3, 93.0, 88.5, 91.0, 86.5, 92.0, 90.2),
(2, '2026-06-14', 1, 85.0, 90.0, 87.0, 88.0, 86.0, 87.2),
(2, '2026-07-05', 2, 86.5, 91.0, 88.0, 89.5, 87.5, 88.5),
(3, '2026-06-25', 1, 95.0, 92.0, 93.5, 90.0, 94.0, 92.9),
(5, '2026-06-25', 3, 82.0, 80.0, 88.0, 78.0, 81.0, 81.8);

INSERT INTO fitness_report (athlete_id, test_date, tester_id, upper_strength, lower_strength, flexibility, endurance, speed, overall_score) VALUES
(1, '2026-06-14', 2, 85.5, 90.0, 78.0, 88.0, 92.0, 86.7),
(2, '2026-06-14', 2, 78.0, 82.0, 88.0, 85.0, 80.0, 82.6),
(2, '2026-07-05', 2, 80.5, 85.0, 89.5, 87.0, 82.0, 84.8),
(3, '2026-06-25', 2, 90.0, 95.0, 80.0, 92.0, 94.0, 90.2),
(5, '2026-06-25', 2, 76.0, 80.0, 85.0, 78.0, 82.0, 80.2);

INSERT INTO injury_record (athlete_id, injury_date, injury_location, injury_type, severity, diagnosis, treatment, recovery_status) VALUES
(1, '2026-05-10', '右肩', '肌肉拉伤',   '中度', '肩袖肌腱炎，建议理疗+减量训练',       '超声波理疗 + 弹力带康复',           '已恢复'),
(3, '2026-06-30', '腰椎', '椎间盘突出', '严重', 'L4-L5椎间盘轻微突出，建议停训治疗',    '牵引 + 核心肌群康复训练',          '治疗中'),
(4, '2026-06-15', '左膝', '韧带扭伤',   '轻微', '左膝内侧副韧带一级扭伤',               '冰敷 + 制动休息 + 氨糖补充',       '康复中');

INSERT INTO user_account (username, password_hash, role, coach_id) VALUES
('admin',  'scrypt:32768:8:1$hashed_admin_password_placeholder',  '管理员', NULL),
('coach1', 'scrypt:32768:8:1$hashed_coach1_password_placeholder', '教练员', 1),
('coach2', 'scrypt:32768:8:1$hashed_coach2_password_placeholder', '教练员', 2);

INSERT INTO match_record (athlete_id, match_date, match_name, opponent, result, score, notes) VALUES
(1, '2026-05-15', '2026全国大学生锦标赛-男单', '刘强',   '胜', '3:1', '正手位拉球得分率较高'),
(1, '2026-05-16', '2026全国大学生锦标赛-男单', '赵明',   '胜', '3:0', '发球轮次优势明显'),
(1, '2026-05-17', '2026全国大学生锦标赛-男单', '何伟',   '负', '1:3', '反手位防守漏洞暴露'),
(3, '2026-06-01', '省青联赛季前热身赛',         '孙磊',   '胜', '3:2', '关键分处理果断'),
(3, '2026-06-15', '省青联赛第一轮',             '李浩',   '负', '2:3', '正手失误偏多需加强'),
(5, '2026-05-20', '校际交流赛',                 '张强',   '胜', '3:1', '削球旋转变化效果显著');


-- ============================================================
-- 第四部分: 事务演示（ACID 教学示例）
-- ============================================================

-- 示例 1: 训练计划 + 体能报告同步提交
START TRANSACTION;
INSERT INTO training_plan (athlete_id, coach_id, plan_name, start_date, end_date,
    training_content, intensity, hours, status)
VALUES (1, 1, '暑期强化集训', '2026-07-01', '2026-07-15',
    '每天上午体能训练 2h + 下午技术专项 2h', '高', 36.0, '已完成');
INSERT INTO fitness_report (athlete_id, test_date, tester_id,
    upper_strength, lower_strength, flexibility, endurance, speed, overall_score)
VALUES (1, '2026-07-01', 1, 85.5, 90.0, 78.0, 88.0, 92.0,
    ROUND((85.5+90.0+78.0+88.0+92.0)/5, 2));
COMMIT;

-- 示例 2: SAVEPOINT 部分回滚（体能数据回滚，保留训练计划）
START TRANSACTION;
INSERT INTO training_plan (athlete_id, coach_id, plan_name, start_date, end_date,
    training_content, intensity, hours, status)
VALUES (2, 2, '伤病恢复训练', '2026-07-01', '2026-07-14',
    '低强度技术维护 + 康复拉伸', '低', 14.0, '进行中');
SAVEPOINT after_plan;
INSERT INTO fitness_report (athlete_id, test_date, tester_id,
    upper_strength, lower_strength, flexibility, endurance, speed, overall_score)
VALUES (2, '2026-07-01', 2, 60.0, 65.0, 70.0, 72.0, 80.0,
    ROUND((60.0+65.0+70.0+72.0+80.0)/5, 2));
ROLLBACK TO SAVEPOINT after_plan;
COMMIT;

-- ============================================================
-- 第五部分: MySQL 数据库用户权限（作业要求"不同账号不同权限"）
-- ============================================================

-- 教练用户: 仅增删改查业务数据，不能改表结构
GRANT SELECT, INSERT, UPDATE, DELETE ON pingpang_db.*
    TO 'coach_app'@'localhost' IDENTIFIED BY 'Coach2026#';

-- 管理员用户: 全部权限
GRANT ALL PRIVILEGES ON pingpang_db.*
    TO 'admin_app'@'localhost' IDENTIFIED BY 'Admin2026#';

FLUSH PRIVILEGES;


-- 验证
SELECT '>>> pingpang_db setup complete! <<<' AS status;
SHOW TABLES;


-- ============================================================
-- ACID 原理说明
-- ============================================================
--
-- 原子性 (Atomicity):
--   START TRANSACTION → 多条 SQL 视为一个逻辑单元
--   COMMIT 全部生效 / ROLLBACK 全部撤销
--   底层: InnoDB undo log 记录旧值，回滚时逐条逆向恢复
--
-- 一致性 (Consistency):
--   事务前后数据库均满足所有约束条件
--   外键: athlete_id/coach_id 必须引用存在行
--   NOT NULL: 必填字段不可为空
--   ENUM: intensity/severity/status 仅允许预定义值
--
-- 隔离性 (Isolation):
--   默认 REPEATABLE-READ: 同一事务内读取的数据保持一致快照
--   其他事务未提交的修改对本事务不可见（InnoDB MVCC + Read View）
--   并发写操作通过行锁（record lock + gap lock）防冲突
--
-- 持久性 (Durability):
--   COMMIT 后数据先写入 redo log（WAL 策略），再异步刷盘
--   即使系统崩溃，重启后 redo log 重放恢复所有已提交数据
--   binlog 可用于增量备份和主从复制
-- ============================================================
