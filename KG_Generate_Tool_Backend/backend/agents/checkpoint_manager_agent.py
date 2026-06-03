from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, Optional


def make_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def _checkpoint_dir() -> str:
    base = os.path.dirname(os.path.dirname(__file__))
    p = os.path.join(base, "runtime", "checkpoints")
    os.makedirs(p, exist_ok=True)
    return p


def checkpoint_path(run_id: str) -> str:
    return os.path.join(_checkpoint_dir(), f"{run_id}.json")


def load_checkpoint(run_id: str) -> Optional[Dict[str, Any]]:
    if not run_id:
        return None
    path = checkpoint_path(run_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_checkpoint(run_id: str, stage: str, state: Dict[str, Any]) -> None:
    if not run_id:
        return
    path = checkpoint_path(run_id)
    payload = {
        "run_id": run_id,
        "stage": stage,
        "updated_at_ms": int(time.time() * 1000),
        "state": state,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        # checkpoint 失败不影响主流程
        pass
