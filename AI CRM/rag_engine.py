import os
import logging
import warnings
import sys
import numpy as np

# 设置 Hugging Face 镜像 - 使用 ModelScope 加速下载
os.environ['HF_ENDPOINT'] = 'https://modelscope.cn'
os.environ['HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

warnings.filterwarnings("ignore")

class HiddenStderr:
    def write(self, text):
        pass
    def flush(self):
        pass

original_stderr = sys.stderr

from config import Config

logger = logging.getLogger(__name__)

# 检查 RAG 依赖是否可用
def check_rag_dependencies():
    """检查 RAG 所需的依赖是否可用"""
    try:
        import torch
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        return True
    except Exception as e:
        logger.warning(f"RAG 依赖不可用: {e}")
        return False

RAG_AVAILABLE = check_rag_dependencies()


class RAGEngine:
    def __init__(self, enable_rag=True):
        self.persist_dir = Config.VECTOR_DB_PATH
        self.upload_dir = Config.UPLOAD_FOLDER
        self.enable_rag = enable_rag and RAG_AVAILABLE
        self.vector_store = None
        self.embeddings = None
        
        if not RAG_AVAILABLE:
            logger.info("RAG功能已禁用（依赖不可用）")
            return
            
        if not self.enable_rag:
            logger.info("RAG功能已禁用")
            return
            
        os.makedirs(self.persist_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # 检查并加载现有的向量数据库
        index_path = os.path.join(self.persist_dir, "index.faiss")
        if os.path.exists(index_path):
            logger.info("检测到现有向量数据库，正在加载...")
            self._load_existing_vector_store(index_path)

    def check_existing_vector_db(self):
        """检查是否存在现有的向量数据库"""
        if not RAG_AVAILABLE:
            return False, 0
        
        index_path = os.path.join(self.persist_dir, "index.faiss")
        index2_path = os.path.join(self.persist_dir, "index.faiss.index")
        pkl_path = os.path.join(self.persist_dir, "index.pkl")
        
        if os.path.exists(index_path) and (os.path.exists(index2_path) or os.path.exists(pkl_path)):
            # 尝试加载并获取向量数量
            try:
                sys.stderr = HiddenStderr()
                from langchain_community.vectorstores import FAISS
                from langchain_community.embeddings import HuggingFaceEmbeddings
                
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="shibing624/text2vec-base-chinese",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
                
                self.vector_store = FAISS.load_local(
                    self.persist_dir, 
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                
                sys.stderr = original_stderr
                vector_count = len(self.vector_store.index_to_docstore_id)
                return True, vector_count
            except Exception as e:
                sys.stderr = original_stderr
                logger.warning(f"检测现有向量数据库时出错: {e}")
                return True, -1
        return False, 0

    def clear_vector_db(self):
        """清除现有的向量数据库"""
        try:
            files_to_delete = [
                os.path.join(self.persist_dir, "index.faiss"),
                os.path.join(self.persist_dir, "index.faiss.index"),
                os.path.join(self.persist_dir, "index.pkl"),
            ]
            
            deleted_count = 0
            for file_path in files_to_delete:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"已删除: {file_path}")
            
            self.vector_store = None
            self.embeddings = None
            return True, deleted_count
        except Exception as e:
            logger.error(f"清除向量数据库失败: {e}")
            return False, 0

    def _load_existing_vector_store(self, index_path):
        try:
            sys.stderr = HiddenStderr()
            
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            logger.info("正在加载嵌入模型...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            self.vector_store = FAISS.load_local(
                self.persist_dir, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            sys.stderr = original_stderr
            logger.info("向量数据库加载成功")
        except Exception as e:
            sys.stderr = original_stderr
            logger.error(f"加载向量数据库失败: {e}")
            self.vector_store = None

    def retrieve_context(self, query: str, top_k: int = 5, similarity_threshold: float = 0.0, use_hybrid: bool = True) -> tuple:
        """返回内容和来源，支持相似度阈值过滤和混合检索"""
        if not self.vector_store:
            return "未找到相关内容", []
        
        try:
            if use_hybrid:
                # 混合检索：向量检索 + BM25
                docs = self._hybrid_search(query, top_k)
            else:
                # 纯向量检索
                docs_with_scores = self.vector_store.similarity_search_with_score(query, k=top_k * 2)
                docs = [doc for doc, score in docs_with_scores]
            
            if not docs:
                return "未找到相关内容", []
            
            # 构建上下文和来源信息
            context_parts = []
            sources = []
            seen_sources = set()
            
            for i, doc in enumerate(docs[:top_k]):
                content = doc.page_content
                source = doc.metadata.get('source', '未知文档')
                filename = os.path.basename(source)
                chunk_index = doc.metadata.get('chunk_index', i)
                
                # 添加上下文片段（包含来源信息）
                context_part = f"【{filename}】\n{content}"
                context_parts.append(context_part)
                
                # 记录来源（去重）
                if filename not in seen_sources:
                    seen_sources.add(filename)
                    sources.append(f"{filename}")
            
            context = "\n\n---\n\n".join(context_parts)
            return context, sources
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return "未找到相关内容", []
    
    def _hybrid_search(self, query: str, top_k: int = 5):
        """混合检索：结合向量检索和关键词检索"""
        try:
            # 向量检索
            vector_docs = self.vector_store.similarity_search(query, k=top_k * 2)
            
            # BM25 检索（如果可用）
            bm25_docs = []
            try:
                from langchain_community.retrievers import BM25Retriever
                from langchain_core.documents import Document
                
                # 创建临时的 BM25 retriever
                bm25_retriever = BM25Retriever.from_documents(vector_docs)
                bm25_retriever.k = top_k * 2
                bm25_docs = bm25_retriever.get_relevant_documents(query)
            except ImportError:
                logger.debug("BM25 检索不可用，仅使用向量检索")
            
            # 合并结果并去重
            all_docs = vector_docs + bm25_docs
            seen_contents = set()
            unique_docs = []
            
            for doc in all_docs:
                content_hash = hash(doc.page_content)
                if content_hash not in seen_contents:
                    seen_contents.add(content_hash)
                    unique_docs.append(doc)
            
            return unique_docs[:top_k]
            
        except Exception as e:
            logger.warning(f"混合检索失败，回退到纯向量检索: {e}")
            return self.vector_store.similarity_search(query, k=top_k)

    def add_documents(self, documents):
        if not self.vector_store or not self.embeddings:
            logger.error("向量数据库未初始化")
            return False
        
        try:
            self.vector_store.add_documents(documents)
            self.vector_store.save_local(self.persist_dir)
            logger.info(f"成功添加 {len(documents)} 个文档")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def ingest_documents(self):
        """从 uploads 目录导入文档并创建向量数据库"""
        try:
            sys.stderr = HiddenStderr()
            
            from langchain_community.vectorstores import FAISS
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # 兼容不同版本的 LangChain
            try:
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            except ImportError:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            from langchain_community.document_loaders import (
                TextLoader,
                PyPDFLoader,
                Docx2txtLoader,
                UnstructuredFileLoader
            )
            
            logger.info("正在初始化嵌入模型...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            documents = []
            
            if not os.path.exists(self.upload_dir):
                logger.warning(f"Upload目录不存在: {self.upload_dir}")
                return False
            
            for filename in os.listdir(self.upload_dir):
                filepath = os.path.join(self.upload_dir, filename)
                
                if filename.startswith('.'):
                    continue
                
                try:
                    logger.info(f"正在加载文档: {filename}")
                    
                    if filename.endswith('.txt'):
                        loader = TextLoader(filepath, encoding='utf-8')
                    elif filename.endswith('.pdf'):
                        loader = PyPDFLoader(filepath)
                    elif filename.endswith('.docx') or filename.endswith('.doc'):
                        loader = Docx2txtLoader(filepath)
                    else:
                        loader = UnstructuredFileLoader(filepath, mode='single')
                    
                    docs = loader.load()
                    
                    # 为每个文档添加元数据
                    for doc in docs:
                        doc.metadata['source'] = filepath
                        doc.metadata['filename'] = filename
                        doc.metadata['doc_id'] = f"{filename}_{id(doc)}"
                    
                    documents.extend(docs)
                    logger.info(f"成功加载文档: {filename}")
                    
                except Exception as e:
                    logger.warning(f"加载文档失败 {filename}: {e}")
                    continue
            
            if not documents:
                logger.warning("未找到有效文档")
                return False
            
            logger.info(f"共加载 {len(documents)} 个文档，正在分割...")
            
            # 优化文本切分策略
            # 采用递归字符分割器，优先按段落、句子、词语层级切分
            # 设置合理重叠（约15%），确保边界信息不丢失
            chunk_size = 500
            chunk_overlap = int(chunk_size * 0.15)  # 约15%重叠
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                add_start_index=True,
                separators=[
                    "\n\n\n",  # 优先按段落分隔
                    "\n\n",     # 段落
                    "\n",       # 换行
                    "。", "！", "？",  # 中文句号
                    "!", "?",    # 英文句号
                    ";", "；",   # 分号
                    " ",         # 空格
                    ""           # 最后用字符分割
                ],
            )
            
            split_docs = text_splitter.split_documents(documents)
            
            # 为分割后的文档块添加元数据
            for i, doc in enumerate(split_docs):
                doc.metadata['chunk_id'] = i
                doc.metadata['total_chunks'] = len(split_docs)
                doc.metadata['chunk_index'] = i
            
            logger.info(f"文档分割完成，共 {len(split_docs)} 个片段")
            
            logger.info("正在创建向量数据库...")
            self.vector_store = FAISS.from_documents(split_docs, self.embeddings)
            self.vector_store.save_local(self.persist_dir)
            
            sys.stderr = original_stderr
            logger.info(f"向量数据库创建成功，共 {len(split_docs)} 个向量")
            return True
            
        except Exception as e:
            sys.stderr = original_stderr
            logger.error(f"导入文档失败: {e}")
            import traceback
            traceback.print_exc()
            return False
