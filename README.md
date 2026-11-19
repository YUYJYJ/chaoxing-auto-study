# 学习通（超星）任务点自动化工具

一个命令行工具，用于自动完成学习通网页版的**视频/文档任务点**与**章节测验**。
它基于开源项目 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)（GPL-3.0），
在其之上补齐了几个实际使用中必需的能力。

## 它解决什么问题

超星的章节是**链式解锁**的：做完第 N 章才解锁第 N+1 章；如果第 N+1 章是章节测验，
必须先做掉测验才能继续。因此单次运行往往只能推进一小段。本工具提供：

- 自动循环「刷视频 → 做测验 → 再刷视频」，直到平台显示进度不再增长；
- 章节测验的题目录取、答案缓存、格式转换与自动提交；
- 从本机浏览器导出登录态（cookie），无需明文保存账号密码；
- 课程 ID、倍速、并发数全部配置文件化，换电脑/换账号都能用。

## 相对上游修复的关键问题

这些是实际跑通时踩出来的坑，上游脚本并未处理：

1. **填空题永远提交空值**  
   超星填空题的答案字段是 `answerEditor{题号}{空号}`，且 HTML 里只有第 1 空的输入框，
   其余由页面 JS 动态生成。上游只写 `answer{id}`，导致填空题提交空值。
   本工具按 `editor_fields` 补齐所有空位，并按英文逗号拆分答案。

2. **答案格式不匹配导致"作业提交失败"**  
   单选必须提交**选项字母**，多选是排序后的字母串，判断是 `true`/`false`；
   填空/简答才是原文。本工具的 `answer_utils.py` 负责转换。

3. **题目标题匹配失败**  
   平台题干里用不换行空格 `\xa0`、中文弯引号 `“”`，与手写的答案键常不一致。
   统一做了归一化 + 模糊匹配。

4. **简答题自动提交不计分**  
   这是平台设计（简答题需人工阅卷），不是脚本 bug。自动提交的简答题得 0 分，
   但任务点仍会算完成。如果要拿分，请自行到网页端补答。

## 安装

需要 Python 3.10+（推荐 3.13）。

```bash
git clone <你的仓库地址>
cd chaoxing-tool
python -m pip install -r requirements.txt
```

依赖来自上游项目：`requests`, `beautifulsoup4`, `lxml`, `loguru`, `tenacity`,
`pyaes`, `fonttools`, `openai`, `httpx`, `urllib3`, `chardet` 等。
验证码识别库 `ddddocr`（约 80MB）是**可选**的，只有遇到平台验证码时才需要：
`pip install ddddocr`。

## 使用流程

### 1. 准备登录态（cookie）

在浏览器里先登录学习通网页版，然后：

```bash
python scripts/setup_cookies.py
```

- 若浏览器开启了 CDP 调试端口（Edge/Chrome 的 `DevToolsActivePort` 文件存在），
  脚本会自动读取运行时 cookie，包含 HttpOnly 字段；
- 否则按提示从开发者工具的 Network 面板手动复制 Cookie 到 `cookies.txt`。

> 也可以在项目根目录的 `config.ini` 里填手机号和密码（`use_cookies=false`），
> 但 cookie 方式更稳，不会触发登录验证码。

### 2. 查看课程列表

```bash
python scripts/list_courses.py
```

会列出你账号下所有课程及其 ID。

### 3. 配置要刷的课程

复制模板并填写课程 ID：

```bash
cp config/courses.example.json config/courses.json
```

```json
{
  "course_ids": ["课程ID1", "课程ID2"],
  "speed": 2.0,
  "jobs": 6
}
```

`course_ids` 留空数组 `[]` 表示账号下全部课程。
`speed` 是视频倍速（2 为常用值，过高易触发风控），`jobs` 是并发章节数。

### 4. 开始刷任务点

```bash
python scripts/auto_run.py
```

它会自动循环：采集题目 → 提交测验 → 刷视频 → 读进度，直到跑不动。

也可以分步骤手动执行：

```bash
python scripts/study.py                 # 只刷视频/文档
python scripts/harvest_quizzes.py       # 只采集章节测验题目
python scripts/fill_quizzes.py          # 提交测验（需先写答案）
```

### 5. 测验答案：自动生成（推荐）或手工填写

章节测验的答案**不在仓库里**。两种做法：

**A. 用你自己的大模型 API 自动生成（推荐）**

```bash
cp config/llm.example.json config/llm.json
# 编辑 config/llm.json，填入 endpoint / key / model
python scripts/generate_answers.py
```

支持任何 OpenAI 兼容的 chat/completions 端点：DeepSeek、智谱、通义、Kimi、
OpenAI，或本地 Ollama（`http://localhost:11434/v1/chat/completions`）。
`config/llm.json` 含密钥，已被 `.gitignore` 排除，不会上传。

配好 `llm.json` 后，`auto_run.py` 会自动调用它，全程无需手工答题。

**B. 手工填写**

采集后题目在 `data/pending_questions.json`。把答案写进 `data/answers.json`
（可先 `cp config/answers.example.json data/answers.json` 再改）：

```json
{
  "【单选题】一套闭环自动控制系统按信号流动的顺序排列...": "B 给定→比较→放大→执行→被控对象→检测反馈",
  "【填空题】偏差的定义式可写作e等于____减____...": "给定值,输出量,r(t)-y(t)"
}
```

规则：
- 键用题目标题（可从 `pending_questions.json` 复制）；
- 单选/多选写**选项原文**即可，脚本会转成字母；
- 判断题写 `对` 或 `错`；
- 填空题多空用**英文逗号**分隔；
- 简答题写完整文字（但平台仍需人工阅卷）。

覆盖率不足 100% 时脚本会**跳过提交**，避免用空答案浪费作答次数。

## 目录结构

```
chaoxing-tool/
├── scripts/
│   ├── setup_cookies.py      # 导出浏览器 cookie
│   ├── list_courses.py       # 列出课程与ID
│   ├── harvest_quizzes.py    # 采集章节测验题目
│   ├── generate_answers.py   # 用你自己的 LLM API 生成答案
│   ├── fill_quizzes.py       # 答案格式转换 + 提交
│   ├── study.py              # 刷视频/文档（包装 upstream/main.py）
│   ├── auto_run.py           # 全自动循环入口
│   ├── answer_utils.py       # 标题归一化 / 答案格式转换
│   └── common.py             # 配置与路径
├── upstream/                 # 修改过的上游代码（GPL-3.0）
│   ├── main.py               # 加了字体字段补丁
│   ├── api/                  # decode.py / base.py 亦有补丁
│   ├── LICENSE
│   └── resource/font_map_table.json
├── config/
│   ├── answers.example.json  # 答案格式示例（非真实答案）
│   ├── llm.example.json      # 大模型 API 配置模板
│   ├── courses.example.json  # 课程配置模板
│   └── config.ini.example    # 上游配置模板
├── data/                     # 运行时数据（被 .gitignore 忽略）
└── requirements.txt
```

## 注意事项

- **遵守你所在学校/平台的规定**。本工具用于自动化自己的学习任务，
  不要用于代考、刷分或任何违反校规的场景。
- 倍速和并发过高容易触发平台风控（403/验证码）。遇到 403 请降低 `speed`/`jobs`。
- 简答题、附件上传类任务无法靠脚本拿到分数，需要人工到网页端处理。
- `cookies.txt` 等同于你的登录凭证，**不要提交到任何代码仓库**，也别发给别人。
- 仓库**不附带任何课程的真实答案**。`config/answers.example.json` 只是格式示例，
  章节测验的答案需要你自己填写——这既是平台要求，也是学习本身的一部分。
- 本项目基于 GPL-3.0 的上游代码修改，因此同样以 GPL-3.0 发布。

## 致谢

- [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing) — 核心 API 与刷课逻辑（GPL-3.0）
