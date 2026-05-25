"""
意图解析与任务分发模块
负责从用户输入中提取分析参数，决定调用哪些子Agent
"""

import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class AnalysisParams:
    """分析参数"""
    brand: str = ""                       # 目标品牌名称
    category: str = ""                    # 品类
    market: str = "中国"                   # 目标市场
    task_type: str = "full_report"       # 分析类型
    scope: str = "broad"                 # 分析范围
    raw_input: str = ""                  # 原始用户输入

    TASK_TYPES = {
        "full_report": "全维度分析",
        "competitor_only": "竞品分析",
        "consumer_only": "消费者洞察",
        "market_entry": "市场进入评估",
        "trend_only": "趋势研判",
        "channel_only": "渠道分析",
    }

    MARKETS = [
        "中国", "东南亚", "拉美", "欧美", "中东", "非洲",
        "日本", "韩国", "印度", "全球",
    ]

    CATEGORIES = [
        "美妆", "护肤", "包袋", "服饰", "鞋履", "珠宝",
        "健康", "食品饮料", "母婴", "宠物", "家居", "3C数码",
        "运动户外", "汽车", "其他",
    ]


@dataclass
class TaskPlan:
    """任务规划"""
    params: AnalysisParams
    agents_to_call: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict:
        return {
            "params": asdict(self.params),
            "agents_to_call": self.agents_to_call,
            "reasoning": self.reasoning,
        }


class IntentParser:
    """意图解析器 — 从自然语言中提取分析参数"""

    @classmethod
    def parse(cls, user_input: str, llm_client=None) -> AnalysisParams:
        """
        解析用户输入，提取分析参数。
        优先使用LLM解析，降级使用规则匹配。
        """
        if llm_client:
            try:
                return cls._llm_parse(user_input, llm_client)
            except Exception:
                pass
        return cls._rule_parse(user_input)

    @classmethod
    def _llm_parse(cls, user_input: str, llm_client) -> AnalysisParams:
        """使用LLM进行意图解析"""
        system_prompt = """你是品牌分析意图解析专家。从用户输入中提取JSON格式参数。
        
返回格式：
{
    "brand": "品牌名称",
    "category": "品类（美妆/护肤/包袋/服饰/鞋履/珠宝/健康/食品饮料/母婴/宠物/家居/3C数码/运动户外/汽车/其他）",
    "market": "目标市场（中国/东南亚/拉美/欧美/中东/非洲/日本/韩国/印度/全球）",
    "task_type": "full_report|competitor_only|consumer_only|market_entry|trend_only|channel_only",
    "scope": "broad|deep|comparison"
}

规则：
- task_type默认"full_report"
- 用户提到"竞品/SWOT/对比"时倾向competitor_only
- 用户提到"消费者/人群/用户画像"时倾向consumer_only
- 用户提到"进入/出海/打入XX市场"时倾向market_entry
- 用户提到"趋势/未来/预测"时倾向trend_only
- 用户提到"渠道/线上线下/门店"时倾向channel_only
- market默认"中国"
- scope默认"broad"，要求深入分析时为"deep"
"""
        response = llm_client(
            system=system_prompt,
            user=user_input
        )
        return cls._parse_json_response(response, user_input)

    @classmethod
    def _rule_parse(cls, user_input: str) -> AnalysisParams:
        """基于规则的关键词匹配解析"""
        params = AnalysisParams(raw_input=user_input)
        text = user_input.lower()

        # 提取品牌名（按优先级排列）
        # 排除常见分析术语，避免误识别
        EXCLUDED_TERMS = {"SWOT", "PEST", "AIPL", "TAM", "SAM", "SOM", "CAGR",
                          "GMV", "ROI", "DTC", "KOL", "KPI", "AI"}
        brand_patterns = [
            r'(?<![A-Za-z])([A-Z][A-Za-z]{2,20})(?![A-Za-z])\s*想进入',  # 英文品牌名 + "想进入"
            r'(?<![A-Za-z])([A-Z][A-Za-z]{2,20})(?![A-Za-z])',         # 纯英文品牌名（大写开头）
            r'(?:分析|评估|看看|查一下|了解|做一下|做一个)\s*[""\u201c]?(.+?[^品牌品类市场])[""\u201d]?\s*(?:品牌|的|在)',
            r'(?:分析|评估|看看|查一下|了解|做一下|做一个)\s*[""\u201c]?(.+?)[""\u201d]?\s*$',
            r'[""\u201c](.+?)[""\u201d]\s*(?:品牌)',
            r'(?:对|给)(.+?)做.*(?:分析|评估)',
        ]
        for pattern in brand_patterns:
            match = re.search(pattern, user_input)
            if match:
                candidate = match.group(1).strip()
                # 过滤掉明显不是品牌名的内容
                if (len(candidate) >= 2 and len(candidate) <= 30
                        and not candidate.startswith(("在", "的", "个", "这"))
                        and candidate not in ("帮我", "一个", "一下")
                        and candidate not in EXCLUDED_TERMS):
                    params.brand = candidate
                    break

        # 品类匹配
        for cat in AnalysisParams.CATEGORIES:
            if cat in user_input:
                params.category = cat
                break

        # 市场匹配
        market_keywords = {
            "中国": ["中国", "国内", "本土"],
            "东南亚": ["东南亚", "印尼", "泰国", "越南", "菲律宾"],
            "拉美": ["拉美", "拉丁美洲", "巴西", "墨西哥"],
            "欧美": ["欧美", "欧洲", "美国", "北美"],
            "中东": ["中东", "沙特", "阿联酋"],
            "非洲": ["非洲"],
            "日本": ["日本"],
            "韩国": ["韩国"],
            "印度": ["印度"],
            "全球": ["全球", "世界", "国际"],
        }
        for market, keywords in market_keywords.items():
            if any(kw in text for kw in keywords):
                params.market = market
                break

        # 任务类型（注意优先级：market_entry > consumer_only）
        if any(kw in text for kw in ["进入", "出海", "打入"]):
            params.task_type = "market_entry"
        elif any(kw in text for kw in ["竞品", "swot", "对比", "对手"]):
            params.task_type = "competitor_only"
        elif any(kw in text for kw in ["消费者", "人群", "用户画像", "客群"]):
            params.task_type = "consumer_only"
        elif any(kw in text for kw in ["趋势", "未来", "预测", "机会"]):
            params.task_type = "trend_only"
        elif any(kw in text for kw in ["渠道", "线上", "线下", "门店", "电商"]):
            params.task_type = "channel_only"
        else:
            params.task_type = "full_report"

        # 分析范围
        if any(kw in text for kw in ["深度", "详细", "全面", "深入"]):
            params.scope = "deep"

        return params

    @classmethod
    def _parse_json_response(cls, response: str, user_input: str) -> AnalysisParams:
        """解析LLM返回的JSON"""
        try:
            # 尝试提取JSON块
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return AnalysisParams(
                    brand=data.get("brand", ""),
                    category=data.get("category", ""),
                    market=data.get("market", "中国"),
                    task_type=data.get("task_type", "full_report"),
                    scope=data.get("scope", "broad"),
                    raw_input=user_input,
                )
        except (json.JSONDecodeError, KeyError):
            pass
        return cls._rule_parse(user_input)


class TaskDispatcher:
    """任务分发器 — 决定调用哪些子Agent"""

    DISPATCH_RULES = {
        "full_report": ["market", "competitor", "consumer", "channel", "trend"],
        "competitor_only": ["competitor"],
        "consumer_only": ["consumer"],
        "channel_only": ["channel"],
        "trend_only": ["trend"],
        "market_entry": ["market", "competitor", "consumer"],
    }

    @classmethod
    def dispatch(cls, params: AnalysisParams) -> TaskPlan:
        """根据分析参数决定调用哪些Agent"""
        agents = cls.DISPATCH_RULES.get(
            params.task_type,
            ["market", "competitor"]  # 默认最小组合
        )

        reasoning = cls._build_reasoning(params, agents)
        return TaskPlan(params=params, agents_to_call=agents, reasoning=reasoning)

    @classmethod
    def _build_reasoning(cls, params: AnalysisParams, agents: List[str]) -> str:
        """构建调度理由说明"""
        agent_names = [AgentConfigManager.get_agent_name(a) for a in agents]
        return (
            f"分析类型: {AnalysisParams.TASK_TYPES.get(params.task_type, params.task_type)}\n"
            f"目标品牌: {params.brand or '未指定'}\n"
            f"品类: {params.category or '未指定'}\n"
            f"目标市场: {params.market}\n"
            f"调度Agent: {', '.join(agent_names)}\n"
            f"分析深度: {'深度' if params.scope == 'deep' else '标准'}"
        )


# 解决循环引用 - 延迟导入
from src.agent_config import AgentConfigManager
