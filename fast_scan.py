import json, time, sys
from pathlib import Path
import httpx

APP_ID = "cli_aa9bf80b5678dbee"
APP_SECRET = "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi"
ROOT_TOKEN = "YYLHfvuCylpAQVdzTRxcdDpgnyc"
BASE = "https://open.feishu.cn/open-apis"
REPORTS_FILE = Path(r"c:\Users\Administrator\CodeBuddy\20260523105640\docs\data\reports.json")

print("[1] Token...")
r = httpx.post(f"{BASE}/auth/v3/app_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15).json()
TOKEN = r["app_access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def api_get(url, params=None):
    for attempt in range(5):
        try:
            resp = httpx.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()
            if data.get("code") == 99991400:
                wait = 5 * (2 ** attempt)
                print(f"    RATE LIMIT -> {wait}s...", flush=True)
                time.sleep(wait)
                continue
            return data
        except Exception as e:
            print(f"    ERR: {e}", flush=True)
            time.sleep(3)
    return {"code": -1}

def list_all_files(folder_token):
    collected = []
    page_token = None
    while True:
        time.sleep(1)
        params = {"folder_token": folder_token, "page_size": 50}
        if page_token:
            params["page_token"] = page_token
        data = api_get(f"{BASE}/drive/v1/files", params)
        if data.get("code") != 0:
            print(f"    ! read err: {data.get('msg','?')}", flush=True)
            return collected
        d = data.get("data", {})
        collected.extend(d.get("files", []))
        if not d.get("has_more"):
            break
        page_token = d.get("page_token")
        print(f"    +{len(d.get('files',[]))} (累计{len(collected)})", flush=True)
    return collected

def recursive_scan(folder_token, category):
    docs = []
    files = list_all_files(folder_token)
    subfolders = []
    for f in files:
        if f.get("type") == "folder":
            subfolders.append(f)
        else:
            f["_category"] = category
            docs.append(f)
    
    doc_count = len(files) - len(subfolders)
    print(f"  [{category}] 文档:{doc_count} 子文件夹:{len(subfolders)}", flush=True)
    
    for sf in subfolders:
        sf_name = sf.get("name", "?")
        sf_token = sf.get("token", "")
        sub_docs = recursive_scan(sf_token, category)
        docs.extend(sub_docs)
    
    return docs

# ── 步骤1: 只读根目录第一页，找子文件夹 ──
print("[2] 列出根目录子文件夹...")
time.sleep(1)
params = {"folder_token": ROOT_TOKEN, "page_size": 50, "order_by": "EditedTime", "direction": "DESC"}
data = api_get(f"{BASE}/drive/v1/files", params)
if data.get("code") != 0:
    print(f"ERROR: {data}")
    sys.exit(1)

root_files = data.get("data", {}).get("files", [])
subfolders = [f for f in root_files if f.get("type") == "folder"]

print(f"    找到 {len(subfolders)} 个子文件夹:")
for sf in subfolders:
    print(f"      - {sf.get('name','?')}")

# ── 步骤2: 加载现有的未分类报告 ──
print("[3] 加载已知数据...")
existing = []
if REPORTS_FILE.exists():
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    existing = [r for r in d.get("reports", []) if not r.get("file_token","").startswith("demo_")]
print(f"    现有 {len(existing)} 篇")

# 去重用
seen_tokens = {r["file_token"] for r in existing}

# ── 步骤3: 递归扫描每个子文件夹 ──
print("[4] 递归扫描子文件夹...")
all_new = []
for sf in subfolders:
    cat = sf.get("name", "未命名")
    token = sf.get("token", "")
    print(f"\n--- {cat} ---", flush=True)
    docs = recursive_scan(token, cat)
    
    new_count = 0
    for d in docs:
        ftoken = d.get("token", "")
        if ftoken in seen_tokens:
            continue
        seen_tokens.add(ftoken)
        ftype = d.get("type", "file")
        name = d.get("name", "未命名")
        category = d.get("_category", cat)
        
        um = {"doc":"docx","docx":"docx","sheet":"sheets","bitable":"base","slides":"slides","mindnote":"mindnotes"}
        ext_um = {"doc":"飞书文档","docx":"飞书文档","sheet":"飞书表格","bitable":"多维表格","slides":"幻灯片","mindnote":"思维导图"}
        url = d.get("url") or f"https://my.feishu.cn/{um.get(ftype,'drive/home/?mode=detail')}/{ftoken}"
        ext = ext_um.get(ftype, "")
        if not ext and "." in name:
            x = name.rsplit(".",1)[-1].upper()
            ext = x if len(x) <= 8 else "文件"
        if not ext: ext = "文件"
        
        all_new.append({
            "file_token": ftoken, "title": name, "file_type": ftype, "file_ext": ext,
            "summary": "", "feishu_url": url, "tags": "", "category": category,
            "view_count": 0, "feishu_modified": d.get("modified_time",""),
        })
        new_count += 1
    
    print(f"    -> 新增 {new_count} 篇 ({cat})", flush=True)

# ── 步骤4: 合并并输出 ──
print(f"\n[5] 合并: 原有{len(existing)} + 新增{len(all_new)} = {len(existing)+len(all_new)}")
all_reports = existing + all_new
all_reports.sort(key=lambda r: r.get("feishu_modified",""), reverse=True)

cats = {}
for r in all_reports:
    c = r["category"]
    cats[c] = cats.get(c, 0) + 1

out = {
    "reports": all_reports,
    "stats": {
        "total": len(all_reports),
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    },
}

REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(REPORTS_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"\n[DONE] {len(all_reports)} 篇")
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
