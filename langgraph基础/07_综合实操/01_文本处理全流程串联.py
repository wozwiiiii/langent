# 文本处理全流程串联

#========基础依赖========
from typing import TypedDict,NotRequired
from langgraph.graph import StateGraph,START,END
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver


#接入模型,查找环境变量
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.types import Checkpointer

load_dotenv()


#初始化模型
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat",
    temperature=0.5,
)


#1.定义State(工作流共享状态 = Agent 内存)
class TextProcessState(TypedDict):
    """
    langgraph状态对象：
    用于节点之间传递数据（类似全局共享内存）
    """
    raw_text: str       #输入：用户原始文本
    deduplicated_text:NotRequired[str] #过程：去重后文本
    summary_text:NotRequired[str] #过程：摘要文本
    has_sensitive:NotRequired[bool] #过程：是否包含敏感信息
    final_output:NotRequired[str] #输出：最终格式化处理结果



#2、定义节点函数（每个节点 = 一个处理函数）
def deduplicate_node(state: TextProcessState) -> TextProcessState:
    """
    去重节点：
    输入：用户原始文本
    输出：去重后文本
    """
    raw_text = state["raw_text"]
    lines = raw_text.split("\n")
    unique_lines = []
    seen = set()
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped not in seen:
            seen.add(line_stripped)
            unique_lines.append(line)
        print("去重节点执行完成")
        return{"deduplicated_text":"\n".join(unique_lines)}



def summary_node(state: TextProcessState) -> TextProcessState:    
    """
    摘要节点：
    输入：去重后文本
    输出：摘要文本
    """
    deduplicated_text = state["deduplicated_text"]
    prompt = PromptTemplate(
        input_variables=["text"],
        template="请为以下文本生成50字以内的简洁摘要，保留核心信息：\n{text}"
    )
    chain = prompt | llm
    summary = chain.invoke({"text":deduplicated_text}).content
    print("摘要节点执行完成")
    return{"summary_text":summary}



def sensitive_node(state: TextProcessState) -> TextProcessState:
    """
    敏感信息检测节点：
    输入：摘要文本
    输出：是否包含敏感信息
    """
    summary = state["summary_text"]
    sensitive_words = ["敏感词1","敏感词2","违法","违规"]
    has_sensitive = any(word in summary for word in sensitive_words)
    print("敏感词检测完成：",has_sensitive)
    return{"has_sensitive":has_sensitive}
    


def output_node(state: TextProcessState) -> TextProcessState:
    """
    输出节点(依据敏感词结果格式化）：
    输入：最终格式化处理结果
    输出：用户最终可见的处理结果
    """
    summary = state["summary_text"]
    has_sensitive = state["has_sensitive"]
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



#3.构建线性工作流图（固定边）
def build_linear_graph():
    """
    构建线性工作流图：
    实际启用状态历史
    从输入节点开始，按顺序执行所有节点，最后输出结果
    """
    graph_builder = StateGraph(TextProcessState)

    #注册节点
    graph_builder.add_node("deduplicate",deduplicate_node)
    graph_builder.add_node("summary",summary_node)
    graph_builder.add_node("sensitive",sensitive_node)
    graph_builder.add_node("output",output_node)


    #配置固定边（线性执行）
    graph_builder.add_edge(START,"deduplicate")
    graph_builder.add_edge("deduplicate","summary")
    graph_builder.add_edge("summary","sensitive")
    graph_builder.add_edge("sensitive","output")
    graph_builder.add_edge("output",END)


    #修改核心：编译时传入MemorySaver,真正启用状态历史
    #MemorySaver: 内存中的状态存储器，用于存储节点之间的状态,内存级检查点，适合测试/开发，重启程序后状态丢失
    return graph_builder.compile(checkpointer=MemorySaver())



#4.测试运行（get_state_history可正常运行）
if __name__ == "__main__":

    #构建图
    linear_graph = build_linear_graph()

    #初始化状态
    test_state: TextProcessState = {
        "raw_text": "Langgrapgh是langchain生态的工作流框架\nLangGraph支持状态管理\nLangGraph是LangChain生态的工作流框架\n支持动态分支和并行执行"
    }

    #thread_id:会话唯一标识，测试用随便取名，多会话用不同ID
    config = {"configurable":{"thread_id":"test_process_test_001"}}
    
    #关键修改2：invoke传入config
    final_state = linear_graph.invoke(test_state,config=config)
    print(final_state["final_output"])
    

    #关键修改3：get_state_history时也传入同一个config
    print("\n"+ "=" * 50)
    history = list(linear_graph.get_state_history(config))
    print("状态快照数量（超步骤）：",len(history))

    for i,state in enumerate(history,1):
        print(f"\n状态快照 {i}:")
        print("state:",state)
        print("=" * 50)