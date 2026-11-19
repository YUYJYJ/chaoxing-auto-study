# -*- coding: utf-8 -*-
"""查看运行状态、平台进度与代理可用性（自检命令）。

用法：
  python scripts/status.py            # 进度 + 运行记录
  python scripts/status.py --proxy    # 额外探测代理池
"""
import argparse
import re
import sys

from common import DATA_DIR, all_course_ids, load_settings
import state as state_mod
import proxy_support


def read_progress():
    from api.base import Chaoxing, SessionManager
    from api.logger import logger
    logger.remove(); logger.add(sys.stdout, level="ERROR")
    cx = Chaoxing()
    if not cx.login(login_with_cookies=True).get("status"):
        print("登录失败：请先在浏览器登录学习通，然后运行 python scripts/setup_cookies.py")
        return None
    s = SessionManager.get_session()
    ids = all_course_ids()
    courses = [c for c in cx.get_course_list() if not ids or c["courseId"] in ids]
    per = {}
    tf = tt = 0
    for c in courses:
        r = s.get("https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/studentcourse",
                  params={"courseid": c["courseId"], "clazzid": c["clazzId"],
                          "cpi": c["cpi"], "ut": "s"}, timeout=20)
        m = re.search(r'已完成任务点:\s*<span[^>]*>(\d+)</span>\s*/\s*(\d+)', r.text)
        if m:
            f_, t_ = int(m.group(1)), int(m.group(2))
            per[c["title"]] = (f_, t_)
            tf += f_; tt += t_
    return tf, tt, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", action="store_true", help="探测代理池可用性")
    args = ap.parse_args()

    print("=" * 52)
    print("学习通任务点自动化 —— 状态自检")
    print("=" * 52)

    st = state_mod.load()
    print(f"\n[运行记录] {state_mod.summary(st)}")
    if st.get("errors"):
        print("  最近错误:")
        for e in st["errors"][-5:]:
            print(f"    {e['ts']}  {e['kind']}: {e['detail'][:90]}")

    try:
        p = read_progress()
    except Exception as e:
        print(f"\n[平台进度] 读取失败: {e}")
        p = None
    if p:
        tf, tt, per = p
        print(f"\n[平台进度] 合计 {tf}/{tt} = {tf/tt*100:.1f}%")
        for k, v in per.items():
            mark = "完成" if v[0] >= v[1] else ""
            print(f"    {k[:30]:<32} {v[0]:>3}/{v[1]:<3} {mark}")

    cfg = load_settings()
    if args.proxy:
        proxies = cfg.get("proxies") or []
        print(f"\n[代理池] 共 {len(proxies)} 个")
        if not proxies:
            print("    未配置代理。可在 config/courses.json 里加 \"proxies\": [...]")
        else:
            for p, ok, ms in proxy_support.check(proxies):
                print(f"    {'OK ' if ok else 'FAIL'} {p}  ({ms}ms)")

    print(f"\n[配置] {cfg['source']}")
    print(f"    speed={cfg['speed']}  jobs={cfg['jobs']}  "
          f"course_ids={cfg['course_ids'] or '(全部课程)'}")


if __name__ == "__main__":
    main()
