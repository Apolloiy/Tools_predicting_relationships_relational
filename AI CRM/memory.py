# core/memory.py
import json
import logging
from database import DatabaseManager

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    上下文与记忆管理器
    支持：对话历史 + CRM 客户数据管理（MySQL 数据库）
    """
    
    def __init__(self):
        self.chat_histories = {}  # 内存中存储对话历史
        try:
            self.db_manager = DatabaseManager()
            # 初始化数据库和表
            self.db_manager.init_database_and_tables()
            # 初始化示例数据
            self._init_sample_data()
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            self.db_manager = None
            logger.warning("将使用内存存储作为备选方案")
            self.customer_data = {}
    
    def _init_sample_data(self):
        """初始化示例客户数据到数据库"""
        sample_customers = [
            {
                "user_id": "1001",
                "name": "张三",
                "phone_number": "13800138001",
                "email": "zhangsan@example.com",
                "status": "active",
                "level": "VIP",
                "balance": 10000.0
            },
            {
                "user_id": "1002",
                "name": "李四",
                "phone_number": "13800138002",
                "email": "lisi@example.com",
                "status": "active",
                "level": "普通",
                "balance": 5000.0
            },
            {
                "user_id": "1003",
                "name": "王五",
                "phone_number": "13800138003",
                "email": "wangwu@example.com",
                "status": "inactive",
                "level": "VIP",
                "balance": 20000.0
            }
        ]
        
        # 检查是否已存在数据，如果不存在则添加
        for customer in sample_customers:
            if self.db_manager:
                exists, result = self.db_manager.get_customer_by_user_id(customer["user_id"])
                if not result:
                    self.db_manager.add_customer(customer)
                    logger.info(f"✅ 添加示例客户: {customer['name']}")
        logger.info("✅ 示例客户数据初始化完成")
    
    def get_chat_history(self, phone_number: str) -> list[dict]:
        """获取指定用户的聊天历史记录"""
        if phone_number not in self.chat_histories:
            self.chat_histories[phone_number] = []
        return self.chat_histories[phone_number]
    
    def save_to_history(self, phone_number: str, user_message: str, ai_response: str):
        """保存一轮新的对话到内存中"""
        if phone_number not in self.chat_histories:
            self.chat_histories[phone_number] = []
        
        self.chat_histories[phone_number].append({"role": "user", "content": user_message})
        self.chat_histories[phone_number].append({"role": "assistant", "content": ai_response})
        
        logger.info(f"对话已保存 (Phone: {phone_number})")
    
    def update_long_term_memory(self, phone_number: str, extracted_data: dict):
        """更新 CRM 客户数据到 MySQL 数据库"""
        try:
            logger.info(f"数据更新请求 (Phone: {phone_number}): {extracted_data}")
            
            if self.db_manager:
                # 使用 MySQL 数据库
                user_id = extracted_data.get('user_id')
                
                # 如果没有 user_id，尝试查找已存在的客户
                if not user_id:
                    # 先尝试通过 phone_number 查找
                    phone = extracted_data.get('phone_number')
                    if phone:
                        exists, customers = self.db_manager.search_customers(phone)
                        if exists and customers:
                            user_id = customers[0]['user_id']
                            extracted_data['user_id'] = user_id
                            logger.info(f"通过 phone_number 找到客户: {user_id}")
                
                # 如果还没找到，尝试通过 name 查找
                if not user_id:
                    name = extracted_data.get('name')
                    if name:
                        exists, customers = self.db_manager.search_customers(name)
                        if exists and customers:
                            # 如果找到多个，用第一个
                            user_id = customers[0]['user_id']
                            extracted_data['user_id'] = user_id
                            logger.info(f"通过 name 找到客户: {user_id}")
                
                # 如果还没找到，尝试通过 email 查找
                if not user_id:
                    email = extracted_data.get('email')
                    if email:
                        exists, customers = self.db_manager.search_customers(email)
                        if exists and customers:
                            user_id = customers[0]['user_id']
                            extracted_data['user_id'] = user_id
                            logger.info(f"通过 email 找到客户: {user_id}")
                
                # 如果还是没有 user_id，生成一个新的（新增客户）
                if not user_id:
                    # 生成新的 user_id
                    user_id = str(len(self.get_all_customers()) + 1001)
                    extracted_data['user_id'] = user_id
                    logger.info(f"创建新客户，分配 user_id: {user_id}")
                
                # 现在执行更新或新增
                success, message = self.db_manager.add_customer(extracted_data)
                if success:
                    logger.info(f"客户数据操作成功: {user_id}")
                    return True
                else:
                    logger.error(f"数据库操作失败: {message}")
                    return False
            else:
                # 备用方案：内存存储
                logger.warning("使用内存存储备用方案")
                user_id = extracted_data.get('user_id', str(len(self.customer_data) + 1001))
                self.customer_data[user_id] = extracted_data
                return True
        except Exception as e:
            logger.error(f"更新客户数据失败: {e}", exc_info=True)
            return False
    
    def query_customer(self, keyword: str) -> list[dict]:
        """查询 CRM 客户数据"""
        try:
            logger.info(f"正在查询客户: {keyword}")
            
            if self.db_manager:
                success, customers = self.db_manager.search_customers(keyword)
                if success:
                    return customers if customers else []
                else:
                    logger.error(f"查询客户失败: {customers}")
                    return []
            else:
                # 备用方案：内存查询
                results = []
                keyword_lower = keyword.lower()
                for customer in self.customer_data.values():
                    if (keyword_lower in str(customer.get('name', '')).lower() or
                        keyword_lower in str(customer.get('user_id', '')).lower() or
                        keyword_lower in str(customer.get('phone_number', '')).lower() or
                        keyword_lower in str(customer.get('email', '')).lower()):
                        results.append(customer)
                return results
        except Exception as e:
            logger.error(f"查询客户失败: {e}")
            return []
    
    def get_all_customers(self) -> list[dict]:
        """获取所有客户数据"""
        try:
            if self.db_manager:
                success, customers = self.db_manager.get_all_customers()
                if success:
                    return customers if customers else []
                else:
                    logger.error(f"获取客户列表失败: {customers}")
                    return []
            else:
                # 备用方案：内存查询
                return list(self.customer_data.values())
        except Exception as e:
            logger.error(f"获取所有客户失败: {e}")
            return []
    
    def trim_short_term_memory(self, history: list[dict], max_rounds: int = 5) -> list[dict]:
        """防止上下文窗口溢出"""
        if len(history) > max_rounds * 2:
            history = history[-(max_rounds * 2):]
        return history
