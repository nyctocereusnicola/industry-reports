#!/usr/bin/env python3
"""
品牌市场洞察多Agent协作系统 — 主入口

用法:
    # 交互模式
    python main.py

    # 单次分析模式
    python main.py "帮我全面分析特斯拉在中国新能源汽车市场的竞争格局"

    # 指定LLM配置
    python main.py --model gpt-4o --api-key sk-xxx
    python main.py --provider deepseek --model deepseek-chat --api-key sk-xxx --api-base https://api.deepseek.com/v1
"""

import argparse
import io
import os
import sys

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件中的配置

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 强制使用UTF-8输出（Windows兼容）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.orchestrator import BrandInsightOrchestrator, create_orchestrator
from src.agent_config import AgentConfigManager


def print_banner():
    """打印系统横幅"""
    print(r"""
  +==================================================+
  |   Brand Insight Multi-Agent System  v1.0         |
  |                                                  |
  |   1 Dispatcher + 5 Specialist Agents             |
  |   Market | Competitor | Consumer | Channel | Trend |
  +==================================================+
""")


def show_agents():
    """显示可用Agent"""
    print("[Available Analysis Dimensions]:\n")
    for key, desc in AgentConfigManager.list_agents().items():
        name = AgentConfigManager.get_agent_name(key)
        print(f"  [{key}] {name}: {desc}")
    print()


def show_help():
    """显示帮助信息"""
    print("""
[Usage Examples]:
  * "帮我全面分析山下有松(Songmont)在中国包袋市场的竞争格局"
  * "特斯拉在东南亚新能源汽车市场的进入评估"
  * "分析完美日记的竞品格局"
  * "瑞幸咖啡的消费者画像分析"
  * "分析小米SU7的渠道策略"
  * "2025年美妆行业趋势分析"

[Quick Commands]:
  /agents  - View available analysis agents
  /help    - Show help
  /exit    - Exit system
""")


def interactive_mode(orchestrator: BrandInsightOrchestrator):
    """交互模式"""
    print_banner()
    show_help()

    while True:
        try:
            user_input = input("\n[Enter analysis query] > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                print("Goodbye!")
                break

            if user_input.lower() in ["/help", "help"]:
                show_help()
                continue

            if user_input.lower() in ["/agents", "agents"]:
                show_agents()
                continue

            # 执行分析
            print()
            result = orchestrator.analyze(user_input, show_progress=True)

            # 显示报告摘要
            print("\n" + "=" * 60)
            print("[Report Summary]")
            print("=" * 60)
            from src.report_generator import ReportGenerator
            summary = ReportGenerator.generate_summary(result["report"])
            print(summary)
            print(f"\nFull report: {result['filepath']}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Analysis failed: {e}")


def single_analysis(orchestrator: BrandInsightOrchestrator, query: str):
    """单次分析模式"""
    print_banner()
    print(f"[Analysis query]: {query}\n")
    result = orchestrator.analyze(query, show_progress=True)
    print("\n" + "=" * 60)
    print("[Full Report]:")
    print("=" * 60)
    print(result["report"])
    print(f"\nReport saved: {result['filepath']}")
    print(f"Elapsed: {result['elapsed_seconds']:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="品牌市场洞察多Agent协作系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py
  python main.py "分析特斯拉品牌的中国市场竞争格局"
  python main.py --model gpt-4o --api-key sk-xxx "分析XX品牌"
        """
    )
    parser.add_argument(
        "query", nargs="?", default=None,
        help="分析需求（不提供则进入交互模式）"
    )
    parser.add_argument(
        "--model", default="gpt-4o",
        help="LLM模型名称 (默认: gpt-4o)"
    )
    parser.add_argument(
        "--provider", default="openai",
        help="LLM提供商 (openai/deepseek/custom)"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API密钥（也可通过环境变量 OPENAI_API_KEY 设置）"
    )
    parser.add_argument(
        "--api-base", default=None,
        help="API端点地址（支持自定义兼容OpenAI的API）"
    )
    parser.add_argument(
        "--config-dir", default="config/agents",
        help="Agent配置文件目录"
    )
    parser.add_argument(
        "--report-dir", default="reports",
        help="报告输出目录"
    )

    args = parser.parse_args()

    # 创建编排器
    orchestrator = create_orchestrator(
        provider=args.provider,
        model=args.model,
        api_key=args.api_key,
        api_base=args.api_base,
    )

    # 更新配置路径
    orchestrator.config_dir = args.config_dir
    orchestrator.report_dir = args.report_dir

    # 运行
    if args.query:
        single_analysis(orchestrator, args.query)
    else:
        interactive_mode(orchestrator)


if __name__ == "__main__":
    main()
