"""Local VP board generator. Python standard library only."""

from __future__ import annotations

import json
import re
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
MAX_BODY = 30 * 1024 * 1024
MAX_REMOTE = 30 * 1024 * 1024


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "CCPC-VP-Board/1.0"})
    with urlopen(request, timeout=25) as response:
        if int(response.headers.get("Content-Length", "0")) > MAX_REMOTE:
            raise ValueError("榜单文件超过 30 MB")
        payload = response.read(MAX_REMOTE + 1)
    if len(payload) > MAX_REMOTE:
        raise ValueError("榜单文件超过 30 MB")
    return json.loads(payload)


def rankland_data(value: str) -> dict:
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {
        "rl.algoux.cn", "rl.algoux.org", "cdn.algoux.cn"
    }:
        raise ValueError("请使用 rl.algoux.cn 的榜单链接或 RankLand CDN JSON 链接")
    if parsed.hostname == "cdn.algoux.cn":
        if not parsed.path.endswith(".json"):
            raise ValueError("CDN 链接需指向 JSON 文件")
        return fetch_json(value)
    path = parsed.path.rstrip("/")
    match = re.fullmatch(r"/ranklist/([A-Za-z0-9_-]+)", path)
    if match:
        contest_id = match.group(1)
    elif re.fullmatch(r"/collection/[A-Za-z0-9_-]+", path):
        contest_id = parse_qs(parsed.query).get("rankId", [""])[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", contest_id):
            raise ValueError("合集链接缺少有效的 rankId 参数，请在合集里先选中一场比赛")
    else:
        raise ValueError("请使用 RankLand 榜单页或带 rankId 的合集链接")
    origin = f"https://{parsed.hostname}"
    meta = fetch_json(f"{origin}/api/v2/public/contests/{contest_id}")
    if not meta.get("success") or meta.get("code") != 0:
        raise ValueError("RankLand 没有返回有效比赛信息")
    file_id = (meta.get("data") or {}).get("srkFileID")
    if not file_id:
        raise ValueError("该榜单没有可下载的 SRK 文件")
    info = fetch_json(f"{origin}/api/v2/public/files/{file_id}")
    if not info.get("success") or info.get("code") != 0:
        raise ValueError("RankLand 没有返回有效文件信息")
    file_url = (info.get("data") or {}).get("url", "")
    parsed_file = urlparse(file_url)
    if parsed_file.scheme != "https" or parsed_file.hostname not in {
        "cdn.algoux.cn", "srk-assets.algoux.cn", "rl.algoux.cn", "rl.algoux.org"
    }:
        raise ValueError("RankLand 返回了不支持的文件地址")
    return fetch_json(file_url)


def validate_srk(data: dict) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("contest"), dict) or not isinstance(data.get("problems"), list) or not isinstance(data.get("rows"), list):
        raise ValueError("文件不是有效的 SRK 榜单：缺少 problems 或 rows")
    if not data["problems"] or not data["rows"]:
        raise ValueError("榜单没有题目或队伍")
    length = len(data["problems"])
    for index, row in enumerate(data["rows"]):
        if not isinstance(row, dict) or not isinstance(row.get("statuses"), list) or len(row["statuses"]) != length:
            raise ValueError(f"第 {index + 1} 行的题目状态数量不匹配")
        if not isinstance(row.get("user"), dict):
            raise ValueError(f"第 {index + 1} 行缺少队伍信息")


def make_board(data: dict, start_at: str, mode: str = "ccpc") -> Path:
    validate_srk(data)
    if mode not in {"ccpc", "icpc"}:
        raise ValueError("赛制必须为 CCPC 或 ICPC")
    start = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
    if start.tzinfo is None:
        raise ValueError("开始时间需要时区")
    payload = json.dumps({"ranklist": data, "startAt": start.isoformat(), "mode": mode}, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace("&", "\\u0026")
    template = (ROOT / "board.html").read_text(encoding="utf-8")
    html = template.replace("/*__VP_DATA__*/", payload)
    OUTPUT.mkdir(exist_ok=True)
    title = data.get("contest", {}).get("title", "VP榜单")
    if isinstance(title, dict):
        title = title.get("zh-CN") or title.get("fallback") or "VP榜单"
    safe = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", str(title), flags=re.UNICODE).strip("_")[:48] or "VP榜单"
    filename = f"{safe}_{mode.upper()}_{start.strftime('%Y%m%d_%H%M')}_{uuid4().hex[:8]}.html"
    path = OUTPUT / filename
    path.write_text(html, encoding="utf-8")
    return path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self.send_file(ROOT / "index.html", "text/html; charset=utf-8")
        elif self.path.startswith("/output/"):
            filename = unquote(self.path.removeprefix("/output/"))
            if filename != Path(filename).name or not filename.endswith(".html"):
                self.send_error(404)
                return
            path = OUTPUT / filename
            if path.is_file():
                self.send_file(path, "text/html; charset=utf-8")
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size < 1 or size > MAX_BODY:
                raise ValueError("请求大小需在 30 MB 以内")
            request = json.loads(self.rfile.read(size))
            source = request.get("source")
            if source == "url":
                data = rankland_data(request.get("url", ""))
            elif source == "file":
                data = request.get("data")
            else:
                raise ValueError("请选择榜单链接或 JSON 文件")
            path = make_board(data, request.get("startAt", ""), request.get("mode", "ccpc"))
            body = json.dumps({"filename": path.name, "url": f"/output/{quote(path.name)}"}, ensure_ascii=False).encode("utf-8")
            status = 200
        except Exception as exc:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            status = 400
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("VP 榜单生成器：http://127.0.0.1:8765/")
    print("按 Ctrl+C 停止")
    threading.Timer(0.5, lambda: webbrowser.open("http://127.0.0.1:8765/")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
