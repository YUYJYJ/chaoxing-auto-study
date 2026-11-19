# -*- coding: utf-8 -*-
"""答案匹配与格式转换（踩坑总结）。

三个关键坑：
  1. 标题里的空白：平台用不换行空格 \\xa0，答案表里常是普通空格 -> 归一化。
  2. 引号差异：直角引号 " 与中文弯引号 “” -> 归一化。
  3. 提交格式：单选要字母、多选要字母串、判断要 true/false，
     填空/简答才是原文。直接填选项全文会报"作业提交失败"。
"""
import difflib
import re

from api.base import clean_res, is_subsequence, multi_cut


def norm_title(t):
    """标题归一化：去题号、去分值后缀、统一空白与引号。"""
    t = re.sub(r"^\d+", "", t)
    t = re.sub(r"（\d+\.\d+分）$", "", t)
    t = t.replace("\xa0", " ")
    t = t.translate(str.maketrans({'"': "\u201c", "'": "\u2018"}))
    return re.sub(r"\s+", "", t)


def find_answer(title, answer_map):
    """按归一化标题查找答案；找不到时模糊匹配（cutoff 0.75）。"""
    n = norm_title(title)
    for k, v in answer_map.items():
        if norm_title(k) == n:
            return v
    m = difflib.get_close_matches(n, [norm_title(k) for k in answer_map], n=1, cutoff=0.75)
    if m:
        for k, v in answer_map.items():
            if norm_title(k) == m[0]:
                return v
    return None


def to_platform_answer(ans, q):
    """把答案原文转换为超星平台要求的格式。"""
    t = q.get("type")
    opts = q.get("options") or ""
    if t == "single":
        for o in multi_cut(opts) or []:
            r = clean_res(ans)
            if r and is_subsequence(r[0], o):
                return o[:1]
        return ans
    if t == "multiple":
        opt_list = multi_cut(opts) or []
        letters = []
        for a in multi_cut(ans) or []:
            for o in opt_list:
                if is_subsequence(a, o):
                    letters.append(o[:1])
                    break
        return "".join(sorted(set(letters))) or ans
    if t in ("judgement", "judge"):
        v = str(ans).strip().lower()
        yes = {"true", "t", "1", "对", "正确", "√", "是", "yes", "y"}
        return "true" if v in yes else "false"
    return ans


def build_answer_fields(question, ans):
    """构造 answer{id} 与 answerEditor{id}{n} 字段。

    多空填空题：平台 HTML 里只有第1空的输入框，其余由 JS 动态生成；
    必须按 editor_fields（或 tiankongsize 声明的空数）补齐所有字段，
    答案用英文逗号分隔到各空。
    """
    qid = question["id"]
    fields = {f"answer{qid}": to_platform_answer(ans, question)}
    ed = question.get("editor_fields") or []
    if ed:
        parts = str(ans).split(",") if "," in str(ans) else [ans]
        for i, name in enumerate(ed):
            fields[name] = parts[i].strip() if i < len(parts) else ""
    return fields
