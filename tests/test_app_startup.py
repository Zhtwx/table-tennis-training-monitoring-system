import subprocess
import sys


def test_app_py_can_start_as_script_without_blueprint_setup_error():
    script = """
import runpy
from flask import Flask

Flask.run = lambda self, *args, **kwargs: None
runpy.run_path("app.py", run_name="__main__")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr + result.stdout
