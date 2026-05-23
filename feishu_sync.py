"""
飞书云空间同步模块

功能：
- 获取飞书 tenant_access_token
- 获取指定文件夹下的文件列表
- 同步到本地 SQLite 数据库
"""

import time
import httpx
from typing import Optional


class FeishuClient:
    """飞书开放平台 API 客户端"""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expire_at: float = 0

    async def _get_access_token(self) -> str:
        """获取 tenant_access_token（带缓存）"""
        if self._access_token and time.time() < self._token_expire_at - 60:
            return self._access_token

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret,
                },
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"获取 access_token 失败: {data.get('msg', data)}")

            self._access_token = data["tenant_access_token"]
            self._token_expire_at = time.time() + data.get("expire", 7200)
            return self._access_token

    async def list_folder_files(
        self,
        folder_token: str,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> dict:
        """
        获取文件夹下的文件列表

        返回格式:
        {
            "files": [
                {
                    "token": "文件token",
                    "name": "文件名",
                    "type": "doc/docx/sheet/bitable/file/folder",
                    "created_time": "创建时间戳(ms)",
                    "modified_time": "修改时间戳(ms)",
                    "owner_id": "所有者ID",
                    "url": "文件访问URL",
                    "size": 文件大小(bytes, 仅 file 类型)
                },
                ...
            ],
            "has_more": bool,
            "page_token": "下一页token"
        }
        """
        token = await self._get_access_token()
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/drive/v1/folders/{folder_token}/files",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"获取文件列表失败: {data.get('msg', data)}")
            return data.get("data", {})

    async def list_all_files(self, folder_token: str) -> list[dict]:
        """获取文件夹下所有文件（自动处理分页）"""
        all_files = []
        page_token = None

        while True:
            result = await self.list_folder_files(
                folder_token, page_size=50, page_token=page_token
            )
            files = result.get("files", [])
            all_files.extend(files)

            if not result.get("has_more"):
                break
            page_token = result.get("page_token")

        return all_files

    async def get_file_info(self, file_token: str) -> dict:
        """获取单个文件信息"""
        token = self._access_token or (await self._get_access_token())
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.BASE_URL}/drive/v1/files/{file_token}",
                headers={"Authorization": f"Bearer {token}"},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise Exception(f"获取文件信息失败: {data.get('msg', data)}")
            return data.get("data", {})

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
        """获取文件扩展名"""
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
        # 从文件名中提取扩展名
        if "." in name:
            ext = name.rsplit(".", 1)[-1].upper()
            return ext if len(ext) <= 8 else "文件"
        return "文件"
