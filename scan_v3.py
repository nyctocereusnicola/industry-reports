"""
飞书扫描 v3 — 极简版
所有文件放一个文件夹，关键词自动分类，一次 API 扫描完成。
"""
import httpx, json, time, os, traceback, re

# --- 配置 ---
APP_ID     = os.getenv("FEISHU_APP_ID",     "cli_aa9bf80b5678dbee")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi")
ROOT       = os.getenv("FEISHU_FOLDER_TOKEN","YYLHfvuCylpAQVdzTRxcdDpgnyc")
BASE       = "https://open.feishu.cn/open-apis"
OUT_DIR    = "docs/data/categories"
DELAY      = 0.3

# --- 关键词分类规则（从上到下，命中即归类）---
RULES = [
    ("美妆",     ["美妆","护肤","彩妆","面膜","精华","口红","化妆","美容","防晒","洁面",
                  "卸妆","粉底","眼影","BB霜","隔离","乳液","面霜","抗老","祛痘","美白"]),
    ("宠物",     ["宠物","猫","狗","猫粮","狗粮","萌宠","宠物食品","宠物用品","猫咪",
                  "狗狗","猫狗","罐头","冻干"]),
    ("抖音",     ["抖音","douyin","TikTok","短视频","直播","抖店","抖音电商"]),
    ("小红书",   ["小红书","redbook","RED","种草","红书","小紅書"]),
    ("潮流时尚", ["时尚","潮流","穿搭","服饰","奢侈品","箱包","配饰","鞋履","时装",
                  "快时尚","设计师","潮牌","包袋","珠宝","首饰"]),
    ("食品饮料", ["食品","饮料","零食","餐饮","酒","茶","咖啡","烘焙","乳制品",
                  "调味","预制菜","方便面","速食","矿泉水","啤酒","白酒"]),
    ("母婴",     ["母婴","婴儿","妈妈","育儿","奶粉","童装","儿童","宝宝","亲子",
                  "月子","辅食","纸尿裤","奶瓶"]),
    ("家居",     ["家居","家具","家装","家电","床上","卫浴","厨房","客厅","卧室",
                  "收纳","灯具","窗帘","地毯"]),
    ("海外市场", ["海外","出海","东南亚","日本","欧美","跨境","全球","国际",
                  "印度","印尼","巴西","中东"]),
    ("户外与运动",["户外","运动","健身","跑步","瑜伽","登山","露营","骑行","滑雪",
                  "游泳","篮球","足球","马拉松"]),
    ("健康养生", ["健康","养生","保健","中医","体检","营养","维生素","益生菌",
                  "按摩","理疗","养老","银发"]),
    ("快消品",   ["快消","零售","超市","便利店","百货","打折","促销","渠道"]),
    ("奢侈品",   ["奢侈品","奢侈","高端","爱马仕","LV","香奈儿","Gucci","保时捷",
                  "劳斯莱斯","名表","名酒"]),
    ("香相关",   ["香水","香氛","香薰","熏香","精油","香料","香氛蜡烛","闻香"]),
]

CATEGORY_LIST = [name for name, _ in RULES] + ["其他"]
COMPILED = [(name, [kw.lower() for kw in kws]) for name, kws in RULES]


def classify(filename: str) -> tuple:
    text = filename.lower()
    for cat_name, keywords in COMPILED:
        matched = [kw for kw in keywords if kw in text]
        if matched:
            return cat_name, matched[:6]
    return "其他", []


def get_token() -> str:
    r = httpx.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=15,
    )
    d = r.json()
    if d.get("code") != 0:
        raise Exception(f"获取 token 失败: {d}")
    return d["tenant_access_token"]


def process_file(f: dict) -> dict:
    name = f.get("name", "未命名")
    cat, keywords = classify(name)

    title = name
    for ext in [".pdf",".docx",".doc",".pptx",".ppt",".xlsx",".xls",".txt",".md",".csv"]:
        if title.lower().endswith(ext):
            title = title[:-len(ext)]
            break

    mtime = f.get("modified_time", "")
    ctime = f.get("created_time", "")
    year = mtime[:4] if mtime else (ctime[:4] if ctime else "")
    date = mtime[:10] if mtime else ""
    score = min(100, 50 + len(keywords) * 5 + min(len(name) // 8, 20))

    return {
        "token":          f.get("token", ""),
        "title":          title,
        "summary":        "",
        "tags":           [cat] + keywords,
        "score":          score,
        "year":           year or "未知",
        "date":           date,
        "url":            f.get("url", ""),
        "type":           f.get("type", ""),
        "size":           f.get("size", 0),
        "created_time":   ctime,
        "modified_time":  mtime,
    }


def list_all_files(token: str, folder_token: str) -> list:
    all_files = []
    page_token = None
    seen = set()

    for page_num in range(1, 200):
        params = {"folder_token": folder_token, "page_size": 50}
        if page_token:
            params["page_token"] = page_token

        r = httpx.get(
            f"{BASE}/drive/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        d = r.json()
        if d.get("code") != 0:
            raise Exception(f"获取文件列表失败 (page {page_num}): {d}")

        data = d.get("data", {})
        batch = data.get("files", [])
        for f in batch:
            tid = f.get("token", "")
            if tid and tid not in seen:
                seen.add(tid)
                all_files.append(process_file(f))

        if not data.get("has_more"):
            break
        new_token = data.get("page_token")
        if not new_token or new_token == page_token:
            break
        page_token = new_token
        time.sleep(DELAY)

    return all_files


def scan():
    print("=== scan_v3 开始 ===")
    print("  → 获取 Token ...")
    token = get_token()
    print("  → Token OK")
    print(f"  → 扫描文件夹 ...")
    files = list_all_files(token, ROOT)
    print(f"  → 共获取 {len(files)} 个文件")

    cats = {c: [] for c in CATEGORY_LIST}
    for f in files:
        cat = f["tags"][0] if f["tags"] else "其他"
        cats[cat].append(f)

    os.makedirs(OUT_DIR, exist_ok=True)
    total = 0
    for cat_name in CATEGORY_LIST:
        items = cats[cat_name]
        total += len(items)
        path = os.path.join(OUT_DIR, f"{cat_name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "category": cat_name,
                "file_count": len(items),
                "files": items,
            }, fh, ensure_ascii=False, indent=2)
        print(f"  💾 {cat_name}: {len(items)} 篇")

    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total,
            "categories": [c for c in CATEGORY_LIST if cats[c]],
        }, fh, ensure_ascii=False, indent=2)

    active = sum(1 for c in CATEGORY_LIST if cats[c])
    print(f"✅ 完成! {total} 个文件 → {active} 个分类")


if __name__ == "__main__":
    try:
        scan()
    except Exception as e:
        print(f"❌ 失败: {e}")
        traceback.print_exc()
        exit(1)
