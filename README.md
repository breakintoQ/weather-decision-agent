<h1 align="center">Weather Decision Assistant</h1>

> 基于中国各地天气状况对于人们出游，活动，及生活的multi-agent简易建议助手demo。

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python" />
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License" />
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status" />
</p>


## 📌 Overview

**Weather Decision Assistant** 是一个面向中国城市的多 Agent 天气决策系统 Demo。
与传统天气查询不同，本项目聚焦于“决策”而非“数据”**，通过多 Agent 协作，将天气、空气质量和生活建议整合为**可执行的行动建议。

### ✨ Key Features

* 🌏 中国城市天气查询
* 🌫️ 空气质量与生活建议融合
* 🤖 多 Agent 工作流架构
* 🔌 MCP 工具调用机制
* 🧠 窗口式短期记忆
* 💬 多轮对话与上下文补全
* 🖥️ 前端交互验证（Streamlit）

---

## 🧠 Architecture

### 🔄 Workflow

```text
User Query
  → Planner
  → Weather Data Agent
  → Verifier
  → Recommender
  → Final Answer
```

### 📊 Data Flow

```text
Natural Language Query
  → Intent Parsing
  → MCP Tool Calls
  → Weather / AQI / Advice
  → Risk Assessment
  → Final Recommendation
```

---

## 🤖 Multi-Agent Design

系统由以下核心 Agent 组成：

| Agent                  | Responsibility       |
| ---------------------- | -------------------- |
| **Planner**            | 解析用户意图（地点 / 时间 / 活动） |
| **Weather Data Agent** | 调用 MCP 获取天气、空气质量等数据  |
| **Verifier**           | 校验数据完整性 & 风险等级       |
| **Recommender**        | 生成最终建议（规则 + LLM）     |

---

## 🔌 MCP Tooling

当前 MCP Server 提供以下工具：

* `geocode_location`
* `get_forecast`
* `get_alerts`
* `get_air_quality`
* `get_life_advice`

> ⚠️ `get_alerts` 已预留天气预警能力，需额外配置 Token

---

## 🧠 Memory Mechanism

系统采用**窗口式短期记忆（Session-based）**：

存储内容包括：

* 用户问题
* 对话摘要
* 决策结果
* 地点 / 时间 / 活动类型 / 问题类型

支持：

* 上下文继承
* 指代消解（如：“那后天呢”）

---

## 🚀 Getting Started

### 1. Install

```bash
pip install -U pip
pip install -e .
```

---

### 2. Run MCP Server

```bash
weather-mcp-serve
```

---

### 3. CLI Demo

```bash
python -m assistant.demo "北京明天天气怎么样"
```

查看完整状态：

```bash
python -m assistant.demo "上海明天适合跑步吗" --json
```

---

### 4. Web UI (Streamlit)

```bash
streamlit run assistant/ui/streamlit_app.py
```

---

## ✅ Verification

### 🔹 Smoke Test

```bash
python -m assistant.verification.smoke
```

验证内容：

* `.env` 配置加载
* LLM 可用性
* MCP 工具调用
* 数据链路完整性
* 最终推荐生成

---

### 🔹 Memory Validation

使用同一个 `Session ID`：

```text
1. 北京明天适合跑步吗
2. 那后天呢
3. 那适合骑行吗
```

重点检查：

* `intent.location`
* `intent.time_range`
* `intent.activity_type`

---

### 🔹 Follow-up Queries

推荐测试：

* 那后天呢
* 那上海呢
* 那适合骑行吗
* 那室内呢
* 那要带伞吗

---

## ⚠️ Limitations

* 天气预警源默认未启用
* 仅支持短期记忆（无用户画像）
* 复杂省略语义仍有优化空间
* 前端仅用于功能验证

---

## 🛣️ Roadmap

### v1.1

* [ ] 接入天气预警源
* [ ] 地点解析增强
* [ ] 指代理解优化

### v1.2

* [ ] 长期记忆
* [ ] 用户偏好建模
* [ ] 更多生活场景模板

---

## 📄 License

MIT License

---

## 💡 Design Philosophy

> 从 “天气查询” → “行动决策”

本项目的核心目标是探索：

* Multi-Agent 如何协作完成复杂任务
* MCP 工具如何与 LLM 解耦
* 如何构建可解释的 AI 决策系统
