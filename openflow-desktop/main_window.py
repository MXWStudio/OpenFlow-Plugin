import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QHeaderView, QListWidget, QCheckBox, 
    QSpinBox, QGridLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor, QFont, QIcon
from main import MaterialProcessor

class DragDropListWidget(QListWidget):
    """支持拖拽文件夹的 QListWidget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #666;
                border-radius: 5px;
                background-color: transparent;
                padding: 5px;
                color: #333;
            }
            QListWidget:hover { border: 2px dashed #0078D7; }
        """)

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
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folders.append(path)
            
            if folders and hasattr(self.parent(), 'add_folders_from_drop'):
                main_win = self.window()
                if hasattr(main_win, 'add_folders_from_drop'):
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
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("素材处理极简工作台 - v3.0")
        self.resize(1100, 800)
        
        # 【优化需求 1：修复主窗口无法接收拖拽】
        # 显式开启主窗口级别的拖放接收权限，否则哪怕重写了事件，系统也会显示禁止图标
        self.setAcceptDrops(True) 
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ==========================================
        # 1. 顶部：项目配置与文件夹拖拽区
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
        
        project_group = QGroupBox("📌 项目名称")
        project_layout = QVBoxLayout(project_group)
        self.edit_project_name = QLineEdit()
        self.edit_project_name.setPlaceholderText("例如：小火车游戏")
        project_layout.addWidget(self.edit_project_name)
        
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
                self.size_widgets[size_str] = {"chk": chkbox}
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
                self.size_widgets[size_str] = {"chk": chkbox}
                config_layout.addWidget(w, row, 1)
            
        right_panel.addWidget(project_group)
        right_panel.addWidget(config_group)
        
        top_layout.addWidget(folder_group, stretch=2)
        top_layout.addLayout(right_panel, stretch=1)
        
        main_layout.addLayout(top_layout)

        # ==========================================
        # 2. 中控仪表盘：极简结果展示区
        # ==========================================
        dash_frame = QFrame()
        dash_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 1px solid #555;
                border-radius: 8px;
            }
        """)
        dash_layout = QVBoxLayout(dash_frame)
        dash_layout.setAlignment(Qt.AlignCenter)
        
        # 【Fix 3】移除易导致拉伸变形的 padding 等内联样式，统一在后面通过 setFont 等方式安全修改；启用 WordWrap 和中心对齐。
        self.lbl_dashboard = QLabel("👋 欢迎！请添加文件夹。")
        self.lbl_dashboard.setAlignment(Qt.AlignCenter)
        self.lbl_dashboard.setWordWrap(True)
        self.lbl_dashboard.setStyleSheet("color: #eee;")
        # 固定最小高度或者提供合适的 SizePolicy 可以防止在内容切换时布局猛烈跳动导致拉伸
        self.lbl_dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font_dash = QFont("Microsoft YaHei", 18, QFont.Bold)
        self.lbl_dashboard.setFont(font_dash)
        
        self.lbl_stats_detail = QLabel("")
        self.lbl_stats_detail.setAlignment(Qt.AlignCenter)
        self.lbl_stats_detail.setWordWrap(True)
        self.lbl_stats_detail.setStyleSheet("color: #eee;")
        self.lbl_stats_detail.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        font_detail = QFont("Microsoft YaHei", 10)
        self.lbl_stats_detail.setFont(font_detail)
        
        dash_layout.addWidget(self.lbl_dashboard)
        dash_layout.addWidget(self.lbl_stats_detail)
        
        main_layout.addWidget(dash_frame)

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
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 100)
        self.tree.setVisible(False) # 默认隐藏
        
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.tree)
        
        # 将日志区的高度策略设为可扩展
        self.log_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        main_layout.addWidget(self.log_container)

        # ==========================================
        # 4. 底部：核心动作大按钮
        # ==========================================
        bottom_layout = QHBoxLayout()
        self.btn_validate = QPushButton("🔍 开始校验检测")
        self.btn_validate.setFixedHeight(50)
        self.btn_validate.setStyleSheet("background-color: #0078D7; color: white; border-radius: 6px; font-size: 16px; font-weight: bold;")
        self.btn_validate.clicked.connect(self.start_validation)

        self.btn_rename = QPushButton("火箭起飞：一键重命名 🚀")
        self.btn_rename.setFixedHeight(50)
        self.btn_rename.setEnabled(False) 
        self.btn_rename.setStyleSheet("""
            QPushButton { background-color: #28A745; color: white; border-radius: 6px; font-size: 16px; font-weight: bold; }
            QPushButton:disabled { background-color: #6c757d; color: #d6d6d6; }
        """)
        self.btn_rename.clicked.connect(self.perform_rename)
        
        bottom_layout.addWidget(self.btn_validate)
        bottom_layout.addWidget(self.btn_rename)
        main_layout.addLayout(bottom_layout)

    # ==================== QSettings 记忆配置 ====================
    def closeEvent(self, event):
        """窗口关闭时保存配置"""
        self.save_settings()
        super().closeEvent(event)

    def save_settings(self):
        self.settings.setValue("project_name", self.edit_project_name.text())
        
        specs_data = {}
        for size_str, widgets in self.size_widgets.items():
            specs_data[size_str] = {
                "checked": widgets["chk"].isChecked(),
                "count": 0
            }
        self.settings.setValue("specs", json.dumps(specs_data))

    def load_settings(self):
        proj_name = self.settings.value("project_name", "小火车游戏")
        self.edit_project_name.setText(proj_name)
        
        specs_json = self.settings.value("specs", "")
        if specs_json:
            try:
                specs_data = json.loads(specs_json)
                for size_str, data in specs_data.items():
                    if size_str in self.size_widgets:
                        self.size_widgets[size_str]["chk"].setChecked(data.get("checked", False))
            except json.JSONDecodeError:
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

    def update_dashboard_ui_state(self, is_cleared):
        self.btn_rename.setEnabled(False)
        self.btn_export_log.setVisible(False)
        if not is_cleared:
            self.lbl_dashboard.setText("⏳ 文件已载入。请点击底部【开始校验检测】")
            self.lbl_dashboard.setStyleSheet("color: #e67e22;") # 橙色
            self.lbl_stats_detail.setText("可以在展开日志中查看已载入的文件结构。")

    # ==================== 尺寸规格管理 ====================
    def get_required_specs(self):
        """【Fix 4】统一规范化规格符号：全部替换 xX 为 *，去除空格"""
        specs = {}
        for size_str, widgets in self.size_widgets.items():
            if widgets["chk"].isChecked():
                # 例如用户或预设带有 "640x360"，统一规范为 "640*360"
                normalized_size = size_str.lower().replace('x', '*').strip()
                specs[normalized_size] = 0
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
        if not project_name:
            QMessageBox.warning(self, "警告", "项目名称不能为空，请输入项目名后再进行重命名。")
            self.edit_project_name.setFocus()
            return
        
        all_success = True
        failed_folders = []
        
        for folder in self.current_folders:
            success = self.processor.rename_files(folder, project_name)
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MaterialProcessorGUI()
    window.show()
    sys.exit(app.exec())
