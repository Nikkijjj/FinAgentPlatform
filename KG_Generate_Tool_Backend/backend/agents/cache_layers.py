# -*- coding: utf-8 -*-
"""
多级缓存：L1 进程内内存；可选 L2 本地磁盘 JSON（跨重启、多 worker 场景仍建议 Redis）。

环境变量：
- KG_CACHE_L2_ENABLED：默认 false，设为 true 启用磁盘层
- KG_CACHE_L2_DIR：磁盘缓存根目录（默认 backend/.cache/kg_backend）
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_NS_LOCK = threading.RLock()

# namespace -> ordered keys list for LRU within namespace
_MEM: Dict[str, Dict[str, Tuple[Any, float]]] = {}
_MEM_ORDER: Dict[str, list] = {}

_DEFAULT_NS_MAX: Dict[str, int] = {
    "intent": int(os.getenv("KG_INTENT_CACHE_MAX_SIZE", "500")),
    "qa_answer": max(32, int(os.getenv("KG_QA_CACHE_MAX_ITEMS", "256"))),
    "qa_retrieval": max(64, int(os.getenv("KG_RETRIEVAL_CACHE_MAX_ITEMS", "128"))),
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _l2_enabled() -> bool:
    return _env_bool("KG_CACHE_L2_ENABLED", False)


def _l2_root() -> Path:
    base = os.getenv("KG_CACHE_L2_DIR")
    if base:
        return Path(base)
    here = Path(__file__).resolve().parent.parent
    return here / ".cache" / "kg_backend"


def _safe_key_digest(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()


def _l2_path(namespace: str, digest: str) -> Path:
    root = _l2_root()
    return root / namespace / f"{digest}.json"


def _l2_read(namespace: str, digest: str) -> Optional[Tuple[Any, float]]:
    if not _l2_enabled():
        return None
    path = _l2_path(namespace, digest)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        obj = json.loads(raw)
        exp = float(obj.get("expire_at") or 0)
        if exp and time.time() > exp:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return obj.get("value"), exp
    except Exception:
        return None


def _l2_write(namespace: str, digest: str, value: Any, expire_at: float) -> None:
    if not _l2_enabled():
        return
    path = _l2_path(namespace, digest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        payload = json.dumps(
            {"expire_at": expire_at, "value": value},
            ensure_ascii=False,
            default=str,
        )
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except (OSError, TypeError, ValueError):
        pass


def _l2_delete(namespace: str, digest: str) -> None:
    if not _l2_enabled():
        return
    try:
        _l2_path(namespace, digest).unlink(missing_ok=True)
    except OSError:
        pass


def _touch_lru(namespace: str, key: str, max_items: int) -> None:
    order = _MEM_ORDER.setdefault(namespace, [])
    if key in order:
        order.remove(key)
    order.append(key)
    while len(order) > max_items:
        oldest = order.pop(0)
        _MEM.get(namespace, {}).pop(oldest, None)


def cache_get(namespace: str, key: str) -> Optional[Any]:
    """按 namespace 读取；过期返回 None。"""
    now = time.time()
    digest = _safe_key_digest(f"{namespace}:{key}")
    with _NS_LOCK:
        bucket = _MEM.setdefault(namespace, {})
        item = bucket.get(key)
        if item:
            val, exp = item
            if exp and now > exp:
                bucket.pop(key, None)
                order = _MEM_ORDER.get(namespace, [])
                if key in order:
                    order.remove(key)
                _l2_delete(namespace, digest)
                return None
            _touch_lru(namespace, key, _DEFAULT_NS_MAX.get(namespace, 256))
            return val
    # L2 fallback
    l2 = _l2_read(namespace, digest)
    if l2 is None:
        return None
    val, exp = l2
    if exp and now > exp:
        return None
    with _NS_LOCK:
        bucket = _MEM.setdefault(namespace, {})
        max_items = _DEFAULT_NS_MAX.get(namespace, 256)
        if len(bucket) >= max_items:
            _evict_one(namespace, max_items)
        bucket[key] = (val, exp)
        _touch_lru(namespace, key, max_items)
    return val


def _evict_one(namespace: str, max_items: int) -> None:
    order = _MEM_ORDER.setdefault(namespace, [])
    while len(order) >= max_items and order:
        oldest = order.pop(0)
        _MEM.get(namespace, {}).pop(oldest, None)


def cache_set(namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
    ttl = max(1, int(ttl_seconds))
    expire_at = time.time() + ttl
    digest = _safe_key_digest(f"{namespace}:{key}")
    with _NS_LOCK:
        bucket = _MEM.setdefault(namespace, {})
        max_items = _DEFAULT_NS_MAX.get(namespace, 256)
        if key not in bucket and len(bucket) >= max_items:
            _evict_one(namespace, max_items)
        bucket[key] = (value, expire_at)
        _touch_lru(namespace, key, max_items)
    _l2_write(namespace, digest, value, expire_at)


def cache_clear_namespace(namespace: str) -> None:
    with _NS_LOCK:
        _MEM.pop(namespace, None)
        _MEM_ORDER.pop(namespace, None)
    if _l2_enabled():
        root = _l2_root() / namespace
        if root.is_dir():
            for p in root.glob("*.json"):
                try:
                    p.unlink()
                except OSError:
                    pass


def cache_stats() -> Dict[str, Any]:
    with _NS_LOCK:
        mem_counts = {ns: len(bucket) for ns, bucket in _MEM.items()}
    return {
        "l2_enabled": _l2_enabled(),
        "l2_dir": str(_l2_root()),
        "memory_items_by_namespace": mem_counts,
        "namespace_limits": dict(_DEFAULT_NS_MAX),
    }
