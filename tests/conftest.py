import os
import sys
from pathlib import Path

os.environ["TRAINING_STORAGE"] = "memory"
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
