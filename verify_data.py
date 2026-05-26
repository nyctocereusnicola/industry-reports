"""验证数据完整性"""
import json, glob, os

CAT_DIR = "docs/data/categories"
files = sorted(glob.glob(f"{CAT_DIR}/*.json"))

total = 0
for f in files:
    name = os.path.basename(f)
    if name in ("_index.json", "_duplicates.json"):
        continue
    d = json.load(open(f, "r", encoding="utf-8"))
    cnt = d.get("count", len(d.get("files", [])))
    total += cnt
    sample = ""
    if d.get("files"):
        first = d["files"][0]
        sample = f" -> e.g. [{first.get('score','?')}] {first.get('title','?')[:50]}"
    print(f"  {name:20s} : {cnt:3d} 篇{sample}")

print(f"\n  总计: {total} 篇")
