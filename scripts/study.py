# -*- coding: utf-8 -*-
"""统一入口：刷视频/文档任务点。

用法：
  python scripts/study.py            # 使用 config/courses.json + config/config.ini
  python scripts/study.py --all      # 忽略课程配置，刷账号下全部课程
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from common import ROOT, CONFIG_DIR, load_settings, ensure_dirs


def prepare_config(all_courses=False):
    """把通用配置渲染成 upstream 需要的 config.ini 和 cookies.txt 位置。"""
    ensure_dirs()
    src = CONFIG_DIR / "config.ini.example"
    dst = ROOT / "config.ini"
    if not dst.exists():
        shutil.copy(src, dst)

    settings = load_settings()
    ids = [] if all_courses else settings["course_ids"]

    # 用 configparser 写回 course_list/speed/jobs
    import configparser
    cp = configparser.ConfigParser()
    cp.read(dst, encoding="utf-8")
    cp.set("common", "course_list", ",".join(ids))
    cp.set("common", "speed", str(settings["speed"]))
    cp.set("common", "jobs", str(settings["jobs"]))
    with dst.open("w", encoding="utf-8") as f:
        cp.write(f)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="刷全部课程")
    args = ap.parse_args()
    prepare_config(args.all)
    print("工作目录:", ROOT)
    # upstream/main.py 依赖当前目录下的 cookies.txt 与 config.ini
    subprocess.run([sys.executable, "-u", str(ROOT / "upstream" / "main.py"),
                    "-c", str(ROOT / "config.ini")], cwd=str(ROOT))


if __name__ == "__main__":
    main()
