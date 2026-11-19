# -*- coding: utf-8 -*-
"""全自动循环：交替刷视频与做测验，直到进度不再增长。

超星章节是链式解锁：做完一章才解锁下一章，单次运行只能推进一小段。
本脚本每轮：
  1. fill_quizzes.py   —— 提交当前可做的章节测验（需 data/answers.json）
  2. study.py          —— 刷当前可做的视频/文档
  3. 读平台进度，有增量就继续；连续两轮无增量则停。
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, DATA_DIR, ensure_dirs, all_course_ids
from api.base import Chaoxing, SessionManager
from api.logger import logger

LOG = DATA_DIR / "auto_run.log"
IDS = all_course_ids()


def log(*a):
    msg = "%s | %s" % (time.strftime("%H:%M:%S"), " ".join(str(x) for x in a))
    print(msg, flush=True)
    ensure_dirs()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def read_progress():
    logger.remove(); logger.add(sys.stdout, level="ERROR")
    cx = Chaoxing()
    if not cx.login(login_with_cookies=True).get("status"):
        return None
    s = SessionManager.get_session()
    courses = [c for c in cx.get_course_list() if not IDS or c["courseId"] in IDS]
    tf = tt = 0
    per = {}
    for c in courses:
        r = s.get("https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/studentcourse",
                  params={"courseid": c["courseId"], "clazzid": c["clazzId"],
                          "cpi": c["cpi"], "ut": "s"}, timeout=20)
        m = re.search(r'已完成任务点:\s*<span[^>]*>(\d+)</span>\s*/\s*(\d+)', r.text)
        if m:
            f_, t_ = int(m.group(1)), int(m.group(2))
            per[c["title"]] = (f_, t_); tf += f_; tt += t_
    return tf, tt, per


def run(script, args=()):
    try:
        p = subprocess.run([sys.executable, "-u", str(ROOT / "scripts" / script)] + list(args),
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=str(ROOT), timeout=7200)
        return p.stdout or "", p.returncode
    except Exception as e:
        return str(e), -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=30)
    args = ap.parse_args()
    ensure_dirs()
    last, stagnant = -1, 0
    for i in range(args.rounds):
        try:
            p0 = read_progress()
        except Exception as e:
            log("读进度失败:", e); break
        if not p0:
            log("登录失败，请先在浏览器登录学习通，然后运行 python scripts/setup_cookies.py 导出登录态"); break
        log(f"=== 轮 {i+1} | 进度 {p0[0]}/{p0[1]} ===")
        if p0[0] >= p0[1]:
            log("全部完成"); break

        out, rc = run("harvest_quizzes.py")
        log(f"  采集题目 rc={rc}")
        # 若用户配置了 LLM，则自动生成答案（无需手工逐题填写）
        llm_cfg = ROOT / "config" / "llm.json"
        if llm_cfg.exists():
            out, rc = run("generate_answers.py")
            for l in [x for x in out.splitlines() if x.startswith("[") or "已生成" in x][-3:]:
                log("  " + l.strip()[:110])
            log(f"  LLM 生成答案 rc={rc}")
        out, rc = run("fill_quizzes.py")
        for l in [x for x in out.splitlines() if "提交:" in x or "缺:" in x][-5:]:
            log("  " + l.strip()[:120])
        log(f"  测验阶段 rc={rc}")

        out, rc = run("study.py")
        log(f"  视频阶段 rc={rc}")

        try:
            p1 = read_progress()
        except Exception as e:
            log("读进度失败:", e); break
        if not p1:
            break
        log(f"  轮后进度 {p1[0]}/{p1[1]}")
        for k, v in p1[2].items():
            if v[0] < v[1]:
                log(f"     未满 {k[:24]} {v[0]}/{v[1]}")
        if p1[0] == last:
            stagnant += 1
            if stagnant >= 2:
                log("连续两轮无进展，停止"); break
        else:
            stagnant = 0
        last = p1[0]
    log("执行器结束")


if __name__ == "__main__":
    main()
