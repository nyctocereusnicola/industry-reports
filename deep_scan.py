import json, time, sys, os
from pathlib import Path
import httpx

APP_ID = "cli_aa9bf80b5678dbee"
APP_SECRET = "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi"
ROOT_TOKEN = "YYLHfvuCylpAQVdzTRxcdDpgnyc"
BASE = "https://open.feishu.cn/open-apis"
REPORTS_FILE = Path(r"c:\Users\Administrator\CodeBuddy\20260523105640\docs\data\reports.json")

# ── 获取 token ──
print("[1] Getting access_token...")
r = httpx.post(f"{BASE}/auth/v3/app_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15).json()
if r.get("code") != 0:
    print(f"ERROR getting token: {r}")
    sys.exit(1)
TOKEN = r["app_access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("    Token OK")

# ── 递归扫描 ──
def list_all_files(folder_token, page_token=None, collected=None):
    if collected is None:
        collected = []
    params = {"folder_token": folder_token, "page_size": 50}
    if page_token:
        params["page_token"] = page_token
    resp = httpx.get(f"{BASE}/drive/v1/files", headers=HEADERS, params=params, timeout=30).json()
    if resp.get("code") != 0:
        print(f"    API error: {resp.get('msg','?')}")
        return collected
    d = resp.get("data", {})
    files = d.get("files", [])
    collected.extend(files)
    if d.get("has_more"):
        return list_all_files(folder_token, d.get("page_token"), collected)
    return collected

def recursive_scan(folder_token, path_name=""):
    """递归扫描，返回所有文档，子文件夹作为分类继续深入"""
    docs = []
    subfolders = []
    files = list_all_files(folder_token)
    for f in files:
        if f.get("type") == "folder":
            subfolders.append(f)
        else:
            f["_path"] = path_name
            docs.append(f)
    
    for sf in subfolders:
        sf_name = sf.get("name", "未知")
        new_path = f"{path_name}/{sf_name}" if path_name else sf_name
        print(f"    -> 进入子文件夹: {new_path}")
        sub_docs = recursive_scan(sf.get("token"), new_path)
        docs.extend(sub_docs)
    
    return docs

print(f"[2] 递归扫描根文件夹: {ROOT_TOKEN}")
all_docs = recursive_scan(ROOT_TOKEN)
print(f"    扫描完成: {len(all_docs)} 个文档")

# ── 解析分类 ──
# 取路径第一层作为 category
def get_category(path):
    if not path:
        return "未分类"
    parts = path.split("/")
    # 第一层文件夹名即为分类
    return parts[0] if parts[0] else "未分类"

print(f"[3] 解析分类...")
reports = []
for d in all_docs:
    token = d.get("token", "")
    ftype = d.get("type", "file")
    name = d.get("name", "未命名")
    path = d.get("_path", "")
    category = get_category(path)
    
    # 构建飞书链接
    url_map = {
        "doc": f"https://my.feishu.cn/docx/{token}",
        "docx": f"https://my.feishu.cn/docx/{token}",
        "sheet": f"https://my.feishu.cn/sheets/{token}",
        "bitable": f"https://my.feishu.cn/base/{token}",
        "slides": f"https://my.feishu.cn/slides/{token}",
        "mindnote": f"https://my.feishu.cn/mindnotes/{token}",
    }
    url = d.get("url") or url_map.get(ftype, f"https://my.feishu.cn/drive/home/?mode=detail&file_token={token}")
    
    ext_map = {
        "doc": "飞书文档", "docx": "飞书文档",
        "sheet": "飞书表格", "bitable": "多维表格",
        "slides": "幻灯片", "mindnote": "思维导图",
    }
    ext = ext_map.get(ftype, "")
    if not ext and "." in name:
        x = name.rsplit(".", 1)[-1].upper()
        ext = x if len(x) <= 8 else "文件"
    if not ext:
        ext = "文件"

    reports.append({
        "file_token": token,
        "title": name,
        "file_type": ftype,
        "file_ext": ext,
        "summary": "",
        "feishu_url": url,
        "tags": "",
        "category": category,
        "view_count": 0,
        "feishu_modified": d.get("modified_time", ""),
    })

# ── 统计 ──
cats = {}
for r in reports:
    c = r["category"]
    cats[c] = cats.get(c, 0) + 1

reports.sort(key=lambda r: r.get("feishu_modified", ""), reverse=True)

output = {
    "reports": reports,
    "stats": {
        "total": len(reports),
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    },
}

# ── 写入 ──
REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(REPORTS_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n[DONE] 已写入 {REPORTS_FILE}")
print(f"        总报告数: {len(reports)}")
print(f"        分类: {json.dumps(cats, ensure_ascii=False)}")
