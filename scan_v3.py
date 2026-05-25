"""
飞书扫描 v3.2 — 修复版
- 修复时间戳解析（Unix秒 → 日期）
- 过滤文件夹不统计
- 补充关键词覆盖
- 从文件名提取报告真实年份
- 递归扫描子文件夹
"""
import httpx, json, time, os, traceback, re

# --- 配置 ---
APP_ID     = os.getenv("FEISHU_APP_ID",     "cli_aa9bf80b5678dbee")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi")
ROOT       = os.getenv("FEISHU_FOLDER_TOKEN","YYLHfvuCylpAQVdzTRxcdDpgnyc")
BASE       = "https://open.feishu.cn/open-apis"
OUT_DIR    = "docs/data/categories"
DELAY      = 0.2

# --- 关键词分类规则 ---
RULES = [
    ("美妆",     ["美妆","护肤","彩妆","面膜","精华","口红","化妆","美容","防晒","洁面",
                  "卸妆","粉底","眼影","BB霜","隔离","乳液","面霜","抗老","祛痘","美白",
                  "美妝","上美","欧莱雅","兰蔻","雅诗兰黛","资生堂","理容","皮肤",
                  "寡肽","玻尿酸","烟酰胺","敏感肌","痘痘","痤疮","保湿","毛孔","角质"]),
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


def to_date(ts):
    """Unix 时间戳 → YYYY-MM-DD"""
    if not ts:
        return ""
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(ts)))
    except:
        return ""


def extract_year_from_title(title):
    """从文件名中提取报告的真实年份，如 '2022 珀莱雅报告' → '2022'"""
    years = re.findall(r'\b((?:19|20)\d{2})\b', title)
    for y in years:
        yi = int(y)
        if 2000 <= yi <= 2030:
            return y
    return None


def classify(filename: str):
    text = filename.lower()
    for cat_name, keywords in COMPILED:
        matched = [kw for kw in keywords if kw in text]
        if matched:
            return cat_name, matched[:6]
    return "其他", []


def get_token():
    r = httpx.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=15,
    )
    d = r.json()
    if d.get("code") != 0:
        raise Exception(f"Token 失败: {d}")
    return d["tenant_access_token"]


def process_file(f: dict):
    name = f.get("name", "未命名")
    ftype = f.get("type", "")

    # 跳过文件夹
    if ftype == "folder":
        return None

    cat, keywords = classify(name)

    # 去扩展名
    title = name
    for ext in [".pdf",".docx",".doc",".pptx",".ppt",".xlsx",".xls",".txt",".md",".csv"]:
        if title.lower().endswith(ext):
            title = title[:-len(ext)]
            break

    mtime = f.get("modified_time", "")
    ctime = f.get("created_time", "")

    # 从标题提取报告真实年份，优先于飞书时间戳
    title_year = extract_year_from_title(name)
    if title_year:
        year = title_year
        date = f"{title_year}-01-01"
    else:
        date = to_date(mtime)
        year = date[:4] if date else "未知"

    score = min(100, 50 + len(keywords) * 5 + min(len(name) // 8, 20))

    return {
        "token":          f.get("token", ""),
        "title":          title,
        "summary":        "",
        "tags":           [cat] + keywords,
        "score":          score,
        "year":           year,
        "date":           date,
        "url":            f.get("url", ""),
        "type":           ftype,
        "size":           f.get("size", 0),
        "created_time":   to_date(ctime),
        "modified_time":  to_date(mtime),
    }


def list_all_files(token: str, folder_token: str, depth: int = 0):
    """递归列出文件夹下的所有文件（包括子文件夹）"""
    all_files = []
    page_token = None
    seen = set()
    skipped_folders = 0

    if depth > 10:  # 安全保护：最多10层
        return all_files

    indent = "  " * depth + "→ "

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
            raise Exception(f"列表失败 (page {page_num}, depth {depth}): {d}")

        data = d.get("data", {})
        for f in data.get("files", []):
            tid = f.get("token", "")
            ftype = f.get("type", "")

            if ftype == "folder":
                fname = f.get("name", "子文件夹")
                print(f"   {indent}[DIR] 进入子文件夹: {fname}")
                sub_files = list_all_files(token, tid, depth + 1)
                all_files.extend(sub_files)
                skipped_folders += 1
            else:
                if tid and tid not in seen:
                    seen.add(tid)
                    result = process_file(f)
                    if result is not None:
                        all_files.append(result)

        if not data.get("has_more"):
            break
        new_token = data.get("page_token")
        if not new_token or new_token == page_token:
            break
        page_token = new_token
        time.sleep(DELAY)

    if depth == 0:
        print(f"   跳过 {skipped_folders} 个文件夹")
    return all_files


def scan():
    print("=== scan_v3.2 开始 ===")
    token = get_token()
    print("  → Token OK")
    files = list_all_files(token, ROOT)
    print(f"  → 共 {len(files)} 个文件")

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
        if items:
            print(f"  [SAVE] {cat_name}: {len(items)} 篇")

    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total,
            "categories": [c for c in CATEGORY_LIST if cats[c]],
        }, fh, ensure_ascii=False, indent=2)

    active = sum(1 for c in CATEGORY_LIST if cats[c])
    print(f"[OK] 完成! {total} 个文件 -> {active} 个分类")


if __name__ == "__main__":
    try:
        scan()
    except Exception as e:
        print(f"[ERR] 失败: {e}")
        traceback.print_exc()
        exit(1)
