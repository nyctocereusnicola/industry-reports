import httpx, json, time, os

APP_ID = "cli_aa9bf80b5678dbee"
APP_SECRET = "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi"
BASE = "https://open.feishu.cn/open-apis"
OUT = "docs/data/categories"
DELAY = 0.5

ORDER = ["潮流时尚","宠物","抖音","小红书","美妆",
         "海外市场","户外与运动","家居","健康养生","快消品",
         "母婴","其他","奢侈品","食品饮料","香相关"]

# 直接用旧 folder_map
FOLDER_MAP = {
    "潮流时尚": "GGZMfWunflg7MPdETDpcpvCrnvd",
    "宠物": "HOwUfQ9bTlKWqydV8nhcMkxxneh",
    "抖音": "Pc53fEW0QlHw8XdvtT3cPxrLn2d",
    "小红书": "TL3gf1uLrlHx0odx7vYc3JIBn6g",
    "美妆": "Qg6Qf6cJclDwuXd6Gmac6ca8nld",
    "海外市场": "QrXif6VW2lVfpUduD5mcMjFfngg",
    "户外与运动": "VTYWfpgPFlG0CJdtVJGcSjpXnad",
    "家居": "CVpOfbWBNl9CtSdVRm2csPeOn5c",
    "健康养生": "EGChfAdp6lapgadNnLkcLNrynAf",
    "快消品": "PYqgfbCqelx3u5d6IQJcC8IInCg",
    "母婴": "Jq1yfRTMCliKozd3oSTc4Yc3nYy",
    "其他": "IIhMf5RQhlSWYAdRWRpccrFunZb",
    "奢侈品": "AsoFfK9gylLQm2dS1Qecyr7inrf",
    "食品饮料": "MIR2fixkHldXaNdh419cpG8BnUg",
    "香相关": "Gb9bf4kbqlbRFdd2Wyuck2NEn4e",
}

def get_token():
    r = httpx.post(f"{BASE}/auth/v3/tenant_access_token/internal",
                   json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=15)
    return r.json()["tenant_access_token"]

def scan_folder(token, folder_token, cat_name, max_depth=5):
    all_files = []
    nfolders = 0
    stack = [(folder_token, 0)]
    
    while stack:
        ft, depth = stack.pop()
        if depth >= max_depth:
            nfolders += 1
            continue
        
        page_token = ""
        while True:
            try:
                r = httpx.get(f"{BASE}/drive/v1/files",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"folder_token": ft, "page_size": 200, "page_token": page_token},
                    timeout=30)
            except:
                time.sleep(2)
                continue
            
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 10)) + 2)
                continue
            
            d = r.json()
            if d.get("code") != 0:
                # 第一个文件夹失败就退出
                if ft == folder_token and page_token == "":
                    print(f"      [ERR] code={d.get('code')} msg={d.get('msg','')[:80]}")
                break
            
            for f in d.get("data", {}).get("files", []):
                if f["type"] == "folder":
                    stack.append((f["token"], depth + 1))
                    nfolders += 1
                elif f["type"] in ("doc", "sheet", "file", "docx", "bitable", "mindnote"):
                    all_files.append({
                        "name": f["name"], "token": f["token"],
                        "type": f["type"], "url": f.get("url", ""),
                        "created": f.get("create_time", ""),
                        "modified": f.get("modified_time", "")
                    })
            
            if not d.get("data", {}).get("has_more"):
                break
            page_token = d["data"]["page_token"]
            time.sleep(0.1)
        
        time.sleep(DELAY)
    
    return all_files, nfolders

def main():
    token = get_token()
    print("Token OK\n")
    
    os.makedirs(OUT, exist_ok=True)
    total_all = 0
    
    for cat in ORDER:
        tid = FOLDER_MAP.get(cat)
        if not tid:
            print(f"[{cat}] SKIP")
            continue
        
        print(f"[{cat}] scanning...", end="", flush=True)
        files, nfolders = scan_folder(token, tid, cat)
        
        seen = set()
        unique = []
        for f in files:
            if f["token"] not in seen:
                seen.add(f["token"])
                unique.append(f)
        
        meta = {"category": cat, "count": len(unique), "files": unique,
                "updated": time.strftime("%Y-%m-%d %H:%M:%S")}
        
        fname = os.path.join(OUT, f"{cat}.json")
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        
        mb = os.path.getsize(fname) / (1024*1024)
        print(f" -> {len(unique)} files, {nfolders} subdirs, {mb:.1f}MB")
        total_all += len(unique)
    
    # index
    idx = {"categories": ORDER, "total_files": total_all,
           "updated": time.strftime("%Y-%m-%d %H:%M:%S"), "counts": {}}
    for cat in ORDER:
        fname = os.path.join(OUT, f"{cat}.json")
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                idx["counts"][cat] = len(json.load(f)["files"])
    with open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Total: {total_all} ===")

if __name__ == "__main__":
    main()
