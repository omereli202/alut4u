#!/usr/bin/env python3
"""Light load test for the hot read paths.

    python scripts/loadtest.py http://localhost:8010 --users 20 --seconds 20

Signs up one caregiver, seeds a child + a template board, then hammers the
endpoints a kiosk actually hits at rest: session, board, schedule day, token
balance. Reports p50/p95/p99 latency and error rate per endpoint.
"""

from __future__ import annotations

import argparse
import random
import statistics
import threading
import time
import uuid

import httpx

READ_PATHS: list[str] = []  # filled in after setup


def setup(base: str) -> httpx.Client:
    c = httpx.Client(base_url=base, timeout=15.0)
    email = f"load-{uuid.uuid4().hex[:10]}@example.com"
    c.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": "load-password-123",
            "display_name": "load",
            "accept_terms": True,
        },
    ).raise_for_status()
    c.put("/api/auth/pin", json={"pin": "2846"}).raise_for_status()
    c.post("/api/auth/pin", json={"pin": "2846"}).raise_for_status()
    child = c.post(
        "/api/children",
        json={"name": "L", "consent_basis": "parent", "board_template_id": "basic-needs"},
    ).json()
    cid = child["id"]
    today = time.strftime("%Y-%m-%d")
    c.post("/api/schedule/items", json={"child_id": cid, "the_date": today, "title": "בוקר"})
    c.delete("/api/auth/pin/elevation")

    READ_PATHS.extend(
        [
            "/api/auth/session",
            f"/api/aac/board?child_id={cid}",
            f"/api/schedule/day?child_id={cid}&date={today}",
            f"/api/tokens/balance?child_id={cid}",
        ]
    )
    return c


def worker(base: str, cookies, stop: float, samples: dict) -> None:
    c = httpx.Client(base_url=base, timeout=15.0, cookies=cookies)
    while time.time() < stop:
        path = random.choice(READ_PATHS)
        t0 = time.perf_counter()
        try:
            r = c.get(path)
            ok = r.status_code < 400
        except httpx.HTTPError:
            ok = False
        dt = (time.perf_counter() - t0) * 1000
        bucket = samples.setdefault(path, {"ms": [], "err": 0})
        bucket["ms"].append(dt)
        if not ok:
            bucket["err"] += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--users", type=int, default=10)
    ap.add_argument("--seconds", type=int, default=15)
    args = ap.parse_args()

    session = setup(args.base)
    samples: dict = {}
    stop = time.time() + args.seconds
    threads = [
        threading.Thread(target=worker, args=(args.base, session.cookies, stop, samples))
        for _ in range(args.users)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\n{args.users} users · {args.seconds}s\n")
    print(f"{'endpoint':<45} {'n':>6} {'p50':>7} {'p95':>7} {'p99':>7} {'err':>5}")
    for path, b in samples.items():
        ms = sorted(b["ms"])
        n = len(ms)
        p = lambda q: ms[min(n - 1, int(n * q))]  # noqa: E731
        print(f"{path:<45} {n:>6} {p(0.5):>7.0f} {p(0.95):>7.0f} {p(0.99):>7.0f} {b['err']:>5}")
    print(f"\ntotal req: {sum(len(b['ms']) for b in samples.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
