"""
飞书报告同步脚本（GitHub Actions 专用）

功能：
- 调用飞书 API 获取指定文件夹下的文件列表
- 生成 docs/data/reports.json 供静态网站使用
- 支持增量更新（按 file_token 去重，按 modified_time 判断更新）

环境变量：
    FEISHU_APP_ID        飞书应用 App ID
    FEISHU_APP_SECRET    飞书应用 App Secret
    FEISHU_FOLDER_TOKEN  要同步的文件夹 Token
"""

import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx

# ─── 静态数据文件路径 ─────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "docs" / "data"
REPORTS_FILE = DATA_DIR / "reports.json"
SYNC_LOG_FILE = DATA_DIR / "sync_log.json"

# ─── 飞书 API 客户端 ─────────────────────────────────
class FeishuClient:
    """飞书开放平台 API 客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expire_at: float = 0

    def _get_access_token(self) -> str:
        """获取 tenant_access_token（同步版本，带缓存）"""
        if self._access_token and time.time() < self._token_expire_at - 60:
            return self._access_token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 access_token 失败: {data.get('msg', data)}")

        self._access_token = data["tenant_access_token"]
        self._token_expire_at = time.time() + data.get("expire", 7200)
        return self._access_token

    def list_folder_files(
        self, folder_token: str, page_size: int = 50, page_token: Optional[str] = None
    ) -> dict:
        """获取文件夹下的文件列表（单页）"""
        token = self._get_access_token()
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        resp = httpx.get(
            f"{self.BASE_URL}/drive/v1/folders/{folder_token}/files",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取文件列表失败: {data.get('msg', data)}")
        return data.get("data", {})

    def list_all_files(self, folder_token: str) -> list:
        """获取文件夹下所有文件（自动处理分页）"""
        all_files = []
        page_token = None
        while True:
            result = self.list_folder_files(folder_token, page_size=50, page_token=page_token)
            files = result.get("files", [])
            all_files.extend(files)
            if not result.get("has_more"):
                break
            page_token = result.get("page_token")
        return all_files

    @staticmethod
    def build_file_url(file_token: str, file_type: str) -> str:
        """根据文件类型构建飞书 Web 访问链接"""
        type_url_map = {
            "doc": f"https://bytedance.feishu.cn/docx/{file_token}",
            "docx": f"https://bytedance.feishu.cn/docx/{file_token}",
            "sheet": f"https://bytedance.feishu.cn/sheets/{file_token}",
            "bitable": f"https://bytedance.feishu.cn/base/{file_token}",
            "slides": f"https://bytedance.feishu.cn/slides/{file_token}",
            "mindnote": f"https://bytedance.feishu.cn/mindnotes/{file_token}",
            "folder": f"https://bytedance.feishu.cn/drive/folder/{file_token}",
        }
        return type_url_map.get(
            file_type,
            f"https://bytedance.feishu.cn/drive/home/?mode=detail&file_token={file_token}",
        )

    @staticmethod
    def get_file_extension(file_type: str, name: str) -> str:
        """获取文件扩展名/类型标签"""
        ext_map = {
            "doc": "飞书文档",
            "docx": "飞书文档",
            "sheet": "飞书表格",
            "bitable": "多维表格",
            "slides": "幻灯片",
            "mindnote": "思维导图",
            "folder": "文件夹",
        }
        if file_type in ext_map:
            return ext_map[file_type]
        if "." in name:
            ext = name.rsplit(".", 1)[-1].upper()
            return ext if len(ext) <= 8 else "文件"
        return "文件"


# ─── 示例数据 ────────────────────────────────────────
def get_demo_reports() -> list:
    """返回预置的示例报告数据"""
    now = datetime.now(timezone.utc)
    return [
        {
            "file_token": "demo_001",
            "title": "2025年中国新能源汽车行业深度洞察报告",
            "file_type": "doc",
            "file_ext": "飞书文档",
            "summary": "全面分析了2025年中国新能源汽车市场格局，涵盖市场规模、竞争态势、技术路线、消费者洞察等核心维度。报告指出，中国新能源汽车渗透率已突破45%，智能化成为差异化竞争的关键。",
            "feishu_url": "#",
            "tags": "新能源汽车,汽车,行业报告",
            "category": "汽车出行",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_002",
            "title": "2025年AI大模型应用落地趋势报告",
            "file_type": "docx",
            "file_ext": "飞书文档",
            "summary": "深入分析2025年AI大模型从技术探索走向商业落地的关键趋势，包括Agent智能体、多模态应用、行业垂直模型等方向的最新进展与投资机会。",
            "feishu_url": "#",
            "tags": "人工智能,AI,大模型,科技",
            "category": "科技前沿",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_003",
            "title": "2025Q1中国消费市场复苏报告",
            "file_type": "sheet",
            "file_ext": "飞书表格",
            "summary": "基于2025年第一季度多维度消费数据，系统梳理消费复苏的结构性特征，包括线上线下消费趋势变化、下沉市场增长动力及新兴消费品牌崛起路径。",
            "feishu_url": "#",
            "tags": "消费,零售,电商",
            "category": "消费零售",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_004",
            "title": "全球半导体产业链重构与中国机遇",
            "file_type": "doc",
            "file_ext": "飞书文档",
            "summary": "分析全球半导体产业链在地缘政治影响下的重构趋势，包括芯片设计、制造、封测各环节的格局变化，以及中国半导体产业的战略机遇与挑战。",
            "feishu_url": "#",
            "tags": "半导体,芯片,产业链",
            "category": "科技前沿",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_005",
            "title": "中国医疗健康产业投融资趋势2025",
            "file_type": "bitable",
            "file_ext": "多维表格",
            "summary": "跟踪2025年医疗健康领域的投融资动态，重点分析创新药、医疗器械、数字医疗、AI制药等细分赛道的资本流向与估值变化。",
            "feishu_url": "#",
            "tags": "医疗,健康,投融资",
            "category": "医疗健康",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_006",
            "title": "2025跨境电商出海白皮书",
            "file_type": "docx",
            "file_ext": "飞书文档",
            "summary": "聚焦中国品牌出海趋势，覆盖东南亚、拉美、中东等新兴市场的电商生态分析，包括平台选择策略、本地化运营、支付物流基础设施等关键洞察。",
            "feishu_url": "#",
            "tags": "跨境电商,出海,全球化",
            "category": "电商贸易",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_007",
            "title": "ESG与企业可持续发展报告指南2025",
            "file_type": "doc",
            "file_ext": "飞书文档",
            "summary": "解读国内外ESG最新政策与披露标准，分析头部企业在环境、社会、治理方面的最佳实践，为企业ESG战略规划提供方法论与工具参考。",
            "feishu_url": "#",
            "tags": "ESG,可持续发展,碳中和",
            "category": "宏观经济",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_008",
            "title": "中国游戏行业市场规模与用户洞察2025",
            "file_type": "doc",
            "file_ext": "飞书文档",
            "summary": "全面解析2025年中国游戏市场，覆盖手游、端游、主机游戏、小游戏等细分市场，包括用户行为分析、付费模式趋势、出海策略等核心内容。",
            "feishu_url": "#",
            "tags": "游戏,文娱,互联网",
            "category": "文娱传媒",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    ]


# ─── 同步逻辑 ────────────────────────────────────────
def sync_feishu_to_json() -> dict:
    """
    从飞书同步文件列表，合并到现有 JSON 数据中

    返回:
        {"status": "success"|"error", "file_count": int, "new_count": int, "message": str}
    """
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    folder_token = os.getenv("FEISHU_FOLDER_TOKEN", "")

    # 加载已有数据
    existing_reports = []
    existing_tokens = set()
    if REPORTS_FILE.exists():
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_reports = data.get("reports", [])
            # 去除非飞书同步的数据（demo_ 前缀）
            existing_reports = [r for r in existing_reports if not r.get("file_token", "").startswith("demo_")]
            existing_tokens = {r["file_token"] for r in existing_reports}
        except Exception:
            existing_reports = []
            existing_tokens = set()

    # 如果没有配置飞书凭证，只写入 demo 数据
    if not app_id or not app_secret or not folder_token:
        print("[INFO] 未配置飞书凭证，使用示例数据")
        return {
            "status": "skipped",
            "reason": "未配置飞书凭证",
            "file_count": 0,
            "new_count": 0,
        }

    try:
        client = FeishuClient(app_id, app_secret)
        files = client.list_all_files(folder_token)

        new_count = 0
        update_count = 0

        for f in files:
            token = f.get("token", "")
            file_type = f.get("type", "file")
            name = f.get("name", "未命名")

            report_data = {
                "file_token": token,
                "title": name,
                "file_type": file_type,
                "file_ext": FeishuClient.get_file_extension(file_type, name),
                "summary": "",
                "feishu_url": f.get("url") or FeishuClient.build_file_url(token, file_type),
                "tags": "",
                "category": "",
                "view_count": 0,
                "feishu_modified": f.get("modified_time", ""),
            }

            if token in existing_tokens:
                # 更新
                for i, r in enumerate(existing_reports):
                    if r["file_token"] == token:
                        # 保留已有的 summary/tags/category（手动编辑的）
                        report_data["summary"] = r.get("summary", "")
                        report_data["tags"] = r.get("tags", "")
                        report_data["category"] = r.get("category", "")
                        report_data["view_count"] = r.get("view_count", 0)
                        existing_reports[i] = report_data
                        break
                update_count += 1
            else:
                existing_reports.append(report_data)
                existing_tokens.add(token)
                new_count += 1

        print(f"[OK] 同步完成：共 {len(files)} 个文件，新增 {new_count}，更新 {update_count}")

        return {
            "status": "success",
            "file_count": len(files),
            "new_count": new_count,
            "update_count": update_count,
        }

    except Exception as e:
        print(f"[ERROR] 同步失败: {e}")
        return {"status": "error", "reason": str(e)}


def write_reports_json(feishu_reports: list, sync_result: dict):
    """生成最终的 reports.json（demo 数据 + 飞书数据）"""
    # 加载 demo 数据
    demo_reports = get_demo_reports()

    # 合并：demo 数据在前，飞书数据在后
    all_reports = demo_reports + feishu_reports

    # 按修改时间排序
    all_reports.sort(key=lambda r: r.get("feishu_modified", ""), reverse=True)

    # 计算统计
    categories = {}
    for r in all_reports:
        cat = r.get("category", "未分类") or "未分类"
        categories[cat] = categories.get(cat, 0) + 1

    output = {
        "reports": all_reports,
        "stats": {
            "total": len(all_reports),
            "categories": [{"name": k, "count": v} for k, v in sorted(categories.items(), key=lambda x: -x[1])],
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 写入同步日志
    log_entry = {
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **sync_result,
    }
    try:
        existing_logs = []
        if SYNC_LOG_FILE.exists():
            with open(SYNC_LOG_FILE, "r", encoding="utf-8") as f:
                existing_logs = json.load(f)
        existing_logs.insert(0, log_entry)
        existing_logs = existing_logs[:50]  # 只保留最近 50 条
        with open(SYNC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 写入同步日志失败: {e}")

    print(f"[OK] 已生成 {REPORTS_FILE}，共 {len(all_reports)} 条报告")


# ─── 主入口 ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  行业报告集合站 - 飞书同步脚本")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 同步飞书数据
    sync_result = sync_feishu_to_json()

    # 获取飞书报告列表
    feishu_reports = []
    if REPORTS_FILE.exists():
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            feishu_reports = [r for r in data.get("reports", []) if not r.get("file_token", "").startswith("demo_")]
        except Exception:
            pass

    # 如果是同步成功，需要重新加载
    if sync_result["status"] == "success":
        feishu_reports = []
        if REPORTS_FILE.exists():
            try:
                with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                feishu_reports = [r for r in data.get("reports", []) if not r.get("file_token", "").startswith("demo_")]
            except Exception:
                pass

    # 写入最终 JSON
    write_reports_json(feishu_reports, sync_result)

    print("=" * 60)
    print("  完成！")
    print("=" * 60)
