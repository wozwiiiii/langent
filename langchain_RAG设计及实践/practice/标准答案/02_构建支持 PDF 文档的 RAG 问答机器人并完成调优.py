"""
练习任务
文档加载：加载1-2份PDF文档（如企业产品手册、行业报告），转换为Document对象；
文本分割：使用RecursiveCharacterTextSplitter对文档进行分割，调试chunk_size和chunk_overlap参数；
向量存储：选择合适的嵌入模型（如通义千问text-embedding-v2），将分割后的片段存入Chroma向量数据库；
检索-生成整合：构建RetrievalQA链，自定义提示词（要求答案基于检索片段，分点清晰）；
评估与调优： - 构建10个测试问题（覆盖PDF文档的核心知识点）； - 用RAGAS工具评估检索精确率、事实一致性等指标； - 根据评估结果调优（如调整分割参数、检索k值、嵌入模型），使核心指标达标（F1≥0.8，事实一致性≥0.9）。
"""

# ===== 1. 环境 & 模型（与项目其他文件保持一致：DeepSeek + temperature=0.3） =====
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

load_dotenv()
llm = ChatOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.deepseek.com",
    model="deepseek-chat",
    temperature=0.3, timeout=30, max_retries=2
)

# ===== 2. PDF 文档加载（PyPDFLoader，按页生成 Document） =====
KNOWLEDGE_DIR = Path(r"d:\AI_Program\langent\langchain_RAG设计及实践\knowledge_docs")
PDF_FILES = [KNOWLEDGE_DIR / "test.pdf"]  # 可追加多个 PDF

def load_pdfs(paths: list[Path]) -> list[Document]:
    """按页加载多份 PDF，每页一个 Document"""
    all_docs: list[Document] = []
    for p in paths:
        if not p.exists():
            print(f"⚠️ 跳过：{p}"); continue
        docs = PyPDFLoader(str(p)).load()
        all_docs.extend(docs)
        print(f"✅ {p.name}：{len(docs)} 页")
    return all_docs

raw_docs = load_pdfs(PDF_FILES)
assert raw_docs, "未找到 PDF，请放入 knowledge_docs 后重试"

# ===== 3. 文本分割（chunk_size / chunk_overlap 可调，参与后续调优） =====
def split_docs(docs, chunk_size: int = 500, chunk_overlap: int = 80) -> list[Document]:
    """递归字符分割：中文 chunk_size 推荐 300-800，overlap 10%-20%"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", "、", " ", ""]
    ).split_documents(docs)

# ===== 4. 嵌入模型（沿用项目内本地 Qwen3-Embedding，与 RAG全流程.py 一致） =====
EMBEDDING_PATH = r"D:\AI_Program\langent\models\Qwen\Qwen3-Embedding-0___6B"
assert Path(EMBEDDING_PATH).exists(), f"嵌入模型不存在：{EMBEDDING_PATH}"

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_PATH,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# ===== 5. Chroma 向量库（持久化到本地） =====
CHROMA_DIR, COLLECTION = "./chroma_db", "pdf_rag"

def build_chroma(docs: list[Document]) -> Chroma:
    return Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION
    )

# ===== 6. 检索器（MMR 兼顾相关性与多样性） =====
def build_retriever(vdb: Chroma, k: int = 4):
    return vdb.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": 12, "lambda_mult": 0.7}
    )

# ===== 7. 自定义提示词（基于资料 + 分点 + 引用） =====
SYSTEM = """你是 PDF 文档问答助手，必须严格遵守：
1. 答案只能基于下方参考资料，不得编造、不得引入外部知识；
2. 用分点形式（1. 2. 3. ...）回答，逻辑清晰；
3. 关键结论用引号引用原文片段，便于溯源；
4. 资料不足时直接回复「根据现有资料无法回答」。

参考资料：
{context}"""
rag_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM), ("human", "{question}")])

# ===== 8. LCEL 风格 RAG 链（等价于 legacy RetrievalQA） =====
def format_docs(docs):
    return "\n\n".join(f"[片段{i+1}] {d.page_content}" for i, d in enumerate(docs))

def build_rag_chain(retriever):
    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt | llm | StrOutputParser()
    )

# ===== 9. 10 个测试问题（含 ground_truth，供 RAGAS 评估） =====
TEST_QA = [
    {"question": "LangChain 的核心定位是什么？", "ground_truth": "LangChain 是一个用于构建大模型应用的开发框架。"},
    {"question": "RAG 系统的核心流程包含哪几步？", "ground_truth": "文档加载、文本分割、向量化、检索、增强生成。"},
    {"question": "RecursiveCharacterTextSplitter 的优势？", "ground_truth": "按分隔符优先级递归切分，保留语义结构。"},
    {"question": "向量数据库在 RAG 中的作用？", "ground_truth": "存储文本向量表示并支持高效相似性检索。"},
    {"question": "MMR 检索相比相似性检索的优势？", "ground_truth": "在相关性与多样性之间取得平衡，避免结果冗余。"},
    {"question": "为什么需要做文本分割？", "ground_truth": "超出模型上下文窗口，检索粒度过粗影响精度。"},
    {"question": "chunk_size 过大会带来什么问题？", "ground_truth": "单片段信息密度低、引入噪声，检索精度下降。"},
    {"question": "chunk_overlap 过小会导致什么？", "ground_truth": "跨片段语义断裂，关键句被切断丢失。"},
    {"question": "RAGAS faithfulness 指标衡量什么？", "ground_truth": "生成答案与检索片段的事实吻合程度。"},
    {"question": "如何提升 RAG 答案的事实一致性？", "ground_truth": "严格约束 prompt 基于资料、降低温度、检索高质量片段。"},
]

# ===== 10. RAGAS 评估（context_precision + faithfulness） =====
try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import context_precision, faithfulness
    RAGAS_OK = True
except ImportError:
    RAGAS_OK = False
    print("⚠️ 未安装 ragas，请先执行：pip install ragas datasets")

def run_ragas(rag_chain, testset, retriever) -> dict:
    """对当前 (split, k) 组合跑 RAGAS，返回核心指标 dict"""
    if not RAGAS_OK: return {}
    rows = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    for item in testset:
        q = item["question"]
        ctxs = [d.page_content for d in retriever.invoke(q)]
        ans = rag_chain.invoke(q)
        rows["question"].append(q); rows["answer"].append(ans)
        rows["contexts"].append(ctxs); rows["ground_truth"].append(item["ground_truth"])
    return evaluate(Dataset.from_dict(rows), metrics=[context_precision, faithfulness])

# ===== 11. 调优主循环（网格搜索 + 评估） =====
SPLIT_CONFIGS = [
    {"chunk_size": 300, "chunk_overlap": 50},
    {"chunk_size": 500, "chunk_overlap": 80},
    {"chunk_size": 800, "chunk_overlap": 120},
]
K_VALUES = [3, 4, 5]

def tune():
    """遍历 (chunk_size, overlap, k) 组合，挑综合得分最高的"""
    best_score, best_cfg, best_res = -1.0, None, None
    for cfg in SPLIT_CONFIGS:
        sd = split_docs(raw_docs, **cfg)
        vdb = build_chroma(sd)
        for k in K_VALUES:
            r = build_retriever(vdb, k=k)
            chain = build_rag_chain(r)
            res = run_ragas(chain, TEST_QA, r)
            cp = float(res.get("context_precision", 0))
            fa = float(res.get("faithfulness", 0))
            print(f"{cfg} k={k} | precision={cp:.3f} faithfulness={fa:.3f}")
            score = 0.5 * cp + 0.5 * fa
            if score > best_score:
                best_score, best_cfg, best_res = score, {**cfg, "k": k}, res
    return best_cfg, best_res

# ===== 12. 执行入口 =====
if __name__ == "__main__":
    split = split_docs(raw_docs, 500, 80)
    print(f"📊 片段数：{len(split)}")
    vdb = build_chroma(split)
    r = build_retriever(vdb, 4)
    chain = build_rag_chain(r)
    sample = TEST_QA[0]
    print(f"\n❓ {sample['question']}\n💡 {chain.invoke(sample['question'])}")
    # 完整调优（耗时较长，可按需启用）
    # best_cfg, best_res = tune()
    # print(f"\n🏆 最优：{best_cfg}  指标：{best_res}")