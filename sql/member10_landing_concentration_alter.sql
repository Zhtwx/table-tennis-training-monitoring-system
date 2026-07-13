-- 已有库升级：落点关联表增加集中程度字段，并恢复落点区域字典
USE pingpang_db;

ALTER TABLE technique_tactic_landing
    ADD COLUMN concentration_level VARCHAR(20) NOT NULL DEFAULT '' COMMENT '集中程度' AFTER landing_dict_id;

DELETE FROM sys_dictionary WHERE category_type = 'landing_point' AND parent_id > 0;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'near_left', '近台左侧', 10 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'near_right', '近台右侧', 20 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'mid_table', '中台', 30 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'far_table', '远台', 40 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'body_line', '追身位', 50 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'wide_left', '大角度左', 60 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;

INSERT INTO sys_dictionary (category_type, parent_id, dict_code, dict_name, sort_order)
SELECT 'landing_point', id, 'wide_right', '大角度右', 70 FROM sys_dictionary WHERE dict_code = 'landing_root' LIMIT 1;
