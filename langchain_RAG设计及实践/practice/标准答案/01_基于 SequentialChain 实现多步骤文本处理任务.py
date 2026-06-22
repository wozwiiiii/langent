"""
练习任务
实现“新闻文本分类→提取核心事件→生成摘要”的多步骤任务
输入：新闻文本（news_text）、分类标签列表（category_list，如[“科技”, “财经”, “娱乐”, “体育”]）；
步骤1（链1）：根据分类标签列表，对新闻文本进行分类，输出分类结果（category）；
步骤2（链2）：根据分类结果和新闻文本，提取该类新闻的核心事件（如科技新闻提取“技术突破、产品发布”等，财经新闻提取“政策变化、企业动态”等），输出核心事件（core_event）；
步骤3（链3）：结合分类结果和核心事件，生成100字以内的新闻摘要（summary）；
输出：分类结果、核心事件、新闻摘要。
"""


from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import os

# 1. 环境变量 & 模型（与项目内其他文件保持一致：DeepSeek + temperature=0.3）
load_dotenv()
llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0.3
)

# 2. 链1：新闻分类（输入 news_text + category_list，输出 category）
classify_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是新闻分类助手，根据给定的分类标签列表，对新闻文本进行分类。\n要求：仅输出一个最匹配的分类标签，不要包含其他内容。"),
    ("human", "分类标签列表：{category_list}\n\n新闻文本：{news_text}\n\n请输出分类结果：")
])
classify_chain = classify_prompt | llm | StrOutputParser()

# 3. 链2：核心事件提取（输入 category + news_text，输出 core_event）
event_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是新闻核心事件提取助手，根据新闻所属分类，从新闻文本中提取核心事件。\n要求：用简洁、精准的语言概括。"),
    ("human", "新闻分类：{category}\n\n新闻文本：{news_text}\n\n请提取该新闻的核心事件：")
])
event_chain = event_prompt | llm | StrOutputParser()

# 4. 链3：摘要生成（输入 category + core_event，输出 summary）
summary_prompt = ChatPromptTemplate.from_messages([
    ("system", "你是新闻摘要生成助手，结合新闻分类与核心事件，生成一段 100 字以内的新闻摘要。\n要求：语言精炼、突出重点、不超过 100 字。"),
    ("human", "新闻分类：{category}\n\n核心事件：{core_event}\n\n请生成 100 字以内的摘要：")
])
summary_chain = summary_prompt | llm | StrOutputParser()

# 5. 多步骤顺序链接（LCEL 风格，等价于 legacy SequentialChain）
# 核心思路：用 RunnablePassthrough.assign() 把每条链的输出累积到同一个 dict 中
#   第 1 步：在 dict 中新增 category
#   第 2 步：在 dict 中新增 core_event（能直接拿到上一步的 category 与原 news_text）
#   第 3 步：在 dict 中新增 summary（能直接拿到上一步的 category 与 core_event）
overall_chain = (
    RunnablePassthrough.assign(category=classify_chain)
    | RunnablePassthrough.assign(core_event=event_chain)
    | RunnablePassthrough.assign(summary=summary_chain)
)

# 6. 测试样例
news_text = """近日，某科技公司正式发布全新一代人工智能芯片，采用 5nm 工艺制程，运算能力较上一代提升 3 倍，能效比提升 50%。
该公司 CEO 在发布会上表示，这款芯片将广泛应用于数据中心、智能驾驶、消费电子等多个领域，
预计将为公司带来数百亿元的新增收入。业内人士分析认为，这一突破将进一步巩固该公司在 AI 芯片领域的全球领先地位。"""

category_list = ["科技", "财经", "娱乐", "体育"]

result = overall_chain.invoke({
    "news_text": news_text,
    "category_list": category_list
})

# 7. 输出最终结果
print("=" * 60)
print(f"📰 分类结果: {result['category']}")
print("=" * 60)
print(f"🔍 核心事件: {result['core_event']}")
print("=" * 60)
print(f"📝 新闻摘要: {result['summary']}")
print("=" * 60)