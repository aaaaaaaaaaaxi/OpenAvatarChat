"""
OpenAvatarChat 前端 Mock 服务器
用于在前端开发调试时，不启动后端也能看到数字人界面。

用法:
  python mock_server.py [--avatar NAME] [--mode MODE]

  --avatar  头像名称，对应 lam_samples/ 下的 zip 文件（不含扩展名），默认 zhangxu
  --mode    聊天模式: ws 或 webrtc，默认 ws
  --port    服务端口，默认 8282

启动后在浏览器访问 https://localhost:8282/ui/index.html

不修改任何原有代码，正常启动后端时忽略此文件即可。
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
import ssl
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = PROJECT_DIR / "src" / "service" / "frontend_service" / "frontend" / "dist"
LAM_SAMPLES = PROJECT_DIR / "lam_samples"

app = FastAPI(docs_url=None, redoc_url=None)

# ---------- 配置 ----------
MOCK_AVATAR = "zhangxu"
MOCK_MODE = "ws"
MOCK_PORT = 8282


# ---------- /openavatarchat/initconfig ----------
@app.get("/openavatarchat/initconfig")
async def init_config():
    return JSONResponse({
        "chat_mode": MOCK_MODE,
        "avatar_config": {
            "avatar_type": "lam",
            "avatar_assets_path": f"/download/avatar/{MOCK_AVATAR}.zip",
            "avatar_ws_route": "/ws/lam_client",
        },
        "rtc_configuration": {
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
        },
    })


# ---------- 头像资源下载 ----------
@app.get("/download/avatar/{avatar_name}.zip")
async def download_avatar(avatar_name: str):
    zip_path = LAM_SAMPLES / f"{avatar_name}.zip"
    if zip_path.exists():
        return FileResponse(zip_path, media_type="application/zip", filename=f"{avatar_name}.zip")
    return JSONResponse({"detail": f"Avatar {avatar_name} not found"}, status_code=404)


# ---------- WebSocket 模拟 ----------
@app.websocket("/ws/lam_client/{session_id}")
async def ws_lam_client(websocket: WebSocket, session_id: str):
    await websocket.accept()

    try:
        # 等待 InitializeAvatarSession
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            header_name = msg.get("header", {}).get("name", "")

            if header_name == "InitializeAvatarSession":
                # 回复会话已初始化
                await websocket.send_json({
                    "header": {"name": "AvatarSessionInitialized", "request_id": str(uuid.uuid4())},
                })
                print(f"[Mock] Avatar session initialized: {session_id}")
                break
            elif header_name == "TriggerHeartbeat":
                await websocket.send_json({
                    "header": {"name": "AvatarHeartbeat", "request_id": str(uuid.uuid4())},
                })

        # 进入对话循环
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            header_name = msg.get("header", {}).get("name", "")
            payload = msg.get("payload", {})

            if header_name == "SendHumanText":
                user_text = payload.get("text", "")
                stream_key = payload.get("stream_key", str(uuid.uuid4()))
                request_id = payload.get("request_id", str(uuid.uuid4()))
                print(f"[Mock] User said: {user_text}")

                # 回显用户文本
                await websocket.send_json({
                    "header": {"name": "EchoHumanText", "request_id": str(uuid.uuid4())},
                    "payload": {
                        "request_id": request_id,
                        "stream_key": stream_key,
                        "mode": "full_text",
                        "text": user_text,
                        "end_of_speech": True,
                    },
                })

                # 模拟 AI 回复
                reply_stream_key = str(uuid.uuid4())
                reply_text = f"你好！我是 Mock 数字人。你说的是「{user_text}」，但我只是个模拟回复。"

                # 分段发送（模拟流式输出）
                chunks = [reply_text[i:i+5] for i in range(0, len(reply_text), 5)]
                accumulated = ""
                for chunk in chunks:
                    accumulated += chunk
                    await websocket.send_json({
                        "header": {"name": "EchoAvatarText", "request_id": str(uuid.uuid4())},
                        "payload": {
                            "request_id": str(uuid.uuid4()),
                            "stream_key": reply_stream_key,
                            "mode": "increment",
                            "text": chunk,
                            "end_of_speech": accumulated == reply_text,
                        },
                    })
                    await asyncio.sleep(0.1)

            elif header_name == "TriggerHeartbeat":
                await websocket.send_json({
                    "header": {"name": "AvatarHeartbeat", "request_id": str(uuid.uuid4())},
                })

            elif header_name == "Interrupt":
                print("[Mock] Interrupt received")

            elif header_name == "SendHumanAudio":
                # 忽略音频数据
                pass

    except WebSocketDisconnect:
        print(f"[Mock] WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"[Mock] WebSocket error: {e}")


# ---------- 静态文件 & 路由 ----------
# 必须在最后挂载，避免覆盖上面的路由
if FRONTEND_DIST.exists():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIST), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/ui/index.html")


def main():
    global MOCK_AVATAR, MOCK_MODE, MOCK_PORT
    parser = argparse.ArgumentParser(description="OpenAvatarChat 前端 Mock 服务器")
    parser.add_argument("--avatar", default="zhangxu", help="头像名称 (lam_samples/ 下的 zip 文件名，不含扩展名)")
    parser.add_argument("--mode", default="ws", choices=["ws", "webrtc"], help="聊天模式")
    parser.add_argument("--port", type=int, default=8282, help="服务端口")
    args = parser.parse_args()

    MOCK_AVATAR = args.avatar
    MOCK_MODE = args.mode
    MOCK_PORT = args.port

    # 自动生成自签名证书（如果不存在）
    cert_file = PROJECT_DIR / "ssl_certs" / "localhost.crt"
    key_file = PROJECT_DIR / "ssl_certs" / "localhost.key"
    ssl_context = None
    if cert_file.exists() and key_file.exists():
        ssl_context = {
            "ssl_certfile": str(cert_file),
            "ssl_keyfile": str(key_file),
        }
        print(f"[Mock] Using SSL certs from {cert_file.parent}")
    else:
        print("[Mock] Warning: SSL certs not found, running without HTTPS")
        print("[Mock]   Frontend may need HTTPS for WebRTC/camera access in browser")

    print(f"[Mock] Frontend dist: {FRONTEND_DIST}")
    print(f"[Mock] Avatar: {MOCK_AVATAR} (lam_samples/{MOCK_AVATAR}.zip)")
    print(f"[Mock] Mode: {MOCK_MODE}")
    print(f"[Mock] Starting server at https://localhost:{MOCK_PORT}")
    print(f"[Mock] Open https://localhost:{MOCK_PORT}/ui/index.html in browser")

    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=MOCK_PORT,
        **(ssl_context or {}),
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


if __name__ == "__main__":
    main()
