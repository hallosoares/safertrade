import os
from pathlib import Path

# The root directory of the project
ROOT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent

# Key directories
CONFIG_DIR = ROOT_DIR / "config"  # Fixed: was pointing to non-existent "configs"
LOGS_DIR = ROOT_DIR / "logs"
SHARED_DIR = ROOT_DIR / "shared"
TOOLS_DIR = ROOT_DIR / ".tools"  # Fixed: was pointing to "tools" instead of ".tools"
DATA_DIR = ROOT_DIR / "data"
DATABASES_DIR = DATA_DIR / "databases"
PAPER_DIR = ROOT_DIR / "_paper"

# Common file paths
SAFERTRADE_DB = DATABASES_DIR / "safertrade.db"
