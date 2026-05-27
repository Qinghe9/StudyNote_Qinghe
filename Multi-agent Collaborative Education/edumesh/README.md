# 🧠 EduMesh - 多Agent智能教育与个性化学习系统

> **Mesh架构 + 事件驱动** 的企业级多Agent教育系统，采用5-Agent协作模式，支持实时个性化学习路径调整。

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        EventBus (事件总线)                     │
│                    支持发布/订阅 + 双向异步通信                 │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │Assessment│    │Curriculum│    │  Tutor  │    │Engagement│
    │  Agent   │    │  Agent   │    │  Agent  │    │  Agent   │
    │  (BKT)   │    │  (SM-2)  │    │(苏格拉底)│    │(状态监测) │
    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                                    │
                              ┌─────┴─────┐
                              │ Hint Agent │
                              │ (三级提示)  │
                              └───────────┘
```

### 5个Agent职责

| Agent | 核心算法/策略 | 职责 |
|-------|-------------|------|
| **Assessment Agent** | BKT贝叶斯知识追踪 | 实时评估学生对每个知识点的掌握概率 P(L) |
| **Curriculum Agent** | SM-2间隔重复算法 | 动态调整学习路径和复习时机 |
| **Tutor Agent** | 苏格拉底式提问 | 85%引导率，通过提问而非直接给答案 |
| **Engagement Agent** | 挫败检测模型 | 监测学习状态，防止放弃 |
| **Hint Agent** | 三级提示策略 | Level 1→2→3 渐进式提示 |

## 🚀 快速启动

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端

```bash
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端将运行在 `http://localhost:8000`

### 3. 启动前端

前端是纯HTML/JS，可直接用浏览器打开 `frontend/index.html`，或使用任意静态服务器：

```bash
# 方式1: Python内置服务器
cd frontend
python -m http.server 3000

# 方式2: Node.js serve
npx serve frontend

# 方式3: VS Code Live Server插件
```

前端将运行在 `http://localhost:3000`

### 4. 配置LLM (可选)

默认使用 Mock 模式（模拟LLM响应）。如需接入真实LLM：

```bash
# OpenAI
export LLM_PROVIDER=openai
export LLM_API_KEY=sk-xxx
export LLM_MODEL=gpt-4

# Anthropic
export LLM_PROVIDER=anthropic
export LLM_API_KEY=sk-ant-xxx
export LLM_MODEL=claude-3-sonnet-20240229
```

## 📡 API文档

启动后端后访问：`http://localhost:8000/docs`

### 核心接口

- `POST /api/students` - 创建学生
- `GET /api/students/{id}` - 获取学生信息
- `GET /api/students/{id}/mastery` - 掌握度数据
- `GET /api/questions/next?student_id=xxx` - 获取下一题
- `POST /api/answers` - 提交答案
- `GET /api/events/{student_id}` - 事件历史
- `WS /ws/{student_id}` - WebSocket实时通信

## 🎯 核心事件流

### 学生答题流程
```
学生提交答案
  → STUDENT_SUBMISSION 事件
  → Assessment Agent (BKT更新P(L))
  → MASTERY_UPDATED 事件
  → Curriculum Agent (SM-2更新复习计划)
  → ASSESSMENT_COMPLETE 事件
  → Tutor Agent (苏格拉底式回复)
  → Engagement Agent (分析状态)
```

### 学生连续答错流程
```
连续答错2次
  → HINT_NEEDED 事件
  → Hint Agent (判断提示级别1/2/3)
  → HINT_RESPONSE 事件
  → Tutor Agent (包装为苏格拉底式提问)
```

### 挫败检测流程
```
参与度<0.3 或 连续错误≥3
  → ENGAGEMENT_ALERT 事件
  → Tutor Agent (安抚+降低难度)
  → Curriculum Agent (放慢节奏+插入复习)
```

## 🧪 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python, FastAPI, WebSocket |
| 架构 | Mesh + EventBus + 事件驱动 |
| 算法 | BKT, SM-2, 苏格拉底Prompt |
| 前端 | 原生HTML/CSS/JS (零依赖) |
| 通信 | REST API + WebSocket双通道 |

## 📁 项目结构

```
edumesh/
├── backend/
│   ├── main.py                 # FastAPI入口 + WebSocket
│   ├── event_bus.py            # Mesh事件总线
│   ├── requirements.txt
│   ├── models/
│   │   ├── events.py           # 事件类型定义
│   │   └── student.py          # 学生/题目数据模型
│   ├── agents/
│   │   ├── base.py             # Agent基类
│   │   ├── assessment.py       # Assessment Agent (BKT)
│   │   ├── curriculum.py       # Curriculum Agent (SM-2)
│   │   ├── tutor.py            # Tutor Agent (苏格拉底)
│   │   ├── engagement.py       # Engagement Agent
│   │   └── hint.py             # Hint Agent (三级提示)
│   └── services/
│       ├── llm.py              # LLM服务接口
│       └── question_bank.py    # 题库数据
└── frontend/
    ├── index.html              # 主页面
    ├── style.css               # 样式
    └── app.js                  # 交互逻辑
```

## 📄 License

MIT License
