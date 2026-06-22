from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithFallbacks 
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException
import os
from dotenv import load_dotenv

load_dotenv()

# 🔑 使用 OpenAI 的 API 密钥（从环境变量读取）
api_key = os.getenv("OPENAI_API_KEY")   # 在 .env 中设置 OPENAI_API_KEY=sk-xxxxx
# 注意：不需要指定 base_url，默认就是 https://api.openai.com

# 1️⃣ 核心链（性能高但可能不稳定）
core_llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4",              
    temperature=0.7
)
core_prompt = ChatPromptTemplate.from_messages([
    ("system", "用专业语言详细解答用户问题。"),
    ("human", "{query}")
])
core_chain = core_prompt | core_llm | StrOutputParser()

# 2️⃣ 降级链（稳定但精度略低）
fallback_llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-3.5-turbo",
    temperature=0.5
)
fallback_prompt = ChatPromptTemplate.from_messages([
    ("system", "用简洁语言解答用户问题，保证信息准确。"),
    ("human", "{query}")
])
fallback_chain = fallback_prompt | fallback_llm | StrOutputParser()

# 3️⃣ 构建带降级的链
chain_with_fallback: RunnableWithFallbacks = core_chain.with_fallbacks(
    fallbacks=[fallback_chain],
    exceptions_to_handle=(ConnectionError, TimeoutError),# ✅ 官方推荐：只捕获临时错误或网络错误
)

# 4️⃣ 调用链并捕获异常
try:
    result = chain_with_fallback.invoke({"query": "什么是RAG技术？"})
    print("解答：", result)
except OutputParserException as e:
    print(f"解析失败：{e}")
except Exception as e:
    print(f"最终失败：{e}")