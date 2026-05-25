"""飞书云空间扫描脚本 v2
自动扫描根目录下所有子文件夹，按行业分类输出 JSON 到 docs/data/categories/
"""
import httpx, json, time, os, traceback

# 优先从环境变量读取（GitHub Actions），fallback 硬编码（本地）
APP_ID = os.getenv("FEISHU_APP_ID", "cli_aa9bf80b5678dbee")
APP_SECRET = os.getenv("FEISHU_APP_SECRET", "BSrMFRLJSEOv9cngkERqEcg83IRbj2oi")
ROOT = os.getenv("FEISHU_FOLDER_TOKEN", "YYLHfvuCylpAQVdzTRxcdDpgnyc")
BASE = "https://open.feishu.cn/open-apis"
OUT = "docs/data/categories"
DELAY = 0.8

# 文件夹名 → 行业分类映射
CAT_MAP = {
    "潮流時尚": "潮流时尚",
    "潮流时尚": "潮流时尚",
    "寵物": "宠物",
    "宠物": "宠物",
    "抖音平台": "抖音",
    "抖音": "抖音",
    "小紅書平台": "小红书",
    "小红书": "小红书",
    "美妝護膚": "美妆",
    "美妆": "美妆",
    "海外市場": "海外市场",
    "海外市场": "海外市场",
    "戶外與運動": "户外与运动",
    "户外与运动": "户外与运动",
    "家居生活": "家居",
    "家居": "家居",
    "健康養生": "健康养生",
    "健康养生": "健康养生",
    "快消品": "快消品",
    "母嬰": "母婴",
    "母婴": "母婴",
    "其他": "其他",
    "奢侈品": "奢侈品",
    "食品飲料": "食品饮料",
    "食品饮料": "食品饮料",
    "關於香": "香相关",
    "香水香氛香薰": "香相关",
    "香相关": "香相关",
}


def get_token():
    """获取 tenant_access_token"""
    r = httpx.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=15,
    )
    d = r.json()
    if d.get("code") != 0:
        raise Exception(f"获取 token 失败: {d}")
    return d["tenant_access_token"]


def list_folder(token, folder_token, page_token=None):
    """获取文件夹下文件列表"""
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
        raise Exception(f"获取文件列表失败: {d}")
    return d.get("data", {})


def list_all(token, folder_token):
    """获取文件夹下所有文件（自动分页）"""
    all_files = []
    page_token = None
    while True:
        data = list_folder(token, folder_token, page_token)
        files = data.get("files", [])
        for f in files:
            # 只保留需要的字段
            all_files.append({
                "token": f.get("token", ""),
                "name": f.get("name", ""),
                "type": f.get("type", ""),
                "url": f.get("url", ""),
                "created_time": f.get("created_time", ""),
                "modified_time": f.get("modified_time", ""),
                "owner_id": f.get("owner_id", ""),
                "size": f.get("size", 0),
            })
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
        time.sleep(DELAY)
    return all_files


def scan():
    """主扫描流程"""
    print(f"🔑 正在获取飞书 Token...")
    token = get_token()
    print(f"✅ Token 获取成功")

    print(f"📁 正在扫描根文件夹: {ROOT}")
    root_files = list_folder(token, ROOT)
    print(f"   找到 {len(root_files.get('files', []))} 个子文件夹/文件")

    categories = {}
    dup_index = {}
    duplicate_ids = []

    for item in root_files.get("files", []):
        name = item.get("name", "")
        cat_name = CAT_MAP.get(name)
        if not cat_name:
            print(f"   ⏭️  跳过未映射: {name}")
            continue

        token_str = item.get("token", "")
        ftype = item.get("type", "")
        print(f"   📂 {name} → {cat_name} (type={ftype})")

        if ftype == "folder":
            try:
                files = list_all(token, token_str)
            except Exception as e:
                print(f"      ⚠️  获取子文件夹失败: {e}")
                files = []
            print(f"      文件数: {len(files)}")
        else:
            files = [item]

        # 去重检测
        kept = []
        for f in files:
            fid = f.get("token")
            fname = f.get("name", "")
            if fid in dup_index:
                dup_index[fid].append(cat_name)
                duplicate_ids.append(fid)
            else:
                dup_index[fid] = [cat_name]
                kept.append(f)

        categories[cat_name] = {
            "category": cat_name,
            "folder_name": name,
            "file_count": len(kept),
            "files": kept,
        }
        time.sleep(DELAY)

    # 构建去重列表
    duplicates = {
        fid: cats for fid, cats in dup_index.items() if len(cats) > 1
    }

    # 写入输出
    os.makedirs(OUT, exist_ok=True)

    for cat_name, data in categories.items():
        path = os.path.join(OUT, f"{cat_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   💾 写入: {path} ({data['file_count']} 个文件)")

    # 写入索引
    index = {
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_files": sum(d["file_count"] for d in categories.values()),
        "categories": list(categories.keys()),
    }
    with open(os.path.join(OUT, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"📊 索引: {index['total_files']} 个文件, {len(categories)} 个分类")

    # 写入去重数据
    with open(os.path.join(OUT, "_duplicates.json"), "w", encoding="utf-8") as f:
        json.dump(duplicates, f, ensure_ascii=False, indent=2)
    print(f"🔍 去重: {len(duplicates)} 个重复文件")

    print("✅ 扫描完成!")


if __name__ == "__main__":
    try:
        scan()
    except Exception as e:
        print(f"❌ 扫描失败: {e}")
        traceback.print_exc()
        exit(1)
