# modules/database.py
import pymysql
from dbutils.pooled_db import PooledDB
from config import Config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    安全的 MySQL 数据库交互管理器
    仅支持增(INSERT)、改(UPDATE)和新建库(CREATE DATABASE)，严禁删除(DELETE)。
    """
    
    def __init__(self):
        self.pool = None
        # 先初始化数据库和表，然后再创建连接池
        self._init_db_and_pool()

    def _init_db_and_pool(self):
        """初始化数据库（如果不存在则创建），然后创建连接池"""
        try:
            # 先创建数据库（不指定数据库连接）
            self._create_database_if_not_exists()
            
            # 现在创建连接池（指定数据库）
            self._create_pool()
        except Exception as e:
            logger.error(f"初始化数据库和连接池失败: {e}")
            raise

    def _create_database_if_not_exists(self):
        """如果数据库不存在则创建"""
        try:
            temp_conn = None
            temp_cursor = None
            try:
                temp_conn = pymysql.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    charset='utf8mb4'
                )
                temp_cursor = temp_conn.cursor()
                
                temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` DEFAULT CHARSET utf8mb4;")
                temp_conn.commit()
                logger.info(f"数据库 '{Config.MYSQL_DB}' 已创建或已存在")
                
                temp_cursor.close()
                temp_conn.close()
            except Exception as e:
                logger.error(f"创建数据库失败: {e}")
                if temp_conn:
                    temp_conn.rollback()
                if temp_cursor:
                    temp_cursor.close()
                if temp_conn:
                    temp_conn.close()
                raise
        except Exception as e:
            logger.error(f"创建数据库时出错: {e}")
            raise

    def _create_pool(self):
        """初始化 MySQL 连接池"""
        try:
            self.pool = PooledDB(
                creator=pymysql,          
                maxconnections=6,         
                mincached=2,              
                maxcached=5,              
                blocking=True,            
                ping=1,                   
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                passwd=Config.MYSQL_PASSWORD,
                db=Config.MYSQL_DB,
                charset='utf8mb4'
            )
            logger.info("MySQL 连接池初始化成功")
        except Exception as e:
            logger.error(f"MySQL 连接池初始化失败: {e}")
            raise

    def get_connection(self):
        """从连接池中获取一个连接"""
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        return self.pool.connection()

    @staticmethod
    def _safe_execute(sql, params=None, is_query=False):
        """
        内部通用安全执行方法 (使用参数化查询防止 SQL 注入)
        """
        conn = None
        cursor = None
        try:
            conn = DatabaseManager().get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql, params or ())
            
            if is_query:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = {"affected_rows": cursor.rowcount}
                
            return True, result
        except Exception as e:
            if conn: 
                conn.rollback()
            logger.error(f"❌ 数据库执行错误: {e}")
            return False, str(e)
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def init_database_and_tables(self):
        """初始化必要的表（数据库已在 __init__ 中创建）"""
        try:
            # 创建表（使用连接池）
            self._create_customers_table()
            logger.info("数据库和表初始化完成")
            return True, "数据库和表初始化完成"
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            return False, str(e)

    def _create_customers_table(self):
        """创建 customers 表"""
        sql = """
        CREATE TABLE IF NOT EXISTS customers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(100) NOT NULL,
            phone_number VARCHAR(20),
            email VARCHAR(100),
            status VARCHAR(20) DEFAULT 'active',
            level VARCHAR(20) DEFAULT '普通',
            balance DECIMAL(10, 2) DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_user_id (user_id),
            INDEX idx_phone (phone_number),
            INDEX idx_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        return self._safe_execute(sql)

    # ================= 客户表操作 =================

    def add_customer(self, data: dict):
        """新增客户"""
        try:
            # 检查是否已存在
            user_id = data.get('user_id')
            if user_id:
                exists, result = self.get_customer_by_user_id(user_id)
                if exists and result:
                    # 如果已存在，更新客户信息
                    return self.update_customer(data)
            
            # 构建 INSERT 语句
            columns = []
            placeholders = []
            params = []
            
            for key, value in data.items():
                columns.append(f"`{key}`")
                placeholders.append("%s")
                params.append(value)
            
            sql = f"INSERT INTO customers ({', '.join(columns)}) VALUES ({', '.join(placeholders)});"
            success, result = self._safe_execute(sql, tuple(params))
            
            if success:
                logger.info(f"✅ 客户添加成功: {data.get('name')}")
                return True, "客户添加成功"
            else:
                return False, result
        except Exception as e:
            logger.error(f"添加客户失败: {e}")
            return False, str(e)

    def update_customer(self, data: dict):
        """更新客户信息"""
        try:
            user_id = data.get('user_id')
            if not user_id:
                return False, "缺少 user_id 字段"
            
            # 构建 UPDATE 语句
            set_clauses = []
            params = []
            
            for key, value in data.items():
                if key != "user_id":
                    set_clauses.append(f"`{key}` = %s")
                    params.append(value)
            
            if not set_clauses:
                return False, "没有提供需要更新的字段"
            
            params.append(user_id)
            sql = f"UPDATE customers SET {', '.join(set_clauses)} WHERE user_id = %s;"
            success, result = self._safe_execute(sql, tuple(params))
            
            if success:
                logger.info(f"✅ 客户更新成功: {user_id}")
                return True, "客户更新成功"
            else:
                return False, result
        except Exception as e:
            logger.error(f"更新客户失败: {e}")
            return False, str(e)

    def get_customer_by_user_id(self, user_id: str):
        """根据 user_id 查询客户"""
        sql = "SELECT * FROM customers WHERE user_id = %s;"
        success, result = self._safe_execute(sql, (user_id,), is_query=True)
        if success and result:
            return True, result[0] if result else None
        return False, None

    def search_customers(self, keyword: str):
        """搜索客户（支持 name、phone_number、email）"""
        sql = """
        SELECT * FROM customers 
        WHERE name LIKE %s 
           OR phone_number LIKE %s 
           OR email LIKE %s
           OR user_id LIKE %s;
        """
        param = f"%{keyword}%"
        return self._safe_execute(sql, (param, param, param, param), is_query=True)

    def get_all_customers(self):
        """获取所有客户"""
        sql = "SELECT * FROM customers ORDER BY created_at DESC;"
        return self._safe_execute(sql, is_query=True)

    # ================= 通用操作 =================

    def add_record(self, table_name: str, data: dict):
        """新增记录 (通用增加方法)"""
        if not data:
            return False, "插入数据不能为空"
            
        columns = ', '.join([f"`{k}`" for k in data.keys()])
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders});"
        params = tuple(data.values())
        return self._safe_execute(sql, params)

    def execute_query(self, sql: str, params=None):
        """只读查询"""
        return self._safe_execute(sql, params, is_query=True)

    # ================= 安全护栏 =================

    @staticmethod
    def validate_agent_sql(sql: str):
        """强制安全校验：拦截任何危险操作"""
        dangerous_keywords = ['DELETE', 'DROP', 'TRUNCATE', 'ALTER']
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                msg = f"⚠️ 安全拦截：系统禁止执行包含 '{keyword}' 的操作！"
                logger.warning(msg)
                return False, msg
        return True, "Validation passed"
