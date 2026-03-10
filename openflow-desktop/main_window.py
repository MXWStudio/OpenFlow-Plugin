import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QHeaderView, QListWidget, QCheckBox, 
    QSpinBox, QGridLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QFrame, QSizePolicy, QInputDialog, QDialog
)
from PySide6.QtCore import Qt, QSettings, QPoint
from PySide6.QtGui import QColor, QFont, QIcon
from pypinyin import lazy_pinyin, Style
from main import MaterialProcessor

class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        # 👇 之前这里的 self.setStyleSheet 已经被删掉了，让它乖乖听全局苹果样式的话！

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    # 【Fix 1.1】修复列表内部的拖放逻辑，确保解析后传给主窗口
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            folders = []
            json_files = [] # 收集拖进来的 json 文件
            
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folders.append(path)
                elif path.lower().endswith('.json'):
                    json_files.append(path)
            
            main_win = self.window()
            
            # 如果拖入了 JSON 文件，直接解析
            if json_files and hasattr(main_win, 'load_data_from_json'):
                main_win.load_data_from_json(json_files[0])
            
            # 处理正常的文件夹拖入
            if folders and hasattr(main_win, 'add_folders_from_drop'):
                main_win.add_folders_from_drop(folders)
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class MaterialProcessorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processor = MaterialProcessor()
        self.current_folders = []
        
        self.preset_sizes = ["1280*720", "720*1280", "1920*1080", "1080*1920", "640*360", "1080*607", "1080*170", "900*900", "1080*1620", "160*160"]
        self.size_widgets = {}
        self.latest_report = [] 
        
        # 配置文件保存
        self.settings = QSettings("MyCompany", "MaterialProcessor")
        self.full_json_data = [] # 新增：保存完整的 JSON 导入数据
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("素材处理极简工作台 - v3.0")
        self.resize(1100, 800)
        
        # === 1. 设置窗口可缩放并保持自定义风格 ===
        # 为了支持全局缩放，我们移除完全无边框限制，或者保留但允许拉伸
        # 这里我们选择保留自定义样式，但确保窗口 flags 允许缩放
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 添加右下角缩放手柄
        from PySide6.QtWidgets import QSizeGrip
        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(15, 15)
        self.size_grip.setCursor(Qt.SizeFDiagCursor)
        self.size_grip.setStyleSheet("background: transparent;")
        
        # 开启拖放接收
        self.setAcceptDrops(True)
        
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget") # 给主容器打个标签
        self.setCentralWidget(central_widget)
        
        # === 2. 给整个主窗口画一个深色圆角底板 ===
        central_widget.setStyleSheet("""
            #CentralWidget {
                background-color: #1E1E1E;
                border: 1px solid #38383A;
                border-radius: 12px;
            }
        """)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0) # 去掉外边距，让标题栏贴边
        main_layout.setSpacing(0)

        # ==========================================
        # 0. 自定义 VSCode 风格标题栏
        # ==========================================
        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(35)
        # 修复顶部圆角：必须在这里明确设置 title_bar 的背景和圆角，
        # 且 radius 必须与 central_widget 保持一致 (12px)
        title_bar.setStyleSheet("""
            #TitleBar {
                background-color: #252526;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 0, 0)
        title_layout.setSpacing(0)

        lbl_title = QLabel("OpenFlow 素材处理工作台")
        lbl_title.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        
        # 窗口控制按钮 (VSCode 风格)
        btn_min = QPushButton("－")
        btn_max = QPushButton("▢")
        btn_close = QPushButton("✕")

        for btn, hover_color in [
            (btn_min, "#3F3F41"),
            (btn_max, "#3F3F41"),
            (btn_close, "#E81123")
        ]:
            btn.setFixedSize(45, 35)
            btn.setFlat(True)
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: #CCCCCC;
                    border: none;
                    font-size: 15px;
                }}
                QPushButton:hover {{ background-color: {hover_color}; color: white; }}
            """)

        btn_close.clicked.connect(self.close)
        btn_min.clicked.connect(self.showMinimized)
        btn_max.clicked.connect(self.toggle_maximize)

        title_layout.addWidget(lbl_title)
        title_layout.addStretch()
        title_layout.addWidget(btn_min)
        title_layout.addWidget(btn_max)
        title_layout.addWidget(btn_close)

        # 添加一个窗口拉伸区域（由于是 Frameless 窗口，我们需要手动处理边缘拉伸，或者使用 sizeGrip）
        # 这里简单起见，配合 layout 伸缩和 QSizeGrip
        main_layout.addWidget(title_bar)
        
        # 内容区域（用 QScrollArea 包裹，让小屏幕用户能滚动看到底部按钮）
        from PySide6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_widget.setObjectName("ScrollContent")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(12)

        # ==========================================
        # 1. 顶部隔离区：项目初始化 (新增)
        # ==========================================
        init_group = QGroupBox("🚀 第一步：项目初始化与文件夹生成")
        init_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #0A84FF; }")
        init_layout = QHBoxLayout(init_group)
        
        self.edit_project_name = QLineEdit()
        self.edit_project_name.setPlaceholderText("项名称 (如：小火车呜呜呜)")
        
        self.btn_import_json = QPushButton("📄 导入需求 JSON")
        self.btn_import_json.clicked.connect(self.select_json_file)
        self.btn_import_json.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3C;
                color: #FFFFFF;
                padding: 12px 25px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #444446; border: 1px solid #0A84FF; }
        """)
        
        self.btn_init_folders = QPushButton("📂 一键初始化文件夹")
        self.btn_init_folders.clicked.connect(self.init_project_folders)
        self.btn_init_folders.setStyleSheet("""
            QPushButton {
                background-color: #0A84FF;
                color: #FFFFFF;
                font-weight: bold;
                padding: 12px 25px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #0070DF; }
        """)
        
        init_layout.addWidget(QLabel("项目名:"))
        init_layout.addWidget(self.edit_project_name, stretch=1)
        init_layout.addWidget(self.btn_import_json)
        init_layout.addWidget(self.btn_init_folders)
        
        content_layout.addWidget(init_group)

        # ==========================================
        # 1.5 仪表盘：反馈与结果展示 (移动到此处)
        # ==========================================
        dash_frame = QFrame()
        dash_frame.setStyleSheet("""
            QFrame {
                background-color: #2C2C2E;
                border: 1px solid #38383A;
                border-radius: 10px;
            }
        """)
        dash_layout = QVBoxLayout(dash_frame)
        dash_layout.setContentsMargins(10, 15, 10, 15)
        dash_layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_dashboard = QLabel("👋 欢迎！首先请点击上方按钮导入需求或初始化文件夹。")
        self.lbl_dashboard.setAlignment(Qt.AlignCenter)
        self.lbl_dashboard.setWordWrap(True)
        self.lbl_dashboard.setStyleSheet("color: #FFFFFF;")
        self.lbl_dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font_dash = QFont("Microsoft YaHei", 18, QFont.Bold)
        self.lbl_dashboard.setFont(font_dash)
        
        self.lbl_stats_detail = QLabel("")
        self.lbl_stats_detail.setAlignment(Qt.AlignCenter)
        self.lbl_stats_detail.setWordWrap(True)
        self.lbl_stats_detail.setStyleSheet("color: #FFFFFF;")
        self.lbl_stats_detail.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font_detail = QFont("Microsoft YaHei", 10)
        self.lbl_stats_detail.setFont(font_detail)
        
        dash_layout.addWidget(self.lbl_dashboard)
        dash_layout.addWidget(self.lbl_stats_detail)
        
        content_layout.addWidget(dash_frame)

        # ==========================================
        # 2. 中部：文件夹拖拽区与尺寸配置
        # ==========================================
        top_layout = QHBoxLayout()
        
        # 左侧：文件夹拖拽区
        folder_group = QGroupBox("📁 待处理的素材文件夹 (支持拖拽导入)")
        folder_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        folder_layout = QVBoxLayout(folder_group)
        
        self.list_folders = DragDropListWidget(self)
        self.list_folders.setFixedHeight(100)
        
        btn_folder_layout = QHBoxLayout()
        self.btn_add_folder = QPushButton("➕ 添加多个文件夹")
        self.btn_add_folder.clicked.connect(self.select_multiple_folders)
        self.btn_clear_folders = QPushButton("🗑️ 清空列表")
        self.btn_clear_folders.clicked.connect(self.clear_folders)
        
        btn_folder_layout.addWidget(self.btn_add_folder)
        btn_folder_layout.addWidget(self.btn_clear_folders)
        
        folder_layout.addWidget(self.list_folders)
        folder_layout.addLayout(btn_folder_layout)
        
        # 右侧：项目与需求配置
        right_panel = QVBoxLayout()
        
        project_group = QGroupBox("📌 重命名配置")
        project_layout = QVBoxLayout(project_group)
        
        # 制作人缩写输入框
        maker_layout = QHBoxLayout()
        maker_label = QLabel("制作人缩写:")
        maker_label.setStyleSheet("color: #98989D; font-size: 12px;")
        self.edit_maker_abbr = QLineEdit()
        self.edit_maker_abbr.setPlaceholderText("拼音首字母大写，如 MXW")
        self.edit_maker_abbr.setText("MXW")
        maker_layout.addWidget(maker_label)
        maker_layout.addWidget(self.edit_maker_abbr)
        project_layout.addLayout(maker_layout)
        
        config_group = QGroupBox("⚙️ 需求尺寸勾选 (左侧:横版/方型, 右侧:竖版)")
        config_layout = QGridLayout(config_group)
        
        horizontal_sizes = []
        vertical_sizes = []
        for size_str in self.preset_sizes:
            parts = size_str.split('*')
            if len(parts) == 2 and int(parts[0]) < int(parts[1]):
                vertical_sizes.append(size_str)
            else:
                horizontal_sizes.append(size_str)
                
        max_rows = max(len(horizontal_sizes), len(vertical_sizes))
        # 重要：先重置 size_widgets
        self.size_widgets = {}
        
        for row in range(max_rows):
            # 左侧：横版/正方形 (Column 0)
            if row < len(horizontal_sizes):
                size_str = horizontal_sizes[row]
                chkbox = QCheckBox(size_str)
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(0,0,0,0)
                l.addWidget(chkbox)
                l.addStretch()
                self.size_widgets[size_str] = {"chk": chkbox, "qty": 0} # 确保初始化 qty
                config_layout.addWidget(w, row, 0)
                
            # 右侧：竖版 (Column 1)
            if row < len(vertical_sizes):
                size_str = vertical_sizes[row]
                chkbox = QCheckBox(size_str)
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(0,0,0,0)
                l.addWidget(chkbox)
                l.addStretch()
                self.size_widgets[size_str] = {"chk": chkbox, "qty": 0} # 确保初始化 qty
                config_layout.addWidget(w, row, 1)
            
        right_panel.addWidget(project_group)
        right_panel.addWidget(config_group)
        
        # 【关键修复】确保 top_layout 包含了所有子组件
        top_layout.addWidget(folder_group, stretch=2)
        top_layout.addLayout(right_panel, stretch=1)
        
        # 将中部区域包装进一个 Widget 中，以便放入 Splitter
        mid_widget = QWidget()
        mid_widget.setLayout(top_layout)
        mid_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        mid_widget.setMinimumHeight(280)

        # ==========================================
        # 3. 隐藏的树状明细日志区
        # ==========================================
        self.log_container = QWidget()
        log_layout = QVBoxLayout(self.log_container)
        log_layout.setContentsMargins(0,0,0,0)
        
        log_header = QHBoxLayout()
        self.btn_toggle_log = QPushButton("🔽 展开明细日志")
        self.btn_toggle_log.setFlat(True)
        self.btn_toggle_log.setStyleSheet("color: #0078D7; font-weight: bold; text-align: left;")
        self.btn_toggle_log.clicked.connect(self.toggle_log)
        
        self.btn_export_log = QPushButton("📤 导出错误报告")
        self.btn_export_log.setVisible(False)
        self.btn_export_log.setStyleSheet("color: #DC3545; font-weight: bold;")
        self.btn_export_log.clicked.connect(self.export_error_log)
        
        log_header.addWidget(self.btn_toggle_log)
        log_header.addStretch()
        log_header.addWidget(self.btn_export_log)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["分类 / 文件名", "所属", "格式", "尺寸", "状态", "详情"])
        self.tree.setAlternatingRowColors(True)
        # 设置自动伸缩列
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tree.setColumnWidth(1, 120)
        self.tree.setColumnWidth(2, 60)
        self.tree.setColumnWidth(3, 100)
        self.tree.setVisible(True) # 默认隐藏
        
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.tree)
        
        # 将日志区的高度策略设为可扩展
        self.log_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_container.setMinimumHeight(150)
        
        # --- 创建垂直分割条 ---
        from PySide6.QtWidgets import QSplitter
        self.v_splitter = QSplitter(Qt.Vertical)
        self.v_splitter.addWidget(mid_widget)
        self.v_splitter.addWidget(self.log_container)
        
        # 设置初始伸缩比例 (配置区 1 : 日志区 1)
        self.v_splitter.setStretchFactor(0, 1)
        self.v_splitter.setStretchFactor(1, 1)
        # 允许拉动
        self.v_splitter.setHandleWidth(6)
        self.v_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #38383A;
                min-height: 2px;
            }
            QSplitter::handle:hover {
                background-color: #0A84FF;
            }
        """)
        
        content_layout.addWidget(self.v_splitter)

        # ==========================================
        # 4. 底部：核心动作大按钮
        # ==========================================
        bottom_layout = QHBoxLayout()
        self.btn_validate = QPushButton("🔍 开始校验检测")
        self.btn_validate.setFixedHeight(50)
        self.btn_validate.setStyleSheet("""
            QPushButton { 
                background-color: #0A84FF; 
                color: white; 
                border-radius: 8px; 
                font-size: 15px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #0070DF; }
        """)
        self.btn_validate.clicked.connect(self.start_validation)

        self.btn_rename = QPushButton("火箭起飞：一键重命名 🚀")
        self.btn_rename.setFixedHeight(50)
        self.btn_rename.setEnabled(False) 
        self.btn_rename.setStyleSheet("""
            QPushButton { 
                background-color: #32D74B; 
                color: #000000;
                border-radius: 8px; 
                font-size: 15px; 
                font-weight: bold; 
            }
            QPushButton:hover { background-color: #28C840; }
            QPushButton:disabled { 
                background-color: #3A3A3C; 
                color: #767677; 
            }
        """)
        self.btn_rename.clicked.connect(self.perform_rename)
        
        bottom_layout.addWidget(self.btn_validate)
        bottom_layout.addWidget(self.btn_rename)
        content_layout.addLayout(bottom_layout)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        self.apply_apple_dark_theme() # 应用苹果深色主题

    # ==================== Apple 深色主题 ====================
    def apply_apple_dark_theme(self):
        """全局 Apple macOS 深色风格样式"""
        apple_qss = """
            /* 1. 全局背景与字体 */
            QWidget {
                background-color: #1E1E1E; /* macOS 深色模式主背景色 */
                color: #FFFFFF;
                font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
            }
            
            /* 2. 模块卡片 (QGroupBox) 改造为 Apple 风格的圆角面板 */
            QGroupBox {
                background-color: #2C2C2E; /* 卡片底色，比主背景稍亮 */
                border: 1px solid #38383A; /* 极弱的描边 */
                border-radius: 10px;
                margin-top: 28px; /* 给标题留出呼吸空间 */
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: 8px;
                color: #98989D; /* 苹果经典次级灰色 */
                font-size: 13px;
                font-weight: bold;
            }

            /* 3. 输入框 (QLineEdit) */
            QLineEdit {
                background-color: #1C1C1E;
                border: 1px solid #38383A;
                border-radius: 6px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #0A84FF; /* 苹果焦点蓝 */
            }

            /* 4. 普通按钮 (次级操作) */
            QPushButton {
                background-color: #3A3A3C;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #444446;
            }
            QPushButton:pressed {
                background-color: #2C2C2E;
            }

            /* 5. 拖拽列表 (去掉虚线，改为更柔和的拖拽区) */
            QListWidget {
                background-color: #1C1C1E;
                border: 1.5px dashed #48484A;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget:hover {
                border: 1.5px dashed #0A84FF;
            }

            /* 6. 复选框 */
            QCheckBox {
                color: #D1D1D6;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #545458;
                background-color: #1C1C1E;
            }
            QCheckBox::indicator:checked {
                background-color: #0A84FF;
                border: 1px solid #0A84FF;
            }
        """
        self.setStyleSheet(apple_qss)

    # ==================== QSettings 记忆配置 ====================
    def closeEvent(self, event):
        """窗口关闭时保存配置"""
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        try:
            self.settings.setValue("project_name", self.edit_project_name.text())
        except Exception:
            pass
            
        specs_data = {}
        # 在循环外导入
        try:
            import shiboken6
        except ImportError:
            shiboken6 = None
            
        for size_str, widgets in self.size_widgets.items():
            try:
                if "chk" in widgets:
                    chk = widgets["chk"]
                    # 检查 C++ 对象是否还存活
                    if shiboken6 and shiboken6.isValid(chk):
                        specs_data[size_str] = {
                            "checked": chk.isChecked(),
                            "count": 0
                        }
            except Exception:
                continue
        self.settings.setValue("specs", json.dumps(specs_data))

    def load_settings(self):
        proj_name = self.settings.value("project_name", "小火车游戏")
        self.edit_project_name.setText(str(proj_name)) # 确保转为字符串
        
        specs_json = self.settings.value("specs", "")
        if specs_json:
            try:
                specs_data = json.loads(specs_json)
                for size_str, data in specs_data.items():
                    # 安全检查：确保 widgets 字典和 chk 对象都有效
                    if size_str in self.size_widgets:
                        widgets = self.size_widgets[size_str]
                        if "chk" in widgets and not widgets["chk"].isHidden(): 
                            widgets["chk"].setChecked(data.get("checked", False))
            except Exception:
                pass


    # ==================== 拖拽与文件选择 ====================
    # 【Fix 1.2】窗口级的拖放事件，正确解析出文件夹
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            folders = [url.toLocalFile() for url in event.mimeData().urls() if os.path.isdir(url.toLocalFile())]
            self.add_folders_from_drop(folders)
            event.acceptProposedAction()

    # 【优化需求 2：智能识别项目根目录，并自动填写项目名】
    def add_folders_from_drop(self, folders):
        added = 0
        real_folders_to_add = []

        # 1. 遍历用户拖入的路径
        for f in folders:
            # 标准化路径分隔符
            f = os.path.normpath(f)
            if not os.path.isdir(f):
                continue
                
            # 2. 获取其内部的子目录列表
            subdirs = [os.path.join(f, name) for name in os.listdir(f) 
                       if os.path.isdir(os.path.join(f, name))]

            # 3. 关键逻辑：如果含有子目录，说明这是项目总文件夹
            if subdirs:
                # 提取父文件夹名称自动填入项目名称输入框 (例如: "小火车呜呜呜")
                root_name = os.path.basename(f)
                self.edit_project_name.setText(root_name)
                
                # 4. 将里面的子文件夹追加到待处理列表
                real_folders_to_add.extend(subdirs)
            else:
                # 如果没有子目录，说明拖入的本身就是最终的尺寸分类文件夹
                real_folders_to_add.append(f)

        # 过滤去重，并真正添加到界面列表中
        for real_f in real_folders_to_add:
            if real_f not in self.current_folders:
                self.current_folders.append(real_f)
                self.list_folders.addItem(real_f)
                added += 1
                
        if added > 0:
            self.update_dashboard_ui_state(False)
            self.preload_files()
            self.auto_check_sizes_from_folders(real_folders_to_add) # 智能识别文件夹名并自动勾选对应尺寸

    def auto_check_sizes_from_folders(self, new_folders):
        """智能识别文件夹名称并自动勾选对应尺寸"""
        for folder_path in new_folders:
            # 提取最后一级文件夹名称 (例如: "1280-720")
            folder_name = os.path.basename(folder_path).lower()
            
            # 兼容不同的命名习惯，把减号、字母 x、下划线都临时替换成星号
            # 例如 "1280-720" 会变成 "1280*720"
            normalized_name = folder_name.replace('-', '*').replace('x', '*').replace('_', '*')
            
            # 遍历右侧面板的尺寸复选框
            for size_str, widgets in self.size_widgets.items():
                # 如果界面上的尺寸（如 "1280*720"）被包含在处理后的文件夹名中
                if size_str in normalized_name:
                    widgets["chk"].setChecked(True) # 自动打勾！

    def select_multiple_folders(self):
        # PyQt原生不原生支持多选目录，妥协用法：使用 QFileDialog.getOpenFileNames 拿路径然后提取目录
        # 这里为了稳妥，仍然使用 getExistingDirectory，但支持被多次点击追加（已在 add_folders_from_drop 中处理不覆盖逻辑）
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹 (可多次点击重复添加，或在桌面直接拖拽)")
        if folder:
            self.add_folders_from_drop([folder])

    def clear_folders(self):
        self.current_folders.clear()
        self.list_folders.clear()
        self.tree.clear()
        self.latest_report.clear()
        self.update_dashboard_ui_state(True)
        self.lbl_dashboard.setText("👋 欢迎！请添加文件夹。")
        self.lbl_dashboard.setStyleSheet("color: #eee;")
        self.lbl_stats_detail.setText("")
        # 同步清空右侧尺寸复选框
        for widgets in self.size_widgets.values():
            widgets["chk"].setChecked(False)

    def update_dashboard_ui_state(self, is_cleared):
        self.btn_rename.setEnabled(False)
        self.btn_export_log.setVisible(False)
        if not is_cleared:
            self.lbl_dashboard.setText("⏳ 文件已载入。请点击底部【开始校验检测】")
            self.lbl_dashboard.setStyleSheet("color: #e67e22;") # 橙色
            self.lbl_stats_detail.setText("可以在展开日志中查看已载入的文件结构。")

    # ==================== 尺寸规格管理 ====================
    def get_required_specs(self):
        """统一规范化规格符号，并读取存储的数量要求"""
        specs = {}
        for size_str, widgets in self.size_widgets.items():
            if widgets["chk"].isChecked():
                normalized_size = size_str.lower().replace('x', '*').strip()
                qty = widgets.get("qty", 0)  # 读取 JSON 导入时存入的数量，默认 0
                specs[normalized_size] = qty
        return specs

    def toggle_log(self):
        is_visible = self.tree.isVisible()
        self.tree.setVisible(not is_visible)
        if not is_visible:
            self.btn_toggle_log.setText("🔼 收起明细日志")
        else:
            self.btn_toggle_log.setText("🔽 展开明细日志")

    # ==================== 核心分组渲染 ====================
    def render_tree(self, grouped_data):
        """通用树状列表渲染器，供校验或预加载时调用"""
        self.tree.clear()
        for cat_name, sub_cats in grouped_data.items():
            cat_item = QTreeWidgetItem(self.tree, [cat_name])
            cat_item.setExpanded(True)
            cat_item.setBackground(0, QColor("#e9ecef"))
            cat_item.setForeground(0, QColor("#495057"))
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            
            for sub_name, files in sub_cats.items():
                if not files: continue
                sub_item = QTreeWidgetItem(cat_item, [f"{sub_name} ({len(files)}个文件)"])
                sub_item.setExpanded(True)
                
                for f_info in files:
                    ext_str = os.path.splitext(f_info['file'])[1].lstrip('.').upper()
                    
                    # 区分状态前缀
                    if f_info['status'] == "校验通过":
                        status_text = f"✅ {f_info['status']}"
                    elif f_info['status'] == "待校验":
                        status_text = f"🔄 {f_info['status']}"
                    else:
                        status_text = f"❌ {f_info['status']}"
                    
                    file_item = QTreeWidgetItem(sub_item, [
                        f_info['file'],
                        f_info.get('folder', '--'),
                        ext_str,
                        f_info['actual_size'],
                        status_text,
                        f_info['reason']
                    ])
                    
                    if f_info['status'] == "待校验":
                         file_item.setForeground(4, QColor("#6c757d"))
                    elif f_info['status'] != "校验通过":
                        file_item.setForeground(0, QColor("#DC3545"))
                        file_item.setForeground(4, QColor("#DC3545"))
                        file_item.setForeground(5, QColor("#DC3545"))
                    else:
                        file_item.setForeground(4, QColor("#28A745"))

    # 【Fix 2】将文件提前扫描抽离
    def preload_files(self):
        """添加列表后，仅作简单枚举与尺寸读取，展示在下方供确认，解耦核心 validate"""
        self.latest_report = []
        
        grouped_data = {
            "视频 (Video)": {"横版": [], "竖版": []},
            "图片 (Image)": {}
        }
        
        for folder in self.current_folders:
            folder_name_short = os.path.basename(folder)
            try:
                files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
            except Exception:
                continue
                
            for file in files:
                file_path = os.path.join(folder, file)
                _, ext = os.path.splitext(file_path)
                
                if ext.lower() not in self.processor.supported_exts:
                    continue
                    
                width, height = self.processor.get_media_dimensions(file_path)
                size_str = f"{width}*{height}" if width and height else "未知"
                
                info = {
                    "file": file,
                    "folder": folder_name_short,
                    "actual_size": size_str,
                    "status": "待校验",
                    "reason": "已载入，等待执行校验规则"
                }
                
                # 分组归类逻辑
                if ext.lower() in self.processor.supported_video_exts:
                    if size_str != "未知":
                        orientation = "横版" if width >= height else "竖版"
                    else:
                        orientation = "未知尺寸"
                        if orientation not in grouped_data["视频 (Video)"]:
                             grouped_data["视频 (Video)"][orientation] = []
                    grouped_data["视频 (Video)"][orientation].append(info)
                else:
                    if size_str not in grouped_data["图片 (Image)"]:
                        grouped_data["图片 (Image)"][size_str] = []
                    grouped_data["图片 (Image)"][size_str].append(info)
                    
        self.tree.setVisible(True)
        self.btn_toggle_log.setText("🔼 收起明细日志")
        self.render_tree(grouped_data)

    # ==================== 正式校验 ====================
    def start_validation(self):
        if not self.current_folders:
            QMessageBox.warning(self, "警告", "请先添加至少一个素材文件夹！\n可以直接拖拽文件夹进来。")
            return

        required_specs = self.get_required_specs()
        if not required_specs:
            QMessageBox.warning(self, "警告", "请在配置面板中至少勾选一项尺寸要求！")
            return

        self.latest_report = []
        global_actual_size_counts = {}
        
        error_count = 0
        total_files = 0
        
        grouped_data = {
            "视频 (Video)": {"横版": [], "竖版": []},
            "图片 (Image)": {}
        }
        
        for folder in self.current_folders:
            folder_name_short = os.path.basename(folder)
            report = self.processor.validate_folder(folder, required_specs)
            
            for info in report:
                if info['file'] == "[整体统计]":
                    continue
                    
                total_files += 1
                info['folder'] = folder_name_short
                self.latest_report.append(info)
                
                if info['status'] == "校验通过":
                    # 【Fix 4】实际尺寸也需要规范化才能精准统计
                    norm_actual = info['actual_size'].lower().replace('x', '*').strip()
                    global_actual_size_counts[norm_actual] = global_actual_size_counts.get(norm_actual, 0) + 1
                else:
                    error_count += 1
                    
                # 分组归类
                ext = os.path.splitext(info['file'])[1].lower()
                size_str = info['actual_size']
                if ext in self.processor.supported_video_exts:
                    if size_str != "未知" and '*' in size_str:
                        w, h = map(int, size_str.split('*'))
                        orientation = "横版" if w >= h else "竖版"
                    else:
                        orientation = "未知尺寸"
                        if "未知尺寸" not in grouped_data["视频 (Video)"]:
                            grouped_data["视频 (Video)"]["未知尺寸"] = []
                            
                    grouped_data["视频 (Video)"][orientation].append(info)
                else:
                    if size_str not in grouped_data["图片 (Image)"]:
                        grouped_data["图片 (Image)"][size_str] = []
                    grouped_data["图片 (Image)"][size_str].append(info)

        # 检查总数量是否达标
        qty_errors = []
        for req_size, req_count in required_specs.items():
            actual_count = global_actual_size_counts.get(req_size, 0)
            if actual_count < req_count:
                error_count += 1
                qty_errors.append(f"{req_size} (缺 {req_count - actual_count} 个)")
        
        self.render_tree(grouped_data)

        # --- 刷新极简仪表盘 (Dashboard) ---
        if error_count == 0 and total_files > 0:
            self.lbl_dashboard.setText(f"✅ 完美通过：共成功读取并匹配 {total_files} 个文件")
            self.lbl_dashboard.setStyleSheet("color: #28A745;")
            self.lbl_stats_detail.setText("所有文件格式正确且数量达标，随时可执行一键重命名。")
            self.btn_rename.setEnabled(True)
            self.btn_export_log.setVisible(False)
            self.tree.setVisible(False)
            self.btn_toggle_log.setText("🔽 展开明细日志")
        else:
            self.lbl_dashboard.setText(f"❌ 校验失败：发现 {error_count} 处异常")
            self.lbl_dashboard.setStyleSheet("color: #DC3545;")
            
            err_detail = []
            if total_files == 0:
                err_detail.append("未找到格式正确的文件。")
            if qty_errors:
                err_detail.append("数量不足：" + ", ".join(qty_errors))
            
            if err_detail:
                self.lbl_stats_detail.setText(" | ".join(err_detail))
            else:
                self.lbl_stats_detail.setText("建议展开下方日志，或点击【导出错误报告】发送给设计师。")

            self.btn_rename.setEnabled(False)
            self.btn_export_log.setVisible(True)
            self.tree.setVisible(True)
            self.btn_toggle_log.setText("🔼 收起明细日志")

    # ==================== 错误导出与重命名 ====================
    def export_error_log(self):
        """将校验错误的日志导出为 TXT 发给设计"""
        if not self.latest_report:
            return
            
        save_path, _ = QFileDialog.getSaveFileName(self, "导出错误报告", "素材修改意见反馈.txt", "Text Files (*.txt)")
        if not save_path:
            return
            
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write("=== 素材尺寸与格式错误报告 ===\n\n")
                
                # 记录文件详细错误
                err_files = [x for x in self.latest_report if x['status'] != "校验通过"]
                if err_files:
                    f.write("【需要修改的问题文件】：\n")
                    for x in err_files:
                        f.write(f"- 文件名：{x['file']}  (所在目录: {x['folder']})\n")
                        f.write(f"  当前尺寸: {x['actual_size']}\n")
                        f.write(f"  错误原因: {x['reason']}\n\n")
                        
                reqs = self.get_required_specs()
                f.write(f"\n【参考需求】：当前所需分辨率与数量为：\n")
                for k, v in reqs.items():
                    f.write(f"- {k} (需要 {v} 个)\n")
                    
            QMessageBox.information(self, "导出成功", f"错误报告已成功保存至：\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"写入文件时发生错误：{e}")

    def perform_rename(self):
        project_name = self.edit_project_name.text().strip()
        maker_abbr = self.edit_maker_abbr.text().strip().upper() or "MXW"
        if not project_name:
            QMessageBox.warning(self, "警告", "项目名称不能为空，请输入项目名后再进行重命名。")
            self.edit_project_name.setFocus()
            return
        
        all_success = True
        failed_folders = []
        
        for folder in self.current_folders:
            success = self.processor.rename_files(folder, project_name, maker_abbr)
            if not success:
                all_success = False
                failed_folders.append(os.path.basename(folder))
        
        if all_success:
            self.lbl_dashboard.setText("🚀 重命名大成功！")
            self.lbl_dashboard.setStyleSheet("color: #6f42c1;")
            self.lbl_stats_detail.setText("所有文件夹的处理已经完毕。你可以清空列表或清空重新投入新工作。")
            self.btn_rename.setEnabled(False) 
            self.tree.setVisible(False)
            
            QMessageBox.information(self, "完成", "✅ 批量重命名已全部顺利下发！")
        else:
            QMessageBox.critical(self, "部分错误", f"重命名过程中遇到失败！\n失败的文件夹有：{', '.join(failed_folders)}")

    # ==================== 窗口控制与拖拽逻辑 ====================
    def toggle_maximize(self):
        """点击绿色按鈕时切换最大化/还原"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def mousePressEvent(self, event):
        """鼠标按下时，判断是否在标题栏区域内，以允许拖动窗口"""
        if event.button() == Qt.LeftButton and event.position().y() < 40:
            self._is_tracking = True
            self._start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动时，更新窗口位置"""
        if getattr(self, '_is_tracking', False):
            self.move(event.globalPosition().toPoint() - self._start_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标松开，结束拖拽"""
        if event.button() == Qt.LeftButton:
            self._is_tracking = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # ==================== JSON 导入解析逻辑 ====================
    def select_json_file(self):
        """手动点击按鈕选择 JSON 文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择需求 JSON 文件", "", "JSON Files (*.json)")
        if file_path:
            self.load_data_from_json(file_path)

    def load_data_from_json(self, json_path):
        """核心解析逻辑：读取 JSON 并自动填入项目名和勾选尺寸"""
        try:
            # 预处理：解决 Invalid control character 错误
            import re
            with open(json_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            
            # 1. 移除 UTF-8 BOM (\ufeff)
            clean = raw.lstrip('\ufeff')
            # 2. 移除 // 单行注释，但要保护 URL（如 https://）
            # 使用 (?<![:/]) 确保 // 前面既不是冒号也不是斜杠
            clean = re.sub(r'(?<![:/])//.*', '', clean)
            
            # 使用 strict=False 允许解析包含物理控制字符的字符串
            data = json.loads(clean, strict=False)

            # 兼容批量模板 (JSON外层是个列表)
            # 确保 full_json_data 在 __init__ 中初始化为 []
            # 并在每次加载 JSON 时，如果 JSON 是列表，则更新 full_json_data
            if isinstance(data, list):
                self.full_json_data = data # 保存完整列表供批量初始化使用
                if not data:
                    raise ValueError("JSON 列表为空")
                
                if len(data) == 1:
                    data = data[0]
                else:
                    # 获取所有项目名称供用户选择
                    project_names = [f"{item.get('项目名称', '未知项目')} ({item.get('日期', '')})" for item in data]
                    
                    dialog = QInputDialog(self)
                    dialog.setWindowTitle("选择要导入的项目")
                    dialog.setLabelText("此 JSON 包含多个项目，请选择：")
                    dialog.setComboBoxItems(project_names)
                    dialog.setComboBoxEditable(False)
                    dialog.setOkButtonText("✅ 确认导入所选")
                    dialog.setCancelButtonText("❌ 取消")
                    
                    # 强制增大按钮和下拉框尺寸
                    dialog.setStyleSheet("""
                        QPushButton { 
                            min-width: 150px; 
                            min-height: 45px; 
                            font-size: 14px; 
                            font-weight: bold;
                        }
                        QComboBox {
                            min-height: 40px;
                            font-size: 14px;
                            padding-left: 10px;
                        }
                        QLabel {
                            font-size: 14px;
                            margin-bottom: 5px;
                        }
                    """)
                    
                    if dialog.exec() == QDialog.Accepted:
                        item = dialog.textValue()
                        selected_index = project_names.index(item)
                        data = data[selected_index]
                    else:
                        return # 用户取消选择

            if not isinstance(data, dict):
                raise ValueError("JSON 格式不正确，期望是一个项目对象")

            # 1. 自动填入项目名称 (优先使用外层的简洁项目名)
            project_name = data.get("项目名称", "")
            if project_name:
                self.edit_project_name.setText(project_name)

            # 2. 自动计算制作人缩写（拼音首字母全大写）
            maker_name = data.get("制作人", "")
            if maker_name:
                initials = "".join(lazy_pinyin(maker_name, style=Style.FIRST_LETTER)).upper()
                self.edit_maker_abbr.setText(initials)

            # 3. 先清空并重置所有勾选状态和数量
            for widgets in self.size_widgets.values():
                widgets["chk"].setChecked(False)
                widgets["qty"] = 0

            # 4. 遍历 JSON 里的尺寸并自动打勾，同时存入所需数量
            details = data.get("尺寸要求明细", [])
            matched_count = 0
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                    
                res = detail.get("分辨率")
                if not res:
                    continue  # 忽略混在里面的“其他信息”等无分辨率字典
                    
                norm_res = res.lower().replace('x', '*').replace('-', '*').strip()
                qty = int(detail.get("所需数量", 0) or 0)
                
                if norm_res in self.size_widgets:
                    self.size_widgets[norm_res]["chk"].setChecked(True)
                    self.size_widgets[norm_res]["qty"] = qty  # 存入数量
                    matched_count += 1

            # 5. 给出反馈提示
            maker_abbr = self.edit_maker_abbr.text()
            self.lbl_dashboard.setText(f"📄 已加载配置：{project_name} | 制作人：{maker_name} ({maker_abbr})")
            self.lbl_dashboard.setStyleSheet("color: #32D74B;")
            self.lbl_stats_detail.setText(f"已自动勾选 {matched_count} 项尺寸需求，将按数量校验。")

        except Exception as e:
            QMessageBox.warning(self, "读取 JSON 失败", f"无法解析该文件，请检查格式。\n{e}")

    def init_project_folders(self):
        """根据已导入的需求一键创建文件夹结构 (支持批量模式)"""
        project_name = self.edit_project_name.text().strip()
        if not project_name and not self.full_json_data:
            QMessageBox.warning(self, "未指定项目", "请先输入项目名称或导入需求 JSON！")
            return

        # 1. 检查是否存在批量数据
        items_to_process = []
        is_batch = False
        
        if len(self.full_json_data) > 1:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("批量创建确认")
            msg_box.setText(f"检测到 JSON 中包含 {len(self.full_json_data)} 个项目。\n\n是否要【批量一次性】创建所有项目的目录？\n\n(选“否”则仅创建当前界面显示的单个项目)")
            msg_box.setIcon(QMessageBox.Question)
            
            btn_yes = msg_box.addButton("✅ 批量创建所有", QMessageBox.YesRole)
            btn_no = msg_box.addButton("👤 仅创建当前这一个", QMessageBox.NoRole)
            btn_cancel = msg_box.addButton("❌ 取消", QMessageBox.RejectRole)
            
            # 强制增大按钮！
            msg_box.setStyleSheet("""
                QPushButton { 
                    min-width: 160px; 
                    min-height: 45px; 
                    font-size: 14px; 
                    font-weight: bold;
                    margin: 5px;
                    padding: 10px;
                }
            """)
            
            msg_box.exec()
            clicked_btn = msg_box.clickedButton()
            
            if clicked_btn == btn_cancel:
                return
            elif clicked_btn == btn_yes:
                items_to_process = self.full_json_data
                is_batch = True
        
        if not items_to_process:
            # 单个项目模式，使用当前 UI 上的信息
            if not project_name:
                QMessageBox.warning(self, "未指定项目", "当前项目名为空，无法创建。")
                return
            
            # 手动构建当前项目的结构
            current_specs = []
            for size_str, widgets in self.size_widgets.items():
                if widgets["chk"].isChecked():
                    current_specs.append({"分辨率": size_str})
            
            items_to_process = [{
                "项目名称": project_name,
                "尺寸要求明细": current_specs
            }]

        # 2. 让用户选择根目录
        root_dir = QFileDialog.getExistingDirectory(self, "选择项目存放的总根目录", "")
        if not root_dir:
            return

        try:
            total_projects = 0
            total_folders = 0
            # 固定 4 个 2 级空文件夹
            fixed_folders = ["截屏素材", "录屏素材", "奇觅生成", "模糊处理"]
            results_log = []

            # 3. 循环处理每一个项目
            for item in items_to_process:
                curr_proj_name = item.get("项目名称", "").strip()
                if not curr_proj_name:
                    continue
                
                project_root = os.path.join(root_dir, curr_proj_name)
                os.makedirs(project_root, exist_ok=True)
                
                # 收集二级目录
                subfolders = []
                details = item.get("尺寸要求明细", [])
                for d in details:
                    if isinstance(d, dict) and d.get("分辨率"):
                        # "1280*720" -> "1280-720"
                        res = d.get("分辨率").replace('*', '-')
                        if res not in subfolders:
                            subfolders.append(res)
                
                subfolders.extend(fixed_folders)
                
                # 创建子目录
                proj_created_count = 0
                for sub in subfolders:
                    target_path = os.path.join(project_root, sub)
                    if not os.path.exists(target_path):
                        os.makedirs(target_path, exist_ok=True)
                        proj_created_count += 1
                        total_folders += 1
                
                total_projects += 1
                results_log.append(f"- {curr_proj_name} (创建 {proj_created_count} 个子目录)")

            # 4. 反馈结果
            if total_projects > 0:
                summary = f"🎉 {'批量' if is_batch else '项目'}初始化完成！\n\n共处理项目：{total_projects} 个\n共创建文件夹：{total_folders} 个\n\n详情：\n" + "\n".join(results_log[:15])
                if len(results_log) > 15:
                    summary += f"\n... 以及其他 {len(results_log)-15} 个项目"
                QMessageBox.information(self, "初始化成功", summary)
            else:
                QMessageBox.warning(self, "初始化未执行", "未找到有效的项目数据进行创建。")
                
        except Exception as e:
            QMessageBox.critical(self, "创建失败", f"处理过程中发生错误：{e}")

    def resizeEvent(self, event):
        """窗口缩放时移动 SizeGrip 到右下角"""
        super().resizeEvent(event)
        if hasattr(self, 'size_grip'):
            self.size_grip.move(self.width() - 15, self.height() - 15)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MaterialProcessorGUI()
    window.show()
    sys.exit(app.exec())
