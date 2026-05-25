import httpx, json, time, os

A="cli_aa9bf80b5678dbee"
S="BSrMFRLJSEOv9cngkERqEcg83IRbj2oi"
B="https://open.feishu.cn/open-apis"
OUT = "docs/data/categories"
DELAY = 0.8

ORDER = ["潮流时尚","宠物","抖音","小红书","美妆",
         "海外市场","户外与运动","家居","健康养生","快消品",
         "母婴","其他","奢侈品","食品饮料","香相关"]

# 文件夹 token
FOLDER_MAP = {
    "宠物": "HOwUfQ9bTlKWqydV8nhcMkxxneh",
    "小红书": "TL3gf1uLrlHx0odx7vYc3JIBn6g",
}

def api(token, folder_token, page_token=None):
    for attempt in range(3):
        try:
            r = httpx.get(f"{B}/drive/v1/files",
                          headers={"Authorization": f"Bearer {token}"},
                          params={"folder_token":folder_token,"page_size":200,
                                  "page_token":page_token or ""}, timeout=30)
            if r.status_code == 429:
                w = int(r.headers.get("Retry-After", 10))
                time.sleep(w + 2)
                continue
            return r.json()
        except Exception as e:
            time.sleep(3)
    return {"code": -1}

def recurse(token, ftoken, depth, max_d):
    files = []
    folders_to_scan = []
    pt = None
    
    while True:
        d = api(token, ftoken, pt)
        if d.get("code", -1) != 0:
            break
        items = d.get("data",{}).get("files",[])
        for it in items:
            t = it.get("type","")
            tk = it.get("token","")
            nm = it.get("name","")
            if t == "folder" and depth < max_d:
                folders_to_scan.append((tk, nm))
            elif t != "folder":
                ext = (it.get("file_extension","") or "").strip(".")
                files.append({
                    "file_token": tk, "title": nm, "file_type": t,
                    "file_ext": ext.upper()[:10],
                    "feishu_url": it.get("url","") or f"https://my.feishu.cn/file/{tk}",
                    "view_count": it.get("view_count",0),
                    "feishu_modified": it.get("modified_time",""),
                    "summary": (it.get("description","") or "")[:200],
                    "tags": "",
                })
        if not d.get("data",{}).get("has_more"):
            break
        pt = d["data"].get("page_token","")
        time.sleep(DELAY)
    
    print(f"  depth={depth}: direct_files={len(files)} sub_folders={len(folders_to_scan)}", flush=True)
    for idx, (sfk, sfn) in enumerate(folders_to_scan):
        print(f"    [{idx+1}/{len(folders_to_scan)}] sub: {sfn[:40]}", flush=True)
        time.sleep(DELAY)
        sub = recurse(token, sfk, depth+1, max_d)
        files.extend(sub)
    return files

def dedup(reports):
    seen = {}
    for r in reports:
        ft = r.get("file_token","")
        if ft and ft not in seen:
            seen[ft] = r
    return list(seen.values())

def main():
    os.makedirs(OUT, exist_ok=True)
    print("=== Token ===", flush=True)
    tok = httpx.post(f"{B}/auth/v3/app_access_token/internal",
                     json={"app_id":A,"app_secret":S}, timeout=10).json()["app_access_token"]
    print("OK\n", flush=True)

    stats = {}
    for cat in ORDER:
        ft = FOLDER_MAP.get(cat)
        if not ft:
            # Wiki 文件夹 (暂无权限)
            stats[cat] = 0
            path = os.path.join(OUT, f"{cat}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"category": cat, "count": 0, "reports": [],
                           "note": "Need Wiki permission"}, f, ensure_ascii=False)
            continue

        print(f"\n=== {cat} ===", flush=True)
        fs = recurse(tok, ft, 0, 6)  # max_depth=6 for deeper scan
        fs = dedup(fs)
        stats[cat] = len(fs)
        path = os.path.join(OUT, f"{cat}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"category": cat, "count": len(fs), "reports": fs}, f, ensure_ascii=False)
        mb = os.path.getsize(path)/(1024*1024)
        print(f"  [OK] {len(fs)} items, {mb:.1f}MB", flush=True)

    total = sum(stats.values())
    idx = {"total": total,
           "categories": [{"name":c,"count":stats[c]} for c in ORDER],
           "last_sync": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "note": "Categories with 0 need Wiki permission in Feishu app"}
    with open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== Done: {total} total ===", flush=True)
    for c in ORDER:
        print(f"  {c}: {stats[c]}", flush=True)

if __name__ == "__main__":
    main()
