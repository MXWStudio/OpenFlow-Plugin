# OpenFlow-Desktop Agent Instructions

你正在参与 **OpenFlow-Desktop** 项目的维护与开发。这是一个基于 PySide6 的桌面应用，主要用于素材重命名、需求校验及自动化文件夹初始化。

## 项目核心背景
- **主要功能**：支持导入自定义 JSON 需求表，自动批量生成对应项目及尺寸文件夹，并根据规则对素材进行重命名。
- **目标用户**：IAA/AIGC 制作人员，追求极简、高效的操作体验。

## 技术规约与架构
- **GUI 框架**：PySide6 (Python)。
- **审美要求**：深色模式 (Dark Mode)，VSCode 风格自定义标题栏，圆角 12px。
- **JSON 解析器 [重要]**：
    - 必须使用 `main_window.preprocess_json_text` 进行预处理（剥离 BOM 和注释）。
    - 注释清理正则必须使用 `(?<![:/])//.*` 以保护 `https://` 协议头。
    - `json.loads` 必须配合 `strict=False` 以容忍非标控制字符（网页抓取数据常见场景）。
- **布局管理**：中部配置区与日志区使用 `QSplitter` 进行弹性连接，默认高度配置需兼顾不同分辨率屏幕。

## 开发与质量保证
- **单元测试**：核心逻辑（如 JSON 预处理）在 `openflow-desktop/test_logic.py` 中。**每次修改解析相关逻辑后，请务必运行此测试。**
- **语言要求**：UI 界面、提示信息及代码注释均使用 **简体中文**。
- **资源清理**：禁止在根目录留下 `diagnose_*.py` 等临时文件。

## 常用命令
- 运行应用：`py openflow-desktop/main_window.py`
- 运行测试：
    - 逻辑测试：`py openflow-desktop/test_logic.py`
    - 启动冒烟测试：`py openflow-desktop/smoke_test_gui.py`
