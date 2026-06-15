#!/usr/bin/env python3
"""
数据库初始化脚本
用于初始化 MySQL 数据库、创建表并添加示例数据
"""
import logging
from config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("=" * 60)
print("AI CRM 数据库初始化")
print("=" * 60)
print()

# 打印配置信息
print("数据库配置信息：")
print(f"  Host: {Config.MYSQL_HOST}")
print(f"  Port: {Config.MYSQL_PORT}")
print(f"  User: {Config.MYSQL_USER}")
print(f"  Database: {Config.MYSQL_DB}")
print()

try:
    # 导入并初始化数据库
    from database import DatabaseManager
    
    print("正在连接数据库并初始化...")
    db_manager = DatabaseManager()
    
    # 初始化数据库和表
    success, message = db_manager.init_database_and_tables()
    
    if success:
        print(f"Success: {message}")
        
        # 测试添加示例数据
        from memory import MemoryManager
        memory = MemoryManager()
        
        # 获取所有客户
        customers = memory.get_all_customers()
        print()
        print(f"Database contains {len(customers)} customers")
        print()
        
        # 显示客户信息
        print("当前客户列表：")
        print("-" * 60)
        for customer in customers:
            print(f"  {customer.get('name', '未知')} (ID: {customer.get('user_id')})")
            print(f"    电话: {customer.get('phone_number', 'N/A')}")
            print(f"    邮箱: {customer.get('email', 'N/A')}")
            print(f"    状态: {customer.get('status', 'N/A')}, 等级: {customer.get('level', 'N/A')}")
            print(f"    余额: {customer.get('balance', 0.0)}")
            print()
        
        print("=" * 60)
        print("Database initialized successfully!")
        print("=" * 60)
    else:
        print(f"Error: {message}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
