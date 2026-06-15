from locust import HttpUser, task, between
import random

class CRMChatUser(HttpUser):
    wait_time = between(1, 3)
    
    test_queries = [
        "你好",
        "今天天气怎么样",
        "查询所有客户",
        "把张三的余额改成5000",
        "公司有哪些产品"
    ]
    
    @task(4)
    def chat(self):
        """测试聊天接口 - 核心业务"""
        query = random.choice(self.test_queries)
        self.client.post(
            "/api/chat",
            json={
                "query": query,
                "phone_number": f"test_user_{random.randint(1, 100)}"
            }
        )
    
    @task(2)
    def health(self):
        """测试健康检查接口"""
        self.client.get("/health")


if __name__ == "__main__":
    print("请运行: locust -f locustfile.py")
