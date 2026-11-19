# 学习通（超星）任务点自动化工具

[![License: GPL-3.0](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

命令行工具，用于自动完成学习通网页版的**视频 / 文档任务点**与**章节测验**。

基于开源项目 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)（GPL-3.0），
在其之上补齐了实际使用中必需的若干能力（见 [相对上游的改动](#相对上游的改动)）。

> ⚠️ **使用前请先读 [注意事项](#注意事项)**。本工具仅供学习交流使用，
> 使用者需自行确保行为符合所在学校与平台的规定。

---

## 目录

- [它能做什么](#它能做什么)
- [它不能做什么](#它不能做什么)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [命令一览](#命令一览)
- [工作原理](#工作原理)
- [相对上游的改动](#相对上游的改动)
- [常见问题](#常见问题)
- [注意事项](#注意事项)
- [目录结构](#目录结构)
- [致谢与许可](#致谢与许可)

---

## 它能做什么

| 能力 | 说明 |
|------|------|
| **视频任务点** | 以指定倍速播放并上报进度，直到平台判定章节完成 |
| **文档任务点** | 自动打开并翻阅课程文档，直到判定完成 |
| **章节测验** | 采集题目 → 生成答案 → 按平台格式提交 |
| **链式解锁** | 自动循环「刷视频 → 做测验 → 再刷」，直到全部章节走完 |
| **多课程并行** | 一次处理账号下多门课程，并发数可调 |
| **断点续跑** | 中断后重跑会从平台当前进度继续，不重复已完成内容 |
| **代理池** | 可配置多出口 IP，失败自动轮换，降低触发风控概率 |
| **状态自检** | 一条命令查看平台进度、运行记录、代理可用性 |

实测场景：一次完整运行可自动推进 40+ 门课、170+ 任务点。

---

## 它不能做什么

说清楚边界比夸大能力更有用：

- **简答题拿不到分。** 超星的简答题需要人工阅卷，自动提交一律计 0 分。
  但**任务点仍会算完成**，只是该测验的成绩是 0。
- **附件上传类任务拿不到分。** 「项目压缩包提交」「任务书提交」这类需要上传文件的题目，
  脚本只能提交文字说明，任务点会计完成，但老师批改时看不到你的真实文件。
  **这类任务请自行到网页端上传。**
- **不能代刷他人账号。** 脚本用的是你自己的登录态。
- **不会提高账号权限**，也不绕过平台的任何权限校验。
- **不是考试作弊工具。** 它只完成"任务点"，不解决需要独立思考的考试。

---

## 快速开始

### 环境要求

- Python 3.10+（推荐 3.13）
- Windows / macOS / Linux 均可

### 1. 安装

```bash
git clone https://github.com/YUYJYJ/chaoxing-auto-study.git
cd chaoxing-auto-study
python -m pip install -r requirements.txt
```

> 验证码识别库 `ddddocr`（约 80MB）是**可选**的，只有遇到平台验证码时才需要：
> `pip install ddddocr`

### 2. 准备登录态

在**浏览器**里打开学习通网页版并登录（手机扫码或账号密码），然后：

```bash
python scripts/setup_cookies.py
```

- 若浏览器开启了 CDP 调试端口（Edge/Chrome 的 `DevToolsActivePort` 文件存在），
  脚本会自动读取运行时 cookie，**包含 HttpOnly 字段**，最省事；
- 否则按提示手动导出：在开发者工具 Network 面板找到任意 `chaoxing` 请求，
  复制 `Cookie:` 请求头整行，粘贴到项目根目录的 `cookies.txt` 保存。

> `cookies.txt` 等同于你的登录凭证。请勿提交到任何仓库，也不要发给别人。

### 3. 看看有哪些课程

```bash
python scripts/list_courses.py
```

输出形如：

```
当前账号: 你的名字

课程ID           班级ID          课程名
----------------------------------------------------------------
100000001        200000001       某某课程（一）
...
```

### 4. 配置要刷的课程

```bash
cp config/courses.example.json config/courses.json
```

编辑 `config/courses.json`：

```json
{
  "course_ids": ["100000001", "100000002"],
  "speed": 2.0,
  "jobs": 6,
  "proxies": [],
  "proxy_rotate_on_error": true
}
```

| 字段 | 含义 | 建议 |
|------|------|------|
| `course_ids` | 要刷的课程 ID 数组；`[]` = 账号下全部课程 | 按需填写 |
| `speed` | 视频倍速 | `2.0`，超过此值极易触发风控 |
| `jobs` | 并发处理的章节数 | `4`~`6`，越大越快也越容易 403 |
| `proxies` | 代理地址数组 | 可选，见[代理池](#代理池) |
| `proxy_rotate_on_error` | 代理失败是否自动轮换 | 建议 `true` |

### 5.（可选）配置大模型 API，用于自动答测验

章节测验的答案**不在仓库里**。想全自动，就接一个你自己的大模型 API：

```bash
cp config/llm.example.json config/llm.json
```

编辑 `config/llm.json`：

```json
{
  "endpoint": "https://api.deepseek.com/v1/chat/completions",
  "key": "sk-你的密钥",
  "model": "deepseek-chat",
  "interval": 0.5,
  "timeout": 60
}
```

任何 **OpenAI 兼容**的 `/chat/completions` 端点都可以：

| 服务 | endpoint 示例 |
|------|---------------|
| DeepSeek | `https://api.deepseek.com/v1/chat/completions` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4/chat/completions` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |
| Kimi | `https://api.moonshot.cn/v1/chat/completions` |
| 本地 Ollama | `http://localhost:11434/v1/chat/completions`（完全免费） |

> `config/llm.json` 含密钥，已被 `.gitignore` 排除，不会误传。

### 6. 开始运行

```bash
python scripts/auto_run.py
```

**就这一条命令**，剩下的它自己搞定：采集题目 → 生成答案 → 提交测验 → 刷视频 → 读进度 → 循环，直到刷不动。

随时可以查看状态：

```bash
python scripts/status.py          # 进度 + 运行记录
python scripts/status.py --proxy  # 额外探测代理池
```

---

## 命令一览

| 命令 | 作用 |
|------|------|
| `python scripts/setup_cookies.py` | 从浏览器导出登录态到 `cookies.txt` |
| `python scripts/list_courses.py` | 列出账号下所有课程及 ID |
| `python scripts/auto_run.py` | **全自动循环**（推荐入口） |
| `python scripts/study.py` | 只刷视频 / 文档任务点 |
| `python scripts/harvest_quizzes.py` | 采集当前可做的章节测验题目 |
| `python scripts/generate_answers.py` | 用你的大模型 API 生成答案 |
| `python scripts/fill_quizzes.py` | 提交测验答案 |
| `python scripts/status.py` | 状态自检（进度 / 记录 / 代理） |

分步执行的顺序：

```bash
python scripts/harvest_quizzes.py    # 1. 采集题目 -> data/pending_questions.json
python scripts/generate_answers.py   # 2. 生成答案 -> data/answers.json
python scripts/fill_quizzes.py       # 3. 提交
python scripts/study.py              # 4. 刷视频
```

### 手工填写答案（不想用大模型）

把答案写进 `data/answers.json`（可先 `cp config/answers.example.json data/answers.json`）：

```json
{
  "【单选题】一套闭环自动控制系统按信号流动的顺序排列...": "B 给定→比较→放大→执行→被控对象→检测反馈",
  "【填空题】偏差的定义式可写作e等于____减____...": "给定值,输出量,r(t)-y(t)",
  "【判断题】磁性开关安装在气缸外部...": "对"
}
```

规则：

- **键**：题目标题（去掉开头的题号即可，脚本会做归一化 + 模糊匹配）
- **单选/多选**：写**选项原文**，脚本自动转成字母
- **判断题**：写 `对` 或 `错`
- **填空题**：多空用**英文逗号**分隔
- **简答题**：写完整文字（但平台仍需人工阅卷）

> 覆盖率不足 100% 时脚本会**跳过提交**，避免用空答案浪费平台的作答次数。

---

## 配置说明

### 代理池

超星按 IP 做频率限制。长时间高并发时单个 IP 容易吃到 403 或验证码。
在 `config/courses.json` 里配置多个代理：

```json
{
  "proxies": [
    "http://127.0.0.1:7890",
    "socks5://127.0.0.1:1080"
  ],
  "proxy_rotate_on_error": true
}
```

先探测哪些能用：

```bash
python scripts/status.py --proxy
```

输出：

```
[代理池] 共 2 个
    OK  http://127.0.0.1:7890  (142ms)
    FAIL socks5://127.0.0.1:1080  (8001ms)
```

> 单账号自用通常**不需要**代理。只有在频繁 403 时才考虑。

### 运行状态

`data/state.json` 记录每轮进度、已提交的测验、遇到的错误。
它不含任何个人信息，可以安全分享。查看摘要：

```bash
python scripts/status.py
```

---

## 工作原理

理解这几点有助于排查问题：

### 章节是链式解锁的

超星课程不是"所有视频一起解锁"的线性列表，而是：

```
1.1 视频 → 1.2 视频 → 1.3 视频 → 1.4 视频 → 1.5 章节测验 → 2.1 视频 → ...
                                    ↑                            ↑
                            必须先做掉 1.5              2.1 才能解锁
```

所以**单次运行只能推进一小段**。这正是 `auto_run.py` 存在的原因 ——
它循环「做测验 → 刷视频」直到全部解锁完毕。

### 视频进度是"上报"而非"下载"

脚本不是把视频下下来看完，而是每隔一段时间调用超星的进度上报接口，
告诉平台"我已经播到第 N 秒"。平台据此判定章节完成。
这解释了为什么 `speed` 会被限制 —— 上报的时间戳不合理会被识别出来。

### 字体加密

超星用 `@font-face` 把题面文字替换成自定义字形，页面里看到的是乱码：

```
"彘匯制造"  ← 实际是 "智能制造"
```

脚本用 `api/font_decoder.py`（配合 `upstream/resource/font_map_table.json`）
还原真实文字。**没有它就读不出题目**。

### 填空题是多空字段

超星填空题的答案字段名是 `answerEditor{题号}{空号}`，例如：

```
answerEditor4062393311   ← 第 1 空
answerEditor4062393312   ← 第 2 空
```

而且 HTML 里**只有第 1 空**的输入框，其余由页面 JS 动态生成。
必须依据 `tiankongsize{题号}` 声明的空数补齐所有字段，答案用英文逗号拆分到各空。

### 提交格式有严格要求

| 题型 | 必须提交 | 填错的后果 |
|------|----------|-----------|
| 单选 | 选项**字母**（`B`） | 平台报「作业提交失败！」 |
| 多选 | 排序后的字母串（`ABD`） | 同上 |
| 判断 | `true` / `false` | 同上 |
| 填空 | 原文（多空逗号分隔） | 提交成功但得 0 分 |
| 简答 | 原文 | 提交成功但得 0 分（需人工阅卷） |

---

## 相对上游的改动

上游 `Samueli924/chaoxing` 能跑，但在真实使用中有几个必须补的坑：

| # | 问题 | 现象 | 本项目的处理 |
|---|------|------|-------------|
| 1 | **填空题永远交空值** | 上游只写 `answer{id}`，而超星要 `answerEditor{id}{n}` | `api/decode.py` 采集 editor 字段，并按 `tiankongsize` 补齐多空 |
| 2 | **多空填空题字段不全** | HTML 只有第 1 空，第 2/3 空缺失 | 按 `tiankongsize` 生成全部 `answerEditor{id}{n}` |
| 3 | **答案格式不匹配** | 填选项原文 → 「作业提交失败！」 | `scripts/answer_utils.py` 统一转换 |
| 4 | **题目标题匹配不上** | 平台用 `\xa0` 和中文弯引号，手写键对不上 | 标题归一化 + 模糊匹配（cutoff 0.75） |
| 5 | **单次运行推不动** | 链式解锁导致大量章节显示「未开放」 | `auto_run.py` 循环推进 |
| 6 | **缺少进度可观测性** | 不知道跑到哪、错了什么 | `scripts/status.py` + `data/state.json` |
| 7 | **缺少代理支持** | 长时间高并发易 403 | `scripts/proxy_support.py` 代理池轮换 |

---

## 常见问题

**Q: 提示「登录失败」**
A: `cookies.txt` 失效或为空。重新运行 `python scripts/setup_cookies.py` 导出。
若浏览器开着调试端口，注意**关掉其他占用该端口的程序**（如某些浏览器扩展），
否则 cookie 读取会超时。

**Q: 日志刷 `403` 或要求验证码**
A: 降速。把 `speed` 调到 `1.5`、`jobs` 调到 `3`；或配置代理池；
必要时手动去网页端过一次验证码。

**Q: 进度一直不变**
A: 大概率卡在某个章节测验上（覆盖率不足 100% 会跳过提交）。
看 `data/state.json` 或日志里的「缺:」提示，把缺题的答案补进 `data/answers.json`。

**Q: 某门课显示 100% 但测验分数很低**
A: 正常。简答题和附件上传类任务自动提交得 0 分，但任务点仍算完成。
想拿分请自行到网页端补答 / 上传。

**Q: 能并行刷多个账号吗？**
A: 技术上可以（每个账号一份 cookie 与配置目录），但极易触发风控，
不建议。自用单账号足够。

**Q: 怎么彻底删掉我的登录信息？**
A: 删除项目根目录的 `cookies.txt`、`config/llm.json`、`config/courses.json`。

---

## 注意事项

请务必阅读：

1. **遵守学校与平台的规定。** 本工具用于自动化**自己的**学习任务。
   不要用于代考、替他人代刷、批量注册账号或任何违反校规的场景，
   也不要用于绕过平台的权限校验。

2. **不要提交 `cookies.txt`。** 它等同于你的登录凭证。
   本项目已通过 `.gitignore` 排除，但请自行留意。

3. **倍速与并发别开太高。** `speed` 建议 ≤ 2、`jobs` 建议 ≤ 6。
   超星有风控，异常参数可能触发验证码甚至临时限制账号。

4. **简答题与附件任务必须人工处理。** 自动化能拿到任务点，拿不到分数。

5. **仅限学习交流使用。** 如果你的课程有明确的禁止自动化条款，请不要使用本工具。

6. **GPL-3.0。** 本项目修改自 GPL-3.0 的上游代码，因此同样以 GPL-3.0 发布，
   保留上游署名与许可证。二次分发时必须同样开源。

---

## 目录结构

```
chaoxing-auto-study/
├── scripts/                   # 本项目新增的脚本
│   ├── setup_cookies.py       #   从浏览器导出登录态
│   ├── list_courses.py        #   列出课程与 ID
│   ├── harvest_quizzes.py     #   采集章节测验题目
│   ├── generate_answers.py    #   用你的 LLM API 生成答案
│   ├── fill_quizzes.py        #   答案格式转换 + 提交
│   ├── study.py               #   刷视频/文档（包装 upstream/main.py）
│   ├── auto_run.py            #   全自动循环入口
│   ├── status.py              #   状态自检
│   ├── answer_utils.py        #   标题归一化 / 答案格式转换
│   ├── proxy_support.py       #   代理池与轮换
│   ├── state.py               #   运行状态记录
│   └── common.py              #   配置与路径
├── upstream/                  # 修改过的上游代码（GPL-3.0）
│   ├── main.py                #   入口
│   ├── api/                   #   核心 API（decode.py / base.py 等有补丁）
│   ├── resource/
│   │   └── font_map_table.json#   字体映射表（解密题面必需）
│   └── LICENSE
├── config/
│   ├── courses.example.json   # 课程配置模板
│   ├── answers.example.json   # 答案格式示例（非真实答案）
│   ├── llm.example.json       # 大模型 API 配置模板
│   └── config.ini.example     # 上游配置模板
├── data/                      # 运行时数据（.gitignore 忽略）
│   ├── pending_questions.json #   采集到的题目
│   ├── answers.json           #   答案
│   └── state.json             #   运行记录
├── requirements.txt
├── LICENSE
└── README.md
```

---

## 致谢与许可

- **[Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)** —— 核心 API 与刷课逻辑
  （GPL-3.0）。本项目修改并重新分发其代码，许可证与署名均予保留。
- **[ddddocr](https://github.com/sml2h3/ddddocr)** —— 可选的验证码识别库（Apache-2.0）。

本项目以 **GPL-3.0** 发布，详见 [LICENSE](LICENSE)。
