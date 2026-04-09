# Weather Decision Assistant v1.0

## 1. 项目简介

`Weather Decision Assistant` 是一个面向中国城市天气决策场景的多 Agent Demo。  
项目不只返回天气数据，还会结合空气质量、生活建议、多轮上下文和短期记忆，为用户生成可执行的出行与活动建议。

当前版本聚焦于以下目标：

- 支持中国城市天气查询
- 支持空气质量与生活建议联动
- 支持多 Agent 工作流
- 支持 MCP 工具调用
- 支持窗口短期记忆
- 支持多轮追问与上下文补全
- 支持前端页面验证

## 2. 核心能力

### 2.1 多 Agent 工作流
当前系统由以下几个 Agent 节点组成：

- `Planner`
  负责解析用户意图，识别地点、时间、活动类型、问题类型

- `Weather Data Agent`
  负责通过 MCP 调用天气、空气质量、生活建议等工具

- `Verifier`
  负责检查数据完整性、风险等级和错误状态

- `Recommender`
  负责融合规则、工具结果和 LLM 输出，生成最终建议

### 2.2 MCP 工具层
当前 MCP server 暴露的工具包括：

- `geocode_location`
- `get_forecast`
- `get_alerts`
- `get_air_quality`
- `get_life_advice`

说明：
- `get_alerts` 当前已预留中国天气预警源接入能力
- 若未配置预警服务 Token，则会返回明确提示

### 2.3 多轮上下文补全
系统支持窗口式短期记忆,优先使用规则模板进行继承与改写,再结合 LLM 对上下文进行理解.

## 5. 系统架构

### 5.1 工作流

```text
User Query
  -> Planner
  -> Weather Data Agent
  -> Verifier
  -> Recommender
  -> Final Answer
```

### 5.2 数据流

```text
Natural Language Query
  -> Intent Parsing
  -> MCP Tool Calls
  -> Forecast / Air Quality / Life Advice
  -> Risk Assessment
  -> Final Recommendation
```

### 5.3 记忆机制

系统使用窗口短期记忆保存最近若干轮对话摘要，按 `session_id` 组织：

- 用户问题
- 助手摘要
- 决策结果
- 地点
- 时间
- 活动类型
- 问题类型

## 6. 环境配置

### 6.1 建议解释器
建议始终使用项目内虚拟环境：

```powershell
.\.venv\Scripts\python.exe
```

### 6.2 配置文件
在项目根目录创建 `.env`，可参考 .env.example

## 7. 安装依赖

```powershell
pip install -U pip
pip install -e .
```

## 8. 运行方式

### 8.1 启动 MCP 服务

```powershell
weather-mcp-serve
```

### 8.2 运行 CLI Demo

```powershell
-m assistant.demo "北京明天天气怎么样"
```

查看完整状态：

```powershell
-m assistant.demo "上海明天适合跑步吗" --json
```

### 8.3 运行前端页面

```powershell
-m streamlit run assistant/ui/streamlit_app.py
```

## 9. 如何验证

### 9.1 运行 smoke test

```powershell
-m assistant.verification.smoke
```

该脚本会验证：

- 配置层是否正确加载 `.env`
- LLM 是否可调用
- MCP 工具是否暴露成功
- 天气、空气质量、生活建议是否进入主链路
- 最终建议是否生成成功

### 9.2 验证短期记忆
在前端页面中使用同一个 `Session ID` 连续提问，例如：

1. `北京明天适合跑步吗`
2. `那后天呢`
3. `那适合骑行吗`

你可以观察：

- 左侧 `Memory Window`
- 右侧 `Latest State`

重点检查：

- `intent.location`
- `intent.time_range`
- `intent.activity_type`

是否被正确继承和补全。

### 9.3 验证指代追问
推荐测试这些追问模板：

- `那后天呢`
- `那上海呢`
- `那适合骑行吗`
- `那室内呢`
- `那要带伞吗`

## 10. 当前版本限制

- 中国天气预警源为可选接入，默认未启用
- 窗口记忆为短期记忆，不包含长期用户画像
- 多轮补全已经支持常见追问，但复杂省略式问法仍可继续优化
- 当前前端以功能验证为主

## 11. 后续规划

### v1.1
- 完善中国天气预警源接入
- 增强地点解析与消歧
- 增强多轮指代理解

### v1.2
- 增加长期记忆
- 增加用户偏好
- 增加更多生活场景建议模板

