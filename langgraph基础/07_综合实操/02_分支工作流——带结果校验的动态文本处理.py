#分支工作流

# ================== 依赖 ==================
from typing import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from torch.fx import graph

# ================== LLM 初始化 ==================
load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0.3
)

# ==========================================================
# 6.4.3 分支工作流案例：带结果校验的动态文本处理
# ==========================================================

# ----------------------------------------------------------
# 1️.状态定义：扩展工作流状态（新增循环控制字段）
# ----------------------------------------------------------
class BranchTextProcessState(TypedDict):
    """
    langgraph状态对象：
    分支工作流共享状态，用于节点之间传递数据（类似共享黑板）
    """
    #输入字段
    raw_text: str

    #中间过程字段
    deduplicated_text: NotRequired[str]
    summary_text: NotRequired[str]
    has_sensitive: NotRequired[bool]
    
    #循环控制字段
    rewrite_count: NotRequired[str]  #重写次数
    quality_valid: NotRequired[bool] #摘要质量是否合格

    #最终输出
    final_output: NotRequired[str]
    

#2.节点定义（工作流执行单元）

#文本去重节点
def deduplicate_node(state: BranchTextProcessState):
    """
    文本去重节点：
    输入：原始文本
    输出：去重后的文本
    """
    raw_text = state["raw_text"]
    lines = raw_text.split("\n")
    seen,unique_lines = set(),[]
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)

    print("[Node]去重完成")        
    return{"deduplicated_text":"\n".join(unique_lines)}


#摘要生成节点
def summary_node(state: BranchTextProcessState):
    """
    摘要生成节点：
    输入：去重后的文本
    输出：摘要文本
    """
    text = state.get("deduplicated_text","")
    
    #判断是否为空文本
    if not text:
        print("summary_text","无效文本")
    
    prompt = PromptTemplate(
        input_variables=["text"],
        template="请为以下文本生成50字以内摘要，保留核心信息：\n{text}"
    )
  
    summary = (prompt | llm).invoke({"text":text}).content
    
    print("[Node]摘要生成完成：",summary)
    return{"summary_text":summary}
    


#敏感词检测节点
def sensitive_check_node(state: BranchTextProcessState):
    """
    敏感词检测节点：
    输入：摘要文本
    输出：是否包含敏感信息
    """
    summary = state.get("summary_text","")
    sensitive_words = ["敏感词1","敏感词2","违法","违规"]
    has_sensitive = any(w in summary for w in sensitive_words)
    
    print("[Node]敏感词检测完成：",has_sensitive)
    return{"has_sensitive":has_sensitive}



#摘要质量检测节点
def quality_check_node(state: BranchTextProcessState):
    """
    摘要质量检测节点：
    输入：摘要文本
    输出：摘要质量是否合格
    """
    summary = state.get("summary_text","")

    #长度校验
    length_valid = 15 <= len(summary) <= 50

    #信息完整性校验
    core_keywords = ["Langgraph","工作流"]
    info_valid = all(k in summary for k in core_keywords)

    quality_valid = length_valid and info_valid
    
    print(f"[Node]摘要质量检测 | 长度0k={length_valid} | 信息完整性ok={info_valid} | 合格={quality_valid}")
    
    return{"quality_valid":quality_valid}   



#重新生成次数更新节点
def update_rewrite_count_node(state: BranchTextProcessState):
    """
    重新生成次数更新节点：
    输入：当前重写次数
    输出：更新重写次数
    """
    count = state.get("rewrite_count",0) + 1
    print(f"[Node]更新重写次数：{count}")

    return{"rewrite_count":count}   


#3.条件分支决策（langGraph核心）
def rewrite_router(state: BranchTextProcessState):
    """
    重写路由节点：
    输入：当前重写次数
    输出：是否继续重写
    """
    quality = state.get("quality_valid",False)
    count = state.get("rewrite_count",0)
    print(f"[Router]quality={quality} | rewrite_count={count}")
    
    #判断质量是否合格
    if quality:
        return "to_output"
    
    #不合格且重写次数未超过2次，继续重写
    if count < 2:
        return "to_rewrite"
   
   #次数超过2次，强制输出
    return "to_force_output"


#4.输出节点
#正常输出
def output_node(state: BranchTextProcessState) -> BranchTextProcessState:
    """
    输出节点(依据敏感词结果格式化）：
    输入：最终格式化处理结果
    输出：用户最终可见的处理结果
    """
    summary = state.get("summary_text","")
    has_sensitive = state.get("has_sensitive",False)
    if has_sensitive:
        final_output = "该文本包含敏感信息，不建议公开发布"
    else:
        final_output = f"""文本处理完成
        摘要：
        {summary}
        
        去重后原文
        {state["deduplicated_text"]}
        """
        
        print("输出节点执行完成")
        return{"final_output":final_output}



#强制输出节点
def force_output_node(state: BranchTextProcessState) -> BranchTextProcessState:
    """
    强制输出节点：
    输入：最终格式化处理结果
    输出：用户最终可见的处理结果
    """
    summary = state.get("summary_text","")
    final_output = f"""
    摘要多次重生成仍不合格（教学示例）
    重生成次数: {state.get('rewrite_count', 0)}
    摘要长度: {len(summary)}

    强制输出摘要：
    {summary}

"""
        
    print("[Node]强制输出节点")
    return{"final_output":final_output}



#5.构建langGraph分支工作流
def build_branch_graph():
    """
    构建分支工作流图：
    实际启用状态历史
    从输入节点开始，根据条件路由，执行不同分支，最后输出结果
    """
    graph = StateGraph(BranchTextProcessState)
    
    #注册节点
    graph.add_node("deduplicate",deduplicate_node)
    graph.add_node("summary",summary_node)
    graph.add_node("sensitive_check",sensitive_check_node)
    graph.add_node("quality_check",quality_check_node)
    graph.add_node("update_rewrite_count",update_rewrite_count_node)
    graph.add_node("router",rewrite_router)
    graph.add_node("output",output_node)
    graph.add_node("force_output",force_output_node)

    #固定执行路径
    graph.add_edge(START,"deduplicate")
    graph.add_edge("deduplicate","summary")
    graph.add_edge("summary","sensitive_check")
    graph.add_edge("sensitive_check","quality_check")

    #条件分支
    graph.add_conditional_edges(
        "quality_check",rewrite_router,
        {"to_output":"output",
        "to_rewrite":"update_rewrite_count",
        "to_force_output":"force_output"}
    )

    #循环回退路径
    graph.add_edge("update_rewrite_count","summary")

    #结束节点
    graph.add_edge("output",END)
    graph.add_edge("force_output",END)

    return graph.compile(checkpointer=MemorySaver())



# ----------------------------------------------------------
# 6️⃣ 运行测试（课堂演示用）
# ----------------------------------------------------------
if __name__ == "__main__":
    branch_graph = build_branch_graph()

    # 初始状态
    test_state: BranchTextProcessState = {
        "raw_text": "LangGraph是LangChain生态下的有状态工作流框架，支持图结构建模、状态追溯、动态分支和并行执行，适用于复杂AI任务编排",
        "rewrite_count": 0,
    }

    config = {"configurable": {"thread_id": "branch_workflow_demo"}}

    print("\n🚀 启动分支工作流示例\n" + "=" * 60)
    final_state = branch_graph.invoke(test_state, config=config)

    # 输出结果
    print("\n🎯 最终结果:")
    print(final_state["final_output"])

    print("\n📊 执行统计:")
    print("重生成次数:", final_state.get("rewrite_count"))
    print("质量是否合格:", final_state.get("quality_valid"))

    # 状态历史（教学亮点）
    history = list(branch_graph.get_state_history(config))
    print(f"\n📜 状态历史步数: {len(history)}")

    # 可视化图
    png_data = branch_graph.get_graph().draw_mermaid_png()
    with open("branch_workflow_graph.png", "wb") as f:
        f.write(png_data)
    print("📊 工作流图已保存: branch_workflow_graph.png")