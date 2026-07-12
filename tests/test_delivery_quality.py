import importlib
import py_compile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__"}
LEGACY_RUNTIME_FILES = [
    REPO_ROOT / "专项技术记录模块开发模块" / "app(1).py",
    REPO_ROOT / "专项技术记录模块开发模块" / "record.py",
    REPO_ROOT / "统计分析与 Excel 数据导入导出模块" / "app(2).py",
]


def is_delivery_file(path):
    relative_parts = path.relative_to(REPO_ROOT).parts
    return not any(part in IGNORED_DIRS for part in relative_parts)


def iter_delivery_files(pattern):
    return (
        path
        for path in REPO_ROOT.rglob(pattern)
        if path.is_file() and is_delivery_file(path)
    )


def test_delivery_python_files_compile():
    failures = []
    for path in iter_delivery_files("*.py"):
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append(f"{path.relative_to(REPO_ROOT)}: {exc.msg}")

    assert failures == []


def test_delivery_contains_no_git_conflict_markers():
    checked_extensions = {".py", ".html", ".sql", ".md", ".txt"}
    offenders = []
    for path in iter_delivery_files("*"):
        if path.suffix.lower() not in checked_extensions:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        start_marker = "<" * 7
        end_marker = ">" * 7
        if start_marker in text or end_marker in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_legacy_runtime_copies_are_not_in_delivery_tree():
    existing = [str(path.relative_to(REPO_ROOT)) for path in LEGACY_RUNTIME_FILES if path.exists()]

    assert existing == []


def test_wsgi_exports_flask_application():
    wsgi = importlib.import_module("wsgi")

    assert wsgi.application.name == "app"
