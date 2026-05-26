"""
夸克网盘连接测试 —— 验证 Cookie 和 FID 是否有效
用法: 
  先设置环境变量 QUARK_COOKIE 和 QUARK_ROOT_FID
  然后运行: python test_quark.py
"""
import os, httpx, json, time

COOKIE = os.getenv("QUARK_COOKIE", "")
FID = os.getenv("QUARK_ROOT_FID", "0")

if not COOKIE:
    print("请先设置 QUARK_COOKIE 环境变量！")
    print('PowerShell: $env:QUARK_COOKIE="你的cookie值"')
    exit(1)

BASE = "https://drive-pc.quark.cn/1/clouddrive"
HEADERS = {
    "cookie": COOKIE,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "origin": "https://pan.quark.cn",
    "referer": "https://pan.quark.cn/",
}

print("=== 夸克网盘连接测试 ===")
print(f"Cookie 长度: {len(COOKIE)}")
print(f"目标 FID: {FID}")
print()

# 测试1: 获取根目录文件列表
print("--- 测试1: 获取文件列表 ---")
params = {
    "pdir_fid": FID,
    "_page": "1",
    "_size": "10",
    "_sort": "file_name:asc",
    "_fetch_total": "1",
    "pr": "ucpro",
    "fr": "pc",
}
try:
    r = httpx.get(f"{BASE}/file/sort", headers=HEADERS, params=params, timeout=30)
    print(f"HTTP 状态码: {r.status_code}")
    data = r.json()
    print(f"响应code: {data.get('code')}, status: {data.get('status')}")

    if data.get("code") == 0 or data.get("status") == 200:
        file_data = data.get("data", {})
        total = file_data.get("total", 0)
        items = file_data.get("list", [])
        print(f"文件总数: {total}")
        print(f"返回条数: {len(items)}")
        if items:
            print(f"\n前5个条目:")
            for item in items[:5]:
                name = item.get("file_name", item.get("name", "???"))
                is_dir = item.get("dir", False)
                fid = item.get("fid", "???")
                print(f"  {'[DIR]' if is_dir else '[FILE]'} {name} (fid={fid})")
        else:
            print("列表为空！")
            print(f"完整响应: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"API 错误! 完整响应:")
        print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
except Exception as e:
    print(f"请求失败: {e}")

# 测试2: 获取用户信息（验证Cookie有效性）
print("\n--- 测试2: 验证用户身份 ---")
try:
    r = httpx.get(f"{BASE}/user/info", headers=HEADERS, timeout=30)
    print(f"HTTP 状态码: {r.status_code}")
    data = r.json()
    if data.get("code") == 0:
        nick = data.get("data", {}).get("nickname", "???")
        print(f"登录用户: {nick}")
    else:
        print(f"用户信息获取失败: {json.dumps(data, ensure_ascii=False)[:300]}")
except Exception as e:
    print(f"请求失败: {e}")

print("\n=== 测试完成 ===")
