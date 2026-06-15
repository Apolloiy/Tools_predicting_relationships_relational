# modules/tools.py
import os
import re
from tavily import TavilyClient
from config import Config
import logging

logger = logging.getLogger(__name__)


class SearchTools:
    """
    封装搜索能力的工具类
    提供通用的网络搜索和特定场景（如天气）的查询，并对结果进行清洗和格式化。
    """
    
    def __init__(self):
        """初始化搜索客户端"""
        try:
            self.client = TavilyClient(api_key=Config.tavily_api_key) 
            logger.info("Tavily search engine initialized successfully")
        except Exception as e:
            logger.error(f"Tavily initialization failed: {e}")
            raise

    def tavily_search(self, query: str, max_results: int = 3) -> list[dict]:
        """
        通用网络搜索方法
        :param query: 搜索关键词
        :param max_results: 最大返回结果数
        :return: 包含 title, url, content 的列表
        """
        try:
            response = self.client.search(
                query=query, 
                search_depth="advanced",
                max_results=max_results,
                include_answer=True
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", "无标题"),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:800]
                })
            
            answer = response.get("answer", "")
            if answer:
                results.insert(0, {
                    "title": "AI总结",
                    "url": "",
                    "content": answer
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily search execution error: {e}")
            return []

    def search_weather(self, location: str) -> str:
        """
        专门用于查询天气的方法，内部调用通用搜索并进行结果清洗。
        :param location: 城市或地点名称
        :return: 格式化后的天气字符串
        """
        city_name = self._normalize_city_name(location)
        
        queries = [
            f"{city_name} 天气预报 今天 天气状况",
            f"{city_name} weather forecast today",
            f"{city_name} 实时天气 气温 湿度"
        ]
        
        all_results = []
        for query in queries:
            results = self.tavily_search(query, max_results=2)
            all_results.extend(results)
        
        if not all_results:
            return f"抱歉，未能查询到 {location} 的天气信息。"
        
        weather_condition = "未知"
        temperature = "未知"
        source_url = ""
        
        for result in all_results:
            content = result["content"]
            url = result["url"]
            
            cond = self._extract_weather_condition(content)
            temp = self._extract_temperature(content)
            
            if cond != "未知" or temp != "未知":
                if cond != "未知":
                    weather_condition = cond
                if temp != "未知":
                    temperature = temp
                if url and not source_url:
                    source_url = url
            
            if weather_condition != "未知" and temperature != "未知":
                break
        
        if weather_condition == "未知":
            weather_condition = self._guess_weather_from_temp(temperature)
        
        formatted_output = (
            f"地点：{location}\n"
            f"天气：{weather_condition}\n"
            f"温度：{temperature}\n"
            f"来源网址：{source_url if source_url else '未知'}"
        )
        
        logger.info(f"Weather query successful: {location}")
        return formatted_output

    def _normalize_city_name(self, location: str) -> str:
        """标准化城市名称"""
        mappings = {
            "苏州": "江苏省苏州市",
            "南京": "江苏省南京市",
            "合肥": "安徽省合肥市",
            "宿州": "安徽省宿州市",
            "北京": "北京市",
            "上海": "上海市",
            "广州": "广东省广州市",
            "深圳": "广东省深圳市",
            "杭州": "浙江省杭州市",
            "成都": "四川省成都市",
        }
        return mappings.get(location, location)

    def _extract_weather_condition(self, content: str) -> str:
        """从文本中提取天气状况"""
        weather_patterns = [
            (r'晴朗|晴(天|空|朗)?', '晴'),
            (r'多云', '多云'),
            (r'阴(天|沉)?', '阴'),
            (r'雷阵雨', '雷阵雨'),
            (r'小雨|毛毛雨|细雨', '小雨'),
            (r'中雨', '中雨'),
            (r'大雨', '大雨'),
            (r'暴雨', '暴雨'),
            (r'阵雨', '阵雨'),
            (r'雨(天|水)?|下雨', '雨'),
            (r'小雪|雨夹雪|阵雪', '小雪'),
            (r'中雪', '中雪'),
            (r'大雪', '大雪'),
            (r'暴雪', '暴雪'),
            (r'雪(天)?|下雪', '雪'),
            (r'雾(霾)?|雾霾|大雾', '雾'),
            (r'霾|雾霾', '霾'),
            (r'大风|阵风', '大风'),
            (r'台风|热带风暴', '台风'),
            (r'沙尘|扬沙|浮尘', '沙尘'),
            (r'冰雹', '冰雹'),
            (r'霜冻|霜', '霜'),
            (r'雾凇', '雾凇'),
            (r'雨夹雪', '雨夹雪'),
            (r'晴转多云|多云转晴', '晴转多云'),
            (r'多云转阴|阴转多云', '多云转阴'),
            (r'阴转雨|雨转阴', '阴转雨'),
            (r'晴转阴|阴转晴', '晴转阴'),
            (r'有(小)?雨', '小雨'),
            (r'有(小)?雪', '小雪'),
        ]
        
        content_lower = content.lower()
        for pattern, condition in weather_patterns:
            if re.search(pattern, content) or re.search(pattern.lower(), content_lower):
                return condition
        
        return "未知"

    def _extract_temperature(self, content: str) -> str:
        """从文本中提取温度信息"""
        patterns = [
            r'(\d{1,3})\s*[°℃度]\s*[-~至到～]\s*(\d{1,3})\s*[°℃度]',
            r'(\d{1,3})\s*[-~至到～]\s*(\d{1,3})\s*[°℃度]',
            r'(\d{1,3})\s*[°℃度]\s*到\s*(\d{1,3})\s*[°℃度]',
            r'(\d{1,3})\s*[°℃度]',
            r'温度[\s：:]*(\d{1,3})\s*[°℃度]',
            r'气温[\s：:]*(\d{1,3})\s*[°℃度]',
            r'temperature[\s：:]*(\d{1,3})',
            r'(\d{1,3})[Ff]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                if len(match.groups()) == 2:
                    return f"{match.group(1)}~{match.group(2)}℃"
                else:
                    temp = int(match.group(1))
                    if 'F' in content[match.end():match.end()+3] or 'f' in content[match.end():match.end()+3]:
                        temp = round((temp - 32) * 5 / 9)
                    return f"{temp}℃"
        
        return "未知"

    def _guess_weather_from_temp(self, temperature: str) -> str:
        """根据温度猜测天气状况"""
        if temperature == "未知":
            return "未知"
        
        match = re.search(r'(\d+)', temperature)
        if match:
            temp = int(match.group(1))
            if temp < 0:
                return "雪"
            elif temp < 10:
                return "冷"
            elif temp > 35:
                return "晴"
        
        return "多云"


# 测试入口
if __name__ == "__main__":
    tools = SearchTools()
    print("测试天气查询：")
    print("=" * 30)
    result = tools.search_weather("苏州")
    print(result)
    print()
    result = tools.search_weather("上海")
    print(result)
    print()
    result = tools.search_weather("北京")
    print(result)
