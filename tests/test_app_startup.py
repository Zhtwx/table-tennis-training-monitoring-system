import json
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


def test_app_py_enables_reloader_for_development_script_startup():
    script = """
import json
import runpy
from flask import Flask

captured = {}

def fake_run(self, *args, **kwargs):
    captured.update(kwargs)

Flask.run = fake_run
runpy.run_path("app.py", run_name="__main__")
print(json.dumps(captured))
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    run_kwargs = json.loads(result.stdout.strip())
    assert run_kwargs["debug"] is True
    assert run_kwargs["use_reloader"] is True
