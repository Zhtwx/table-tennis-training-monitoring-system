# 乒乓球运动员综合训练监控管理系统 — 全局 E-R 图

```mermaid
erDiagram
    athlete ||--o{ training_plan : "1:N"
    athlete ||--o{ technical_record : "1:N"
    athlete ||--o{ fitness_report : "1:N"
    athlete ||--o{ injury_record : "1:N"
    athlete ||--o{ match_record : "1:N"
    coach ||--o{ training_plan : "1:N"
    coach ||--o{ technical_record : "1:N（评估者）"
    coach ||--o{ fitness_report : "1:N（测试者）"
    coach ||--o| user_account : "1:1（可选）"

    athlete {
        INT id PK "主键"
        VARCHAR student_no UK "学号"
        VARCHAR name "姓名"
        ENUM gender "男/女"
        DATE birth_date "出生日期"
        VARCHAR team "所属队伍"
        ENUM skill_level "二级/一级/国家级/健将/青年队"
        VARCHAR play_style "打法"
        VARCHAR grip "持拍手"
        VARCHAR contact_phone "联系电话"
        ENUM injury_status "健康/观察中/康复中/伤病中"
        TIMESTAMP create_time
        TIMESTAMP update_time
    }

    coach {
        INT id PK
        VARCHAR name "姓名"
        ENUM gender "男/女"
        VARCHAR specialty "擅长领域"
        VARCHAR contact_phone
        VARCHAR email UK
        TIMESTAMP create_time
    }

    training_plan {
        INT id PK
        INT athlete_id FK "→athlete"
        INT coach_id FK "→coach"
        VARCHAR plan_name "计划名称"
        DATE start_date
        DATE end_date
        TEXT training_content
        ENUM intensity "低/中/高/极高"
        DECIMAL hours "训练时长"
        ENUM status "进行中/已完成/已取消"
        TIMESTAMP create_time
        TIMESTAMP update_time
    }

    technical_record {
        INT id PK
        INT athlete_id FK "→athlete"
        DATE record_date
        INT evaluator_id FK "→coach"
        DECIMAL forehand_score "正手评分"
        DECIMAL backhand_score "反手评分"
        DECIMAL serve_score "发球评分"
        DECIMAL footwork_score "步伐评分"
        DECIMAL reaction_score "反应评分"
        DECIMAL overall_score "综合评分"
        TEXT notes
        TIMESTAMP create_time
    }

    fitness_report {
        INT id PK
        INT athlete_id FK "→athlete"
        DATE test_date
        INT tester_id FK "→coach"
        DECIMAL upper_strength "上肢力量"
        DECIMAL lower_strength "下肢力量"
        DECIMAL flexibility "关节活动度"
        DECIMAL endurance "耐力"
        DECIMAL speed "速度"
        DECIMAL overall_score "综合体能分"
        TEXT notes
        TIMESTAMP create_time
    }

    injury_record {
        INT id PK
        INT athlete_id FK "→athlete"
        DATE injury_date
        VARCHAR injury_location "伤病部位"
        VARCHAR injury_type "伤病类型"
        ENUM severity "轻微/中度/严重"
        TEXT diagnosis "诊断描述"
        TEXT treatment "治疗方案"
        ENUM recovery_status "治疗中/康复中/已恢复"
        DATE expected_recovery_date
        TEXT notes
        TIMESTAMP create_time
        TIMESTAMP update_time
    }

    match_record {
        INT id PK
        INT athlete_id FK "→athlete"
        DATE match_date
        VARCHAR match_name "赛事名称"
        VARCHAR opponent "对手"
        ENUM result "胜/负/平"
        VARCHAR score "比分"
        TEXT notes
        TIMESTAMP create_time
    }

    user_account {
        INT id PK
        VARCHAR username UK
        VARCHAR password_hash
        ENUM role "管理员/教练员"
        INT coach_id FK UK "→coach(可选)"
        TIMESTAMP create_time
    }
```

## 关系说明

| 关系 | 说明 | 外键策略 |
|---|---|---|
| athlete 1:N training_plan | 一名运动员有多条训练计划 | CASCADE 删除 |
| coach 1:N training_plan | 一名教练制定多条训练计划 | RESTRICT 删除 |
| athlete 1:N technical_record | 一名运动员有多条技术评估 | CASCADE 删除 |
| coach 1:N technical_record | 一名教练作为评估者 | SET NULL 删除 |
| athlete 1:N fitness_report | 一名运动员有多条体能报告 | CASCADE 删除 |
| coach 1:N fitness_report | 一名教练作为测试者 | SET NULL 删除 |
| athlete 1:N injury_record | 一名运动员有多条伤病记录 | CASCADE 删除 |
| athlete 1:N match_record | 一名运动员有多条比赛记录 | CASCADE 删除 |
| coach 1:1 user_account | 教练可选关联一个登录账号 | SET NULL 删除 |
