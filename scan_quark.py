"""
夸克网盘扫描 v1.0
- Cookie 认证
- 递归扫描子文件夹
- 从文件名提取报告真实年份
- 批量获取下载链接
- 输出格式与 scan_v3.py 完全一致，网页无需改动
"""
import httpx, json, time, os, traceback, re, math

# --- 配置 ---
COOKIE    = os.getenv("QUARK_COOKIE", "")
ROOT_FID  = os.getenv("QUARK_ROOT_FID", "0")
BASE      = "https://drive-pc.quark.cn/1/clouddrive"
OUT_DIR   = "docs/data/categories"
DELAY     = 0.3
BATCH     = 25   # 批量获取下载链接，每次25个

HEADERS = {
    "cookie":         COOKIE,
    "user-agent":     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "origin":         "https://pan.quark.cn",
    "referer":        "https://pan.quark.cn/",
    "accept":         "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
}

# --- 关键词分类规则（与 scan_v3 完全一致）---
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


def ekv(d, *keys, default=""):
    """安全取值，连续尝试多个key"""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def extract_year_from_title(title):
    """从文件名中提取报告的真实年份"""
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


def ts_to_date(ts_val):
    """夸克 timestamp（秒或毫秒）→ YYYY-MM-DD"""
    if not ts_val:
        return ""
    try:
        ts = int(ts_val)
        if ts > 1e12:
            ts = ts // 1000
        return time.strftime("%Y-%m-%d", time.gmtime(ts))
    except:
        return ""


def fmt_size(byte_size):
    """字节 → 可读大小"""
    if not byte_size:
        return "未知"
    try:
        size = int(byte_size)
    except:
        return str(byte_size)
    if size == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = min(int(math.log(size, 1024)), len(units) - 1)
    return f"{size / (1024 ** i):.1f} {units[i]}"


# ==================== 夸克 API ====================

def quark_get(path, params=None):
    if params is None:
        params = {}
    params["pr"] = "ucpro"
    params["fr"] = "pc"
    params["uc_param_str"] = ""
    params["__t"] = str(int(time.time() * 1000))
    params["__dt"] = "1000"

    r = httpx.get(
        f"{BASE}{path}",
        headers=HEADERS,
        params=params,
        timeout=30,
    )
    return r.json()


def quark_post(path, data=None):
    if data is None:
        data = {}
    r = httpx.post(
        f"{BASE}{path}",
        headers=HEADERS,
        json=data,
        timeout=60,
    )
    return r.json()


# ==================== 文件扫描 ====================

def list_all_files(folder_fid: str, depth: int = 0):
    """递归列出夸克网盘文件夹下所有文件"""
    all_files = []
    seen = set()
    skipped_folders = 0
    page = 1

    if depth > 10:
        return all_files

    indent = "  " * depth + "> "

    while True:
        d = quark_get("/file/sort", {
            "pdir_fid":          folder_fid,
            "_page":             str(page),
            "_size":             "100",
            "_sort":             "file_name:asc",
            "_fetch_total":      "1",
            "_fetch_sub_dirs":   "0",
        })

        if d.get("code") != 0 and d.get("status") != 200:
            raise Exception(f"列表失败 (page {page}, depth {depth}): {d}")

        data = d.get("data", {})
        items = data.get("list", [])

        for item in items:
            fid   = ekv(item, "fid")
            fname = ekv(item, "file_name", "name", default="未命名")
            is_dir = item.get("dir", False)

            if is_dir:
                print(f"   {indent}[DIR] {fname}")
                sub = list_all_files(fid, depth + 1)
                all_files.extend(sub)
                skipped_folders += 1
            else:
                if fid and fid not in seen:
                    seen.add(fid)
                    result = process_item(item)
                    if result:
                        all_files.append(result)

        page += 1

        # 检查是否还有更多页
        total = int(data.get("total", 0))
        if total == 0 and not items:
            break
        if len(items) == 0:
            break
        if page > 200:
            break

        time.sleep(DELAY)

    if depth == 0:
        print(f"   [INFO] 跳过 {skipped_folders} 个子文件夹")
    return all_files


def process_item(item: dict):
    """处理单个夸克文件，返回统一格式"""
    name = ekv(item, "file_name", "name", default="未命名")
    fid  = ekv(item, "fid")
    ftype = ekv(item, "file_type", default="file")

    cat, keywords = classify(name)

    # 去扩展名
    title = name
    for ext in [".pdf",".docx",".doc",".pptx",".ppt",".xlsx",".xls",".txt",".md",".csv"]:
        if title.lower().endswith(ext):
            title = title[:-len(ext)]
            break

    created  = ekv(item, "created_at", default=0)
    modified = ekv(item, "updated_at", default=0)

    title_year = extract_year_from_title(name)
    if title_year:
        year = title_year
        date = f"{title_year}-01-01"
    else:
        date = ts_to_date(modified)
        year = date[:4] if date else "未知"

    score = min(100, 50 + len(keywords) * 5 + min(len(name) // 8, 20))
    raw_size = ekv(item, "size", default=0)

    return {
        "token":          fid,
        "title":          title,
        "summary":        "",
        "tags":           [cat] + keywords,
        "score":          score,
        "year":           year,
        "date":           date,
        "url":            "",    # 稍后批量填充下载链接
        "type":           ftype,
        "size":           int(raw_size) if raw_size else 0,
        "size_display":   fmt_size(raw_size),
        "created_time":   ts_to_date(created),
        "modified_time":  ts_to_date(modified),
    }


def batch_download_urls(files: list):
    """批量获取文件下载链接"""
    if not files:
        return
    total = len(files)
    filled = 0

    for i in range(0, total, BATCH):
        batch = files[i:i + BATCH]
        fids = [f["token"] for f in batch]

        try:
            d = quark_post("/file/download", {"fids": fids})
            if d.get("code") != 0 and d.get("status") != 200:
                print(f"   [WARN] 下载链接批量获取失败 (batch {i // BATCH + 1}): {d}")
                continue

            data = d.get("data", [])
            url_map = {entry.get("fid"): entry.get("download_url", "") for entry in data}

            for f in batch:
                dl = url_map.get(f["token"], "")
                if dl:
                    f["url"] = dl
                    filled += 1

            print(f"   [DL] {filled}/{total} 个下载链接已获取")
        except Exception as e:
            print(f"   [WARN] 下载链接请求异常: {e}")

        time.sleep(DELAY)


def scan():
    print("=== scan_quark v1.0 ===")
    if not COOKIE:
        print("[ERR] 未设置 QUARK_COOKIE 环境变量")
        exit(1)

    print(f"  [AUTH] Cookie 长度: {len(COOKIE)}")
    print(f"  [ROOT] 扫描根目录 fid={ROOT_FID}")

    files = list_all_files(ROOT_FID)
    print(f"  [STAT] 共扫描到 {len(files)} 个文件")

    # 批量获取下载链接
    print(f"  [DL] 开始获取下载链接...")
    batch_download_urls(files)

    # 按分类分组
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
                "category":   cat_name,
                "file_count": len(items),
                "files":      items,
            }, fh, ensure_ascii=False, indent=2)
        if items:
            print(f"  [SAVE] {cat_name}: {len(items)} 篇")

    with open(os.path.join(OUT_DIR, "_index.json"), "w", encoding="utf-8") as fh:
        json.dump({
            "updated":     time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total,
            "categories":  [c for c in CATEGORY_LIST if cats[c]],
            "source":      "夸克网盘",
        }, fh, ensure_ascii=False, indent=2)

    active = sum(1 for c in CATEGORY_LIST if cats[c])
    has_url = sum(1 for f in files if f.get("url"))
    print(f"[OK] 完成! {total} 个文件 -> {active} 个分类, {has_url} 个有下载链接")


if __name__ == "__main__":
    try:
        scan()
    except Exception as e:
        print(f"[ERR] 失败: {e}")
        traceback.print_exc()
        exit(1)
