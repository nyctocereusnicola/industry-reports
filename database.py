"""
本地 SQLite 数据库操作

存储从飞书同步过来的报告元数据，支持增删改查。
"""

import sqlite3
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports.db")


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            file_token      TEXT UNIQUE NOT NULL,
            title           TEXT NOT NULL,
            file_type       TEXT DEFAULT '',
            file_ext        TEXT DEFAULT '',
            summary         TEXT DEFAULT '',
            feishu_url      TEXT DEFAULT '',
            size_bytes      INTEGER DEFAULT 0,
            tags            TEXT DEFAULT '',
            category        TEXT DEFAULT '',
            owner_id        TEXT DEFAULT '',
            feishu_created  TEXT DEFAULT '',
            feishu_modified TEXT DEFAULT '',
            view_count      INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            synced_at   TEXT DEFAULT (datetime('now','localtime')),
            file_count  INTEGER DEFAULT 0,
            new_count   INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'success',
            message     TEXT DEFAULT ''
        )
    """)
    # 创建索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_title ON reports(title)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(file_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_active ON reports(is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reports_modified ON reports(feishu_modified)")
    conn.commit()
    conn.close()


def seed_demo_data():
    """如果数据库为空，插入示例数据（方便预览效果）"""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    if count == 0:
        demo_reports = [
            {
                "file_token": "demo_001",
                "title": "2025年中国新能源汽车行业深度洞察报告",
                "file_type": "doc",
                "file_ext": "飞书文档",
                "summary": "本报告全面分析了2025年中国新能源汽车市场格局，涵盖市场规模、竞争态势、技术路线、消费者洞察等核心维度。报告指出，中国新能源汽车渗透率已突破45%，智能化成为差异化竞争的关键。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "新能源汽车,汽车,行业报告",
                "category": "汽车出行",
                "feishu_created": (datetime.now() - timedelta(days=7)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=2)).isoformat(),
            },
            {
                "file_token": "demo_002",
                "title": "2025年AI大模型应用落地趋势报告",
                "file_type": "docx",
                "file_ext": "飞书文档",
                "summary": "深入分析2025年AI大模型从技术探索走向商业落地的关键趋势，包括Agent智能体、多模态应用、行业垂直模型等方向的最新进展与投资机会。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "人工智能,AI,大模型,科技",
                "category": "科技前沿",
                "feishu_created": (datetime.now() - timedelta(days=5)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=1)).isoformat(),
            },
            {
                "file_token": "demo_003",
                "title": "2025Q1中国消费市场复苏报告",
                "file_type": "sheet",
                "file_ext": "飞书表格",
                "summary": "基于2025年第一季度多维度消费数据，系统梳理了消费复苏的结构性特征，包括线上线下的消费趋势变化、下沉市场增长动力、以及新兴消费品牌的崛起路径。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "消费,零售,电商",
                "category": "消费零售",
                "feishu_created": (datetime.now() - timedelta(days=14)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=7)).isoformat(),
            },
            {
                "file_token": "demo_004",
                "title": "全球半导体产业链重构与中国机遇",
                "file_type": "doc",
                "file_ext": "飞书文档",
                "summary": "分析全球半导体产业链在地缘政治影响下的重构趋势，包括芯片设计、制造、封测各环节的格局变化，以及中国半导体产业在其中的战略机遇与挑战。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "半导体,芯片,产业链",
                "category": "科技前沿",
                "feishu_created": (datetime.now() - timedelta(days=10)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=3)).isoformat(),
            },
            {
                "file_token": "demo_005",
                "title": "中国医疗健康产业投融资趋势2025",
                "file_type": "bitable",
                "file_ext": "多维表格",
                "summary": "跟踪2025年医疗健康领域的投融资动态，重点分析创新药、医疗器械、数字医疗、AI制药等细分赛道的资本流向与估值变化。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "医疗,健康,投融资",
                "category": "医疗健康",
                "feishu_created": (datetime.now() - timedelta(days=3)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=1)).isoformat(),
            },
            {
                "file_token": "demo_006",
                "title": "2025跨境电商出海白皮书",
                "file_type": "docx",
                "file_ext": "飞书文档",
                "summary": "聚焦中国品牌出海趋势，覆盖东南亚、拉美、中东等新兴市场的电商生态分析，包括平台选择策略、本地化运营、支付物流基础设施等关键洞察。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "跨境电商,出海,全球化",
                "category": "电商贸易",
                "feishu_created": (datetime.now() - timedelta(days=21)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=5)).isoformat(),
            },
            {
                "file_token": "demo_007",
                "title": "ESG与企业可持续发展报告指南2025",
                "file_type": "doc",
                "file_ext": "飞书文档",
                "summary": "解读国内外ESG最新政策与披露标准，分析头部企业在环境、社会、治理方面的最佳实践，为企业ESG战略规划提供方法论与工具参考。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "ESG,可持续发展,碳中和",
                "category": "宏观经济",
                "feishu_created": (datetime.now() - timedelta(days=30)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=10)).isoformat(),
            },
            {
                "file_token": "demo_008",
                "title": "中国游戏行业市场规模与用户洞察2025",
                "file_type": "doc",
                "file_ext": "飞书文档",
                "summary": "全面解析2025年中国游戏市场，覆盖手游、端游、主机游戏、小游戏等细分市场，包括用户行为分析、付费模式趋势、出海策略等核心内容。",
                "feishu_url": "#",
                "size_bytes": 0,
                "tags": "游戏,文娱,互联网",
                "category": "文娱传媒",
                "feishu_created": (datetime.now() - timedelta(days=12)).isoformat(),
                "feishu_modified": (datetime.now() - timedelta(days=4)).isoformat(),
            },
        ]
        for r in demo_reports:
            conn.execute(
                """INSERT INTO reports
                (file_token, title, file_type, file_ext, summary, feishu_url,
                 size_bytes, tags, category, feishu_created, feishu_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["file_token"], r["title"], r["file_type"], r["file_ext"],
                    r["summary"], r["feishu_url"], r["size_bytes"],
                    r["tags"], r["category"], r["feishu_created"], r["feishu_modified"],
                ),
            )
        conn.commit()
    conn.close()


# ===================== 数据库操作函数 =====================

def count_reports(search: str = "", category: str = "", file_type: str = "") -> int:
    """统计报告数量"""
    conn = get_connection()
    sql = "SELECT COUNT(*) FROM reports WHERE is_active = 1"
    params = []
    if search:
        sql += " AND (title LIKE ? OR summary LIKE ? OR tags LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if category:
        sql += " AND category = ?"
        params.append(category)
    if file_type:
        sql += " AND file_type = ?"
        params.append(file_type)
    result = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return result


def list_reports(
    search: str = "",
    category: str = "",
    file_type: str = "",
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "feishu_modified",
    sort_order: str = "DESC",
) -> tuple[list[dict], int]:
    """分页查询报告列表，返回 (报告列表, 总数)"""
    conn = get_connection()
    allowed_sorts = ["feishu_modified", "feishu_created", "title", "view_count"]
    if sort_by not in allowed_sorts:
        sort_by = "feishu_modified"
    if sort_order.upper() not in ("ASC", "DESC"):
        sort_order = "DESC"

    where = "WHERE is_active = 1"
    params = []

    if search:
        where += " AND (title LIKE ? OR summary LIKE ? OR tags LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if category:
        where += " AND category = ?"
        params.append(category)
    if file_type:
        where += " AND file_type = ?"
        params.append(file_type)

    # 总数
    total = conn.execute(f"SELECT COUNT(*) FROM reports {where}", params).fetchone()[0]

    # 分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT * FROM reports {where}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(sql, params + [page_size, offset]).fetchall()
    reports = [dict(row) for row in rows]
    conn.close()
    return reports, total


def get_report(report_id: int) -> Optional[dict]:
    """获取单个报告详情"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_report(file_token: str, data: dict) -> bool:
    """插入或更新报告（按 file_token 去重）"""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id, feishu_modified FROM reports WHERE file_token = ?", (file_token,)
    ).fetchone()

    if existing:
        # 如果更新时间没变则跳过
        if existing["feishu_modified"] == data.get("feishu_modified", ""):
            conn.close()
            return False
        conn.execute(
            """UPDATE reports SET
                title=?, file_type=?, file_ext=?, summary=?, feishu_url=?,
                size_bytes=?, owner_id=?, feishu_created=?, feishu_modified=?,
                updated_at=datetime('now','localtime')
            WHERE file_token=?""",
            (
                data["title"], data["file_type"], data["file_ext"],
                data.get("summary", ""), data["feishu_url"],
                data.get("size_bytes", 0), data.get("owner_id", ""),
                data.get("feishu_created", ""), data.get("feishu_modified", ""),
                file_token,
            ),
        )
        conn.commit()
        conn.close()
        return True
    else:
        conn.execute(
            """INSERT INTO reports
            (file_token, title, file_type, file_ext, summary, feishu_url,
             size_bytes, owner_id, feishu_created, feishu_modified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                file_token, data["title"], data["file_type"], data["file_ext"],
                data.get("summary", ""), data["feishu_url"],
                data.get("size_bytes", 0), data.get("owner_id", ""),
                data.get("feishu_created", ""), data.get("feishu_modified", ""),
            ),
        )
        conn.commit()
        conn.close()
        return True


def update_report(report_id: int, data: dict):
    """手动更新报告信息（summary, tags, category）"""
    conn = get_connection()
    fields = []
    values = []
    for key in ["summary", "tags", "category"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return
    fields.append("updated_at = datetime('now','localtime')")
    values.append(report_id)
    conn.execute(f"UPDATE reports SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def increment_view(report_id: int):
    """增加查看次数"""
    conn = get_connection()
    conn.execute("UPDATE reports SET view_count = view_count + 1 WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()


def log_sync(file_count: int, new_count: int, status: str = "success", message: str = ""):
    """记录同步日志"""
    conn = get_connection()
    conn.execute(
        "INSERT INTO sync_log (file_count, new_count, status, message) VALUES (?, ?, ?, ?)",
        (file_count, new_count, status, message),
    )
    conn.commit()
    conn.close()


def get_last_sync() -> Optional[dict]:
    """获取最近一次同步记录"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_stats() -> dict:
    """获取统计信息"""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM reports WHERE is_active=1").fetchone()[0]
    categories = conn.execute(
        "SELECT category, COUNT(*) as cnt FROM reports WHERE is_active=1 AND category!='' GROUP BY category ORDER BY cnt DESC"
    ).fetchall()
    file_types = conn.execute(
        "SELECT file_type, COUNT(*) as cnt FROM reports WHERE is_active=1 GROUP BY file_type ORDER BY cnt DESC"
    ).fetchall()
    last_sync = conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return {
        "total": total,
        "categories": [dict(c) for c in categories],
        "file_types": [dict(f) for f in file_types],
        "last_sync": dict(last_sync) if last_sync else None,
    }
