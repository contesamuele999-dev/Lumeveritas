"""Simple in-memory sliding-window rate limiter keyed by IP or user id.
Not distributed — good enough for a single-instance app.
"""
import time
from collections import deque, defaultdict
from typing import Deque, Dict
from fastapi import Request, HTTPException

_buckets: Dict[str, Deque[float]] = defaultdict(deque)


def check_rate(key: str, max_events: int, window_seconds: int):
    now = time.time()
    dq = _buckets[key]
    cutoff = now - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= max_events:
        retry_in = int(dq[0] + window_seconds - now) + 1
        raise HTTPException(status_code=429, detail=f"Troppe richieste. Riprova tra {retry_in}s.")
    dq.append(now)


def client_key(request: Request, user_doc=None) -> str:
    if user_doc:
        return f"u:{user_doc['id']}"
    fwd = request.headers.get("x-forwarded-for") or ""
    ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    return f"ip:{ip}"
