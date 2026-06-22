#第一部分：环境准备及组件初始化
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os


#加载并验证环境变量
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")


#1.初始化本地CPU运行的Qwen3-Embedding-0___6B模型
embedding_model_name = r"D:\AI_Program\langent\models\Qwen\Qwen3-Embedding-0___6B"
if not os.path.exists(embedding_model_name):
    raise ValueError(f"Embedding model not found at {embedding_model_name}")


embeddings = HuggingFaceEmbeddings(
    model_name=embedding_model_name,
    model_kwargs={
        "device": "cpu",  # 强制CPU运行，无需GPU
        # 如需加载量化模型，可添加以下配置（按需）
        "trust_remote_code": True,
        # "load_in_8bit": False
    },
    encode_kwargs={
        "normalize_embeddings": True  # 归一化向量，提升检索效果
    }
)


#2.加载已有的FAISS向量数据库
#注意：首次构建是需用FAISS.from_documents(docs,embeddings)方法，创建并save_local()方法保存到指定路径。
#后续加载则用FAISS.load_local()方法。
vector_db = FAISS.load_local(
    folder_path=r"D:\AI_Program\langent\faiss_db",  # 之前存储向量的路径
    embeddings=embeddings,
    index_name="local_cpu_faiss_index",  # 需和保存时的索引名一致
    allow_dangerous_deserialization=True
)

#3.初始化检索其（MMR策略，平衡相关性和多样性，参数无变化）
retriever = vector_db.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.7}
)

#4.初始化大模型
llm = ChatOpenAI(
    api_key=api_key,
    model_name="deepseek-v4-flash",
    base_url="https://api.deepseek.com",
    temperature=0.3, #低温保证答案精准，减少幻觉
    timeout=30, #新增超时时间，避免请求挂起
    max_retries=2 #网络破洞是自动重试，提升稳定性
)



#第二部分：用LCEL构建检索-生成链
#1.自定义文档格式化函数（将检索到的多个文本冰洁为统一文本，供提示词使用）
def format_doc(docs):
    """格式化检索到的文档片段，用空行分割"""
    return "\n\n".join([doc.page_content for doc in docs])

#2.自定义提示词模板
#保持原业务规则：基于参考资料、分点说明、带案例
system_prompt = """
你是一个专业的RAG系统问答助手，必须基于以下提供的参考资料（context）回答用户问题。
规则:
1.答案必须严格基于参考资料,不能编造未提及的信息；
2.语言简洁明了，分点说明（如果有多个要点）；
3.每个要点搭配1个简单案例，帮助理解。

参考资料：{context}
"""

custom_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt), #系统指令
    ("human", "{question}") #用户问题输入
])


#3.用LCEL构建完整检索——生成链（管道串联组件，数据流式传递）
rag_qa_chain = (
    #第一步：并行处理输入（传递用户问题+检索文档）
    {"context": retriever | format_doc, "question": RunnablePassthrough()}
    #第二步：将格式化数据传入提示词模板
    | custom_prompt
    #第三步：将提示词传入大模型
    | llm
    #第四步：将大模型输出解析为字符串
    | StrOutputParser()
)


#如需返回检索原文档，可调整链结构
rag_qa_chain_with_source = (
    {
        "context": retriever | format_doc,
        "question": RunnablePassthrough(),
        "source_doc": retriever #保留原始检索文档
    }
    | custom_prompt
    | llm
    | StrOutputParser()
)


#第三步：测试并验证结果
# 测试问题列表（覆盖不同类型的查询）
test_questions = [
    "LangChain是什么？",
    "LangChain支持哪些语言？",
    "LangChain的核心功能有哪些？"
]

# 执行测试并打印结果
for i, question in enumerate(test_questions):
    print(f"\n===== 测试问题{i+1}：{question} =====")
    # 执行RAG链（1.x统一用invoke方法）
    result = rag_qa_chain_with_source.invoke(question)  # 带源文档的链
    
    # 打印生成的答案
    print("\n生成答案：")
    print(result)
    
    # 打印参考资料（验证答案来源）
    print("\n参考资料：")
    # 注意：源文档从链的输入参数中获取（因链结构中保留了source_documents）
    sources = retriever.invoke(question)  # 重新调用检索器获取源文档（或在链中传递）
    for j, doc in enumerate(sources):
        print(f"\n参考片段{j+1}：")
        print(doc.page_content)
        if doc.metadata:  # 打印文档元数据（如文件名、页码等）
            print(f"元数据：{doc.metadata}")