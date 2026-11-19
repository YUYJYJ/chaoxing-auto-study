# -*- coding: utf-8 -*-
"""代理支持与连接健康检查。

超星会按 IP 做频率限制，长时间高并发时单个 IP 容易被 403/验证码。
支持配置代理池（每行一个 http/https/socks5 代理），失败时自动轮换。

配置（config/courses.json）：
    "proxies": ["http://127.0.0.1:7890", "socks5://127.0.0.1:1080"],
    "proxy_rotate_on_error": true
"""
import itertools
import random
import threading

try:
    import requests
    from requests.adapters import HTTPAdapter
except ImportError:
    requests = None
    HTTPAdapter = None

_pool = []
_lock = threading.Lock()
_rr = None


def load_proxies(proxies):
    """初始化代理池。"""
    global _pool, _rr
    with _lock:
        _pool = [p.strip() for p in (proxies or []) if p and p.strip()]
        _rr = itertools.cycle(_pool) if _pool else None
    return len(_pool)


def current_proxy():
    """取一个代理（轮询）。无池时返回 None。"""
    if not _pool:
        return None
    with _lock:
        return next(_rr)


def rotate(proxy):
    """把出问题的代理挪到队尾，下次不再优先使用。"""
    if not proxy or not _pool:
        return
    with _lock:
        try:
            _pool.remove(proxy)
            _pool.append(proxy)
        except ValueError:
            pass
        global _rr
        _rr = itertools.cycle(_pool)


def apply_to_session(session):
    """把当前代理挂到 requests.Session 上。"""
    p = current_proxy()
    if p and session is not None:
        session.proxies = {"http": p, "https": p}
    return p


def check(proxies, timeout=8, test_url="https://mooc1.chaoxing.com/favicon.ico"):
    """逐个探测代理可用性，返回 [(proxy, ok, 耗时ms)]。"""
    if not proxies:
        return []
    results = []
    for p in proxies:
        p = p.strip()
        if not p:
            continue
        if requests is None:
            results.append((p, False, 0))
            continue
        import time
        t0 = time.time()
        try:
            r = requests.get(test_url, proxies={"http": p, "https": p}, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0"})
            ok = r.status_code < 500
        except Exception:
            ok = False
        results.append((p, ok, int((time.time() - t0) * 1000)))
    return results
