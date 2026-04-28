# OpenAvatarChat 前端架构

## 目录结构

```
src/
├── main/                          ← Electron 主进程（桌面端）
│   ├── index.ts                     主进程入口
│   └── features/
│       ├── appState.ts              应用状态管理
│       └── contextMenu.ts           右键菜单
│
├── preload/                       ← Electron 预加载脚本
│   ├── index.ts                     桥接主进程与渲染进程
│   └── index.d.ts                   类型声明
│
└── renderer/                      ← 渲染进程（前端核心，浏览器端运行）
    ├── index.html                   主页面入口（数字人对话）
    ├── manager.html                 管理页面入口
    │
    └── src/
        ├── main.ts                  主应用启动文件
        ├── manager.ts               管理页面启动文件
        ├── App.vue                  主应用根组件（背景/路由选择）
        ├── ManagerApp.vue           管理页根组件
        ├── style.less               全局样式
        │
        ├── apis/                    ← API 接口层
        │   ├── base.ts               HTTP 基础配置
        │   └── index.ts              接口定义
        │
        ├── assets/                  ← 静态资源
        │   ├── background.png        背景图
        │   └── *.png                 其他图片
        │
        ├── components/              ← 可复用组件
        │   ├── ActionGroup.vue       工具栏（摄像头/麦克风/音量按钮）
        │   ├── AudioWave.vue         音频波形动画
        │   ├── ChatBtn.vue           语音聊天按钮（按住说话）
        │   ├── ChatInput.vue         文字输入框（静音时显示）
        │   ├── ChatMessage.vue       单条聊天消息气泡
        │   ├── ChatRecords.vue       聊天记录列表
        │   ├── InlineAudioPlayer.vue 内联音频播放器
        │   ├── PulsingIcon.vue       脉冲动画图标
        │   ├── WebcamPermission.vue  摄像头权限请求页
        │   └── Iconfont/             SVG 图标组件集
        │
        ├── handlers/                ← 数字人渲染处理
        │   ├── avatarHandler.ts      头像渲染调度器
        │   └── avatarRenderers/
        │       └── lam.ts            LAM 模型渲染器（Audio2Expression）
        │
        ├── helpers/                 ← 核心辅助模块
        │   ├── player.ts             音频播放（PCM/WAV 处理）
        │   ├── processor.ts          数据处理（WebSocket 消息解析）
        │   └── ws.ts                 WebSocket 客户端封装
        │
        ├── store/                   ← Pinia 状态管理
        │   ├── app.ts                全局应用状态（chatMode/avatarType）
        │   ├── chat.ts               聊天状态（消息/静音/回复中）
        │   ├── media.ts              媒体设备状态（摄像头/麦克风）
        │   ├── vision.ts             视觉布局状态（横竖屏/容器引用）
        │   ├── webrtc.ts             WebRTC 连接状态与控制
        │   ├── ws.ts                 WebSocket 连接状态与控制
        │   └── manager.ts            管理页状态
        │
        ├── views/                   ← 页面视图
        │   ├── VideoChat/             WebRTC 模式对话页
        │   │   ├── index.vue            页面组件（视频+聊天+工具栏）
        │   │   └── index.less           页面样式
        │   ├── WSVideoChat/          WebSocket 模式对话页
        │   │   └── index.vue            页面组件
        │   └── Manager/              管理调试页
        │       ├── index.vue           页面组件
        │       └── components/         会话列表/信号查看器等
        │
        ├── interface/               ← TypeScript 类型定义
        │   ├── eventType.ts           事件类型
        │   └── voiceChat.ts           语音聊天类型
        │
        ├── langs/                   ← 国际化（i18n）
        │   ├── index.ts               语言切换
        │   ├── zh.ts                  中文
        │   └── en.ts                  英文
        │
        ├── utils/                   ← 工具函数
        │   ├── binaryUtils.ts         二进制数据处理
        │   ├── streamUtils.ts         流处理工具
        │   ├── webrtcUtils.ts         WebRTC 工具
        │   ├── isElectron.ts          判断是否 Electron 环境
        │   └── utils.ts               通用工具
        │
        └── worklets/                ← Web Audio 工作线程
            ├── heartbeat-worker.js     心跳检测
            └── mic-processor.js        麦克风音频处理
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API + `<script setup>`) |
| 构建工具 | Vite 7 |
| 语言 | TypeScript |
| 状态管理 | Pinia |
| 样式 | Less |
| UI 组件库 | Ant Design Vue |
| 桌面端 | Electron（可选） |

## 核心数据流

```
用户输入（语音/文字）
  → ChatBtn / ChatInput 组件
    → store/ws.ts 或 store/webrtc.ts（发送消息）
      → helpers/ws.ts（WebSocket 通信）
        → 服务器返回 EchoAvatarText + EchoAvatarAudio
          → helpers/processor.ts（解析消息）
            → ChatRecords 显示文字 / player.ts 播放音频
              → handlers/lam.ts 渲染数字人表情动画
```

## 关键文件说明

### 入口与路由
- `App.vue` — 根组件，根据 `chatMode` 选择 `VideoChat`（WebRTC）或 `WSVideoChat`（WebSocket）视图
- `main.ts` — 应用启动入口，挂载 Vue 实例

### 两种对话模式
- `views/VideoChat/` — WebRTC 模式，支持音视频流，有本地摄像头画面
- `views/WSVideoChat/` — WebSocket 模式，仅文字/音频交互，无本地摄像头

### 数字人渲染
- `handlers/avatarHandler.ts` — 根据配置选择渲染器
- `handlers/avatarRenderers/lam.ts` — LAM 模型渲染，接收音频数据驱动数字人表情

### 通信协议
- WebSocket 消息格式定义在 `interface/` 目录
- 消息收发逻辑在 `helpers/ws.ts` 和 `helpers/processor.ts`
- 协议包括：InitializeAvatarSession、SendHumanText、EchoAvatarText、EchoAvatarAudio 等

## 构建命令

```bash
cd src/service/frontend_service/frontend
npm install          # 安装依赖
npx vite build       # 构建生产版本，输出到 dist/
npx vite build --emptyOutDir  # 清空 dist 后构建
```

构建产物输出到 `src/service/frontend_service/frontend/dist/`，由后端服务直接提供静态文件服务。
