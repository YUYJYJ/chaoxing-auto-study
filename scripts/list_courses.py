# -*- coding: utf-8 -*-
"""列出当前账号下所有课程及ID，用于填写 config/courses.json。"""
import sys
from common import ROOT, ensure_dirs
from api.base import Chaoxing
from api.logger import logger

logger.remove(); logger.add(sys.stdout, level="ERROR")


def main():
    ensure_dirs()
    cx = Chaoxing()
    if not cx.login(login_with_cookies=True).get("status"):
        print("登录失败。请先在浏览器登录学习通，然后运行 python scripts/setup_cookies.py 导出登录态。")
        return
    print(f"当前账号: {cx.get_name()}\n")
    courses = cx.get_course_list()
    print(f"{'课程ID':<14}{'班级ID':<14}课程名")
    print("-" * 60)
    for c in courses:
        print(f"{c['courseId']:<14}{c['clazzId']:<14}{c['title']}")
    print(f"\n共 {len(courses)} 门课程")
    print("把要刷的课程ID填入 config/courses.json 的 course_ids 数组；留空 [] 表示全部课程。")


if __name__ == "__main__":
    main()
