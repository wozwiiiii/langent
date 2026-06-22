# 安装依赖：pip install ragas datasets faiss-cpu  # 补充：安装FAISS依赖
from ragas import evaluate
from ragas.metrics.collections import (
    ContextPrecision,     # 检索精确率
    ContextRecall,        # 检索召回率
    Faithfulness,         # 事实一致性
    AnswerRelevancy       # 答案相关性
)
from datasets import Dataset
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("未找到OPENAI_API_KEY环境变量")

# 1. 初始化RAG系统组件
embedding_model_path = "./models/Qwen/Qwen3-Embedding-0___6B"
if not os.path.exists(embedding_model_path):
    raise FileNotFoundError(f"Qwen3嵌入模型路径不存在：{embedding_model_path}")

embeddings = HuggingFaceEmbeddings(
    model_name=embedding_model_path,
    model_kwargs={
        "device": "cpu",
        "trust_remote_code": True,
    },
    encode_kwargs={
        "normalize_embeddings": True
    }
)

# 加载FAISS向量库
faiss_db_path = "./faiss_db"
if not os.path.exists(faiss_db_path):
    raise FileNotFoundError(f"FAISS向量数据库路径不存在：{faiss_db_path}")

vector_db = FAISS.load_local(
    folder_path=faiss_db_path,
    embeddings=embeddings,
    allow_dangerous_deserialization=True
)
retriever = vector_db.as_retriever(search_kwargs={"k": 3})

# 定义提示词
system_prompt = "基于以下上下文回答问题：{context}"
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{question}")
])

# 文档格式化函数
def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# 修复LCEL链语法（管道符连接）
rag_qa_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(api_key=api_key, temperature=0.3)
    | StrOutputParser()
)

# 2. 构建测试数据集
test_questions = [
    "RAG系统的核心价值是什么？",
    "SequentialChain的作用是什么？",
    "RAG系统的构建流程有哪些步骤？"
]

# 3. 采集RAG输出结果
test_data = []
for question in test_questions:
    answer = rag_qa_chain.invoke(question)
    retrieved_docs = retriever.invoke(question)
    contexts = [doc.page_content for doc in retrieved_docs]
    
    test_data.append({
        "question": question,
        "answer": answer,
        "contexts": contexts
    })

# 4. 转换为RAGAS标准格式
dataset = Dataset.from_list(test_data)

# 5. 评估指标
metrics = [ContextPrecision(), ContextRecall(), Faithfulness(), AnswerRelevancy()]

# 6. 执行评估
results = evaluate(
    dataset=dataset,
    metrics=metrics,
    llm=ChatOpenAI(api_key=api_key, temperature=0)
)

# 7. 输出结果
print("RAG系统自动化评估结果：")
print(results)