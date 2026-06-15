import os
os.environ['HF_ENDPOINT'] = 'https://modelscope.cn'
os.environ['HUGGINGFACE_HUB_DISABLE_PROGRESS_BARS'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

import logging
from config import Config
from rag_engine import RAGEngine, RAG_AVAILABLE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("开始初始化知识库")
    logger.info("=" * 50)
    
    Config.init_storage()
    logger.info(f"Upload directory: {Config.UPLOAD_FOLDER}")
    logger.info(f"Vector DB path: {Config.VECTOR_DB_PATH}")
    
    # 检查 RAG 依赖
    if not RAG_AVAILABLE:
        logger.error("RAG 依赖不可用，请检查环境配置")
        return False
    
    logger.info("\n正在初始化 RAG 引擎...")
    try:
        rag_engine = RAGEngine(enable_rag=True)
        logger.info("RAG 引擎初始化成功")
    except Exception as e:
        logger.error(f"RAG 引擎初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 检测现有向量数据库
    logger.info("\n检测现有向量数据库...")
    exists, vector_count = rag_engine.check_existing_vector_db()
    
    if exists:
        if vector_count > 0:
            logger.info(f"发现现有的向量数据库，包含 {vector_count} 个向量")
        else:
            logger.info("发现现有的向量数据库")
        
        # 询问用户是否覆盖
        print("\n" + "=" * 50)
        print("检测到现有向量数据库！")
        print("=" * 50)
        if vector_count > 0:
            print(f"当前向量数据库包含 {vector_count} 个向量")
        print("\n是否覆盖现有向量数据库?")
        
        while True:
            try:
                choice = input("请输入 (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    print("\n正在清除现有向量数据库...")
                    logger.info("正在清除现有向量数据库...")
                    success, deleted = rag_engine.clear_vector_db()
                    if success:
                        print(f"已清除 {deleted} 个文件")
                        logger.info(f"已清除 {deleted} 个文件")
                    else:
                        print("清除失败")
                        logger.error("清除失败")
                        return False
                    break
                elif choice in ['n', 'no']:
                    print("\n保留现有向量数据库，跳过导入")
                    logger.info("保留现有向量数据库，跳过导入")
                    print("\n" + "=" * 50)
                    print("知识库初始化完成（保留现有数据）")
                    print("=" * 50)
                    logger.info("\n" + "=" * 50)
                    logger.info("知识库初始化完成（保留现有数据）")
                    logger.info("=" * 50)
                    return True
                else:
                    print("请输入 y 或 n")
            except KeyboardInterrupt:
                print("\n操作已取消")
                logger.info("\n操作已取消")
                return False
    
    logger.info("\n正在导入文档...")
    try:
        success = rag_engine.ingest_documents()
        if success:
            logger.info("\n" + "=" * 50)
            logger.info("知识库初始化成功！")
            logger.info("=" * 50)
            return True
        else:
            logger.warning("\n未找到有效文档或导入失败")
            return False
    except Exception as e:
        logger.error(f"文档导入过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()