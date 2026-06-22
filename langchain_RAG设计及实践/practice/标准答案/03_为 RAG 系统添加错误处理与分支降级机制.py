"""
练习任务
提升RAG系统的工程化能力，通过错误处理和分支降级机制，确保系统在异常情况下仍能正常响应。

添加重试机制：为RAG系统的检索环节和生成环节添加重试逻辑，当API调用超时或临时失败时，自动重试2-3次；
添加异常捕获：捕获API密钥错误、输入格式错误、检索无结果等常见异常，返回友好的错误提示；
添加分支降级：-核心链：使用GPT-4作为大模型，通义千问text-embedding-v2作为嵌入模型； -降级链：当核心链失败（如API调用失败、指标不达标）时，自动切换为GPT-3.5-turbo-instruct（大模型）和m3e-base（开源嵌入模型）；
测试验证：模拟多种异常场景（如错误API密钥、网络中断、检索无结果），验证系统是否能正常降级并返回有效响应。
"""

# ===== 1. 基础依赖（与项目其他文件保持一致） =====
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ===== 2. 自定义异常（精准分类，对应 lang_chain/05.py 风格） =====
class RAGInputError(ValueError):       """输入校验失败（空问题、类型错误）"""
class RAGNoResultError(RuntimeError):  """检索无结果（兜底友好提示）"""
class RAGAuthError(RuntimeError):      """API Key 鉴权失败"""

# ===== 3. 模型工厂（默认 DeepSeek；可切到任务要求的 GPT-4 / GPT-3.5） =====
def build_core_llm():
    """核心链：高精度（任务要求 GPT-4，默认用项目内 DeepSeek）"""
    return ChatOpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY"),
        model=os.getenv("CORE_LLM_MODEL", "deepseek-chat"),
        base_url=os.getenv("CORE_LLM_BASE_URL", "https://api.deepseek.com"),
        temperature=0.3, timeout=10, max_retries=1
    )

def build_fallback_llm():
    """降级链：更稳更快（任务要求 GPT-3.5-turbo-instruct）"""
    return ChatOpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY"),
        model=os.getenv("FALLBACK_LLM_MODEL", "deepseek-chat"),
        base_url=os.getenv("FALLBACK_LLM_BASE_URL", "https://api.deepseek.com"),
        temperature=0.5, timeout=15, max_retries=1
    )

EMBEDDING_PATH = r"D:\AI_Program\langent\models\Qwen\Qwen3-Embedding-0___6B"
def build_embedding():
    """嵌入模型（任务要求 text-embedding-v2 / m3e-base；本项目用本地 Qwen3）"""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_PATH,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

# ===== 4. 双套向量库（核心 + 降级） =====
def build_vector_stores(docs):
    """返回 (核心vdb, 降级vdb)；本示例共享嵌入以保证可运行，生产环境建议分开"""
    emb = build_embedding()
    core = Chroma.from_documents(docs, emb, persist_directory="./chroma_core", collection_name="core")
    fb = Chroma.from_documents(docs, emb, persist_directory="./chroma_fb", collection_name="fallback")
    return core, fb

# ===== 5. 自定义提示词（参考 RAG全流程.py） =====
SYSTEM = """你是 PDF 文档问答助手。规则：
1. 严格基于参考资料，不得编造、不得引入外部知识；
2. 用分点形式回答，逻辑清晰；
3. 资料不足回复「无法回答」。"""
rag_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "参考资料：\n{context}\n\n问题：{question}")
])

# ===== 6. RAG 子链：单链内置 with_retry（参考 lang_chain/04.py） =====
def format_docs(docs):
    return "\n\n".join(f"[片段{i+1}] {d.page_content}" for i, d in enumerate(docs))

def build_rag_subchain(llm, retriever):
    """检索 → 提示 → LLM → 解析；外层裹 with_retry（仅对网络/超时重试）"""
    def rag_logic(question: str) -> str:
        docs = retriever.invoke(question)
        if not docs:
            raise RAGNoResultError(f"未检索到相关内容：{question}")
        return (rag_prompt | llm | StrOutputParser()).invoke({
            "context": format_docs(docs), "question": question
        })
    return RunnableLambda(rag_logic).with_retry(
        stop_after_attempt=3, wait_exponential_jitter=True,
        retry_if_exception_type=(ConnectionError, TimeoutError, OSError),
    )

# ===== 7. 主链：核心 + 降级（参考 lang_chain/06.py with_fallbacks） =====
def build_rag_with_fallback(core_llm, fb_llm, core_r, fb_r):
    """官方推荐：只兑底临时错误，不兑底鉴权/输入错误（避免隐藏严重问题）"""
    core = build_rag_subchain(core_llm, core_r)
    fb = build_rag_subchain(fb_llm, fb_r)
    return core.with_fallbacks(
        fallbacks=[fb],
        exceptions_to_handle=(ConnectionError, TimeoutError, OSError, RAGNoResultError),
    )

# ===== 8. 输入校验（参考 lang_chain/05.py） =====
def validate_input(q: str) -> str:
    if not q or not isinstance(q, str):
        raise RAGInputError("问题必须为非空字符串")
    q = q.strip()
    if not q:
        raise RAGInputError("问题不能全是空白字符")
    return q

# ===== 9. 统一入口：异常分类兑底（参考 lang_chain/05.py 风格） =====
def ask(rag_chain, question: str) -> str:
    try:
        return rag_chain.invoke(validate_input(question))
    except RAGInputError as e:    return f"❌ 输入错误：{e}"
    except RAGAuthError as e:     return f"🔐 鉴权失败：{e}，请检查 API Key"
    except RAGNoResultError:      return "📭 未找到答案：知识库中暂无相关内容"
    except (ConnectionError, TimeoutError, OSError) as e:
        return f"🌐 网络异常：{e}，请稍后重试"
    except Exception as e:
        return f"⚠️ 系统异常：{type(e).__name__}，请联系管理员"

# ===== 10. 测试场景：使用 Mock 类模拟 3 类异常（不需真实失败环境） =====
class _AuthFailingLLM:
    """场景 1 Mock：模拟鉴权失败"""
    def invoke(self, *a, **kw): raise RAGAuthError("Invalid API Key")
class _NetFailingLLM:
    """场景 2 Mock：模拟网络中断"""
    def invoke(self, *a, **kw): raise ConnectionError("模拟网络中断")
class _EmptyRetriever:
    """场景 3 Mock：返回空结果"""
    def invoke(self, *a, **kw): return []

def test_scenarios(cr, fr):
    print("\n[场景 1] 核心 LLM 鉴权失败 → 期望触发降级")
    bad = build_rag_with_fallback(_AuthFailingLLM(), build_fallback_llm(), cr, fr)
    print(" →", ask(bad, "什么是RAG？"))
    print("\n[场景 2] 核心 LLM 网络中断 → 期望触发降级")
    bad = build_rag_with_fallback(_NetFailingLLM(), build_fallback_llm(), cr, fr)
    print(" →", ask(bad, "什么是RAG？"))
    print("\n[场景 3] 检索无结果 → 期望返回友好提示")
    chain = build_rag_with_fallback(build_core_llm(), build_fallback_llm(), _EmptyRetriever(), fr)
    print(" →", ask(chain, "量子诗歌与天体物理的哲学关系？"))

# ===== 11. 主入口 =====
if __name__ == "__main__":
    pdf = Path(r"d:\AI_Program\langent\langchain_RAG设计及实践\knowledge_docs\test.pdf")
    docs = PyPDFLoader(str(pdf)).load() if pdf.exists() else []
    split = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80).split_documents(docs) if docs else []
    if split:
        core_vdb, fb_vdb = build_vector_stores(split)
        cr = core_vdb.as_retriever(search_type="mmr", search_kwargs={"k": 4, "fetch_k": 12, "lambda_mult": 0.7})
        fr = fb_vdb.as_retriever(search_type="mmr", search_kwargs={"k": 4, "fetch_k": 12, "lambda_mult": 0.7})
        main = build_rag_with_fallback(build_core_llm(), build_fallback_llm(), cr, fr)
        print("正常调用：", ask(main, "什么是RAG？")[:120])
        test_scenarios(cr, fr)
    else:
        print("未找到 PDF 文档，请放入 knowledge_docs")