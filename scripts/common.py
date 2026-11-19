# -*- coding: utf-8 -*-
"""公共配置与路径工具。

所有路径都相对于项目根目录（本文件的上一级），不写死用户名或盘符。
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"

# 让 upstream/ 下的 api 包可被 import
sys.path.insert(0, str(UPSTREAM))
# 上游用相对路径 resource/font_map_table.json 找字体表，需切到 upstream 目录
# （只影响字体解码，不改变调用方的工作目录）
import os
os.chdir(str(UPSTREAM))

DEFAULT_COURSES = CONFIG_DIR / "courses.example.json"
USER_COURSES = CONFIG_DIR / "courses.json"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_settings():
    """读取用户配置；未配置时返回全部课程（course_ids 为空表示不限）。"""
    ensure_dirs()
    path = USER_COURSES if USER_COURSES.exists() else DEFAULT_COURSES
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    ids = cfg.get("course_ids") or []
    return {
        "course_ids": [str(x).strip() for x in ids if str(x).strip()],
        "speed": float(cfg.get("speed", 2.0)),
        "jobs": int(cfg.get("jobs", 6)),
        "source": str(path),
    }


def all_course_ids():
    """course_ids 为空时返回 None（表示账号下全部课程）。"""
    ids = load_settings()["course_ids"]
    return ids or None


def answer_files():
    """返回用户答案文件列表（可按课程名命名，如 answers_我的课程.py）。"""
    ensure_dirs()
    return sorted(DATA_DIR.glob("answers_*.py"))
