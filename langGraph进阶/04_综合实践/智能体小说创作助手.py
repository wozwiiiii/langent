import os
from typing import List,Dict,Optional,TypedDict
from langgraph.types import Checkpointer
from typing_extensions import NotRequired
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.memory import MemorySaver


#1.加载环境变量
load_dotenv()


#2.初始化LLM
llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0.2
)


#3.定义工作流状态结构
class NovelCreateState(TypedDict):
    #初始输入
    user_requirement: str
    #基础设定：生成小说的核心信息
    novel_title: NotRequired[Optional[str]] #小说标题
    main_characters: NotRequired[Optional[List[Dict[str, str]]]] #主要角色
    plot_overview: NotRequired[Optional[str]] #剧情概述
    
    #确认状态：标记人工审核结果
    is_setting_confirmed: NotRequired[Optional[bool]]  #基础设定是否确认
    is_outline_confirmed: NotRequired[Optional[bool]]  #大纲是否确认

    #大纲与章节：生成的结构信息
    novel_outline: NotRequired[Optional[str]] #小说大纲
    chapter_structure: NotRequired[Optional[List[Dict[str, str]]]] #章节结构

    #最终内容：生成的完整正文
    complete_novel: NotRequired[Optional[str]] 

    #进度追踪
    current_stage: NotRequired[str] #当前流程阶段（需求收集/设定生成/大纲生成/小说生成）
    chapter_generated_count: NotRequired[int] #已生成的章节数量


#4.工具函数-进度展示
def print_progress(current_stage: str,detail: str = ""):
    """
    打印整体流程进度，让用户直观了解当前执行阶段
    """
    stage_map = {
        "需求收集": "0.25",
        "设定生成": "0.5",
        "大纲生成": "0.75",
        "小说生成": "1.00"
    }
    progress = stage_map.get(current_stage,"未知阶段")
    print(f"\n当前整体进度：{progress} - {current_stage} {detail}")
    

def print_chapter_progress(generate: int, total: int):
    """
    打印章节生成进度（小数），监控小说生成进度
    """
    percentage = generate / total if total > 0 else 0.0
    print(f"\n当前章节生成进度：{generate}/{total} - {generate}/{total} 章 {percentage:.2f}%")



#5.定义各阶段节点函数
def get_user_input(state: NovelCreateState) -> NovelCreateState:
    """
    节点1：接受用户输入的创作需求（流程入口）
    """
    print_progress("需求收集","(开始)")

    #获取用户输入
    user_input = input("\n请输入您的小说创作需求（示例：科幻类型，主角是通信工程专业大学生，要有AI相关的反转情节，篇幅简短）：")
    
    #初始化核心状态字段
    state["user_requirement"] = user_input
    state["current_stage"] = "需求收集"
    state["is_setting_confirmed"] = False  #初始化为未确认
    state["is_outline_confirmed"] = False  #初始化为未确认
    print_progress("需求收集","(完成)")
    return state


def generate_novel_setting(state: NovelCreateState) -> NovelCreateState:
    """
    节点2：根据用户需求生成小说的基础设定（标题/角色/情节）
    """
    print_progress("设定生成","(开始生成标题/角色/情节)")

    #定义基础设定生成的提示词模板，约束输出格式和内容要求
    prompt = PromptTemplate(
        template="""
        请根据用户需求生成小说基础设定，要求：
        1. 小说题目：1-2个备选，简洁有吸引力
        2. 主要角色：至少3个，格式为「姓名：性格描述」
        3. 情节概述：100-200字，清晰说明故事整体走向
        
        用户需求：{user_requirement}
        
        输出格式（严格遵循）：
        题目：xxx
        主要角色：
        - 姓名1：性格描述1
        - 姓名2：性格描述2
        - 姓名3：性格描述3
        情节概述：xxx
        """,
        input_variables=["user_requirement"]
    )

    #调用LLM生成基础设定内容
    response = llm.invoke(prompt.format(user_requirement=state["user_requirement"]))
    setting_content = response.content.strip()

    #解析模型输出内容，提取标题、角色、情节概述
    lines = setting_content.split("\n")
    state["main_characters"] = []
    for line in lines:
        if line.startswith("题目："):
            state["novel_title"] = line.replace("题目：","").strip()
        elif line.startswith("主要角色："):
            continue
        elif line.startswith("- "):
            name,desc = line.replace("-","").split("：",1)
            state["main_characters"].append({"姓名":name,"性格描述":desc})
        elif line.startswith("情节概述："):
            state["plot_overview"] = line.replace("情节概述：","").strip()    

        #展示生成的基础设定，供用户审核
    print("\n===== 生成的小说基础设定 =====")
    print(f"题目：{state['novel_title']}")
    print("主要角色：")    
    for char in state["main_characters"]:
        print(f"- {char['姓名']}：{char['性格描述']}")
    print(f"情节概述：{state['plot_overview']}")
    
    state["current_stage"] = "设定生成"
    print_progress("设定生成","(完成)")

    return state


def confirm_novel_setting(state: NovelCreateState) -> NovelCreateState:
    """
    节点3：人工审核确认小说基础设定（标题/角色/情节，支持修改后重新生成）
    """
    print("\n===== 人工审核确认小说基础设定 =====")

    #获取用户确认
    confirm = input("是否确认以上基础设定？（确认请输入y，需修改请输入n并说明修改内容）：")
    if confirm.lower() == "y":
        state["is_setting_confirmed"] = True
        print_progress("基础设定确认，进入下一阶段")
    else:
        # 用户需要修改，接收修改需求并重新生成设定
        modify_content = input("请输入你的修改需求（如：修改角色名/调整情节/更换题目）：")
        print("正在根据你的需求修改基础设定...")

        #定义修改后的提示词模板，基于原始需求+需改需求重新生成
        prompt = PromptTemplate(
            template="""
            请根据用户的原始需求和修改需求，更新小说基础设定：
            原始需求：{user_requirement}
            修改需求：{modify_content}
            输出格式（严格遵循）：
            题目：xxx
            主要角色：
            - 姓名1：性格描述1
            - 姓名2：性格描述2
            - 姓名3：性格描述3
            情节概述：xxx
            """,
            input_variables=["user_requirement", "modify_content"]
        )

        #调用LLM生成修改后的基础设定内容
        response = llm.invoke(prompt.format(user_requirement=state["user_requirement"],modify_content=modify_content))
        setting_content = response.content.strip()


        #重新解析修改后的设定内容
        lines = setting_content.split("\n")
        state["main_characters"] = []
        for line in lines:
            if line.startswith("题目："):
                state["novel_title"] = line.replace("题目：", "").strip()
            elif line.startswith("主要角色："):
                continue
            elif line.startswith("- "):
                name, desc = line.replace("- ", "").split("：", 1)
                state["main_characters"].append({"姓名": name, "性格描述": desc})
            elif line.startswith("情节概述："):
                state["plot_overview"] = line.replace("情节概述：", "").strip()
        

        #展示修改后的基础设定，供用户审核
        print("\n===== 修改后的小说基础设定 =====")
        print(f"题目：{state['novel_title']}")
        print("主要角色：")    
        for char in state["main_characters"]:
            print(f"- {char['姓名']}：{char['性格描述']}")
        print(f"情节概述：{state['plot_overview']}")

        re_confirm = input("是否确认以上修改？（确认请输入y，需修改请输入n并说明修改内容）：")
        if re_confirm.lower() == "y":
            state["is_setting_confirmed"] = True
            print_progress("基础设定确认，进入下一阶段")
        else:
            # 用户需要修改，接收修改需求并重新生成设定
            print("未确认，将重新生成基础设定")

    return state


def generate_novel_content(state: NovelCreateState) -> NovelCreateState:
    """
    节点4：根据小说基础设定生成小说大纲与章节结构
    """

    #检验前置条件：基础设定未确认则无法生成大纲
    if not state.get("is_setting_confirmed",False):
        raise ValueError("基础设定未确认，无法生成大纲")

    print_progress("大纲生成","(开始生成大纲/章节结构)")
    
    #定义大纲生成提示词模板，约束大纲和章节的内容要求
    prompt = PromptTemplate(
        template="""
        请根据已确认的小说基础设定，生成：
        1. 小说整体大纲：200-300字，清晰说明故事的开端、发展、高潮、结局
        2. 章节结构：至少8章，格式为「章节X：章节情节概述（1-2句话）」，章节间逻辑连贯
        
        基础设定：
        题目：{novel_title}
        主要角色：{main_characters}
        情节概述：{plot_overview}
        
        输出格式（严格遵循）：
        整体大纲：xxx
        章节结构：
        - 章节1：xxx
        - 章节2：xxx
        ...
        """,
        input_variables=["novel_title", "main_characters", "plot_overview"]
    )

    #格式化角色信息，适配提示词输入格式
    char_str = "\n".join(f"{char['姓名']}：{char['性格描述']}" for char in state["main_characters"])

    #调用LLM生成大纲和章节结构
    response = llm.invoke(prompt.format(
        novel_title=state["novel_title"],
        main_characters=char_str,
        plot_overview=state["plot_overview"]
    ))
    outline_content = response.content.strip()

    #解析模型输出，提取大纲和章节结构
    lines = outline_content.split("\n")
    state["chapter_structure"] = []
    for line in lines[1:]:
        if line.startswith("整体大纲"):
            state["novel_outline"] = line.replace("整体大纲：", "").strip()
        elif line.startswith("章节结构："):
            continue
        elif line.startswith("- 章节"):
            chapter_name, chapter_desc = line.replace("- ", "").split("：", 1)
            state["chapter_structure"].append({"章节名": chapter_name, "情节概述": chapter_desc})

    
    #展示生成的大纲和章节结构
    print("\n===== 生成的大纲和章节结构 =====")
    print(f"整体大纲：{state['novel_outline']}")
    print("章节结构：")
    for chapter in state["chapter_structure"]:
        print(f"- {chapter['章节名']}：{chapter['情节概述']}")
    
    state["current_stage"] = "大纲生成" 
    print_progress("大纲生成","(大纲生成章节结构完成)")

    return state



def confirm_outline_chapter(state: NovelCreateState) -> NovelCreateState:
    """节点5：人工审核确认大纲与章节结构（支持修改后重新生成）"""
    print("\n===== ⚠️ 人工审核 - 大纲与章节结构确认环节 =====")
    confirm = input("是否确认以上大纲与章节结构？（确认请输入y，需修改请输入n并说明修改内容）：")
    
    if confirm.lower() == "y":
        # 用户确认大纲，标记状态为已确认
        state["is_outline_confirmed"] = True
        print("✅ 大纲与章节结构已确认，进入小说生成阶段！")
    else:
        # 用户需要修改，接收修改需求并重新生成大纲
        modify_content = input("请输入你的修改需求（如：调整章节顺序/修改某章情节/增减章节数）：")
        print("🔄 正在根据你的需求修改大纲与章节结构...")
        
        # 格式化角色信息
        char_str = "\n".join([f"{c['姓名']}：{c['性格描述']}" for c in state["main_characters"]])
        # 定义修改后的大纲生成提示词模板
        prompt = PromptTemplate(
            template="""
            请根据已确认的基础设定和用户修改需求，更新小说大纲与章节结构：
            基础设定：
            题目：{novel_title}
            主要角色：{main_characters}
            情节概述：{plot_overview}
            修改需求：{modify_content}
            
            输出格式（严格遵循）：
            整体大纲：xxx
            章节结构：
            - 章节1：xxx
            - 章节2：xxx
            ...
            """,
            input_variables=["novel_title", "main_characters", "plot_overview", "modify_content"]
        )
        
        # 调用模型重新生成修改后的大纲
        response = llm.invoke(prompt.format(
            novel_title=state["novel_title"],
            main_characters=char_str,
            plot_overview=state["plot_overview"],
            modify_content=modify_content
        ))
        outline_content = response.content.strip()
        
        # 重新解析修改后的大纲和章节结构
        lines = outline_content.split("\n")
        state["novel_outline"] = None
        state["chapter_structure"] = []
        for line in lines:
            if line.startswith("整体大纲："):
                state["novel_outline"] = line.replace("整体大纲：", "").strip()
            elif line.startswith("章节结构："):
                continue
            elif line.startswith("- 章节"):
                chapter_name, chapter_desc = line.replace("- ", "").split("：", 1)
                state["chapter_structure"].append({"章节名": chapter_name, "情节概述": chapter_desc})
        
        # 展示修改后的大纲，再次确认
        print("\n===== 修改后的大纲与章节结构 =====")
        print(f"整体大纲：{state['novel_outline']}")
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

def generate_complete_novel(state: NovelCreateState) -> NovelCreateState:
    """节点6：基于已确认的大纲逐章生成小说正文（带章节进度监控）"""
    # 校验前置条件：大纲未确认则无法生成小说正文
    if not state.get("is_outline_confirmed", False):
        raise ValueError("❌ 大纲与章节未确认，无法生成小说！")
    
    print_progress("小说生成", "（开始逐章生成正文）")
    # 初始化章节生成进度
    state["chapter_generated_count"] = 0
    chapter_total = len(state["chapter_structure"])
    print_chapter_progress(0, chapter_total)
    
    # 格式化小说基础信息，供单章生成时使用
    char_str = "\n".join([f"{c['姓名']}：{c['性格描述']}" for c in state["main_characters"]])
    novel_basic_info = f"""
    小说题目：{state['novel_title']}
    主要角色：{char_str}
    整体大纲：{state['novel_outline']}
    """
    # 初始化小说完整内容，包含标题和核心设定
    full_novel_content = f"# {state['novel_title']}\n\n## 小说核心设定\n{novel_basic_info.replace('    ', '')}\n\n---\n"
    
    # 定义单章正文生成的提示词模板，约束单章内容的格式和质量
    chapter_prompt = PromptTemplate(
        template="""
        请根据小说的核心设定、整体大纲，生成指定章节的正文内容，要求：
        1. 内容严格遵循该章节的情节概述，细节丰富，符合小说创作风格
        2. 角色性格与基础设定一致，对话自然，动作、心理描写贴合角色
        3. 章节开头标注章节名，结尾做轻微过渡，为下一章铺垫
        4. 单章字数控制在200-400字，语言流畅，情节连贯
        
        小说核心设定：{novel_basic_info}
        当前生成章节：{chapter_name}
        本章节情节概述：{chapter_desc}
        已生成章节数：{generated_chapter_num}/{total_chapter}
        
        输出格式：直接输出生成的章节正文，无需额外说明
        """,
        input_variables=["novel_basic_info", "chapter_name", "chapter_desc", "generated_chapter_num", "total_chapter"]
    )
    
    # 逐章生成小说正文
    for idx, chapter in enumerate(state["chapter_structure"], 1):
        chapter_name = chapter["章节名"]
        chapter_desc = chapter["情节概述"]
        print(f"\n🔨 【生成中】{chapter_name}...")
        
        # 调用模型生成单章正文
        chapter_response = llm.invoke(chapter_prompt.format(
            novel_basic_info=novel_basic_info,
            chapter_name=chapter_name,
            chapter_desc=chapter_desc,
            generated_chapter_num=idx,
            total_chapter=chapter_total
        ))
        chapter_content = chapter_response.content.strip()
        
        # 拼接单章内容到完整小说中
        full_novel_content += f"\n{chapter_content}\n\n---\n"
        # 更新章节生成进度
        state["chapter_generated_count"] = idx
        print_chapter_progress(idx, chapter_total)
        print(f"✅ 【生成完成】{chapter_name}：\n{chapter_content}\n" + "-"*50)
    
    # 补充小说完本信息，完成最终内容拼接
    full_novel_content += f"\n### 小说完本（总章节数：{chapter_total} | 创作基于用户需求：{state['user_requirement']}）"
    state["complete_novel"] = full_novel_content
    state["current_stage"] = "小说生成"
    
    # 展示最终进度
    print_progress("小说生成", "（完成）✅")
    print(f"\n🎉 逐章生成完成！小说共{chapter_total}章，总字数≥2000字")
    return state


#6.构建langGraph工作流
def build_novel_creation_graph() -> CompiledStateGraph:
    """构建小说创作工作流"""

    #1.初始化状态图，绑定自定义的状态数据结构
    graph = StateGraph(NovelCreateState)

    #2.添加阶段节点
    graph.add_node("get_user_input", get_user_input)
    graph.add_node("generate_basic_setting", generate_novel_setting)
    graph.add_node("confirm_basic_setting", confirm_novel_setting)
    graph.add_node("generate_outline_chapter", generate_novel_content)
    graph.add_node("confirm_outline_chapter", confirm_outline_chapter)
    graph.add_node("generate_complete_novel", generate_complete_novel)
    
    #3.定义节点执行顺序（核心工作逻辑）
    graph.set_entry_point("get_user_input")
    graph.add_edge("get_user_input","generate_basic_setting")
    graph.add_edge("generate_basic_setting","confirm_basic_setting")

    #4.定义设定确认后的分支逻辑：确认则生成大纲，为确认则重新生成设定
    def setting_confirm_router(state: NovelCreateState) -> str:
        return "generate_outline_chapter" if state.get("is_setting_confirmed", False) else "generate_basic_setting"
    graph.add_conditional_edges("confirm_basic_setting", setting_confirm_router)

    #5.大纲生成后跳转至大纲确认点
    graph.add_edge("generate_outline_chapter","confirm_outline_chapter")

    #6.定义大纲确认后的分支逻辑：确认则生成小说，为确认则重新生成大纲
    def outline_confirm_router(state: NovelCreateState) -> str:
        return "generate_complete_novel" if state.get("is_outline_confirmed", False) else "generate_outline_chapter"
    graph.add_conditional_edges("confirm_outline_chapter", outline_confirm_router)

    #7.小说生成完成后，跳转至结束点
    graph.add_edge("generate_complete_novel", END)

    #8.配置检查点存储：使用内存存储工作流状态，支持中断后恢复
    checkpointer = MemorySaver()

    #9.编译工作流：配置中断点（在人工确认节点前暂停，等待用户输入）
    compiled_graph = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["confirm_basic_setting", "confirm_outline_chapter"]
    )

    return compiled_graph



# ===================== 7. 运行小说创作流程 =====================
if __name__ == "__main__":
    # 1. 构建工作流实例
    novel_graph = build_novel_creation_graph()
    
    # 2. 配置线程ID（用于区分不同的创作流程，每个流程独立存储状态）
    thread_id = "novel_creation_enterprise_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 3. 初始化工作流状态
    initial_state: NovelCreateState = {
        "user_requirement": "",
        "current_stage": "初始",
        "chapter_generated_count": 0
    }

    print("🚀 小说创作助手启动")
    print("==============================================")

    # 核心逻辑：处理工作流中断与恢复
    # 第一次启动：执行从入口节点到第一个中断点的流程
    novel_graph.invoke(initial_state, config=config)

    while True:
        # 获取当前线程的状态快照，判断流程是否中断
        state_snapshot = novel_graph.get_state(config)
        
        # 如果没有下一个待执行节点，说明流程已完成，退出循环
        if not state_snapshot.next:
            print("\n🎉 所有流程已完成！")
            break
        
        # 流程中断在某个审核节点前，提示用户并恢复执行
        target_node = state_snapshot.next[0]
        print(f"\n--- ⏸️ 流程在节点 [{target_node}] 处等待人工干预 ---")
        
        # 恢复执行：传入None表示从上一个检查点继续，触发人工审核节点的输入交互
        novel_graph.invoke(None, config=config)

    # 4. 获取最终生成结果并保存到文件
    final_state = novel_graph.get_state(config).values
    if "complete_novel" in final_state and final_state["complete_novel"]:
        filename = "novel_final_output.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_state["complete_novel"])
        print(f"\n📁 完整小说已保存到: {filename}")
    else:
        print("\n⚠️ 流程未能生成完整内容。")