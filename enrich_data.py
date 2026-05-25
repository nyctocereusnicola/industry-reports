"""
从报告文件名中提取：标题、摘要、行业标签、日期、质量评分
+ 两层去重：
  Level 1 - Token 去重：同一飞书 file token 只保留一份
  Level 2 - 标题相似去重：归一化标题后同内容保留最佳版本
重新生成 enriched JSON + _duplicates.json
"""
import json, os, re, time, random

SRC = "docs/data/categories"
DST = "docs/data/categories"

# 来源词库与质量评分
SOURCE_SCORE = {
    # 券商/研究机构 → 高分
    "天风证券": 95, "国信证券": 93, "东方证券": 92, "申万宏源": 93,
    "德邦证券": 88, "万联证券": 85, "国金证券": 90,
    # 咨询/巨头 → 高分
    "毕马威": 95, "德勤": 93, "艾瑞咨询": 90, "沙利文": 88,
    "亿欧智库": 85, "头豹研究院": 83, "尼尔森": 88, "NIQ": 88,
    "京东": 82, "天猫": 82, "巨量引擎": 85, "巨量营销科学": 85,
    # 数据平台 → 中高分
    "蝉妈妈": 80, "蝉魔方": 80, "炼丹炉": 80, "解数咨询": 82,
    "魔镜洞察": 80, "果集行研": 78, "洞见研报": 75,
    "MobTech": 75, "艺恩": 78, "维卓": 75,
    # 平台 → 中分
    "小红书": 78, "抖音电商": 76, "TikTok": 74, "Shopee": 72,
    "阿里巴巴": 80, "淘天": 78,
    # 品牌/营销 → 中分
    "品牌": 65, "营销": 65,
    # 其他
    "亚宠研究院": 75, "西窗科技": 72, "大数跨境": 70,
}

# 标签关键词 → 标签
TAG_KEYWORDS = [
    ("趋势", "趋势分析"), ("洞察", "消费洞察"), ("白皮书", "行业白皮书"),
    ("品牌", "品牌研究"), ("营销", "营销策略"), ("电商", "电商数据"),
    ("抖音", "抖音"), ("小红书", "小红书"), ("TikTok", "TikTok"),
    ("市场竞争", "竞争格局"), ("出海", "跨境电商"), ("全球", "全球化"),
    ("消费者", "消费者研究"), ("品类", "品类分析"), ("食品", "食品"),
    ("保健品", "保健品"), ("用品", "消费品"), ("服务", "服务"),
    ("经济", "经济分析"), ("消费", "消费趋势"), ("新品", "新品"),
    ("供应链", "供应链"), ("增长", "增长趋势"), ("数字化", "数字化"),
    ("618", "618"), ("双11", "双11"), ("双十一", "双11"),
    ("宠物", "宠物"), ("洗发", "日化"), ("香氛", "香氛"), ("香水", "香水"),
    ("美妆", "美妆"), ("护肤", "护肤"), ("彩妆", "彩妆"),
    ("户外", "户外"), ("运动", "运动"), ("家居", "家居"),
    ("母婴", "母婴"), ("食品饮料", "食品饮料"), ("咖啡", "咖啡"),
    ("奢侈品", "奢侈品"), ("时尚", "时尚"),
]

def extract_metadata(filename):
    name_no_ext = re.sub(r'\.(pdf|docx?|pptx?|xlsx?)$', '', filename)
    
    # 提取年份
    year_match = re.search(r'(20\d{2})', name_no_ext)
    year = year_match.group(1) if year_match else "未知"
    
    # 提取来源
    source = ""
    source_score = 50
    for s, sc in sorted(SOURCE_SCORE.items(), key=lambda x: -len(x[0])):
        if s in name_no_ext and len(s) > len(source):
            source = s
            source_score = sc
    
    # 如果没匹配到，根据文件名长度和关键词给分
    if not source:
        if "报告" in name_no_ext or "研究" in name_no_ext:
            source_score = 68
        elif "白皮书" in name_no_ext:
            source_score = 72
    
    # 提取标签
    tags = []
    for kw, tag in TAG_KEYWORDS:
        if kw in name_no_ext and tag not in tags:
            tags.append(tag)
    if not tags:
        tags = ["行业报告"]
    
    # 生成摘要：取文件名中较有信息量的部分
    # 清理文件名中的格式信息
    summary = name_no_ext
    # 去掉年份+空格开头
    summary = re.sub(r'^20\d{2}\s*', '', summary)
    # 去掉末尾来源+日期
    summary = re.sub(r'[-_].{0,30}$', '', summary).strip()
    if len(summary) < 5:
        summary = name_no_ext[:80]
    
    # 如果有来源，加上来源信息
    if source:
        summary = summary.rstrip("-_") + f"（数据来源：{source}）"
    
    # 提取月份（如果有的话）
    month = ""
    month_match = re.search(r'(20\d{2})(0[1-9]|1[0-2])', name_no_ext)
    if month_match:
        month = month_match.group(0)
    
    # 尝试解析完整日期
    date = year
    if month:
        date = f"{month_match.group(1)}-{month_match.group(2)}"
    
    return {
        "title": name_no_ext[:120],
        "summary": summary[:200],
        "tags": tags[:6],
        "year": year,
        "month": month,
        "date": date,
        "source": source,
        "score": source_score,
    }

# ==================== 去重 ====================

def normalize_title(title):
    """归一化标题：只去掉年份/页数等噪音，保留月份等区分信息"""
    t = re.sub(r'\.(pdf|docx?|pptx?|xlsx?)$', '', title, flags=re.I)
    t = re.sub(r'20\d{2}', '', t)                      # 去掉年份（2021, 2022...）
    t = re.sub(r'\d+页', '', t)                         # 去掉页数标记
    t = re.sub(r'[-_\s（）()\[\]【】《》""''·•,，。；;：:！!？?…/\\|@#$%^&*+=~`×]+', '', t)
    t = t.lower().strip()
    return t

def dedup_files(files):
    """两层去重返回 (clean_files, removed_files)"""
    removed = []

    # Level 1: Token 去重
    seen_tokens = {}
    token_clean = []
    for f in files:
        tok = f.get("token", "")
        if tok and tok in seen_tokens:
            exist = seen_tokens[tok]
            if (f.get("score", 0) > exist.get("score", 0)):
                removed.append({**exist, "_dup_reason": "token重复(被更高分替换)", "_dup_of": tok})
                seen_tokens[tok] = f
                for i, item in enumerate(token_clean):
                    if item.get("token") == tok:
                        token_clean[i] = f; break
            else:
                removed.append({**f, "_dup_reason": "token重复", "_dup_of": tok})
        else:
            seen_tokens[tok] = f
            token_clean.append(f)

    # Level 2: 标题相似去重（同归一化key + 同年 → 保留最优）
    norm_groups = {}
    for f in token_clean:
        key = normalize_title(f.get("name", ""))
        yr = f.get("year", "未知")
        gk = (key, yr)
        norm_groups.setdefault(gk, []).append(f)

    clean = []
    for (nkey, yr), group in norm_groups.items():
        if len(group) == 1:
            clean.append(group[0])
        else:
            group.sort(key=lambda x: (x.get("score", 0), len(x.get("name", ""))), reverse=True)
            best = group[0]
            clean.append(best)
            for dup in group[1:]:
                removed.append({**dup,
                    "_dup_reason": f"标题相似去重(key={nkey[:30]}... 同年={yr})",
                    "_dup_of": best.get("title", "")[:60]})
    return clean, removed


def main():
    os.makedirs(DST, exist_ok=True)
    categories = ["潮流时尚","宠物","抖音","小红书","美妆",
                  "海外市场","户外与运动","家居","健康养生","快消品",
                  "母婴","其他","奢侈品","食品饮料","香相关"]
    
    total_enriched = 0
    total_removed = 0
    all_removed = []
    
    for cat in categories:
        fname = os.path.join(SRC, f"{cat}.json")
        if not os.path.exists(fname):
            print(f"  [{cat}] 文件不存在，跳过")
            continue
        
        with open(fname, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        files = data.get("files", [])
        enriched_files = []
        
        for f_item in files:
            original_name = f_item.get("name", "")
            meta = extract_metadata(original_name)
            enriched = {
                **f_item,
                **meta,
            }
            # 将 modified timestamp 转换为可读日期
            mod_ts = f_item.get("modified", "")
            if mod_ts and mod_ts.isdigit():
                try:
                    mod_dt = time.strftime("%Y-%m-%d", time.localtime(int(mod_ts)))
                    enriched["modified_date"] = mod_dt
                except:
                    enriched["modified_date"] = mod_ts
            enriched_files.append(enriched)
        
        # --- 去重 ---
        clean_files, removed_files = dedup_files(enriched_files)
        enriched_files = clean_files  # 后续输出去重后的
        
        # 按评分降序排列
        enriched_files.sort(key=lambda x: x.get("score", 0), reverse=True)
        removed_files.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        out_data = {
            "category": cat,
            "count": len(enriched_files),
            "dup_removed": len(removed_files),
            "files": enriched_files,
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 也保留被去重的文件（供前端可切换查看）
        if removed_files:
            out_data["_removed"] = removed_files
        
        out_fname = os.path.join(DST, f"{cat}.json")
        with open(out_fname, "w", encoding="utf-8") as f:
            json.dump(out_data, f, ensure_ascii=False)
        
        mb = os.path.getsize(out_fname) / (1024*1024)
        print(f"  [{cat}] {len(enriched_files)}条 (去重{len(removed_files)}), {mb:.2f}MB")
        total_enriched += len(enriched_files)
        total_removed += len(removed_files)
        all_removed.extend(removed_files)
    
    # 输出去重详情
    if all_removed:
        dup_out = os.path.join(DST, "_duplicates.json")
        with open(dup_out, "w", encoding="utf-8") as f:
            json.dump({"count": len(all_removed), "duplicates": all_removed}, f, ensure_ascii=False, indent=2)
        print(f"\n  去重详情: {dup_out}")
    
    # 更新索引
    index = {
        "categories": categories,
        "total_files": total_enriched,
        "dup_removed": total_removed,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "counts": {}
    }
    for cat in categories:
        fname = os.path.join(DST, f"{cat}.json")
        if os.path.exists(fname):
            with open(fname, "r", encoding="utf-8") as f:
                d = json.load(f)
            index["counts"][cat] = d["count"]
    
    with open(os.path.join(DST, "_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n总计: {total_enriched} 条 (已去重 {total_removed} 条)")
    
    # 打印几条示例
    print("\n--- 示例（宠物前3条）---")
    fname = os.path.join(DST, "宠物.json")
    if os.path.exists(fname):
        with open(fname, "r", encoding="utf-8") as f:
            d = json.load(f)
        for item in d["files"][:3]:
            print(f"  标题: {item['title'][:60]}")
            print(f"  摘要: {item['summary'][:80]}")
            print(f"  标签: {item['tags']}")
            print(f"  来源: {item['source']} | 评分: {item['score']} | 年份: {item['year']}")
            print()

if __name__ == "__main__":
    main()
