import os
from typing import Dict, List, Optional, TypedDict
from typing_extensions import NotRequired
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver

# ===================== 1. 加载环境变量 =====================
# 加载.env文件中的环境变量（如API_KEY），避免硬编码敏感信息
load_dotenv()

# ===================== 2. 初始化大语言模型 =====================
# 配置DeepSeek大模型参数，用于小说创作各阶段的文本生成
llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),  # 从环境变量读取API密钥
    base_url="https://api.deepseek.com",  # DeepSeek API地址
    model="deepseek-chat",  # 选用的模型版本
    temperature=0.3  # 生成文本的随机性，0.3表示低随机性，输出更稳定
)

# ===================== 4. 工具函数：进度展示 =====================
def print_process(current_stage: str, detail: str = ""):
    """打印整体流程进度，让用户直观了解当前执行阶段"""
    # 阶段映射表：将阶段名称转换为进度百分比标识
    stage_map = {
        "需求收集": "1/4",
        "设定生成": "2/4",
        "大纲生成": "3/4",
        "报告生成": "4/4"
    }
    progress = stage_map.get(current_stage, "未知阶段")
    print(f"\n🔄 【整体进度 {progress}】- {current_stage} {detail}")

def print_chapter_progress(generated: int, total: int):
    """打印章节生成进度（百分比），监控正文生成进度"""
    percentage = (generated / total) * 100 if total > 0 else 0
    print(f"\n📖 【章节进度】已完成 {generated}/{total} 章 ({percentage:.1f}%)")


class ExperimentReportState(TypedDict):
    '报告创作全流程状态管理（含进度状态）'
    
    #初始输入
    experiment_topic: str

    #基础设定（第二阶段）
    experiment_title: NotRequired[Optional[str]] 
    main_chapters: NotRequired[Optional[List[Dict[str, str]]]] 
    plot_content: NotRequired[Optional[str]]

    #确认状态
    is_setting_confirmed: NotRequired[bool] 
    is_outline_confirmed: NotRequired[bool] 

    #大纲与章节
    experiment_outline: NotRequired[Optional[str]] 
    chapter_structure: NotRequired[Optional[List[Dict[str, str]]]]

    #最终实验报告
    completed_report: NotRequired[Optional[str]] 

    #进度追踪
    current_stage: NotRequired[Optional[str]]
    experiment_generate_count: NotRequired[int]



#核心步骤2：定义各个节点
# 1：用户输入节点"""
def user_input_node(state: ExperimentReportState) -> ExperimentReportState:
    #提示用户输入要求，引导用户输入实验具体科目及部分相关内容
    print("请输入你的实验报告创作需求（示例：实验具体科目是通信原理，相关内容为傅里叶变换，要实事求是）")
    user_input = input()
    
    #将用户输入的实验具体科目及部分相关内容赋值给状态中的experiment_topic
    state['experiment_topic'] = user_input
    state['current_stage'] = "需求收集"
    state['is_setting_confirmed'] = False
    state['is_outline_confirmed'] = False
    print_process("需求收集", "（完成）✅")

    return state


# 2：LLM初始生成节点
def generate_basic_setting(state: ExperimentReportState) -> ExperimentReportState:
    '节点2：LLM初始生成节点'
    print_process("设定生成","（开始生成题目，章节目录，报告大致要点）")

    prompt = PromptTemplate(
        template="""
        请根据用户需求生成实验报告基础设定，要求：
        1. 实验报告题目：1-2个备选，简洁，符合实验具体科目
        2. 章节目录：至少4个，格式为「章节描述」
        3. 报告大致要点：每章节50字，清晰说明实验整体走向
        报告题目：{experiment_topic}
        
        输出格式（严格遵循）：
        题目：xxx
        主要章节：
        - 章节1：章节描述1
        - 章节2：章节描述2
        - 章节3：章节描述3
        - 章节4：章节描述4
        报告大致要点：xxx
        """
        ,
        input_variables=['experiment_topic'] 
    )
    
    response = llm.invoke(prompt.format(experiment_topic=state["experiment_topic"]))    
    setting_content = response.content.strip()
    
    # 解析结果
    lines = setting_content.split("\n")
    state["main_chapters"] = []
    for line in lines:
        if line.startswith("题目："):
            state["experiment_title"] = line.replace("题目：", "").strip()
        elif line.startswith("主要章节："):
            continue
        elif line.startswith("- "):
            name, desc = line.replace("- ", "").split("：", 1)
            state["main_chapters"].append({"章节名称": name, "章节描述": desc})
        elif line.startswith("报告大致要点："):
            state["plot_content"] = line.replace("报告大致要点：", "").strip()
    
    # 展示设定
    print("\n===== 生成的报告基础设定 =====")
    print(f"题目：{state['experiment_title']}")
    print("主要章节：")
    for char in state["main_chapters"]:
        print(f"- {char['章节名称']}：{char['章节描述']}")
    print(f"报告大致要点：{state['plot_content']}")
    
    state["current_stage"] = "设定生成"
    print_process("设定生成", "（完成）✅")
    return state

# 3：用户审核节点（确认报告基础设定）
def confirm_basic_setting(state: ExperimentReportState) -> ExperimentReportState:   
    "节点3：人工审核确认基础设定（LangGraph 中断后执行）"
    print("\n===== ⚠️ 人工审核 - 基础设定确认环节 =====")
    confirm = input("是否确认以上基础设定？（确认请输入y，需修改请输入n并说明修改内容）：")
    
    if confirm.lower() == "y":
        state["is_setting_confirmed"] = True
        print("✅ 基础设定已确认，进入下一阶段！")
    else:
        # 接收修改需求并更新
        modify_content = input("请输入你的修改需求（如：修改章节名称/调整报告大致要点/更换题目）：")
        print("🔄 正在根据你的需求修改基础设定...")
        
        prompt = PromptTemplate(
            template="""
            请根据用户的原始需求和修改需求，更新实验报告基础设定：
            原始需求：{experiment_topic}
            修改需求：{modify_content}
            输出格式（严格遵循）：
            题目：xxx
            主要章节：
            - 章节1：章节描述1
            - 章节2：章节描述2
            - 章节3：章节描述3
            - 章节4：章节描述4
            报告大致要点：xxx   
            """,
            input_variables=["experiment_topic", "modify_content"]
        )
        
        response = llm.invoke(prompt.format(
            experiment_topic=state["experiment_topic"],
            modify_content=modify_content
        ))
        setting_content = response.content.strip()
        
        # 重新解析
        lines = setting_content.split("\n")
        state["main_chapters"] = []
        for line in lines:
            if line.startswith("题目："):
                state["experiment_title"] = line.replace("题目：", "").strip()
            elif line.startswith("主要章节："):
                continue
            elif line.startswith("- "):
                chapter_name, desc = line.replace("- ", "").split("：", 1)
                state["main_chapters"].append({"章节名称": chapter_name, "章节描述": desc})
            elif line.startswith("报告大致要点："):
                state["plot_content"] = line.replace("报告大致要点：", "").strip()
        
        # 再次展示并确认
        print("\n===== 修改后的基础设定 =====")
        print(f"题目：{state['experiment_title']}")
        print("主要章节：")
        for char in state["main_chapters"]:
            print(f"- {char['章节名称']}：{char['章节描述']}")
        print(f"报告大致要点：{state['plot_content']}")
        
        re_confirm = input("是否确认修改后的设定？（y/n）：")
        if re_confirm.lower() == "y":
            state["is_setting_confirmed"] = True
            print("✅ 基础设定已确认！")
        else:
            print("❌ 未确认，将重新生成基础设定。")
    
    return state

# 4：生成报告的大纲内容（基于通过的目录、要点，相当于对于要点的一定扩写）
def generate_outline_chapter(state: ExperimentReportState) -> ExperimentReportState:
    "节点4：生成报告大纲与章节结构"
    if not state.get("is_setting_confirmed", False):
        raise ValueError("❌ 基础设定未确认，无法生成大纲！")
    
    print_process("大纲生成", "（开始生成大纲/章节结构）")
    
    prompt = PromptTemplate(
        template="""
        请根据已确认的实验报告基础设定，生成：
        1. 报告整体大纲：200-300字，清晰说明实验的内容、方法、结果和结论
        2. 章节结构：至少6章，格式为「章节X：章节情节概述（1-2句话）」，章节间逻辑连贯
        
        基础设定：
        题目：{experiment_title}
        主要章节：{main_chapters}
        报告大致要点：{plot_content}
        
        输出格式（严格遵循）：
        整体大纲：xxx
        章节结构：
        - 章节1：xxx
        - 章节2：xxx
        ...
        """,
        input_variables=["experiment_title", "main_chapters", "plot_content"]
    )
    
    # 格式化章节信息
    char_str = "\n".join([f"{c['章节名称']}：{c['章节描述']}" for c in state["main_chapters"]])
    
    response = llm.invoke(prompt.format(
        experiment_title=state["experiment_title"],
        main_chapters=char_str,
        plot_content=state["plot_content"]
    ))
    outline_content = response.content.strip()
    
    # 解析结果
    lines = outline_content.split("\n")
    state["chapter_structure"] = []
    for line in lines:
        if line.startswith("整体大纲："):
            state["experiment_outline"] = line.replace("整体大纲：", "").strip()
        elif line.startswith("章节结构："):
            continue
        elif line.startswith("- 章节"):
            chapter_name, chapter_desc = line.replace("- ", "").split("：", 1)
            state["chapter_structure"].append({"章节名": chapter_name, "情节概述": chapter_desc})
    
    # 展示大纲
    print("\n===== 生成的实验报告大纲与章节结构 =====")
    print(f"整体大纲：{state['experiment_outline']}")
    print("章节结构：")
    for chapter in state["chapter_structure"]:
        print(f"- {chapter['章节名']}：{chapter['情节概述']}")
    
    state["current_stage"] = "大纲生成"
    print_process("大纲生成", "（完成）✅")
    return state

# 5：确认报告的大纲设定
def confirm_outline_chapter(state: ExperimentReportState) -> ExperimentReportState:
    "节点5：人工审核确认大纲与章节结构（LangGraph 中断后执行）"
    print("\n===== ⚠️ 人工审核 - 大纲与章节结构确认环节 =====")
    confirm = input("是否确认以上大纲与章节结构？（确认请输入y，需修改请输入n并说明修改内容）：")
    
    if confirm.lower() == "y":
        state["is_outline_confirmed"] = True
        print("✅ 大纲与章节结构已确认，进入实验报告生成阶段！")
    else:
        # 接收修改需求并更新
        modify_content = input("请输入你的修改需求（如：调整章节顺序/修改某章情节/增减章节数）：")
        print("🔄 正在根据你的需求修改大纲与章节结构...")
        
        char_str = "\n".join([f"{c['章节名称']}：{c['章节描述']}" for c in state["main_chapters"]])
        prompt = PromptTemplate(
            template="""
            请根据已确认的基础设定和用户修改需求，更新实验报告大纲与章节结构：
            基础设定：
            题目：{experiment_title}
            主要章节：{main_chapters}
            报告大致要点：{plot_content}
            修改需求：{modify_content}
            
            输出格式（严格遵循）：
            整体大纲：xxx
            章节结构：
            - 章节1：xxx
            - 章节2：xxx
            ...
            """,
            input_variables=["experiment_title", "main_chapters", "plot_content", "modify_content"]
        )
        
        response = llm.invoke(prompt.format(
            experiment_title=state["experiment_title"],
            main_chapters=char_str,
            plot_content=state["plot_content"],
            modify_content=modify_content
        ))
        outline_content = response.content.strip()
        
        # 重新解析
        lines = outline_content.split("\n")
        state["experiment_outline"] = None
        state["chapter_structure"] = []
        for line in lines:
            if line.startswith("整体大纲："):
                state["experiment_outline"] = line.replace("整体大纲：", "").strip()
            elif line.startswith("章节结构："):
                continue
            elif line.startswith("- 章节"):
                chapter_name, chapter_desc = line.replace("- ", "").split("：", 1)
                state["chapter_structure"].append({"章节名": chapter_name, "情节概述": chapter_desc})
        
        # 再次展示并确认
        print("\n===== 修改后的大纲与章节结构 =====")
        print(f"整体大纲：{state['experiment_outline']}")
        print("章节结构：")
        for chapter in state["chapter_structure"]:
            print(f"- {chapter['章节名']}：{chapter['情节概述']}")
        
        re_confirm = input("是否确认修改后的大纲与章节结构？（y/n）：")
        if re_confirm.lower() == "y":
            state["is_outline_confirmed"] = True
            print("✅ 大纲与章节结构已确认！")
        else:
            print("❌ 未确认，将重新生成大纲。")
    
    return state

# 6：报告生成节点（基于大纲）
def generate_complete_experiment(state: ExperimentReportState) -> ExperimentReportState:
    "节点6：逐章生成实验报告正文（带章节进度）"
    if not state.get("is_outline_confirmed", False):
        raise ValueError("❌ 大纲与章节未确认，无法生成报告！")
    
    print_process("报告生成", "（开始逐章生成正文）")
    # 初始化进度
    state["experiment_generated_count"] = 0
    chapter_total = len(state["chapter_structure"])
    print_chapter_progress(0, chapter_total)
    
    # 格式化基础信息
    char_str = "\n".join([f"{c['章节名称']}：{c['章节描述']}" for c in state["main_chapters"]])
    experiment_basic_info = f"""
    报告题目：{state['experiment_title']}
    主要角色：{char_str}
    整体大纲：{state['experiment_outline']}
    """
    full_experiment_content = f"# {state['experiment_title']}\n\n## 报告核心设定\n{experiment_basic_info.replace('    ', '')}\n\n---\n"
    
    # 单章生成Prompt
    chapter_prompt = PromptTemplate(
        template="""
        请根据实验报告的核心设定、整体大纲，生成指定章节的正文内容，要求：
        1. 内容严格遵循该章节的情节概述，细节丰富，符合实验报告创作风格
        2. 报告描述与实验设定一致，贴合实验内容
        3. 章节开头标注章节名，结尾做轻微过渡，为下一章铺垫
        4. 单章字数控制在200-400字，语言流畅，情节连贯
        
        报告核心设定：{experiment_basic_info}
        当前生成章节：{chapter_name}
        本章节情节概述：{chapter_desc}
        已生成章节数：{generated_chapter_num}/{total_chapter}
        
        输出格式：直接输出生成的章节正文，无需额外说明
        """,
        input_variables=["experiment_basic_info", "chapter_name", "chapter_desc", "generated_chapter_num", "total_chapter"]
    )
    
    # 逐章生成
    for idx, chapter in enumerate(state["chapter_structure"], 1):
        chapter_name = chapter["章节名"]
        chapter_desc = chapter["情节概述"]
        print(f"\n🔨 【生成中】{chapter_name}...")
        
        # 调用LLM生成单章
        chapter_response = llm.invoke(chapter_prompt.format(
            experiment_basic_info=experiment_basic_info,
            chapter_name=chapter_name,
            chapter_desc=chapter_desc,
            generated_chapter_num=idx,
            total_chapter=chapter_total
        ))
        chapter_content = chapter_response.content.strip()
        
        # 拼接内容
        full_experiment_content += f"\n{chapter_content}\n\n---\n"      
        # 更新进度
        state["experiment_generated_count"] = idx
        print_chapter_progress(idx, chapter_total)
        print(f"✅ 【生成完成】{chapter_name}：\n{chapter_content}\n" + "-"*50)
    
    # 补充结尾
    full_experiment_content += f"\n### 结语（总章节数：{chapter_total} | 创作基于用户需求：{state['experiment_topic']}）"
    state["completed_report"] = full_experiment_content
    state["current_stage"] = "报告生成"
    
    # 最终进度展示
    print_process("报告生成", "（完成）✅")
    print(f"\n🎉 逐章生成完成！报告共{chapter_total}章，总字数≥2000字")
    return state

# 核心步骤3：构建langgraph图

def build_experiment_report_graph():
    "构建带中断的实验报告创作工作流"
    graph = StateGraph(ExperimentReportState)

    #添加节点
    graph.add_node("get_user_input", user_input_node)
    graph.add_node("generate_basic_setting", generate_basic_setting)
    graph.add_node("user_review", confirm_basic_setting)
    graph.add_node("generate_outline", generate_outline_chapter)
    graph.add_node("confirm_outline", confirm_outline_chapter)
    graph.add_node("generate_complete_experiment", generate_complete_experiment)
 
    #定义节点跳转逻辑
    graph.set_entry_point("get_user_input")
    graph.add_edge("get_user_input", "generate_basic_setting")
    graph.add_edge("generate_basic_setting", "user_review")

    #设定确认后跳转逻辑
    def setting_confirm_router(state: ExperimentReportState) -> str:
        return "generate_outline" if state.get("is_setting_confirmed", False) else "generate_basic_setting"
    graph.add_conditional_edges("user_review", setting_confirm_router)

    #大纲生成后跳转
    graph.add_edge("generate_outline", "confirm_outline")
    
    #确认大纲后跳转
    def outline_confirm_router(state: ExperimentReportState) -> str:
        return "generate_complete_experiment" if state.get("is_outline_confirmed", False) else "generate_outline"
    graph.add_conditional_edges("confirm_outline", outline_confirm_router)
    
    #报告生成后结束工作流
    graph.add_edge("generate_complete_experiment", END)

    # 1. 创建官方推荐的 MemorySaver 检查点
    checkpointer = MemorySaver()
    # 2. 编译工作流：完全匹配 v1.0.0+ 接口规范
    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["user_review", "confirm_outline"]  # 审核节点前中断
    )
    
    return compiled_graph


# ===================== 7. 运行实验报告创作流程 =====================
if __name__ == "__main__":
    # 1. 构建工作流实例
    experiment_graph = build_experiment_report_graph()
    
    # 2. 配置线程ID（用于区分不同的创作流程，每个流程独立存储状态）
    thread_id = "experiment_report_enterprise_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 3. 初始化工作流状态
    initial_state: ExperimentReportState = {
        "experiment_title": "",
        "current_stage": "初始",
        "chapter_generated_count": 0
    }

    print("🚀 实验报告创作助手启动")
    print("==============================================")

    # 核心逻辑：处理工作流中断与恢复
    # 第一次启动：执行从入口节点到第一个中断点的流程
    experiment_graph.invoke(initial_state, config=config)

    while True:
        # 获取当前线程的状态快照，判断流程是否中断
        state_snapshot = experiment_graph.get_state(config)
        
        # 如果没有下一个待执行节点，说明流程已完成，退出循环
        if not state_snapshot.next:
            print("\n🎉 所有流程已完成！")
            break
        
        # 流程中断在某个审核节点前，提示用户并恢复执行
        target_node = state_snapshot.next[0]
        print(f"\n--- ⏸️ 流程在节点 [{target_node}] 处等待人工干预 ---")
        
        # 恢复执行：传入None表示从上一个检查点继续，触发人工审核节点的输入交互
        experiment_graph.invoke(None, config=config)

    # 4. 获取最终生成结果并保存到文件
    final_state = experiment_graph.get_state(config).values
    if "completed_report" in final_state and final_state["completed_report"]:
        filename = "experiment_final_output.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_state["completed_report"])
        print(f"\n📁 完整报告已保存到: {filename}") 
    else:
        print("\n⚠️ 流程未能生成完整内容。")    