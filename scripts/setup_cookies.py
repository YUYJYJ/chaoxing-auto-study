# -*- coding: utf-8 -*-
"""从本机浏览器导出学习通 cookie，生成 cookies.txt。

支持 Edge / Chrome：
  1) 若浏览器已开启 CDP 调试端口（9222），直接读取运行时 cookie（推荐，能拿到 HttpOnly）。
  2) 否则提示用户手动从浏览器开发者工具复制 cookie。
"""
import json
import os
import socket
import sys
from pathlib import Path

from common import ROOT, ensure_dirs

BASE64 = __import__("base64")


def find_devtools_port():
    """从常见浏览器的 DevToolsActivePort 文件读取端口。"""
    home = Path.home()
    candidates = [
        home / "AppData/Local/Microsoft/Edge/User Data/DevToolsActivePort",   # Windows Edge
        home / "AppData/Local/Google/Chrome/User Data/DevToolsActivePort",    # Windows Chrome
        home / "Library/Application Support/Google/Chrome/DevToolsActivePort",  # macOS Chrome
        home / ".config/google-chrome/DevToolsActivePort",                    # Linux Chrome
    ]
    for p in candidates:
        if p.exists():
            try:
                lines = [x.strip() for x in p.read_text().split("\n") if x.strip()]
                if lines and lines[0].isdigit():
                    return int(lines[0]), lines[1] if len(lines) > 1 else None
            except Exception:
                pass
    return None, None


class WS:
    """极简 WebSocket 客户端，仅用于 CDP。"""
    def __init__(self, port, path, timeout=15):
        s = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        s.settimeout(timeout)
        key = BASE64.b64encode(os.urandom(16)).decode()
        req = (f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        s.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            d = s.recv(4096)
            if not d:
                raise RuntimeError("握手被关闭")
            buf += d
        head, _, rest = buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError("WebSocket 握手失败: " + head.decode("utf-8", "replace")[:120])
        self.sock, self.buf, self.id = s, rest, 0

    def _exact(self, n):
        while len(self.buf) < n:
            d = self.sock.recv(65536)
            if not d:
                raise RuntimeError("连接关闭")
            self.buf += d
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def call(self, method, params=None):
        import struct
        self.id += 1
        mid = self.id
        payload = json.dumps({"id": mid, "method": method, "params": params or {}}).encode()
        mask = os.urandom(4)
        n = len(payload)
        h = bytearray([0x81])
        if n < 126:
            h.append(0x80 | n)
        elif n < 65536:
            h.append(0x80 | 126); h += struct.pack(">H", n)
        else:
            h.append(0x80 | 127); h += struct.pack(">Q", n)
        h += mask
        self.sock.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        while True:
            b0, b1 = self._exact(2)
            ln = b1 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._exact(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._exact(8))[0]
            if not ln:
                continue
            data = self._exact(ln)
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(str(msg["error"]))
                return msg["result"]

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    ensure_dirs()
    port, path = find_devtools_port()
    if not port:
        print("未发现浏览器 CDP 调试端口。请用方式二手动导出 cookie。")
        print_manual()
        return
    print(f"发现调试端口 {port}，尝试连接...")
    if not path:
        print("未找到 WebSocket 路径，请用方式二。")
        print_manual()
        return
    try:
        ws = WS(port, path)
        cks = ws.call("Storage.getCookies")["cookies"]
        ws.close()
    except Exception as e:
        print(f"CDP 连接失败: {e}")
        print_manual()
        return
    cx = [k for k in cks if "chaoxing" in k.get("domain", "")]
    if not cx:
        print("未找到学习通 cookie，请先在浏览器登录学习通后重试。")
        return
    buf = ";".join(f"{k['name']}={k['value']}" for k in cx)
    out = ROOT / "cookies.txt"
    out.write_text(buf, encoding="utf-8")
    print(f"已导出 {len(cx)} 条 cookie -> {out}")


def print_manual():
    print("\n方式二（手动）：")
    print("  1. 浏览器打开学习通并登录")
    print("  2. F12 -> 网络(Network) -> 刷新页面 -> 点任意 chaoxing 请求")
    print("  3. 在'请求标头'里找到 Cookie: 一行，复制全部内容")
    print("  4. 粘贴到项目根目录的 cookies.txt 并保存")


if __name__ == "__main__":
    main()
