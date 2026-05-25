"""
品牌洞察多Agent协作系统 — 核心编排引擎

架构: 1个主调度Agent + 5个专业子Agent
流程: 意图解析 → 任务分发 → 并行调度 → 报告汇总 → 质量检查
"""

import asyncio
import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.agent_config import AgentConfigManager
from src.intent_parser import AnalysisParams, IntentParser, TaskDispatcher, TaskPlan
from src.report_generator import ReportGenerator


# LLM客户端类型定义
LLMClient = Callable[[str, str], str]


class BrandInsightOrchestrator:
    """品牌洞察多Agent协作编排器"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config_dir: str = "config/agents",
        report_dir: str = "reports",
    ):
        """
        初始化编排器

        Args:
            llm_client: LLM调用函数，签名: fn(system_prompt: str, user_prompt: str) -> str
            config_dir: Agent配置文件目录
            report_dir: 报告输出目录
        """
        self.llm_client = llm_client
        self.config_dir = config_dir
        self.report_dir = report_dir

        # 确保Agent提示词与用户意图能正确结合
        self.agent_prompts: Dict[str, str] = {}
        for agent_key in ["market", "competitor", "consumer", "channel", "trend"]:
            prompt = AgentConfigManager.load_prompt(agent_key, config_dir)
            if prompt:
                self.agent_prompts[agent_key] = prompt

    def analyze(self, user_input: str, show_progress: bool = True) -> Dict[str, Any]:
        """
        执行品牌洞察分析（同步版本）

        Args:
            user_input: 用户输入的分析需求
            show_progress: 是否显示进度

        Returns:
            包含报告和元数据的字典
        """
        return asyncio.run(self.analyze_async(user_input, show_progress))

    async def analyze_async(
        self, user_input: str, show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        执行品牌洞察分析（异步版本）

        工作流程:
        1. 意图解析 → 提取品牌、品类、市场、分析类型
        2. 任务分发 → 决定调用哪些子Agent
        3. 并行调度 → 同时调用所有需要的子Agent
        4. 报告汇总 → 整合各维度分析结果
        5. 质量检查 → 验证报告完整性
        """
        start_time = datetime.now()

        # Step 1: 意图解析
        if show_progress:
            print("[Step 1/5] 意图解析中...")
        params = IntentParser.parse(user_input, self.llm_client)

        # Step 2: 任务分发
        if show_progress:
            print("[Step 2/5] 任务分发中...")
        task_plan = TaskDispatcher.dispatch(params)
        if show_progress:
            print(f"   品牌: {params.brand or '待识别'}")
            print(f"   品类: {params.category or '待识别'}")
            print(f"   市场: {params.market}")
            print(f"   类型: {params.task_type}")
            print(f"   调度Agent: {task_plan.agents_to_call}")

        # Step 3: 并行调度子Agent
        if show_progress:
            print("[Step 3/5] 并行调用子Agent分析中...")

        agent_results = await self._dispatch_agents(task_plan, show_progress)

        # Step 4: 报告汇总
        if show_progress:
            print("[Step 4/5] 整合生成报告中...")

        report = ReportGenerator.generate(
            brand=params.brand or "目标品牌",
            category=params.category or "未指定品类",
            market=params.market,
            task_type=params.task_type,
            agent_results=agent_results,
            llm_client=self.llm_client,
        )

        # Step 5: 质量检查
        if show_progress:
            print("[Step 5/5] 质量检查中...")
        quality = ReportGenerator.quality_check(report)

        # 保存报告
        filepath = ReportGenerator.save_report(
            report, params.brand or "unknown", self.report_dir
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if show_progress:
            print(f"\n===== 分析完成! 耗时 {elapsed:.1f}秒 =====")
            print(f"   报告已保存: {filepath}")
            qual_status = "[PASS] 通过" if quality.get("passed") else "[WARN] 部分未通过"
            print(f"   质量检查: {qual_status}")
            for key, val in quality.items():
                if key != "passed":
                    status = "[PASS]" if val else "[FAIL]"
                    print(f"     {status} {key}")

        return {
            "report": report,
            "filepath": filepath,
            "params": params,
            "task_plan": task_plan.to_dict(),
            "quality": quality,
            "elapsed_seconds": elapsed,
            "generated_at": datetime.now().isoformat(),
        }

    async def _dispatch_agents(
        self, task_plan: TaskPlan, show_progress: bool = True
    ) -> Dict[str, str]:
        """
        并行调度各子Agent执行分析任务

        如果配置了LLM客户端，使用LLM进行分析；
        否则返回基于配置的框架性分析结果。
        """
        params = task_plan.params

        # 构建统一的任务指令
        task_instruction = self._build_task_instruction(params)

        # 创建异步任务列表
        tasks = []
        for agent_key in task_plan.agents_to_call:
            tasks.append(
                self._run_agent(agent_key, task_instruction, show_progress)
            )

        # 并行执行所有Agent
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        agent_results = {}
        for agent_key, result in zip(task_plan.agents_to_call, results):
            if isinstance(result, Exception):
                agent_results[agent_key] = f"## {AgentConfigManager.get_agent_name(agent_key)} 分析\n\n> [WARN] 分析异常: {str(result)}"
                if show_progress:
                    print(f"   [FAIL] {AgentConfigManager.get_agent_name(agent_key)} 分析失败")
            else:
                agent_results[agent_key] = result

        return agent_results

    async def _run_agent(
        self, agent_key: str, task_instruction: str, show_progress: bool
    ) -> str:
        """运行单个Agent分析"""
        agent_name = AgentConfigManager.get_agent_name(agent_key)

        if show_progress:
            print(f"   -> {agent_name} 分析中...")

        if self.llm_client:
            # 使用LLM进行分析
            system_prompt = self.agent_prompts.get(
                agent_key,
                self._get_fallback_prompt(agent_key)
            )
            try:
                result = self.llm_client(system_prompt, task_instruction)
                if show_progress:
                    print(f"   [OK] {agent_name} 完成")
                return result
            except Exception as e:
                raise Exception(f"{agent_name}: {str(e)}")
        else:
            # 无LLM时返回框架性提示
            return self._generate_framework_response(agent_key, task_instruction)

    def _build_task_instruction(self, params: AnalysisParams) -> str:
        """构建统一的任务指令"""
        brand = params.brand or "目标品牌"
        category = params.category or "该品类"
        market = params.market
        depth = "深度" if params.scope == "deep" else "标准"

        return (
            f"请对【{brand}】在【{market}】的【{category}】领域，"
            f"进行专业维度的分析。\n"
            f"分析深度：{depth}\n"
            f"要求：按照标准模板输出，每个数据点标注来源和置信度，"
            f"确保结论有数据支撑。"
        )

    def _get_fallback_prompt(self, agent_key: str) -> str:
        """获取降级提示词"""
        prompts = {
            "market": "你是一位消费品市场分析师，请分析目标品牌所在品类的市场规模、增长趋势和价格带格局。",
            "competitor": "你是一位竞品分析专家，请识别目标品牌的核心竞品，运用4P和SWOT框架进行分析。",
            "consumer": "你是一位消费者研究专家，请描绘目标品牌的消费者画像和AIPL决策旅程。",
            "channel": "你是一位全渠道策略分析师，请分析目标品牌的线上线下渠道布局和ROI。",
            "trend": "你是一位趋势研究专家，请运用PEST框架分析宏观趋势和品类创新机会。",
        }
        return prompts.get(agent_key, "请进行专业的品牌洞察分析。")

    def _generate_framework_response(
        self, agent_key: str, task_instruction: str
    ) -> str:
        """生成框架性响应（无LLM时使用）"""
        agent_name = AgentConfigManager.get_agent_name(agent_key)
        description = AgentConfigManager.get_agent_description(agent_key)

        # 从提示词中提取输出格式
        prompt = self.agent_prompts.get(agent_key, "")
        output_format = ""
        if prompt and "## 输出格式" in prompt:
            format_start = prompt.index("## 输出格式") + len("## 输出格式")
            format_section = prompt[format_start:]
            if "## 约束" in format_section:
                format_end = format_section.index("## 约束")
                output_format = format_section[:format_end].strip()
            else:
                output_format = format_section.strip()
            # 清理markdown代码块标记
            output_format = output_format.replace("```markdown", "").replace("```", "").strip()

        return f"""## {agent_name} — {description}

> [WARN] Framework mode - connect LLM for data-driven insights.

{output_format or 'Please refer to agent config for standard output format.'}

*Note: This analysis is based on structural framework. Connect LLM for data-driven deep insights.*
"""


def create_orchestrator(
    llm_client: Optional[LLMClient] = None,
    provider: str = "openai",
    model: str = "gpt-4o",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
) -> BrandInsightOrchestrator:
    """
    快速创建编排器实例

    Args:
        llm_client: 自定义LLM调用函数
        provider: LLM提供商 (openai / deepseek / custom)
        model: 模型名称
        api_key: API密钥
        api_base: API端点地址

    Returns:
        配置好的编排器
    """
    if llm_client:
        return BrandInsightOrchestrator(llm_client=llm_client)

    # 尝试从环境变量获取配置
    api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        print("[WARN] No API key detected, running in framework mode (no data insights)")
        return BrandInsightOrchestrator()

    # 创建默认的LLM客户端
    if provider == "openai" or provider == "custom":
        api_base = api_base or os.getenv(
            "LLM_API_BASE", "https://api.openai.com/v1"
        )

        def openai_client(system: str, user: str) -> str:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=api_base)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content

        return BrandInsightOrchestrator(llm_client=openai_client)

    return BrandInsightOrchestrator()
