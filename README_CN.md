# 🌐 云原生外刊有声化系统 (Cloud-Based Magazine-to-MP3 Pipeline)

本项目是一个结合了**本地文档解析**、**云端 AI 语音合成（Azure/Edge TTS）**以及未来**云存储自动同步（OneDrive/Azure Blob）**的自动化音频转换系统。它完整记录了我从零发现需求、经历多次功能迭代、最终在 Windows 上完成多语言封装和开源管理的项目全生命周期。

---

## 🔬 实验阶段记录（项目进化史）

### 阶段一：发现原始需求 (Origin)
*   **痛点发现**：在阅读《经济学人》（The Economist）等高强度英文外刊时，长时间盯着屏幕容易眼睛疲劳。虽然官方网站提供部分文章的音频，但大量深度杂志长文缺少语音版，无法满足碎片化时间的听书需求。
*   **核心需求**：构建一个灵活、可自定制的外刊有声化工具，支持将本地下载的各种文档格式流畅地转化为高质感、纯正口音的 MP3 音频。
*   **技术选型**：Python 异步架构 + 微软云端神经语音库（Neural Voices），实现接近真人朗读的磨耳朵体验。

### 阶段二：初版开发与多格式扩展 (MVP & Iteration)
*   **1.0 版本**：跑通了 `.pdf` 和 `.epub` 格式电子书的文本提取，调用 `edge-tts` 库异步合成音频。
*   **2.0 版本**：根据实际阅读场景，引入 `python-docx` 库，重构底层逻辑。支持通过登录后将外刊网页直接“另存为”或复制粘贴到 Word (`.docx`) 格式，实现自动识别与平滑解析。
*   **3.0 图形化升级**：为了提升交互体验，引入了 `Tkinter` 框架构建了精美的图形用户界面（GUI），配备了实时执行日志流水线以及云端度量监控仪表盘。

### 阶段三：国际化交付与独立运行 (Localization & Packaging)
*   **多语言版本支持 (v3.5)**：针对日常使用习惯，对代码逻辑和界面语言进行了本地化解耦，同时输出了**中文旗舰版**与**英文国际版**两套独立的代码和成品。
*   **独立交付（Windows 优化）**：在 Windows 环境下利用 `PyInstaller` 将复杂的 Python 依赖环境和异步事件循环封装成单个 `.exe` 可执行文件。解决了窗口自适应居中、避免黑框秒退、以及无控制台环境下的 `RuntimeError` 熔断机制。

### 阶段四：未来演进 —— 云管理员视角 (Cloud Infrastructure Integration)
为了将该工具演进为更具扩展性的系统，并作为 **Azure Administrator (AZ-104)** 的实战演练，项目架构向“云端化”进行了全面规划：
1.  **混合云处理模式 (Hybrid Processing)**：本地提取的文本流上传至微软云端语音合成引擎，利用其庞大的深度学习模型将文字高效渲染为 MP3（数据隐私与本地化控制）。
2.  **云存储自动流转 (Storage Pipeline)**：系统集成云存储 API（如 Microsoft Graph API 或 Azure Blob Storage SDK）。当云端生成 MP3 后，不再回传并占用本地磁盘，而是直接由内存流（BytesIO）直连、上传并加密保存在用户的 **OneDrive** 中。用户可以在手机端 OneDrive 上直接点击播放，实现多端同步听书。

---

## 🏗️ 演进后的系统架构图 (System Architecture)

[本地文件 (PDF/Docx)] 
       │ (解析为纯文本)
       ▼
[本地 Python / .exe] 
       │ (网络请求: 文本流)
       ▼
[微软云端 TTS 引擎 (Azure/Edge)] 
       │ (云端计算，渲染为 MP3)
       ▼
[云端内存音频流] 
       │ (通过 Microsoft Graph API 传输)
       ▼
[OneDrive / 云端存储] ───► [用户手机/iPad 端随时收听]

---

## 🛠️ 技术栈与 AZ-104 实战考点

*   **Core**: Python 3.x, Asyncio, Tkinter GUI
*   **Parsers**: `pypdf`, `ebooklib`, `beautifulsoup4`, `python-docx`
*   **TTS Engine**: `edge-tts` (Microsoft Neural Voices)