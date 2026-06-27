# ================== 导入依赖 ==================
import os
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# ================== 初始化环境变量 & LLM ==================
load_dotenv()
llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),            # DeepSeek API Key
    base_url="https://api.deepseek.com",    # DeepSeek 接口地址
    model="deepseek-chat",
    temperature=0.3                          # 低温度保证输出稳定
)

class NovelState(TypedDict):
    novel_name: str
    plot: Optional[str]
    retry_count: int
    review_result: Optional[str]
# ================== 1. 定义核心节点 ==================

def plot_agent(state):
    prompt = ChatPromptTemplate.from_template(
        """请撰写小说《{novel_name}》的第一章情节，要求：
1. 引出主角；
2. 交代核心冲突；
3. 篇幅约200字。"""
    ) | llm

    plot_result = prompt.invoke({"novel_name": state["novel_name"]})
    retry_count = state.get("retry_count", 0)
    return {"plot": plot_result.content, "retry_count": retry_count}

def review_agent(state):
    """
    审核 Agent：判断情节是否达标
    严格返回 'pass' 或 'retry'
    """
    prompt = ChatPromptTemplate.from_template(
        """请审核以下小说情节是否达标，审核标准：
1. 引出主角；
2. 交代核心冲突；
3. 篇幅约200字。

情节：
{plot}

⚠️ 注意：只返回 'pass' 或 'retry'，不要输出其他内容，严格按照要求执行！"""
    ) | llm

    result = prompt.invoke({"plot": state["plot"]})
    return {"review_result": result.content.strip().lower()}

# ================== 2. 定义条件分支 ==================

def decide_next_node(state):
    """
    根据审核结果，决定下一步：
    - 'pass' -> 结束
    - 'retry' -> 重新生成情节，并累加重试次数
    """
    if state["review_result"] == "pass":
        return "end"
    else:
        # 重试次数 +1
        state["retry_count"] = state.get("retry_count", 0) + 1
        return "plot"

# ================== 3. 构建循环逻辑图 ==================
graph = StateGraph(NovelState)

# 添加节点
graph.add_node("plot", plot_agent)
graph.add_node("review", review_agent)
graph.add_node("end", lambda state: state)  # 结束节点

# 构建边
graph.add_edge(START, "plot")
graph.add_edge("plot", "review")

# 条件分支（审核结果决定下一步）
graph.add_conditional_edges(
    source="review",
    path=decide_next_node  # 直接返回 "end" 或 "plot"
)

# ================== 4. 编译 & 运行 ==================
app = graph.compile()

# 初始参数
input_state = {"novel_name": "星际流浪记", "retry_count": 0}

result = app.invoke(input_state)

# ================== 5. 打印最终结果 ==================
print(f"\n最终情节（重试 {result['retry_count']} 次）：\n")
print(result["plot"])