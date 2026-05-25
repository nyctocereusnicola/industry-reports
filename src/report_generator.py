"""
报告生成器
负责将各Agent分析结果整合为结构化专业报告
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ReportGenerator:
    """报告生成器 — 整合各维度分析结果，输出专业报告"""

    REPORT_SECTIONS = [
        ("Executive Summary", "executive_summary"),
        ("市场全景分析", "market"),
        ("竞品格局分析", "competitor"),
        ("消费者深度洞察", "consumer"),
        ("渠道策略分析", "channel"),
        ("趋势与机会研判", "trend"),
    ]

    QUALITY_CHECKS = {
        "min_tables": 3,
        "min_frameworks": 2,
        "min_actionable_insights": 3,
        "require_data_sourcing": True,
    }

    @classmethod
    def load_template(cls, template_path: str = "templates/full_report.md") -> str:
        """加载报告模板"""
        return Path(template_path).read_text(encoding="utf-8")

    @classmethod
    def generate(
        cls,
        brand: str,
        category: str,
        market: str,
        task_type: str,
        agent_results: Dict[str, str],
        llm_client=None,
    ) -> str:
        """
        生成完整报告。
        优先使用LLM进行智能整合，降级使用模板拼接。
        """
        if llm_client:
            try:
                return cls._llm_integrate(
                    brand, category, market, task_type,
                    agent_results, llm_client
                )
            except Exception:
                pass
        return cls._template_integrate(brand, category, market, agent_results)

    @classmethod
    def _llm_integrate(
        cls,
        brand: str,
        category: str,
        market: str,
        task_type: str,
        agent_results: Dict[str, str],
        llm_client,
    ) -> str:
        """使用LLM智能整合报告"""
        sections_text = "\n\n---\n\n".join([
            f"## {title}\n{content}"
            for title, content in agent_results.items()
        ])

        quality_rules = cls._get_quality_rules()

        system_prompt = f"""你是资深品牌策略报告撰写专家。请将以下各维度的分析结果整合为一份专业的品牌洞察报告。

{quality_rules}

要求：
1. Executive Summary 300字以内，核心结论为先
2. 数据必须标注来源和置信度
3. 至少生成3张结构化表格
4. 应用至少2个分析框架
5. 战略建议部分必须具体可执行（含产品/价格/渠道/推广层面）
6. 使用markdown格式，结构清晰
"""

        user_prompt = f"""# 报告整合任务

品牌: {brand}
品类: {category}
市场: {market}
分析类型: {task_type}
生成日期: {datetime.now().strftime('%Y-%m-%d')}

## 各维度分析结果

{sections_text}

请整合输出完整的品牌洞察报告。
"""
        return llm_client(system=system_prompt, user=user_prompt)

    @classmethod
    def _template_integrate(
        cls,
        brand: str,
        category: str,
        market: str,
        agent_results: Dict[str, str],
    ) -> str:
        """基于模板拼接报告"""
        report = f"""# {brand} 品牌深度洞察报告

> **分析日期**: {datetime.now().strftime('%Y-%m-%d')}
> **品类**: {category}
> **目标市场**: {market}
> **数据截止**: {datetime.now().strftime('%Y-%m-%d')}

---

"""
        # 添加各维度分析结果
        section_titles = {
            "executive_summary": "Executive Summary",
            "market": "## 1. 市场全景分析",
            "competitor": "## 2. 竞品格局分析",
            "consumer": "## 3. 消费者深度洞察",
            "channel": "## 4. 渠道策略分析",
            "trend": "## 5. 趋势与机会研判",
        }

        for key, title in section_titles.items():
            if key in agent_results:
                report += f"\n{title}\n\n{agent_results[key]}\n\n---\n"

        report += f"""
## 6. 战略建议

> 综合以上分析维度，建议关注以下关键行动方向。详细策略需进一步人工研判后制定。

1. **产品策略**: 关注品类创新方向，结合竞品差异化机会
2. **价格策略**: 参考价格带格局，制定竞争力定价
3. **渠道策略**: 优化线上线下的渠道协同
4. **推广策略**: 基于消费者内容偏好精准触达

---

## 附录

### 分析框架
本报告运用了 TAM/SAM/SOM、4P、SWOT、AIPL、PEST 等分析框架。

### 数据来源
报告数据来源于公开信息、行业报告及AI分析模型推算。

### 免责声明
本报告基于公开信息和分析模型生成，仅供参考决策使用。

---

*报告由 Brand Insight AI Agent 自动生成 | v1.0*
"""
        return report

    @classmethod
    def _get_quality_rules(cls) -> str:
        """获取质量检查规则"""
        return f"""## 质量门禁规则
- 每个数据点需标注来源
- 至少包含 {cls.QUALITY_CHECKS['min_tables']} 张结构化表格
- 至少应用 {cls.QUALITY_CHECKS['min_frameworks']} 个分析框架（TAM/SAM/SOM, 4P, SWOT, AIPL, PEST等）
- 至少 {cls.QUALITY_CHECKS['min_actionable_insights']} 条具体可执行的战略建议
- 不确定数据标注 [待验证]
- 关键指标标注英文术语 (CAGR, TAM, GMV, YoY, ARPU 等)
- 置信度分级：[高]多源交叉验证 | [中]单一来源 | [低/待验证]推测"""

    @classmethod
    def quality_check(cls, report: str) -> Dict[str, bool]:
        """对报告进行质量检查"""
        checks = {
            "has_tables": report.count("|---") >= cls.QUALITY_CHECKS["min_tables"],
            "has_data_sourcing": "来源" in report or "source" in report.lower(),
            "has_actionable_insights": any(
                kw in report
                for kw in ["战略建议", "建议", "推荐", "优化"]
            ),
            "has_markdown_structure": report.count("##") >= 3,
        }
        checks["passed"] = all(checks.values())
        return checks

    @classmethod
    def save_report(cls, report: str, brand: str, output_dir: str = "reports") -> str:
        """保存报告到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{brand}_{date_str}_洞察报告.md"
        filepath = output_path / filename
        filepath.write_text(report, encoding="utf-8")
        return str(filepath)

    @classmethod
    def generate_summary(cls, report: str, max_chars: int = 500) -> str:
        """生成报告摘要（用于微信推送等场景）"""
        # 提取 Executive Summary 段落
        lines = report.split("\n")
        summary_lines = []
        in_summary = False
        for line in lines:
            if "Executive Summary" in line:
                in_summary = True
                continue
            if in_summary:
                if line.startswith("---") or line.startswith("##"):
                    break
                if line.strip():
                    summary_lines.append(line.strip())
        summary = " ".join(summary_lines)
        if len(summary) > max_chars:
            summary = summary[:max_chars-3] + "..."
        return summary or report[:max_chars] + "..."
