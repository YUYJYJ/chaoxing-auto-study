# -*- coding: utf-8 -*-
"""根据 data/answers.json 作答并提交章节测验。

流程：
  1. harvest_quizzes.py 采集题目 -> data/pending_questions.json
  2. 你在 data/answers.json 里按题目标题写答案（原文即可，如 "B 选项内容"）
  3. 本脚本转换格式、提交，并输出每份测验的覆盖情况
"""
import importlib.util
import json
import sys
import time

from common import DATA_DIR, ROOT, ensure_dirs
from api.base import SessionManager
from answer_utils import build_answer_fields, find_answer
from api.logger import logger

logger.remove(); logger.add(sys.stdout, level="ERROR")
SUBMIT_URL = "https://mooc1.chaoxing.com/mooc-ans/work/addStudentWorkNew"


def load_answers():
    """加载答案：内置样例作为基础，用户自己的 answers.json 覆盖/补充。"""
    merged = {}
    sample = ROOT / "config" / "answers.example.json"
    if sample.exists():
        try:
            _sd = json.loads(sample.read_text(encoding="utf-8"))
            merged.update({k: v for k, v in _sd.items() if not k.startswith("_")})
        except Exception:
            pass
    path = DATA_DIR / "answers.json"
    if path.exists():
        try:
            _ud = json.loads(path.read_text(encoding="utf-8"))
            merged.update({k: v for k, v in _ud.items() if not k.startswith("_")})
        except Exception as e:
            print(f"读取 {path} 失败: {e}")
    if not merged:
        print(f"提示：未找到答案。请用 data/answers.json 补充，或依赖 config/answers.example.json 内置题库。")
    return merged


def main():
    ensure_dirs()
    pending_path = DATA_DIR / "pending_questions.json"
    if not pending_path.exists():
        print("请先运行 python scripts/harvest_quizzes.py")
        return
    quizzes = json.loads(pending_path.read_text(encoding="utf-8"))
    answers = load_answers()
    session = SessionManager.get_session()
    cache = []   # 累积已答对的题，供后续复用

    for quiz in quizzes:
        form = dict(quiz.get("form", {}))
        form["pyFlag"] = ""     # 直接提交；设为 "1" 则只保存不提交
        qs = quiz["questions"]
        form["answerwqbid"] = ",".join(q["id"] for q in qs) + ","
        filled, missing = 0, []
        for q in qs:
            ans = find_answer(q["title"], answers)
            if not ans:
                ans = find_answer(q["title"], dict(cache))
            if not ans:
                missing.append(q["title"][:50])
                form[f"answer{q['id']}"] = ""
                continue
            form.update(build_answer_fields(q, ans))
            cache.append((q["title"], ans))
            filled += 1
        print(f"{quiz['course'][:14]} | {quiz['chapter'][:18]} -> {filled}/{len(qs)} 题有答案")
        if missing:
            for m in missing[:5]:
                print(f"    缺: {m}")
        if filled < len(qs):
            print("    覆盖率不足，跳过提交（避免用空答案占掉作答次数）")
            continue
        r = session.post(SUBMIT_URL, data=form, headers={
            "Host": "mooc1.chaoxing.com",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://mooc1.chaoxing.com",
            "Referer": "https://mooc1.chaoxing.com/",
        }, timeout=25)
        try:
            j = r.json()
            ok = bool(j.get("status")) or "success" in str(j.get("msg", "")).lower()
        except Exception:
            ok = False
            j = {"raw": r.text[:120]}
        print(f"    提交: {'成功' if ok else '失败'} {str(j)[:100]}")
        time.sleep(2)

    # 保存本轮用过的答案，方便复用
    out = DATA_DIR / "answer_cache.json"
    out.write_text(json.dumps(dict(cache), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n答案缓存 -> {out}")


if __name__ == "__main__":
    main()
