"""
示例脚本 — 演示系统框架模式（无需LLM API Key）

运行: python example.py
"""

import sys
import os
import io

# 强制使用UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.orchestrator import BrandInsightOrchestrator
from src.intent_parser import IntentParser, TaskDispatcher
from src.agent_config import AgentConfigManager


def demo_intent_parsing():
    """演示意图解析能力"""
    print("=" * 60)
    print("[Intent Parsing Demo]")
    print("=" * 60)

    test_queries = [
        "帮我全面分析山下有松(Songmont)品牌在中国包袋市场的竞争格局",
        "ULTRAMO想进入拉美彩妆市场，帮我分析一下竞争格局和消费者",
        "给我做一下特斯拉的竞品SWOT分析",
        "分析瑞幸咖啡的核心消费者画像",
        "2025年宠物食品行业的趋势和机会",
        "分析小米SU7的渠道策略",
    ]

    for query in test_queries:
        params = IntentParser.parse(query)
        plan = TaskDispatcher.dispatch(params)
        print(f"\n  Input: {query}")
        print(f"   Brand: {params.brand}")
        print(f"   Category: {params.category}")
        print(f"   Market: {params.market}")
        print(f"   Type: {params.task_type}")
        print(f"   Dispatch: {plan.agents_to_call}")
    print()


def demo_agent_info():
    """演示Agent信息"""
    print("=" * 60)
    print("[Agent Configuration Info]")
    print("=" * 60)

    for key in ["market", "competitor", "consumer", "channel", "trend"]:
        name = AgentConfigManager.get_agent_name(key)
        desc = AgentConfigManager.get_agent_description(key)
        prompt_len = len(AgentConfigManager.load_prompt(key))
        print(f"\n  [{key}] {name}")
        print(f"      {desc}")
        print(f"      Prompt length: {prompt_len} chars")
    print()


def demo_framework_run():
    """演示框架模式运行（无LLM）"""
    print("=" * 60)
    print("[Framework Mode Demo]")
    print("=" * 60)

    orchestrator = BrandInsightOrchestrator()
    result = orchestrator.analyze(
        "分析完美日记在中国美妆市场的竞争格局",
        show_progress=True
    )

    print("\n" + "=" * 60)
    print("[Generated Report Preview]:")
    print("=" * 60)
    # 只打印报告的前800字符作为预览
    report = result["report"]
    preview = report[:800] + "\n\n... (Full report saved to file)"
    print(preview)

    print(f"\n  Report file: {result['filepath']}")
    print(f"  Elapsed: {result['elapsed_seconds']:.2f}s")
    print(f"  Quality check: {result['quality']}")


if __name__ == "__main__":
    print("\n===== Brand Insight Multi-Agent System - Framework Mode Demo =====\n")

    demo_agent_info()
    demo_intent_parsing()
    demo_framework_run()

    print("\n===== Framework mode demo completed! =====")
    print("   Connect LLM API Key for data-driven deep insights.")
    print("   Usage: python main.py --api-key sk-xxx\n")
