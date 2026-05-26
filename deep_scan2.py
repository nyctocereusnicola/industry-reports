import json, time, sys
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
    print(f"ERROR: {r}")
    sys.exit(1)
TOKEN = r["app_access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
print("    Token OK")

# ── 限速 API 调用 ──
def api_get(url, params=None, retries=3):
    for attempt in range(retries):
        try:
            resp = httpx.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()
            if data.get("code") == 99991400:  # frequency limit
                wait = 2 ** attempt
                print(f"    频率限制，等待 {wait}s...")
                time.sleep(wait)
                continue
            return data
        except Exception as e:
            print(f"    请求异常: {e}")
            time.sleep(2)
    return {"code": -1, "msg": "max retries"}

# ── 分页列出文件 ──
def list_all_files(folder_token):
    collected = []
    page_token = None
    while True:
        time.sleep(0.3)  # 限速
        params = {"folder_token": folder_token, "page_size": 50}
        if page_token:
            params["page_token"] = page_token
        data = api_get(f"{BASE}/drive/v1/files", params)
        if data.get("code") != 0:
            print(f"    list error: {data.get('msg','?')}")
            return collected
        d = data.get("data", {})
        collected.extend(d.get("files", []))
        if not d.get("has_more"):
            break
        page_token = d.get("page_token")
    return collected

# ── 递归扫描（用栈避免递归无限循环） ──
print(f"[2] 递归扫描...")
all_docs = []
folder_queue = [(ROOT_TOKEN, "")]
seen_folders = set()

while folder_queue:
    ftoken, path = folder_queue.pop(0)
    if ftoken in seen_folders:
        print(f"    SKIP (already visited): {path or 'root'}")
        continue
    seen_folders.add(ftoken)
    
    label = path if path else "根目录"
    print(f"    [{len(seen_folders)}] 扫描: {label}")
    
    files = list_all_files(ftoken)
    subfolders = []
    for f in files:
        if f.get("type") == "folder":
            subfolders.append(f)
        else:
            f["_path"] = path
            all_docs.append(f)
    
    for sf in subfolders:
        sf_name = sf.get("name", "未知")
        sf_token = sf.get("token", "")
        new_path = f"{path}/{sf_name}" if path else sf_name
        if sf_token not in seen_folders:
            folder_queue.append((sf_token, new_path))
    
    print(f"        文档:{len(files)-len(subfolders)} 子文件夹:{len(subfolders)} 队列:{len(folder_queue)}")

print(f"\n    总文档: {len(all_docs)}")

# ── 构建报告 ──
print(f"[3] 构建数据...")
def get_category(path):
    if not path:
        return "未分类"
    return path.split("/")[0]

reports = []
for d in all_docs:
    token = d.get("token", "")
    ftype = d.get("type", "file")
    name = d.get("name", "未命名")
    category = get_category(d.get("_path", ""))
    
    url_map = {
        "doc": f"https://my.feishu.cn/docx/{token}",
        "docx": f"https://my.feishu.cn/docx/{token}",
        "sheet": f"https://my.feishu.cn/sheets/{token}",
        "bitable": f"https://my.feishu.cn/base/{token}",
        "slides": f"https://my.feishu.cn/slides/{token}",
        "mindnote": f"https://my.feishu.cn/mindnotes/{token}",
    }
    url = d.get("url") or url_map.get(ftype,
        f"https://my.feishu.cn/drive/home/?mode=detail&file_token={token}")
    
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

REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(REPORTS_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n[DONE] reports.json 已更新")
print(f"        总计: {len(reports)} 篇")
print(f"        分类: {json.dumps(cats, ensure_ascii=False)}")
