"""
Agent 配置管理模块
负责加载和管理所有子Agent的提示词配置
"""

from pathlib import Path
from typing import Dict, Optional


class AgentConfigManager:
    """Agent配置管理器"""

    AGENTS = {
        "dispatcher": "品牌洞察调度官",
        "market": "市场透视官",
        "competitor": "竞品雷达",
        "consumer": "消费者解码器",
        "channel": "渠道策略官",
        "trend": "趋势望远镜",
    }

    AGENT_DESCRIPTIONS = {
        "market": "品类市场规模、增长趋势、价格带格局分析",
        "competitor": "竞品识别、4P对比、SWOT矩阵、差异化策略",
        "consumer": "消费者画像、AIPL决策旅程、内容偏好分析",
        "channel": "全渠道策略、ROI评估、线上线下协同",
        "trend": "PEST宏观扫描、品类创新方向、风险预警与机会窗口",
    }

    @classmethod
    def get_agent_name(cls, agent_key: str) -> str:
        """获取Agent中文名称"""
        return cls.AGENTS.get(agent_key, agent_key)

    @classmethod
    def get_agent_description(cls, agent_key: str) -> str:
        """获取Agent功能描述"""
        return cls.AGENT_DESCRIPTIONS.get(agent_key, "")

    @classmethod
    def load_prompt(cls, agent_key: str, config_dir: str = "config/agents") -> str:
        """从配置文件加载Agent提示词"""
        base = Path(config_dir)
        prompt_file = base / f"{agent_key}_analyst.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""

    @classmethod
    def list_agents(cls) -> Dict[str, str]:
        """列出所有分析子Agent"""
        return {
            k: v for k, v in cls.AGENT_DESCRIPTIONS.items()
        }

    @classmethod
    def get_deployment_order(cls) -> list:
        """获取推荐部署顺序"""
        return [
            {"phase": "Phase 1", "agents": ["dispatcher", "competitor"],
             "desc": "核心Agent上线，可跑通基本竞品分析流程"},
            {"phase": "Phase 2", "agents": ["market", "consumer"],
             "desc": "补齐3大核心维度"},
            {"phase": "Phase 3", "agents": ["channel", "trend"],
             "desc": "5个子Agent全量上线"},
        ]
