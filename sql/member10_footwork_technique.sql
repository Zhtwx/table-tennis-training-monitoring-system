-- ============================================================
-- 乒乓球训练监控管理系统 · 步法训练 & 技战术训练 模块重构
-- MySQL 5.5+ 兼容
-- 用法: mysql -u root -p pingpang_db < member10_footwork_technique.sql
-- ============================================================

USE pingpang_db;

-- ------------------------------------------------------------
-- 1. 统一数据字典表（二级联动）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sys_dictionary (
    id              INT             AUTO_INCREMENT  PRIMARY KEY  COMMENT '主键ID',
    category_type   VARCHAR(30)     NOT NULL                     COMMENT '分类类型：footwork=步法, technique_tactic=技战术, landing_point=落点分布',
    parent_id       INT             NOT NULL DEFAULT 0           COMMENT '父级ID，0 表示一级节点',
    dict_code       VARCHAR(50)     NOT NULL                     COMMENT '字典编码（程序引用，唯一）',
    dict_name       VARCHAR(100)    NOT NULL                     COMMENT '字典名称（界面展示）',
    sort_order      INT             NOT NULL DEFAULT 0           COMMENT '排序权重，升序排列',
    is_enabled      TINYINT(1)      NOT NULL DEFAULT 1           COMMENT '是否启用：1=启用，0=禁用',
    remark          VARCHAR(200)                                 COMMENT '备注说明',
    create_time     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
    update_time     TIMESTAMP                                    COMMENT '更新时间',

    UNIQUE KEY uk_dict_code (dict_code),
    INDEX idx_dict_category_parent (category_type, parent_id),
    INDEX idx_dict_enabled_sort (is_enabled, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='统一数据字典表（二级联动）';


-- ------------------------------------------------------------
-- 2. 步法训练业务表（原「专项技术录入」重构）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS footwork_training (
    id                  INT             AUTO_INCREMENT  PRIMARY KEY  COMMENT '主键ID',
    athlete_id          INT             NOT NULL                     COMMENT '运动员ID，关联 athlete.id',
    training_date       DATE            NOT NULL                     COMMENT '训练日期',
    footwork_dict_id    INT             NOT NULL                     COMMENT '步法类型ID，关联 sys_dictionary.id',
    duration_minutes    SMALLINT        NOT NULL DEFAULT 0           COMMENT '训练时长（分钟）',
    set_count           SMALLINT        NOT NULL DEFAULT 0           COMMENT '训练组数（整型）',
    note                TEXT                                         COMMENT '训练备注（技术问题、教练建议等定性描述）',
    created_by          INT                                          COMMENT '录入人ID，关联 coach.id',
    create_time         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
    update_time         TIMESTAMP                                    COMMENT '更新时间',

    CONSTRAINT fk_footwork_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_footwork_dict
        FOREIGN KEY (footwork_dict_id) REFERENCES sys_dictionary(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_footwork_creator
        FOREIGN KEY (created_by) REFERENCES coach(id)
        ON DELETE SET NULL ON UPDATE CASCADE,

    INDEX idx_footwork_athlete_date (athlete_id, training_date),
    INDEX idx_footwork_date (training_date),
    INDEX idx_footwork_dict (footwork_dict_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='步法训练记录表';


-- ------------------------------------------------------------
-- 3. 技战术训练业务表（原「专项技术查询」重构）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS technique_tactic_training (
    id                      INT             AUTO_INCREMENT  PRIMARY KEY  COMMENT '主键ID',

    -- 执行记录（考核执行层面）
    athlete_id              INT             NOT NULL                     COMMENT '运动员ID',
    training_date           DATE            NOT NULL                     COMMENT '训练日期',
    technique_dict_id       INT             NOT NULL                     COMMENT '技战术字典ID（二级叶子节点）',
    multi_ball_count        INT             NOT NULL DEFAULT 0           COMMENT '多球训练球数',
    serve_frequency         ENUM('高','中','低') NOT NULL DEFAULT '中'  COMMENT '发球频率',
    plan_execution_rate     DECIMAL(5,2)    NOT NULL DEFAULT 0.00        COMMENT '计划执行率（0-100%）',

    -- 效果反馈（考核真实训练效果）
    on_table_rate           DECIMAL(5,2)                                 COMMENT '上台率（%），核心量化指标',
    landing_distribution    VARCHAR(500)                                 COMMENT '落点分布摘要，如：近台左侧（较为集中）、中台（集中）',
    qualitative_comment     TEXT                                         COMMENT '主观文字打分/定性描述',

    created_by              INT                                          COMMENT '录入人ID',
    create_time             TIMESTAMP       DEFAULT CURRENT_TIMESTAMP    COMMENT '创建时间',
    update_time             TIMESTAMP                                    COMMENT '更新时间',

    CONSTRAINT fk_tt_athlete
        FOREIGN KEY (athlete_id) REFERENCES athlete(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tt_technique_dict
        FOREIGN KEY (technique_dict_id) REFERENCES sys_dictionary(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_tt_creator
        FOREIGN KEY (created_by) REFERENCES coach(id)
        ON DELETE SET NULL ON UPDATE CASCADE,

    INDEX idx_tt_athlete_date (athlete_id, training_date),
    INDEX idx_tt_date (training_date),
    INDEX idx_tt_technique (technique_dict_id),
    INDEX idx_tt_on_table_rate (on_table_rate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='技战术训练记录表（计划执行 + 效果评估）';


-- ------------------------------------------------------------
-- 4. 技战术训练 · 落点分布关联表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS technique_tactic_landing (
    id                          INT     AUTO_INCREMENT  PRIMARY KEY,
    technique_tactic_id         INT     NOT NULL        COMMENT '技战术训练记录ID',
    landing_dict_id             INT     NOT NULL        COMMENT '落点区域字典ID',
    concentration_level         VARCHAR(20) NOT NULL DEFAULT '' COMMENT '集中程度：集中/较为集中/一般/较为分散/分散',

    CONSTRAINT fk_ttl_training
        FOREIGN KEY (technique_tactic_id) REFERENCES technique_tactic_training(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_ttl_landing_dict
        FOREIGN KEY (landing_dict_id) REFERENCES sys_dictionary(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    UNIQUE KEY uk_tt_landing (technique_tactic_id, landing_dict_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='技战术训练落点分布关联表';


-- ------------------------------------------------------------
-- 5. 列表页聚合统计视图
-- ------------------------------------------------------------
DROP VIEW IF EXISTS v_technique_tactic_stats;
CREATE VIEW v_technique_tactic_stats AS
SELECT
    COUNT(*)                                        AS total_records,
    COALESCE(SUM(multi_ball_count), 0)              AS total_ball_count,
    COALESCE(ROUND(AVG(on_table_rate), 2), 0)       AS avg_on_table_rate,
    COALESCE(ROUND(AVG(plan_execution_rate), 2), 0) AS avg_plan_execution_rate
FROM technique_tactic_training;


-- ============================================================
-- 字典初始化数据
-- ============================================================

-- 步法字典
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('footwork', 0, 'footwork_root', '步法', 0);

SET @footwork_root_id = LAST_INSERT_ID();

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('footwork', @footwork_root_id, 'single_step',    '单步',     10),
('footwork', @footwork_root_id, 'parallel_step',  '并步',     20),
('footwork', @footwork_root_id, 'stride_step',    '跨步',     30),
('footwork', @footwork_root_id, 'cross_step',     '交叉步',   40),
('footwork', @footwork_root_id, 'shuffle_step',   '碎步',     50),
('footwork', @footwork_root_id, 'side_step',      '侧身步',   60),
('footwork', @footwork_root_id, 'composite_step', '综合步法', 70),
('footwork', @footwork_root_id, 'recovery_step',  '还原步',   80);

-- 技战术一级节点
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', 0, 'serve',                 '发球',       100),
('technique_tactic', 0, 'receive',               '接发球',     200),
('technique_tactic', 0, 'attack_technique',      '进攻技术',   300),
('technique_tactic', 0, 'defense_transition',    '防守/过渡',  400),
('technique_tactic', 0, 'first_three_tactic',    '前三板战术', 500),
('technique_tactic', 0, 'rally_tactic',          '相持战术',   600),
('technique_tactic', 0, 'placement_tactic',      '落点战术',   700),
('technique_tactic', 0, 'attack_defense_switch', '攻防转换',   800);

SET @serve_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'serve');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @serve_id, 'serve_underspin', '发下旋球', 10),
('technique_tactic', @serve_id, 'serve_topspin',   '发上旋球', 20),
('technique_tactic', @serve_id, 'serve_sidespin',  '发侧旋球', 30),
('technique_tactic', @serve_id, 'serve_long',      '发长球',   40),
('technique_tactic', @serve_id, 'serve_short',     '发短球',   50);

SET @receive_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'receive');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @receive_id, 'receive_flick',      '挑打',     10),
('technique_tactic', @receive_id, 'receive_push_short', '摆短',     20),
('technique_tactic', @receive_id, 'receive_loop',       '接发抢拉', 30),
('technique_tactic', @receive_id, 'receive_control',    '控接',     40);

SET @attack_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'attack_technique');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @attack_id, 'forehand_loop',  '正手前冲弧圈球', 10),
('technique_tactic', @attack_id, 'backhand_flick', '反手拧拉',       20),
('technique_tactic', @attack_id, 'forehand_smash', '正手扣杀',       30),
('technique_tactic', @attack_id, 'backhand_loop',  '反手弧圈',       40);

SET @defense_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'defense_transition');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @defense_id, 'block',        '挡球',     10),
('technique_tactic', @defense_id, 'chop',         '削球',     20),
('technique_tactic', @defense_id, 'lob',          '放高球',   30),
('technique_tactic', @defense_id, 'counter_loop', '对拉过渡', 40);

SET @first3_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'first_three_tactic');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @first3_id, 'serve_attack',      '发球抢攻',   10),
('technique_tactic', @first3_id, 'receive_attack',    '接发抢攻',   20),
('technique_tactic', @first3_id, 'third_ball_attack', '第三板进攻', 30);

SET @rally_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'rally_tactic');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @rally_id, 'change_pace',      '变节奏', 10),
('technique_tactic', @rally_id, 'change_spin',      '变旋转', 20),
('technique_tactic', @rally_id, 'change_direction', '变线路', 30);

SET @placement_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'placement_tactic');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @placement_id, 'wide_angle',  '大角度调动', 10),
('technique_tactic', @placement_id, 'body_attack', '追身球',     20),
('technique_tactic', @placement_id, 'deep_short',  '深浅结合',   30);

SET @switch_id = (SELECT id FROM sys_dictionary WHERE dict_code = 'attack_defense_switch');
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('technique_tactic', @switch_id, 'defense_to_attack', '防转攻', 10),
('technique_tactic', @switch_id, 'attack_to_defense', '攻转防', 20);

-- 落点区域字典
INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('landing_point', 0, 'landing_root', '落点区域', 0);

SET @landing_root_id = LAST_INSERT_ID();

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order) VALUES
('landing_point', @landing_root_id, 'near_left',  '近台左侧', 10),
('landing_point', @landing_root_id, 'near_right', '近台右侧', 20),
('landing_point', @landing_root_id, 'mid_table',  '中台',     30),
('landing_point', @landing_root_id, 'far_table',  '远台',     40),
('landing_point', @landing_root_id, 'body_line',  '追身位',   50),
('landing_point', @landing_root_id, 'wide_left',  '大角度左', 60),
('landing_point', @landing_root_id, 'wide_right', '大角度右', 70);

SELECT '>>> member10 footwork & technique tactic module ready <<<' AS status;
