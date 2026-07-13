from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workflow_refactor_sql_defines_required_tables_and_indexes():
    sql_path = ROOT / "sql" / "workflow_refactor.sql"
    sql = sql_path.read_text(encoding="utf-8").lower()

    for table_name in [
        "tactical_standard_version",
        "match_tactical_analysis",
        "match_phase_stat",
        "training_plan_source",
        "training_plan_item",
    ]:
        assert f"create table if not exists {table_name}" in sql

    for index_name in [
        "uk_analysis_phase",
        "uk_analysis_version",
        "idx_plan_item_module_status",
        "idx_plan_source_analysis",
    ]:
        assert index_name in sql


def test_workflow_refactor_sql_stays_mysql55_compatible():
    sql_path = ROOT / "sql" / "workflow_refactor.sql"
    sql = sql_path.read_text(encoding="utf-8").lower()

    forbidden_fragments = [
        " json",
        " with ",
        " over (",
        " check ",
        "->",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in sql


def test_tactical_standard_source_register_marks_unverified_sources():
    register_path = ROOT / "docs" / "技战术标准来源登记表.md"
    text = register_path.read_text(encoding="utf-8")

    assert "《乒乓球技战术分析理论与实践》" in text
    assert "技战术评估指标.docx" in text
    assert "待核验" in text
    assert "不得启用正式评级" in text
