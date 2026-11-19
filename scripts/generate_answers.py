# -*- coding: utf-8 -*-
"""用你自己的大模型 API 自动生成 data/answers.json。

这样章节测验不需要手工逐题作答。支持任何 OpenAI 兼容的 chat/completions 端点，
例如 DeepSeek、通义、智谱、Kimi、OpenAI、本地 Ollama 等。

用法：
  1. 复制 config/llm.example.json 为 config/llm.json，填入 endpoint / key / model
  2. python scripts/harvest_quizzes.py         # 采集题目
  3. python scripts/generate_answers.py        # 自动生成答案
  4. python scripts/fill_quizzes.py            # 提交
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

from common import ROOT, CONFIG_DIR, DATA_DIR, ensure_dirs

LLM_CONFIG = CONFIG_DIR / "llm.json"
PROMPTS = {
    "single": "这是单选题。只输出正确选项的【原文】（不要输出字母、不要解释、不要 markdown、不要 JSON）。",
    "multiple": "这是多选题。按原文输出所有正确选项，用英文逗号分隔，不要输出字母、不要解释。",
    "completion": "这是填空题。按空的顺序输出答案，用英文逗号分隔，不要解释。",
    "judgement": "这是判断题。只输出“对”或“错”，不要解释。",
    "shortanswer": "这是简答题。输出完整答案文字，条理清晰，不要 markdown 标记。",
    "unknown": "请根据题意给出准确的答案文字。",
}


def load_llm_config():
    if not LLM_CONFIG.exists():
        print(f"未找到 {LLM_CONFIG}")
        print("请复制 config/llm.example.json 为 config/llm.json 并填写 endpoint/key/model。")
        return None
    cfg = json.loads(LLM_CONFIG.read_text(encoding="utf-8"))
    for k in ("endpoint", "model"):
        if not cfg.get(k):
            print(f"config/llm.json 缺少 {k}")
            return None
    return cfg


def ask_llm(cfg, title, options, qtype):
    prompt = PROMPTS.get(qtype, PROMPTS["unknown"])
    user = f"题目：{title}\n"
    if options and options.strip():
        user += f"选项：\n{options}\n"
    user += "\n答案："
    body = json.dumps({
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["endpoint"], data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + str(cfg.get("key", ""))},
        method="POST")
    timeout = int(cfg.get("timeout", 60))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content)
    return clean(content)


def clean(text):
    t = str(text).strip()
    # 去掉 markdown 代码围栏
    t = re.sub(r"^```[a-z]*\s*", "", t, flags=re.I)
    t = re.sub(r"\s*```$", "", t)
    # 去掉 "答案：" 前缀
    t = re.sub(r"^\s*答案\s*[:：]\s*", "", t)
    # 去掉选项字母前缀 A. / A、/ A 等
    t = re.sub(r"^\s*[A-Za-z]\s*[.、,，:：]?\s*", "", t) if len(t) < 200 else t
    return t.strip()


def main():
    ensure_dirs()
    cfg = load_llm_config()
    if not cfg:
        return
    pending = DATA_DIR / "pending_questions.json"
    if not pending.exists():
        print("请先运行 python scripts/harvest_quizzes.py")
        return
    quizzes = json.loads(pending.read_text(encoding="utf-8"))
    answers_path = DATA_DIR / "answers.json"
    answers = {}
    if answers_path.exists():
        answers = json.loads(answers_path.read_text(encoding="utf-8"))
    interval = float(cfg.get("interval", 0.5))
    total = sum(len(q["questions"]) for q in quizzes)
    done = 0
    for quiz in quizzes:
        for q in quiz["questions"]:
            title = q["title"]
            if title in answers and answers[title]:
                continue
            try:
                ans = ask_llm(cfg, title, q.get("options", ""), q.get("type", "unknown"))
                answers[title] = ans
                done += 1
                print(f"[{done}/{total}] {q.get('type')}: {ans[:50]}")
            except urllib.error.HTTPError as e:
                print(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:150]}")
                break
            except Exception as e:
                print(f"失败: {type(e).__name__}: {e}")
                break
            time.sleep(interval)
    answers_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已生成 {len(answers)} 条答案 -> {answers_path}")
    print("接下来运行: python scripts/fill_quizzes.py")


if __name__ == "__main__":
    main()
