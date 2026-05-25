"""
行业报告集合站 — FastAPI Web 服务

启动方式:
    python web_server.py

功能:
    - 报告搜索与浏览
    - 飞书文件夹同步
    - 统计概览
    - 定时自动同步
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

# 初始化数据库
from database import (
    init_db, seed_demo_data, list_reports, get_report,
    update_report, increment_view, get_stats, get_last_sync,
    count_reports,
)
from feishu_sync import FeishuClient

# ─── 配置 ─────────────────────────────────────────────
FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_FOLDER_TOKEN = os.getenv("FEISHU_FOLDER_TOKEN", "")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL_MINUTES", "30"))
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─── 同步服务 ─────────────────────────────────────────
class SyncService:
    """飞书同步服务（支持后台定时 + 手动触发）"""

    def __init__(self):
        self.feishu = None
        self._running = False
        self.folder_token = FEISHU_FOLDER_TOKEN
        if FEISHU_APP_ID and FEISHU_APP_SECRET:
            self.feishu = FeishuClient(FEISHU_APP_ID, FEISHU_APP_SECRET)

    async def run_sync(self) -> dict:
        """执行一次全量同步"""
        from database import upsert_report, log_sync

        if not self.feishu:
            return {"status": "skipped", "reason": "未配置飞书凭证，使用示例数据"}

        if not self.folder_token:
            return {"status": "error", "reason": "未配置 FEISHU_FOLDER_TOKEN"}

        try:
            logger.info("🔄 开始同步飞书文件夹...")
            files = await self.feishu.list_all_files(self.folder_token)
            new_count = 0
            update_count = 0

            from database import get_connection

            for f in files:
                token = f.get("token", "")
                file_type = f.get("type", "file")
                name = f.get("name", "未命名")

                data = {
                    "title": name,
                    "file_type": file_type,
                    "file_ext": FeishuClient.get_file_extension(file_type, name),
                    "feishu_url": f.get("url") or FeishuClient.build_file_url(token, file_type),
                    "size_bytes": f.get("size", 0),
                    "owner_id": f.get("owner_id", ""),
                    "feishu_created": f.get("created_time", ""),
                    "feishu_modified": f.get("modified_time", ""),
                }

                # 判断新增还是更新
                conn = get_connection()
                existing = conn.execute(
                    "SELECT id FROM reports WHERE file_token=?", (token,)
                ).fetchone()
                conn.close()

                upsert_report(token, data)
                if existing:
                    update_count += 1
                else:
                    new_count += 1

            # 精确计数
            conn = get_connection()
            total_in_db = conn.execute(
                "SELECT COUNT(*) FROM reports WHERE is_active=1 AND file_token NOT LIKE 'demo_%'"
            ).fetchone()[0]
            conn.close()

            log_sync(len(files), new_count, "success",
                     f"同步完成：{len(files)} 个文件，新增 {new_count} 个")
            logger.info(f"✅ 同步完成：共 {len(files)} 个文件")

            return {
                "status": "success",
                "file_count": len(files),
                "new_count": new_count,
                "total_in_db": total_in_db,
            }
        except Exception as e:
            logger.error(f"❌ 同步失败: {e}")
            log_sync(0, 0, "error", str(e))
            return {"status": "error", "reason": str(e)}

    async def background_loop(self):
        """后台定时同步循环"""
        while self._running:
            await asyncio.sleep(SYNC_INTERVAL * 60)
            if self._running:
                await self.run_sync()

    def start_background(self):
        self._running = True
        asyncio.create_task(self.background_loop())

    def stop(self):
        self._running = False


sync_service = SyncService()


# ─── 应用生命周期 ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的初始化与清理"""
    logger.info("🚀 初始化数据库...")
    init_db()
    seed_demo_data()

    # 启动后台同步（如果配置了飞书凭证）
    if FEISHU_APP_ID and FEISHU_FOLDER_TOKEN:
        logger.info(f"🔄 启动飞书同步（间隔 {SYNC_INTERVAL} 分钟）...")
        sync_service.start_background()
        # 首次立即同步
        asyncio.create_task(sync_service.run_sync())
    else:
        logger.info("ℹ️ 未配置飞书凭证，使用示例数据运行。请编辑 .env 文件配置。")

    yield
    sync_service.stop()
    logger.info("👋 服务已停止")


# ─── FastAPI 应用 ────────────────────────────────────
app = FastAPI(
    title="行业报告集合站",
    description="搜索、浏览行业报告，一键跳转飞书查看源文件",
    version="1.0.0",
    lifespan=lifespan,
)

# 静态文件
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── 页面路由 ─────────────────────────────────────────
@app.get("/")
async def index():
    """首页"""
    return FileResponse("static/index.html")


# ─── API 路由 ─────────────────────────────────────────
@app.get("/api/reports")
async def api_list_reports(
    search: str = Query("", description="搜索关键词"),
    category: str = Query("", description="分类筛选"),
    file_type: str = Query("", description="文件类型筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("feishu_modified", description="排序字段"),
    sort_order: str = Query("DESC", description="排序方向"),
):
    """获取报告列表（支持搜索、筛选、分页）"""
    reports, total = list_reports(
        search=search,
        category=category,
        file_type=file_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "data": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@app.get("/api/reports/{report_id}")
async def api_get_report(report_id: int):
    """获取单个报告详情"""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    increment_view(report_id)
    return report


@app.patch("/api/reports/{report_id}")
async def api_update_report(report_id: int, data: dict):
    """更新报告信息（摘要、标签、分类）"""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    update_data = {}
    for key in ["summary", "tags", "category"]:
        if key in data:
            update_data[key] = data[key]
    if update_data:
        update_report(report_id, update_data)
    return {"status": "ok"}


@app.get("/api/stats")
async def api_get_stats():
    """获取统计信息"""
    return get_stats()


@app.get("/api/sync/status")
async def api_sync_status():
    """获取同步状态"""
    last = get_last_sync()
    return {
        "configured": bool(FEISHU_APP_ID and FEISHU_FOLDER_TOKEN),
        "last_sync": last,
    }


@app.post("/api/sync")
async def api_trigger_sync(background_tasks: BackgroundTasks):
    """手动触发同步"""
    if not FEISHU_APP_ID or not FEISHU_FOLDER_TOKEN:
        raise HTTPException(
            status_code=400,
            detail="未配置飞书凭证（FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_FOLDER_TOKEN）",
        )
    result = await sync_service.run_sync()
    return result


# ─── 启动入口 ─────────────────────────────────────────
if __name__ == "__main__":
    print(r"""
  ╔══════════════════════════════════════════════╗
  ║      📊 行业报告集合站  v1.0                  ║
  ║                                              ║
  ║  搜索浏览行业报告，一键跳转飞书查看源文件       ║
  ╚══════════════════════════════════════════════╝
    """)
    print(f"  🌐 访问地址: http://localhost:{PORT}")
    print(f"  🔄 同步间隔: {SYNC_INTERVAL} 分钟")
    print(f"  📡 飞书配置: {'✅ 已配置' if FEISHU_APP_ID else '⚠️ 未配置（使用示例数据）'}")
    print()

    uvicorn.run(
        "web_server:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
