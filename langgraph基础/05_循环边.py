from typing import TypedDict, NotRequired

# ====== 全局共享状态（黑板） ======
class TaskState(TypedDict):
    user_query: str #用户原始查询
    intent: NotRequired[str] #用户意图
    llm_answer: NotRequired[str] #LLM 生成的回答
    tool_result: NotRequired[str] #工具调用结果
    final_answer: NotRequired[str] #最终回答
    progress: NotRequired[int] #任务进度百分比
    
    
#========固定边（线性流程）实践代码======
def parse_intent(state: TaskState):
    print("\n🔹 parse_intent")
    # 简单模拟意图识别
    intent = "summarize" if "总结" in state['user_query'] else "rewrite"
    return {"intent": intent, "progress": 30}


def summarize_node(state: TaskState):
    print("\n🔹 summarize_node")
    return {"llm_answer": f"总结结果: {state['user_query']}", "progress": 60}


def rewrite_node(state: TaskState):
    print("\n🔹 rewrite_node")
    return {"llm_answer": f"改写结果: {state['user_query']}", "progress": 60}


def final_node(state: TaskState):
    print("\n🔹 final_node")
    return {"progress": 100}

from langgraph.graph import StateGraph

builder = StateGraph(TaskState)

builder.add_node("parse_intent", parse_intent)
builder.add_node("summarize_node", summarize_node)
builder.add_node("rewrite_node", rewrite_node)
builder.add_node("final_node", final_node)

# 固定边（线性）
builder.set_entry_point("parse_intent")
builder.add_edge("parse_intent", "summarize_node")   # 固定走总结
builder.add_edge("summarize_node", "final_node")

graph = builder.compile()

state = TaskState(user_query="请帮我总结这段话")
print(graph.invoke(state))


def route_by_intent(state: TaskState):
    if state.get("intent") == "summarize":
        return "summarize_node"
    else:
        return "rewrite_node"


builder = StateGraph(TaskState)

builder.add_node("parse_intent", parse_intent)
builder.add_node("summarize_node", summarize_node)
builder.add_node("rewrite_node", rewrite_node)
builder.add_node("final_node", final_node)

builder.set_entry_point("parse_intent")

#=======循环节点======
def loop_node(state: TaskState):
    progress = state.get("progress", 0)
    print("\n🔄 loop_node, progress =", progress)
    return {"progress": progress + 30}

#=======循环条件函数======
def loop_router(state: TaskState):
    if state["progress"] >= 100:
        return "final_node"
    return "loop_node"

#=======构建图=========
builder = StateGraph(TaskState)

builder.add_node("loop_node", loop_node)
builder.add_node("final_node", final_node)

builder.set_entry_point("loop_node")

builder.add_conditional_edges(
    "loop_node",
    loop_router,
    {
        "loop_node": "loop_node",     # 回环
        "final_node": "final_node"    # 终止
    }
)

graph = builder.compile()

print(graph.invoke(TaskState(user_query="test")))