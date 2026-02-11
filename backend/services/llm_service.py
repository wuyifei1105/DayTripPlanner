"""NVIDIA NIM API LLM服务封装"""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from config import settings


class LLMService:
    """NVIDIA NIM API封装，兼容OpenAI接口"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
        self.model = settings.nvidia_model
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> str:
        """发送聊天请求"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API调用失败: {str(e)}")
    
    async def extract_places(self, text: str, location: str) -> List[Dict[str, Any]]:
        """从文本中提取地点信息"""
        prompt = f"""从以下文本中提取与"{location}"相关的地点信息。
返回JSON数组格式，每个地点包含：
- name: 地点名称
- category: 分类（景点/美食/购物/娱乐）
- description: 简短描述

文本内容：
{text}

只返回JSON数组，不要其他内容。如果没有找到地点，返回空数组[]。""".translate(str.maketrans({'/': '/'}))
        
        messages = [
            {"role": "system", "content": "你是一个地点信息提取助手，只返回JSON格式的数据。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat(messages, temperature=0.3)
        
        # 尝试解析JSON
        import json
        try:
            # 处理可能的markdown代码块
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return []
    
    async def plan_trip(self, places: List[Dict], location: str, start_time: str = "09:00") -> Dict:
        """规划一日行程"""
        places_text = "\n".join([
            f"- {p.get('name', '未知')}: {p.get('category', '未知')}, {p.get('description', '')}"
            for p in places
        ])
        
        prompt = f"""请为"{location}"规划一日游行程。

可选地点：
{places_text}

要求：
1. 从{start_time}开始
2. 合理安排景点和美食，午餐和晚餐时间合理
3. 考虑地点之间的距离，尽量减少折返
4. 每个地点给出建议停留时间

返回JSON格式：
{{
  "stops": [
    {{
      "name": "地点名称",
      "arrival_time": "到达时间",
      "stay_duration": 停留分钟数,
      "activity": "在此处的活动建议"
    }}
  ],
  "tips": "行程小贴士"
}}"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的旅行规划师。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat(messages, temperature=0.5)
        
        import json
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return {"stops": [], "tips": "规划生成失败"}
    
    async def analyze_xhs_notes(self, notes: List[Dict], location: str) -> List[Dict]:
        """分析小红书笔记，提取旅行地点/美食/评价等信息（LLM SubAgent）
        
        Args:
            notes: 爬虫获取的笔记列表（每个包含 title, description, tags 等）
            location: 目标位置
        
        Returns:
            提取出的地点信息列表
        """
        if not notes:
            return []
        
        # 组装笔记摘要
        notes_text = ""
        for i, note in enumerate(notes[:15]):  # 最多分析15条
            title = note.get('title', '')
            desc = note.get('description', '')[:200]
            tags = ', '.join(note.get('tags', [])[:5])
            likes = note.get('likes', 0)
            collected = note.get('collected', 0)
            notes_text += f"\n笔记{i+1}: 标题={title}\n描述={desc}\n标签=[{tags}]\n点赞={likes} 收藏={collected}\n"
        
        prompt = f"""你是一个旅行信息分析助手。请从以下小红书笔记中提取与"{location}"相关的具体地点和美食信息。

{notes_text}

请提取所有提到的具体地点（景点、餐厅、咖啡馆、商场等），返回JSON数组格式：
[
  {{
    "name": "地点名称（具体的店名或景点名）",
    "category": "景点/美食/购物/娱乐",
    "description": "基于笔记内容的简短描述",
    "popularity_hint": "从点赞和收藏数判断的热度（高/中/低）",
    "tips": "来自笔记的实用建议（如果有）"
  }}
]

注意：
1. 只提取具体的、可定位的地点名称，不要提取模糊的描述
2. 如果多条笔记提到同一个地点，合并信息
3. 只返回JSON数组，不要其他内容
4. 如果没有找到具体地点，返回空数组[]"""

        messages = [
            {"role": "system", "content": "你是一个旅行信息分析助手，专注从社交媒体笔记中提取地点信息。只返回JSON格式的数据。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat(messages, temperature=0.3, max_tokens=3000)
        
        import json
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except json.JSONDecodeError:
            return []


# 全局实例
llm_service = LLMService()

