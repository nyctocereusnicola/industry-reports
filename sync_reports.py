"""
椋炰功鎶ュ憡鍚屾鑴氭湰锛堜釜浜虹増椋炰功 / GitHub Actions 涓撶敤锛?

鍔熻兘锛?
- 浣跨敤 app_access_token 璁よ瘉锛堜釜浜虹増椋炰功锛?
- 閫掑綊鎵弿鏍规枃浠跺す涓嬬殑鎵€鏈夊瓙鏂囦欢澶?
- 鑷姩鎸夊瓙鏂囦欢澶瑰悕绉板垎閰嶈涓氬垎绫?
- 鐢熸垚 docs/data/reports.json 渚涢潤鎬佺綉绔欎娇鐢?
- 鏀寔澧為噺鏇存柊锛堟寜 file_token 鍘婚噸锛?

鐜鍙橀噺锛?
    FEISHU_APP_ID        椋炰功搴旂敤 App ID
    FEISHU_APP_SECRET    椋炰功搴旂敤 App Secret
    FEISHU_FOLDER_TOKEN  鏍规枃浠跺す Token
"""

import os
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import httpx

# 鈹€鈹€鈹€ 璺緞 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "docs" / "data"
REPORTS_FILE = DATA_DIR / "reports.json"
SYNC_LOG_FILE = DATA_DIR / "sync_log.json"

# 鈹€鈹€鈹€ 椋炰功 API 瀹㈡埛绔?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
class FeishuClient:
    """椋炰功涓汉鐗?API 瀹㈡埛绔紙app_access_token锛?""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expire_at: float = 0

    def _get_access_token(self) -> str:
        """鑾峰彇 app_access_token锛堜釜浜虹増椋炰功鐢ㄨ繖涓級"""
        if self._access_token and time.time() < self._token_expire_at - 60:
            return self._access_token

        resp = httpx.post(
            f"{self.BASE_URL}/auth/v3/app_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"鑾峰彇 access_token 澶辫触: {data.get('msg', data)}")

        self._access_token = data["app_access_token"]
        self._token_expire_at = time.time() + data.get("expire", 7200)
        return self._access_token

    def list_folder_files(
        self, folder_token: str, page_size: int = 50, page_token: Optional[str] = None
    ) -> dict:
        """鑾峰彇鏂囦欢澶逛笅鐨勬枃浠跺垪琛紙鍗曢〉锛?""
        token = self._get_access_token()
        params = {"folder_token": folder_token, "page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        resp = httpx.get(
            f"{self.BASE_URL}/drive/v1/files",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"鑾峰彇鏂囦欢鍒楄〃澶辫触: {data.get('msg', data)}")
        return data.get("data", {})

    def list_all_files(self, folder_token: str) -> list:
        """鑾峰彇鏂囦欢澶逛笅鎵€鏈夋枃浠讹紙鑷姩澶勭悊鍒嗛〉锛?""
        all_files = []
        page_token = None
        while True:
            result = self.list_folder_files(folder_token, page_size=50, page_token=page_token)
            files = result.get("files", [])
            all_files.extend(files)
            if not result.get("has_more"):
                break
            page_token = result.get("page_token")
        return all_files

    def recursive_list(self, folder_token: str, category: str = "") -> list[dict]:
        """
        閫掑綊鎵弿鏂囦欢澶癸細杩斿洖鎵€鏈夋枃妗ｏ紙璺宠繃宓屽瀛愭枃浠跺す锛?
        姣忎釜鏂囨。棰濆闄勫甫 _category 瀛楁锛堟潵鑷《灞傚瓙鏂囦欢澶瑰悕锛?
        """
        all_docs = []
        files = self.list_all_files(folder_token)
        for f in files:
            ftype = f.get("type", "")
            if ftype == "folder":
                # 閫掑綊杩涘叆瀛愭枃浠跺す锛屽垎绫诲悕缁ф壙鐖舵枃浠跺す鍚?
                sub_cat = f.get("name", category)
                sub_docs = self.recursive_list(f.get("token"), sub_cat)
                all_docs.extend(sub_docs)
            else:
                f["_category"] = category
                all_docs.append(f)
        return all_docs

    @staticmethod
    def build_file_url(file_token: str, file_type: str) -> str:
        """鏍规嵁鏂囦欢绫诲瀷鏋勫缓椋炰功 Web 璁块棶閾炬帴锛堜釜浜虹増鐢?my.feishu.cn锛?""
        type_url_map = {
            "doc": f"https://my.feishu.cn/docx/{file_token}",
            "docx": f"https://my.feishu.cn/docx/{file_token}",
            "sheet": f"https://my.feishu.cn/sheets/{file_token}",
            "bitable": f"https://my.feishu.cn/base/{file_token}",
            "slides": f"https://my.feishu.cn/slides/{file_token}",
            "mindnote": f"https://my.feishu.cn/mindnotes/{file_token}",
        }
        return type_url_map.get(
            file_type,
            f"https://my.feishu.cn/drive/home/?mode=detail&file_token={file_token}",
        )

    @staticmethod
    def get_file_extension(file_type: str, name: str) -> str:
        """鑾峰彇鏂囦欢鎵╁睍鍚?绫诲瀷鏍囩"""
        ext_map = {
            "doc": "椋炰功鏂囨。",
            "docx": "椋炰功鏂囨。",
            "sheet": "椋炰功琛ㄦ牸",
            "bitable": "澶氱淮琛ㄦ牸",
            "slides": "骞荤伅鐗?,
            "mindnote": "鎬濈淮瀵煎浘",
        }
        if file_type in ext_map:
            return ext_map[file_type]
        if "." in name:
            ext = name.rsplit(".", 1)[-1].upper()
            return ext if len(ext) <= 8 else "鏂囦欢"
        return "鏂囦欢"


# 鈹€鈹€鈹€ 绀轰緥鏁版嵁锛堥娆℃棤椋炰功鏁版嵁鏃跺睍绀猴級鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
def get_demo_reports() -> list:
    now = datetime.now(timezone.utc)
    return [
        {
            "file_token": "demo_001",
            "title": "2025骞翠腑鍥芥柊鑳芥簮姹借溅琛屼笟娣卞害娲炲療鎶ュ憡",
            "file_type": "doc",
            "file_ext": "椋炰功鏂囨。",
            "summary": "鍏ㄩ潰鍒嗘瀽浜?025骞翠腑鍥芥柊鑳芥簮姹借溅甯傚満鏍煎眬锛屾兜鐩栧競鍦鸿妯°€佺珵浜夋€佸娍銆佹妧鏈矾绾裤€佹秷璐硅€呮礊瀵熺瓑鏍稿績缁村害銆傛姤鍛婃寚鍑猴紝涓浗鏂拌兘婧愭苯杞︽笚閫忕巼宸茬獊鐮?5%锛屾櫤鑳藉寲鎴愪负宸紓鍖栫珵浜夌殑鍏抽敭銆?,
            "feishu_url": "#",
            "tags": "鏂拌兘婧愭苯杞?姹借溅,琛屼笟鎶ュ憡",
            "category": "姹借溅鍑鸿",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_002",
            "title": "2025骞碅I澶фā鍨嬪簲鐢ㄨ惤鍦拌秼鍔挎姤鍛?,
            "file_type": "docx",
            "file_ext": "椋炰功鏂囨。",
            "summary": "娣卞叆鍒嗘瀽2025骞碅I澶фā鍨嬩粠鎶€鏈帰绱㈣蛋鍚戝晢涓氳惤鍦扮殑鍏抽敭瓒嬪娍锛屽寘鎷珹gent鏅鸿兘浣撱€佸妯℃€佸簲鐢ㄣ€佽涓氬瀭鐩存ā鍨嬬瓑鏂瑰悜鐨勬渶鏂拌繘灞曚笌鎶曡祫鏈轰細銆?,
            "feishu_url": "#",
            "tags": "浜哄伐鏅鸿兘,AI,澶фā鍨?绉戞妧",
            "category": "绉戞妧鍓嶆部",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_003",
            "title": "2025Q1涓浗娑堣垂甯傚満澶嶈嫃鎶ュ憡",
            "file_type": "sheet",
            "file_ext": "椋炰功琛ㄦ牸",
            "summary": "鍩轰簬2025骞寸涓€瀛ｅ害澶氱淮搴︽秷璐规暟鎹紝绯荤粺姊崇悊娑堣垂澶嶈嫃鐨勭粨鏋勬€х壒寰侊紝鍖呮嫭绾夸笂绾夸笅娑堣垂瓒嬪娍鍙樺寲銆佷笅娌夊競鍦哄闀垮姩鍔涘強鏂板叴娑堣垂鍝佺墝宕涜捣璺緞銆?,
            "feishu_url": "#",
            "tags": "娑堣垂,闆跺敭,鐢靛晢",
            "category": "娑堣垂闆跺敭",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_004",
            "title": "鍏ㄧ悆鍗婂浣撲骇涓氶摼閲嶆瀯涓庝腑鍥芥満閬?,
            "file_type": "doc",
            "file_ext": "椋炰功鏂囨。",
            "summary": "鍒嗘瀽鍏ㄧ悆鍗婂浣撲骇涓氶摼鍦ㄥ湴缂樻斂娌诲奖鍝嶄笅鐨勯噸鏋勮秼鍔匡紝鍖呮嫭鑺墖璁捐銆佸埗閫犮€佸皝娴嬪悇鐜妭鐨勬牸灞€鍙樺寲锛屼互鍙婁腑鍥藉崐瀵间綋浜т笟鐨勬垬鐣ユ満閬囦笌鎸戞垬銆?,
            "feishu_url": "#",
            "tags": "鍗婂浣?鑺墖,浜т笟閾?,
            "category": "绉戞妧鍓嶆部",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_005",
            "title": "涓浗鍖荤枟鍋ュ悍浜т笟鎶曡瀺璧勮秼鍔?025",
            "file_type": "bitable",
            "file_ext": "澶氱淮琛ㄦ牸",
            "summary": "璺熻釜2025骞村尰鐤楀仴搴烽鍩熺殑鎶曡瀺璧勫姩鎬侊紝閲嶇偣鍒嗘瀽鍒涙柊鑽€佸尰鐤楀櫒姊般€佹暟瀛楀尰鐤椼€丄I鍒惰嵂绛夌粏鍒嗚禌閬撶殑璧勬湰娴佸悜涓庝及鍊煎彉鍖栥€?,
            "feishu_url": "#",
            "tags": "鍖荤枟,鍋ュ悍,鎶曡瀺璧?,
            "category": "鍖荤枟鍋ュ悍",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_006",
            "title": "2025璺ㄥ鐢靛晢鍑烘捣鐧界毊涔?,
            "file_type": "docx",
            "file_ext": "椋炰功鏂囨。",
            "summary": "鑱氱劍涓浗鍝佺墝鍑烘捣瓒嬪娍锛岃鐩栦笢鍗椾簹銆佹媺缇庛€佷腑涓滅瓑鏂板叴甯傚満鐨勭數鍟嗙敓鎬佸垎鏋愶紝鍖呮嫭骞冲彴閫夋嫨绛栫暐銆佹湰鍦板寲杩愯惀銆佹敮浠樼墿娴佸熀纭€璁炬柦绛夊叧閿礊瀵熴€?,
            "feishu_url": "#",
            "tags": "璺ㄥ鐢靛晢,鍑烘捣,鍏ㄧ悆鍖?,
            "category": "鐢靛晢璐告槗",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_007",
            "title": "ESG涓庝紒涓氬彲鎸佺画鍙戝睍鎶ュ憡鎸囧崡2025",
            "file_type": "doc",
            "file_ext": "椋炰功鏂囨。",
            "summary": "瑙ｈ鍥藉唴澶朎SG鏈€鏂版斂绛栦笌鎶湶鏍囧噯锛屽垎鏋愬ご閮ㄤ紒涓氬湪鐜銆佺ぞ浼氥€佹不鐞嗘柟闈㈢殑鏈€浣冲疄璺碉紝涓轰紒涓欵SG鎴樼暐瑙勫垝鎻愪緵鏂规硶璁轰笌宸ュ叿鍙傝€冦€?,
            "feishu_url": "#",
            "tags": "ESG,鍙寔缁彂灞?纰充腑鍜?,
            "category": "瀹忚缁忔祹",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        {
            "file_token": "demo_008",
            "title": "涓浗娓告垙琛屼笟甯傚満瑙勬ā涓庣敤鎴锋礊瀵?025",
            "file_type": "doc",
            "file_ext": "椋炰功鏂囨。",
            "summary": "鍏ㄩ潰瑙ｆ瀽2025骞翠腑鍥芥父鎴忓競鍦猴紝瑕嗙洊鎵嬫父銆佺娓搞€佷富鏈烘父鎴忋€佸皬娓告垙绛夌粏鍒嗗競鍦猴紝鍖呮嫭鐢ㄦ埛琛屼负鍒嗘瀽銆佷粯璐规ā寮忚秼鍔裤€佸嚭娴风瓥鐣ョ瓑鏍稿績鍐呭銆?,
            "feishu_url": "#",
            "tags": "娓告垙,鏂囧ū,浜掕仈缃?,
            "category": "鏂囧ū浼犲獟",
            "view_count": 0,
            "feishu_modified": (now - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    ]


# 鈹€鈹€鈹€ 鍚屾閫昏緫 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
def sync_feishu_to_json() -> dict:
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    folder_token = os.getenv("FEISHU_FOLDER_TOKEN", "")

    # 鍔犺浇宸叉湁鏁版嵁
    existing_reports = []
    existing_tokens = set()
    if REPORTS_FILE.exists():
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            existing_reports = [
                r for r in data.get("reports", [])
                if not r.get("file_token", "").startswith("demo_")
            ]
            existing_tokens = {r["file_token"] for r in existing_reports}
        except Exception:
            pass

    if not app_id or not app_secret or not folder_token:
        print("[INFO] 鏈厤缃涔﹀嚟璇侊紝灏嗕娇鐢ㄧず渚嬫暟鎹?)
        return {"status": "skipped", "reason": "鏈厤缃涔﹀嚟璇?}

    try:
        client = FeishuClient(app_id, app_secret)

        # 閫掑綊鎵弿鏍规枃浠跺す锛堝惈鎵€鏈夊瓙鏂囦欢澶癸級
        print(f"[INFO] 寮€濮嬮€掑綊鎵弿鏍规枃浠跺す: {folder_token}")
        all_files = client.recursive_list(folder_token)
        print(f"[INFO] 鎵弿瀹屾垚锛屽叡 {len(all_files)} 涓枃妗?)

        new_count = 0
        update_count = 0

        for f in all_files:
            token = f.get("token", "")
            file_type = f.get("type", "file")
            name = f.get("name", "鏈懡鍚?)
            category = f.get("_category", "")

            report_data = {
                "file_token": token,
                "title": name,
                "file_type": file_type,
                "file_ext": FeishuClient.get_file_extension(file_type, name),
                "summary": "",
                "feishu_url": f.get("url") or FeishuClient.build_file_url(token, file_type),
                "tags": "",
                "category": category,
                "view_count": 0,
                "feishu_modified": f.get("modified_time", ""),
            }

            if token in existing_tokens:
                for i, r in enumerate(existing_reports):
                    if r["file_token"] == token:
                        report_data["summary"] = r.get("summary", "")
                        report_data["tags"] = r.get("tags", "")
                        report_data["view_count"] = r.get("view_count", 0)
                        # 淇濈暀鎵嬪姩缂栬緫鐨勫垎绫伙紝浣嗗鏋滃師鏉ヤ负绌哄垯鐢ㄦ枃浠跺す鍚?
                        if not report_data["category"]:
                            report_data["category"] = r.get("category", category)
                        existing_reports[i] = report_data
                        break
                update_count += 1
            else:
                existing_reports.append(report_data)
                existing_tokens.add(token)
                new_count += 1

        print(f"[OK] 鍚屾瀹屾垚锛氬叡 {len(all_files)} 涓枃浠讹紝鏂板 {new_count}锛屾洿鏂?{update_count}")
        return {
            "status": "success",
            "file_count": len(all_files),
            "new_count": new_count,
            "update_count": update_count,
        }

    except Exception as e:
        print(f"[ERROR] 鍚屾澶辫触: {e}")
        return {"status": "error", "reason": str(e)}


def write_reports_json(feishu_reports: list, sync_result: dict):
    """鐢熸垚鏈€缁堢殑 reports.json"""
    demo_reports = get_demo_reports() if sync_result["status"] != "success" else []
    all_reports = demo_reports + feishu_reports
    all_reports.sort(key=lambda r: r.get("feishu_modified", ""), reverse=True)

    categories = {}
    for r in all_reports:
        cat = r.get("category", "鏈垎绫?) or "鏈垎绫?
        categories[cat] = categories.get(cat, 0) + 1

    output = {
        "reports": all_reports,
        "stats": {
            "total": len(all_reports),
            "categories": [
                {"name": k, "count": v}
                for k, v in sorted(categories.items(), key=lambda x: -x[1])
            ],
            "last_sync": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 鍚屾鏃ュ織
    log_entry = {
        "synced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **sync_result,
    }
    try:
        existing_logs = []
        if SYNC_LOG_FILE.exists():
            with open(SYNC_LOG_FILE, "r", encoding="utf-8") as f:
                existing_logs = json.load(f)
        existing_logs.insert(0, log_entry)
        existing_logs = existing_logs[:50]
        with open(SYNC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] 鍐欏叆鍚屾鏃ュ織澶辫触: {e}")

    print(f"[OK] 宸茬敓鎴?{REPORTS_FILE}锛屽叡 {len(all_reports)} 鏉℃姤鍛?)


# 鈹€鈹€鈹€ 涓诲叆鍙?鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€
if __name__ == "__main__":
    print("=" * 60)
    print("  琛屼笟鎶ュ憡闆嗗悎绔?- 椋炰功鍚屾鑴氭湰 (涓汉鐗?")
    print(f"  鏃堕棿: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    sync_result = sync_feishu_to_json()

    # 璇诲彇椋炰功鎶ュ憡锛堜笉鍚?demo锛?
    feishu_reports = []
    if REPORTS_FILE.exists():
        try:
            with open(REPORTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            feishu_reports = [
                r for r in data.get("reports", [])
                if not r.get("file_token", "").startswith("demo_")
            ]
        except Exception:
            pass

    # 鍚屾鎴愬姛鏃跺彧淇濈暀椋炰功鏁版嵁锛堜笉鏄剧ず demo锛?
    if sync_result["status"] != "success":
        feishu_reports = []

    write_reports_json(feishu_reports, sync_result)

    print("=" * 60)
    print("  瀹屾垚锛?)
    print("=" * 60)
