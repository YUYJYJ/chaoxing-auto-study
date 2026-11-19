# -*- coding: utf-8 -*-
"""采集当前可做章节测验的题目，输出 data/pending_questions.json。

只读取题目，不作答、不提交。答案由用户自己或 AI 填写。
"""
import json
import re
import sys
import time
from common import ROOT, DATA_DIR, ensure_dirs, all_course_ids
from api.base import Chaoxing, SessionManager
from api.decode import decode_questions_info
from api.font_decoder import FontDecoder
from api.logger import logger

logger.remove(); logger.add(sys.stdout, level="ERROR")
QUIZ_URL = "https://mooc1.chaoxing.com/mooc-ans/api/work"


def fetch_quiz(session, course, job, info):
    wid = str(job["jobid"]).replace("work-", "")
    r = session.get(QUIZ_URL, params={
        "api": "1", "workId": wid, "jobid": job["jobid"], "originJobId": job["jobid"],
        "needRedirect": "true", "skipHeader": "true",
        "knowledgeid": str(info.get("knowledgeid", "")), "ktoken": info.get("ktoken", ""),
        "cpi": info.get("cpi", ""), "ut": "s", "clazzId": course["clazzId"], "type": "",
        "enc": job.get("enc", ""), "mooc2": "1", "courseid": course["courseId"],
    }, timeout=25)
    if r.status_code != 200:
        return None
    d = decode_questions_info(r.text)
    qs = d.get("questions", [])
    if not qs:
        return None
    dec = None
    if "cxSecretStyle" in r.text:
        try:
            dec = FontDecoder(r.text)
        except Exception:
            pass

    def dec_text(t):
        if dec:
            try:
                return dec.decode(t)
            except Exception:
                return t
        return t

    out = []
    for q in qs:
        title = dec_text(q["title"])
        title = re.sub(r"^\d+", "", title)
        title = re.sub(r"（\d+\.\d+分）$", "", title)
        out.append({
            "id": q["id"], "type": q["type"], "title": title,
            "options": q["options"], "editor_fields": q.get("editorFields", []),
            "course_id": course["courseId"], "course": course["title"],
            "chapter": job.get("chapterName", ""), "jobid": job["jobid"],
        })
    return {"course": course["title"], "course_id": course["courseId"],
            "chapter": job.get("chapterName", ""), "jobid": job["jobid"],
            "form": {k: v for k, v in d.items() if k != "questions"}, "questions": out}


def main():
    ensure_dirs()
    cx = Chaoxing()
    if not cx.login(login_with_cookies=True).get("status"):
        print("登录失败，请检查 cookies.txt。")
        return
    want = all_course_ids()
    session = SessionManager.get_session()
    result = []
    for course in cx.get_course_list():
        if want and course["courseId"] not in want:
            continue
        try:
            pd = cx.get_course_point(course["courseId"], course["clazzId"], course["cpi"])
        except Exception:
            continue
        for point in pd.get("points", []):
            try:
                jobs, info = cx.get_job_list(course, point)
            except Exception:
                continue
            if not info or info.get("notOpen"):
                continue
            for job in jobs:
                if job.get("type") != "workid":
                    continue
                quiz = fetch_quiz(session, course, job, info)
                if quiz:
                    quiz["chapter"] = point.get("title", "")
                    result.append(quiz)
                    quiz["questions"][0]["chapter"] = point.get("title", "")
                    print(f"采集: {course['title'][:20]} | {point['title'][:20]} | {len(quiz['questions'])} 题")
                time.sleep(0.3)
    out = DATA_DIR / "pending_questions.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(q["questions"]) for q in result)
    print(f"\n共 {len(result)} 份测验 / {total} 题 -> {out}")
    print("请编辑 data/answers.json，按题目标题给出答案，然后运行 fill_quizzes.py")


if __name__ == "__main__":
    main()
