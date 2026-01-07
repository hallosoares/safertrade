import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv as _load
except Exception:

    def _load(*a, **k):
        return False


def load_env(root: Optional[Path]):
    if root is None:
        return
    # Base .env
    _load(root / ".env")
    # Preferred environment locations
    _load(root / "config/environments/global.runtime.env")
    _load(root / "config/environments/safertrade.runtime.env")
    _load(root / "config/environments/api.env")
    # Secrets override
    _load(root / "secrets/.env.runtime")
    # Export root for portability
    os.environ.setdefault("SAFERTRADE_ROOT", str(root))
