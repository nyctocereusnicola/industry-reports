import json, time, sys, os
from pathlib import Path
import httpx

APP_ID = "cli_aa9bf80b5678dbee"
APP_SECRET = "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi"
ROOT_TOKEN = "YYLHfvuCylpAQVdzTRxcdDpgnyc"
BASE = "https://open.feishu.cn/open-apis"
REPORTS_FILE = Path(r"c:\Users\Administrator\CodeBuddy\20260523105640\docs\data\reports.json")
STATE_FILE = Path(r"c:\Users\Administrator\CodeBuddy\20260523105640\_sync_state.json")

# ── Token ──
print("[1] Token...")
r = httpx.post(f"{BASE}/auth/v3/app_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15).json()
if r.get("code") != 0:
    print(f"ERROR: {r}")
    sys.exit(1)
TOKEN = r["app_access_token"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# ── 限速 API ──
def api_get(url, params=None):
    for attempt in range(5):
        try:
            resp = httpx.get(url, headers=HEADERS, params=params, timeout=30)
            data = resp.json()
            if data.get("code") == 99991400:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s, 40s, 80s
                print(f"    RATE LIMIT -> 等 {wait}s ...", flush=True)
                time.sleep(wait)
                continue
            return data
        except Exception as e:
            print(f"    NET ERR: {e}, 等 5s...", flush=True)
            time.sleep(5)
    return {"code": -1, "msg": "max retries"}

# ── 列出所有文件 ──
def list_all_files(folder_token, folder_label=""):
    collected = []
    page_token = None
    while True:
        time.sleep(1.5)  # 每个分页请求等 1.5s
        params = {"folder_token": folder_token, "page_size": 50}
        if page_token:
            params["page_token"] = page_token
        data = api_get(f"{BASE}/drive/v1/files", params)
        if data.get("code") != 0:
            print(f"  ! 无法读取 {folder_label}: {data.get('msg','?')}", flush=True)
            return collected
        d = data.get("data", {})
        files = d.get("files", [])
        collected.extend(files)
        print(f"  {folder_label}: +{len(files)} (累计{len(collected)})", flush=True)
        if not d.get("has_more"):
            break
        page_token = d.get("page_token")
    return collected

# ── 加载/保存状态 ──
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"all_docs": [], "seen": [], "done": [], "queue": []}

def save_state(all_docs, seen, done, queue):
    state = {
        "all_docs": all_docs,
        "seen": list(seen),
        "done": list(done),
        "queue": queue,
        "time": time.time()
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

# ── 恢复或新建 ──
print(f"[2] 加载状态...")
st = load_state()
all_docs = st.get("all_docs", [])
seen = set(st.get("seen", []))
done = set(st.get("done", []))
queue = st.get("queue", [])

if not queue:
    queue = [(ROOT_TOKEN, "")]
    print("    新扫描")
else:
    print(f"    恢复: {len(all_docs)} 文档, {len(queue)} 待扫")

# ── 主循环 ──
print(f"[3] 开始扫描 (约需几分钟) ...")
round_num = 0
while queue:
    ftoken, path = queue.pop(0)
    if ftoken in done:
        continue
    
    label = path if path else "根目录"
    print(f"\n--- [{round_num+1}] {label} ---", flush=True)
    
    files = list_all_files(ftoken, label)
    done.add(ftoken)
    
    subfolders = []
    for f in files:
        if f.get("type") == "folder":
            subfolders.append(f)
        else:
            f["_path"] = path
            all_docs.append(f)
    
    new_folders = 0
    for sf in subfolders:
        sf_name = sf.get("name", "?")
        sf_token = sf.get("token", "")
        new_path = f"{path}/{sf_name}" if path else sf_name
        if sf_token not in done and sf_token not in seen:
            seen.add(sf_token)
            queue.append((sf_token, new_path))
            new_folders += 1
    
    print(f"  文档:{len(files)-len(subfolders)} 子文件夹:{len(subfolders)}(新增{new_folders}) 总:{len(all_docs)} 队列:{len(queue)}", flush=True)
    
    # 每5个文件夹存一次状态
    round_num += 1
    if round_num % 5 == 0:
        save_state(all_docs, seen, done, queue)

# ── 构建输出 ──
print(f"\n[4] 构建, 共 {len(all_docs)} 文档...")
def get_category(path):
    if not path: return "未分类"
    return path.split("/")[0]

reports = []
for d in all_docs:
    token = d.get("token", "")
    ftype = d.get("type", "file")
    name = d.get("name", "未命名")
    category = get_category(d.get("_path", ""))
    
    um = {"doc":"docx","docx":"docx","sheet":"sheets","bitable":"base","slides":"slides","mindnote":"mindnotes"}
    ext_um = {"doc":"飞书文档","docx":"飞书文档","sheet":"飞书表格","bitable":"多维表格","slides":"幻灯片","mindnote":"思维导图"}
    
    url = d.get("url") or f"https://my.feishu.cn/{um.get(ftype,'drive/home/?mode=detail')}/{token}"
    ext = ext_um.get(ftype, "")
    if not ext and "." in name:
        x = name.rsplit(".",1)[-1].upper()
        ext = x if len(x) <= 8 else "文件"
    if not ext: ext = "文件"
    
    reports.append({
        "file_token": token, "title": name, "file_type": ftype, "file_ext": ext,
        "summary": "", "feishu_url": url, "tags": "", "category": category,
        "view_count": 0, "feishu_modified": d.get("modified_time",""),
    })

cats = {}
for r in reports: cats[r["category"]] = cats.get(r["category"],0) + 1
reports.sort(key=lambda r: r.get("feishu_modified",""), reverse=True)

out = {
    "reports": reports,
    "stats": {"total":len(reports),
        "categories":[{"name":k,"count":v} for k,v in sorted(cats.items(),key=lambda x:-x[1])],
        "last_sync":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
}

REPORTS_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(REPORTS_FILE, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# 清理状态文件
if STATE_FILE.exists():
    STATE_FILE.unlink()

print(f"\n[DONE] {len(reports)} 篇")
print(json.dumps(cats, ensure_ascii=False))
