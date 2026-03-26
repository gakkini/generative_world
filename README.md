# 🌍 Generative World Simulator

> 修仙世界AI模拟器 — 基于论文 "Generative Agents" 的开源实现

一个可以模拟仙侠世界中角色生活、社交、日记生成的AI系统。

## ✨ 功能特色

- 🎭 **16个可交互角色** — 每个角色有独特性格、目标和记忆
- 🧠 **完整认知架构** — 感知、规划、对话、反思、日记
- 📜 **动态主线剧本** — 可随时编辑的YAML剧本格式
- 🗺️ **大地图系统** — 支持传送阵和交通工具（1个月路程）
- 📖 **每日日记生成** — 角色视角的修仙日志

## 🚀 快速开始

### 环境要求

- Python 3.9+
- OpenAI API Key（可选，用于更智能的日记生成）

### 安装

```bash
# 克隆仓库
git clone https://github.com/gakkini/generative_world.git
cd generative_world

# 安装依赖
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

输出示例：

```
🌍 Generative World Simulator - 完整版
📍 世界：苍澜大陆
🗺️  地点数：5
👥 主角数：6
📅 第 1 天 | 修仙纪元1年 第1日

【李青云】
  👁️ 感知：看到慕容雪也在此
  💬 遇到同处一地的角色：['慕容雪']
  📋 计划：在客栈休息
  📖 日记：...
```

## 📂 项目结构

```
generative_world/
├── agents/                 # Agent核心模块
│   ├── base.py            # Agent总控
│   ├── memory.py          # 关联记忆 + 检索
│   ├── planning.py        # 规划大脑
│   ├── perception.py       # 感知系统
│   ├── dialogue.py        # 对话生成
│   └── diary.py           # 日记生成
├── core/                  # 世界核心
│   ├── world.py          # 世界状态管理
│   ├── time_system.py    # 时间系统
│   └── transport.py       # 交通系统
├── plot/                  # 剧本引擎
│   └── engine.py         # 动态剧本
├── config/                # 配置文件
│   ├── world.yaml        # 世界配置
│   └── plot_example.yaml # 剧本示例
└── main.py               # 入口
```

## ⚙️ 自定义配置

### 修改世界设定

编辑 `config/world.yaml`：

```yaml
world:
  name: "你的世界名称"

locations:
  - id: "your_location"
    name: "你的地点"
    type: "sect"  # sect / neutral / hostile

characters:
  - id: "p001"
    name: "角色名"
    sect: "your_sect"
    personality: "性格描述"
    cultivation: "修为等级"
```

### 添加剧本

编辑 `config/plot_example.yaml`：

```yaml
nodes:
  "chapter_1_01":
    title: "你的剧情"
    trigger:
      type: "day"
      value: 3  # 第3天触发
    actions:
      - type: "force_event"
        target_id: "p001"
        content: "事件内容"
```

## 🔧 LLM配置

要使用GPT-4生成更智能的日记，修改 `llm/interface.py`：

```python
class OpenAIClient:
    def __init__(self, api_key="你的API Key", model="gpt-4"):
        ...
```

或设置环境变量：

```bash
export OPENAI_API_KEY="你的API Key"
```

## 📖 模块说明

| 模块 | 说明 |
|------|------|
| **memory.py** | 记忆流 + 加权检索（相关度/新鲜度/重要度）|
| **planning.py** | 基于地点/性格生成行为计划 |
| **perception.py** | 感知周围角色、危险、机遇 |
| **dialogue.py** | 多轮对话生成 |
| **diary.py** | 日记生成（模板版 + LLM版）|

## 🎮 交通系统

| 方式 | 耗时 | 说明 |
|------|------|------|
| 传送阵 | 瞬间 | 配置 `days: 0` |
| 御剑 | 1个月 | 普通连接 |

## 📝 License

MIT License

## 🙏 致谢

基于斯坦福大学论文 [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
