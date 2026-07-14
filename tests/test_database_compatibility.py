from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fitness_training_redesign_keeps_legacy_reports_separate():
    sql = (ROOT / "sql" / "fitness_training_redesign.sql").read_text(encoding="utf-8").lower()

    assert "create table if not exists fitness_training_record" in sql
    assert "from fitness_report" not in sql
    for field_name in [
        "plan_name",
        "training_hours",
        "training_intensity",
        "plan_status",
        "sprint_30m",
        "abdominal_endurance",
        "back_endurance",
        "lateral_slide",
        "a_footwork",
        "double_under",
        "seated_rotation_throw",
        "standing_long_jump",
    ]:
        assert field_name in sql


def test_member9_exports_the_redesigned_fitness_training_records():
    sql = (ROOT / "sql" / "member9_stats_excel.sql").read_text(encoding="utf-8").lower()

    assert "v_member9_fitness_training_monthly_stats" in sql
    assert "from fitness_training_record" in sql


def test_member9_import_indexes_are_safe_on_repeat_execution():
    sql = (ROOT / "sql" / "member9_stats_excel.sql").read_text(encoding="utf-8").lower()

    assert "key idx_member9_import_batch (import_batch_no)" in sql
    assert "key idx_member9_import_student_date (student_no, record_date)" in sql
    assert "create index idx_member9_import_batch" not in sql
    assert "create index idx_member9_import_student_date" not in sql
