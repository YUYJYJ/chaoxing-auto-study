# -*- coding: utf-8 -*-
"""运行状态记录，实现断点续跑与问题排查。

记录内容写到 data/state.json：
  - 每轮进度快照（用于观察推进速度）
  - 已提交成功的测验（避免重复提交浪费作答次数）
  - 出现过的错误（403 / 验证码 / 登录失效等）

这个文件不含任何个人信息，可以安全分享。
"""
import json
import time
from pathlib import Path

from common import DATA_DIR, ensure_dirs

STATE_FILE = DATA_DIR / "state.json"


def load():
    ensure_dirs()
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"rounds": [], "submitted_quizzes": [], "errors": [], "started_at": None}


def save(state):
    ensure_dirs()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def record_round(state, done, total, per_course=None):
    state["rounds"].append({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "done": done, "total": total,
        "per_course": per_course or {},
    })
    if not state.get("started_at"):
        state["started_at"] = state["rounds"][0]["ts"]
    # 只保留最近 200 轮，避免文件无限增长
    if len(state["rounds"]) > 200:
        state["rounds"] = state["rounds"][-200:]
    save(state)


def record_submitted(state, course, chapter, jobid):
    key = f"{course}|{chapter}|{jobid}"
    if key not in state["submitted_quizzes"]:
        state["submitted_quizzes"].append(key)
        save(state)


def record_error(state, kind, detail):
    state["errors"].append({
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "detail": str(detail)[:300],
    })
    if len(state["errors"]) > 100:
        state["errors"] = state["errors"][-100:]
    save(state)


def summary(state):
    rounds = state.get("rounds", [])
    if not rounds:
        return "尚无运行记录"
    first, last = rounds[0], rounds[-1]
    delta = last["done"] - first["done"]
    return (f"共 {len(rounds)} 轮，{first['ts']} ~ {last['ts']}，"
            f"进度 {first['done']} -> {last['done']}（+{delta}），"
            f"已提交测验 {len(state.get('submitted_quizzes', []))} 份，"
            f"错误 {len(state.get('errors', []))} 次")
