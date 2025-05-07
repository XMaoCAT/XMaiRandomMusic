import sys
import json
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFileDialog, QTextEdit, QCheckBox, QLineEdit, QScrollArea,
    QFrame, QMessageBox, QGraphicsBlurEffect, QGraphicsView, QGraphicsScene, QStackedWidget, QFormLayout,
    QListWidget, QListWidgetItem
)
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
from PyQt5.QtGui import QDesktopServices, QPainter, QColor, QBrush, QFont, QMovie, QPixmap, QPalette
from PyQt5.QtCore import Qt, QTimer, QRect, QEasingCurve, QPropertyAnimation, QParallelAnimationGroup, QUrl
from functools import partial
import weakref

STYLE = {
    "primary": "#fcf7f7",
    "secondary": "#FFFFFF",
    "accent": "#00b2ff",
    "text": "#404040",
    "background": "#fcf7f7",
    "radius": "12px"
}

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            background-color: {STYLE['primary']};
            border-top-left-radius: {STYLE['radius']};
            border-top-right-radius: {STYLE['radius']};
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        self.title = QLabel("MaiMaiDX - 比赛歌曲抽选器")
        self.title.setStyleSheet(f"""
            color: {STYLE['text']};
            font-size: 16px;
            font-weight: 500;
        """)
        
        btn_style = f"""
            QPushButton {{
                color: {STYLE['text']};
                border: none;
                min-width: 30px;
                min-height: 30px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {STYLE['secondary']};
            }}
        """
        
        self.min_btn = QPushButton("—")
        self.close_btn = QPushButton("×")
        for btn in [self.min_btn, self.close_btn]:
            btn.setStyleSheet(btn_style)
        
        self.min_btn.clicked.connect(self.parent.showMinimized)
        self.close_btn.clicked.connect(self.parent.close)
        
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.min_btn)
        layout.addWidget(self.close_btn)

class ModernLabel(QLabel):
    def __init__(self, text=""):
        super().__init__(text)
        self.setStyleSheet(f"""
            color: {STYLE['text']};
            font-size: 14px;
            padding: 8px 0;
        """)

class DynamicBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bubbles = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_bubbles)
        self.timer.start(30)
        self.init_bubbles()

    def init_bubbles(self):
        for _ in range(50):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            radius = random.randint(5, 20)
            speed_x = random.uniform(-1, 1)
            speed_y = random.uniform(-1, 1)
            color = QColor(*random.choices([255, 200, 150], k=3))
            self.bubbles.append((x, y, radius, speed_x, speed_y, color))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 50))  # 白色背景带透明度

        for bubble in self.bubbles:
            x, y, radius, _, _, color = bubble
            painter.setBrush(QBrush(color, Qt.SolidPattern))
            painter.drawEllipse(x, y, radius, radius)

    def update_bubbles(self):
        for i, bubble in enumerate(self.bubbles):
            x, y, radius, speed_x, speed_y, color = bubble
            x += speed_x
            y += speed_y
            if x < -radius or x > self.width() + radius:
                x = random.randint(0, self.width())
            if y < -radius or y > self.height() + radius:
                y = random.randint(0, self.height())
            self.bubbles[i] = (x, y, radius, speed_x, speed_y, color)
        self.update()

class MaimaiDraw(QMainWindow):
    def __init__(self):
        super().__init__(flags=Qt.FramelessWindowHint)
        self.init_ui()
        self.data = []
        self.current_result = None
        self.net_manager = QNetworkAccessManager()
        self.partial_list = []
        self.anim_group = None
        self.flash_timer = None
        self.flash_index = 0
        self.old_pos = None
        self.animation_labels = []
        self.is_fullscreen = False
        self.fullscreen_factor = 1.5
        self.nav_visible = True
        self.selected_songs = set()  # 用于存储勾选的歌曲 MusicID
        self.filtered_data = []  # 用于存储当前筛选出的数据
        self.selected_songs_list = {}  # 用于存储选中的歌曲及其对应的 QLabel 和 QCheckBox

        self.setMinimumSize(1200, 800)
        self.setStyleSheet(f"background-color: {STYLE['background']};")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 动态背景
        self.dynamic_background = DynamicBackground(self)
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(10)
        self.dynamic_background.setGraphicsEffect(blur_effect)
        main_layout.addWidget(self.dynamic_background)
        
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # 导航栏
        self.nav_frame = QFrame()
        self.nav_frame.setFixedWidth(200)
        self.nav_frame.setStyleSheet(f"""
            background-color: {STYLE['secondary']};
            border-radius: {STYLE['radius']};
        """)
        nav_layout = QVBoxLayout(self.nav_frame)
        nav_layout.setContentsMargins(10, 20, 10, 20)
        nav_layout.setSpacing(15)
        
        self.btn_draw = self.create_nav_button("🐱  开始抽选")
        self.btn_settings = self.create_nav_button("⚙️ 软件设置")
        self.btn_search = self.create_nav_button("🔍 查找/制作")
        nav_layout.addWidget(self.btn_draw)
        nav_layout.addWidget(self.btn_settings)
        nav_layout.addWidget(self.btn_search)
        nav_layout.addStretch()
        
        self.fullscreen_btn = QPushButton("全屏化")
        self.fullscreen_btn.setFixedHeight(50)
        self.fullscreen_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE['accent']};
                color: {STYLE['primary']};
                border-radius: {STYLE['radius']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
        """)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        nav_layout.addWidget(self.fullscreen_btn)

        content_layout.addWidget(self.nav_frame)
        
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {STYLE['primary']};
                border-radius: {STYLE['radius']};
            }}
        """)
        
        self.init_draw_page()
        self.init_settings_page()
        self.init_search_page()
        
        content_layout.addWidget(self.stack, 1)
        main_layout.addWidget(content_widget)

        self.btn_draw.clicked.connect(self.switch_to_draw_page)
        self.btn_settings.clicked.connect(self.switch_to_settings_page)
        self.btn_search.clicked.connect(self.switch_to_search_page)
        self.stack.currentChanged.connect(self.on_stack_changed)

    def create_nav_button(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(50)
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {STYLE['text']};
                font-size: 14px;
                background-color: {STYLE['accent']};
                border-radius: 8px;
                padding: 8px;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
            QPushButton:pressed {{
                background-color: #007bb5;
            }}
        """)
        return btn

    def init_draw_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        self.result_label = ModernLabel("点击下方按钮开始抽选喵 OvO")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet(f"""
            font-size: 24px;
            background-color: {STYLE['secondary']};
            border-radius: {STYLE['radius']};
            padding: 20px;
        """)
        
        # 动画区域
        self.animation_area = QWidget()
        self.animation_area.setFixedHeight(120)
        self.animation_area.setStyleSheet(f"background-color: {STYLE['background']};")
        
        # 信息展示区
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setSpacing(20)
        
        # 封面图片
        self.image_view = QGraphicsView()
        self.image_scene = QGraphicsScene()
        self.image_view.setScene(self.image_scene)
        self.image_view.setFixedSize(300, 300)
        self.image_view.setAlignment(Qt.AlignCenter)
        self.image_view.setStyleSheet(f"""
            background-color: {STYLE['secondary']};
            border-radius: {STYLE['radius']};
        """)
        
        # 详细信息
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {STYLE['secondary']};
                color: {STYLE['text']};
                border: 2px solid {STYLE['accent']};
                border-radius: {STYLE['radius']};
                padding: 15px;
                font-size: 26px; /* 增加字体大小 */
            }}
        """)
        
        info_layout.addWidget(self.image_view)
        info_layout.addWidget(self.info_text)
        
        # 开始按钮
        self.start_btn = QPushButton("✨ 开始抽选")
        self.start_btn.setFixedHeight(50)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE['accent']};
                color: {STYLE['primary']};
                border-radius: {STYLE['radius']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
        """)
        self.start_btn.clicked.connect(self.start_animation)
        
        # 加载状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            color: {STYLE['text']};
            font-size: 14px;
            padding: 8px 0;
        """)
        
        layout.addWidget(self.result_label)
        layout.addWidget(self.animation_area)
        layout.addWidget(info_widget, 1)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.status_label)
        self.stack.addWidget(page)

    def init_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 设置项样式
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        
        page.setStyleSheet(f"""
            QLabel {{
                color: {STYLE['text']};
                font-size: 14px;
                padding: 8px 0;
            }}
            QComboBox, QLineEdit {{
                background-color: {STYLE['secondary']};
                color: {STYLE['text']};
                border: 2px solid {STYLE['accent']};
                border-radius: 8px;
                padding: 8px;
                min-height: 40px;
            }}
        """)
        
        # 文件选择按钮
        self.json_btn = self.create_tool_button("📁 选择曲目数据库")
        self.json_path = ModernLabel("未选择")
        self.txt_btn = self.create_tool_button("📝 选择要进行随机的表单")
        self.txt_path = ModernLabel("未选择")
        
        # 下拉菜单
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["全部随机", "部分随机"])
        self.level_combo = QComboBox()
        levels = [
            "全部等级",
            "1", "2", "3", "4", "5", "6", "7", "7+", "8", "8+", "9", "9+", "10", "10+", 
            "11", "11+", "12", "12+", "13", "13+", "14", "14+", "15"
        ]
        self.level_combo.addItems(levels)
        
        # 统一控件高度
        self.json_btn.setMinimumHeight(40)
        self.txt_btn.setMinimumHeight(40)
        self.mode_combo.setMinimumHeight(40)
        self.level_combo.setMinimumHeight(40)
        
        # 表单布局
        form_layout.addRow(ModernLabel("数据库文件:"), self.json_btn)
        form_layout.addRow(ModernLabel("当前路径:"), self.json_path)
        form_layout.addRow(ModernLabel("随机模式:"), self.mode_combo)
        form_layout.addRow(ModernLabel("等级选择:"), self.level_combo)
        form_layout.addRow(ModernLabel("部分列表:"), self.txt_btn)
        form_layout.addRow(ModernLabel("当前列表:"), self.txt_path)
        
        # 版权信息和 GitHub 按钮
        bottom_layout = QHBoxLayout()
        copyright_label = QLabel("@XMaoCAT 2025 | Debug&fix @Qwen-code-plus")
        copyright_label.setStyleSheet(f"""
            color: {STYLE['text']};
            font-size: 18px;
            align: center;
            margin-top: 18px;
        """)
        
        self.github_btn = QPushButton("   🐱   ")
        self.github_btn.setFixedHeight(30)
        self.github_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE['accent']};
                color: {STYLE['primary']};
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
        """)
        self.github_btn.clicked.connect(self.open_github)
        
        bottom_layout.addWidget(copyright_label)
        bottom_layout.addWidget(self.github_btn)
        bottom_layout.addStretch()
        
        # 添加到布局
        layout.addLayout(form_layout)
        layout.addLayout(bottom_layout)
        
        # 信号连接
        self.json_btn.clicked.connect(self.load_json)
        self.txt_btn.clicked.connect(self.load_txt)
        self.mode_combo.currentIndexChanged.connect(self.update_mode)
        self.level_combo.currentIndexChanged.connect(self.filter_data)
        
        self.stack.addWidget(page)

    def init_search_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 搜索框
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("输入歌曲名称、别名或 MusicID")
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                background-color: {STYLE['secondary']};
                color: {STYLE['text']};
                border: 2px solid {STYLE['accent']};
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }}
        """)
        self.search_box.textChanged.connect(self.search_songs)
        search_layout.addWidget(self.search_box)
        
        # 保存按钮
        self.save_btn = QPushButton("保存选中的歌曲")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE['accent']};
                color: {STYLE['primary']};
                border-radius: {STYLE['radius']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
        """)
        self.save_btn.clicked.connect(self.save_selected_songs)
        search_layout.addWidget(self.save_btn)
        
        layout.addLayout(search_layout)
        
        # 搜索结果区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)
        
        # 选中歌曲列表
        self.selected_songs_list_widget = QListWidget()
        self.selected_songs_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {STYLE['secondary']};
                color: {STYLE['text']};
                border: 2px solid {STYLE['accent']};
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }}
        """)
        self.selected_songs_list_widget.itemClicked.connect(self.remove_from_selected_songs)
        layout.addWidget(self.selected_songs_list_widget)
        
        self.stack.addWidget(page)

    def create_tool_button(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(40)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLE['accent']};
                color: {STYLE['primary']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #0095cc;
            }}
        """)
        return btn

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择JSON文件", "", "JSON文件 (*.json)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                self.json_path.setText(path.split('/')[-1])
                self.filter_data()
                QMessageBox.information(self, "成功", "数据库加载成功！")
                self.status_label.setText("数据库已加载")
                print(f"Loaded data: {len(self.data)} items")  # 调试信息
            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件加载失败：{str(e)}")
                self.data = []  # 确保数据清空
                self.status_label.setText("数据库加载失败")

    def load_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择TXT文件", "", "如果没有随机歌单请用[查找/制作]制作一份"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.partial_list = [
                        line.strip().split(',') for line in f if line.strip()
                    ]
                    self.partial_list = [item.strip() for sublist in self.partial_list for item in sublist]
                self.txt_path.setText(path.split('/')[-1])
                print(f"Loaded partial list: {self.partial_list}")  # 调试信息
            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件加载失败：{str(e)}")

    def filter_data(self):
        selected_level = self.level_combo.currentText()
        if selected_level == "全部等级":
            filtered_data = self.data
        else:
            # 处理等级选项，支持 "7+"、"8+" 等形式
            filtered_data = [
                item for item in self.data
                if selected_level in item["基础信息"]["等级"]
            ]
        
        if not filtered_data:
            print("No data after filtering")  # 调试信息
            QMessageBox.warning(self, "警告", "没有符合所选等级的曲目！")
            self.data = []  # 清空数据以避免后续错误
            self.status_label.setText("过滤后无数据")
            return
        
        self.data = filtered_data
        print(f"Filtered data: {len(self.data)} items")  # 调试信息
        self.status_label.setText(f"数据已过滤，共 {len(self.data)} 个项目")

    def update_mode(self, index):
        self.txt_btn.setEnabled(index == 1)
        self.txt_path.setEnabled(index == 1)

    def start_animation(self):
        if not self.data:
            QMessageBox.warning(self, "警告", "请先加载数据库文件！")
            return

        # 清理旧动画
        for label in self.animation_labels:
            label.deleteLater()
        self.animation_labels.clear()

        # 启动按钮果冻效果
        self.button_jelly_effect()

        # 启动倒计时和快速闪现动画
        self.countdown = 5
        self.start_btn.setText(str(self.countdown))
        self.start_btn.setEnabled(False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)

        self.flash_index = 0
        self.flash_timer = QTimer(self)
        self.flash_timer.timeout.connect(self.flash_song_info)
        self.flash_timer.start(50)  # 初始速度较快

    def button_jelly_effect(self):
        # 创建果冻效果动画组
        anim_group = QParallelAnimationGroup()

        # 放大
        scale_up = QPropertyAnimation(self.start_btn, b"geometry")
        scale_up.setDuration(300)  # 增加动画时间
        scale_up.setStartValue(QRect(self.start_btn.geometry()))
        scale_up.setEndValue(QRect(self.start_btn.x() - 10, self.start_btn.y() - 10, 160, 60))
        scale_up.setEasingCurve(QEasingCurve.OutBack)

        # 缩小
        scale_down = QPropertyAnimation(self.start_btn, b"geometry")
        scale_down.setDuration(300)  # 增加动画时间
        scale_down.setStartValue(QRect(self.start_btn.x() - 10, self.start_btn.y() - 10, 160, 60))
        scale_down.setEndValue(QRect(self.start_btn.geometry()))
        scale_down.setEasingCurve(QEasingCurve.InBack)

        # 颜色变化
        color_anim = QPropertyAnimation(self.start_btn, b"palette")
        color_anim.setDuration(3000)  # 增加动画时间
        color_anim.setStartValue(QPalette(QColor("#00b2ff")))
        color_anim.setEndValue(QPalette(QColor("#007bb5")))

        anim_group.addAnimation(scale_up)
        anim_group.addAnimation(scale_down)
        anim_group.addAnimation(color_anim)
        anim_group.start()

    def update_countdown(self):
        if self.countdown > 1:
            self.countdown -= 1
            self.start_btn.setText(str(self.countdown))
        else:
            self.timer.stop()
            self.start_btn.setText("✨ 开始抽选")
            self.start_btn.setEnabled(True)
            self.flash_timer.stop()
            self.show_final_result()

    def flash_song_info(self):
        if self.flash_index < len(self.data):
            # 从当前索引附近随机选择一首歌
            start_index = max(0, self.flash_index - 5)
            end_index = min(len(self.data), self.flash_index + 5)
            random_index = random.randint(start_index, end_index - 1)
            song_info = self.data[random_index]["基础信息"]
            self.result_label.setText(f"快速闪现：{song_info['歌名']} ({'/'.join(song_info['等级'])})")
            self.flash_index += 1

    def show_final_result(self):
        try:
            if not self.data:
                raise ValueError("数据库未加载")
                
            if self.mode_combo.currentIndex() == 1 and not self.partial_list:
                raise ValueError("部分随机模式需要加载列表文件")

            candidates = self.data if self.mode_combo.currentIndex() == 0 else [
                x for x in self.data if x["基础信息"]["MusicID"] in self.partial_list
            ]
            
            if not candidates:
                raise ValueError("没有符合条件的曲目")
            
            self.current_result = random.choice(candidates)
            info = self.current_result["基础信息"]
            
            # 更新界面
            self.result_label.setText(f"结果：{info['歌名']}")
            self.info_text.setText(
                f"艺术家：{info.get('artist', '未知')}\n"
                f"BPM：{info.get('bpm', '未知')}\n"
                f"版本：{info.get('版本', '未知')}\n"
                f"等级：{'/'.join(info['等级'])}\n"
                f"定数：{'/'.join(map(str, info['定数']))}"
            )
            
            if 'image_url' in info:
                image_url = f"https://maimaidx.jp/maimai-mobile/img/Music/{info['image_url']}"
                self.load_image(image_url)
            else:
                self.image_scene.clear()

        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def load_image(self, url):
        request = QNetworkRequest(QUrl(url))
        reply = self.net_manager.get(request)
        reply.finished.connect(partial(self.handle_image_load, reply=reply))

    def handle_image_load(self, reply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.image_scene.clear()
            if self.is_fullscreen:
                self.image_view.setFixedSize(500, 500)
            else:
                self.image_view.setFixedSize(300, 300)
            self.image_scene.addPixmap(pixmap)
            self.image_view.fitInView(self.image_scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            self.image_scene.clear()
            self.image_scene.addText("图片加载失败", QFont("Arial", 12))
        reply.deleteLater()

    def switch_to_draw_page(self):
        self.fade_out_current_page()
        self.stack.setCurrentIndex(0)
        self.fade_in_new_page()

    def switch_to_settings_page(self):
        self.fade_out_current_page()
        self.stack.setCurrentIndex(1)
        self.fade_in_new_page()

    def switch_to_search_page(self):
        self.fade_out_current_page()
        self.stack.setCurrentIndex(2)
        self.fade_in_new_page()

    def fade_out_current_page(self):
        current_widget = self.stack.currentWidget()
        fade_out = QPropertyAnimation(current_widget, b"windowOpacity")
        fade_out.setDuration(500)
        fade_out.setStartValue(1)
        fade_out.setEndValue(0)
        fade_out.start()

    def fade_in_new_page(self):
        new_widget = self.stack.currentWidget()
        fade_in = QPropertyAnimation(new_widget, b"windowOpacity")
        fade_in.setDuration(500)
        fade_in.setStartValue(0)
        fade_in.setEndValue(1)
        fade_in.start()

    def on_stack_changed(self, index):
        pass  # 不再需要单独的页面切换动画

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            self.fullscreen_btn.setText("最大化")
            self.scale_widgets(1 / self.fullscreen_factor)
            self.image_view.setFixedSize(300, 300)
        else:
            self.showFullScreen()
            self.is_fullscreen = True
            self.fullscreen_btn.setText("还原")
            self.scale_widgets(self.fullscreen_factor)
            self.image_view.setFixedSize(500, 500)

    def scale_widgets(self, factor):
        for widget in self.findChildren(QWidget):
            if widget is not self.fullscreen_btn:
                widget.resize(widget.size() * factor)
                widget.move(widget.pos() * factor)

    def mousePressEvent(self, event):
        self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = event.globalPos() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

    def open_github(self):
        url = QUrl("https://github.com/XMaoCAT")
        if not QDesktopServices.openUrl(url):
            QMessageBox.warning(self, "错误", "无法打开链接")

    def search_songs(self):
        query = self.search_box.text().lower()
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        # 清空之前的搜索结果
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        if not query:
            self.filtered_data = self.data
        else:
            self.filtered_data = [
                item for item in self.data
                if (query in item["基础信息"].get("歌名", "").lower() or
                    any(query in alias.lower() for alias in item.get("别名", [])) or
                    query in item["基础信息"].get("MusicID", "").lower())
            ]
        
        for item in self.filtered_data:
            song_info = item["基础信息"]
            music_id = song_info["MusicID"]
            
            # 创建一个容器来容纳每首歌的信息和复选框
            song_container = QWidget()
            song_layout = QHBoxLayout(song_container)
            song_layout.setContentsMargins(0, 0, 0, 0)
            song_layout.setSpacing(10)
            
            # 歌曲名称和艺术家
            song_label = QLabel(f"{song_info['歌名']} - {song_info.get('artist', '未知')}")
            song_label.setStyleSheet(f"""
                color: {STYLE['text']};
                font-size: 14px;
            """)
            
            # 复选框
            checkbox = QCheckBox()
            checkbox.setChecked(music_id in self.selected_songs)
            checkbox.stateChanged.connect(lambda state, mid=music_id, container=song_container: self.toggle_selection(state, mid, container))
            
            # 图片
            image_label = QLabel()
            image_label.setFixedSize(50, 50)
            image_label.setStyleSheet(f"""
                background-color: {STYLE['secondary']};
                border-radius: {STYLE['radius']};
            """)
            if 'image_url' in song_info:
                image_url = f"https://maimaidx.jp/maimai-mobile/img/Music/{song_info['image_url']}"
                self.load_song_image(image_url, image_label)
            
            song_layout.addWidget(checkbox)
            song_layout.addWidget(image_label)
            song_layout.addWidget(song_label)
            
            self.scroll_layout.addWidget(song_container)

    def load_song_image(self, url, label):
        request = QNetworkRequest(QUrl(url))
        reply = self.net_manager.get(request)
        weak_label = weakref.ref(label)
        reply.finished.connect(partial(self.handle_song_image_load, weak_label=weak_label, reply=reply))

    def handle_song_image_load(self, weak_label, reply):
        label = weak_label()  
        if label is None:
            reply.deleteLater()
            return
        
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            label.setText("图片加载失败")
        reply.deleteLater()

    def toggle_selection(self, state, music_id, container):
        if state == Qt.Checked:
            self.selected_songs.add(music_id)
            self.add_to_selected_songs_list(music_id, container)
        else:
            self.selected_songs.discard(music_id)
            self.remove_from_selected_songs_list(music_id)

    def add_to_selected_songs_list(self, music_id, container):
        if music_id not in self.selected_songs_list:

            for item in self.filtered_data:
                if item["基础信息"]["MusicID"] == music_id:
                    song_info = item["基础信息"]
                    break
            else:
                return
            
            list_item = QListWidgetItem(f"{song_info['歌名']} - {song_info.get('artist', '未知')}")
            self.selected_songs_list[music_id] = list_item
            self.selected_songs_list_widget.addItem(list_item)

    def remove_from_selected_songs_list(self, music_id):
        if music_id in self.selected_songs_list:
            list_item = self.selected_songs_list.pop(music_id)
            self.selected_songs_list_widget.takeItem(self.selected_songs_list_widget.row(list_item))

    def remove_from_selected_songs(self, item):
        music_id = None
        for mid, list_item in self.selected_songs_list.items():
            if list_item == item:
                music_id = mid
                break
        
        if music_id is not None:
            self.selected_songs.discard(music_id)
            self.remove_from_selected_songs_list(music_id)

    def save_selected_songs(self):
        if not self.selected_songs:
            QMessageBox.warning(self, "警告", "没有选中的歌曲")
            return
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存选中的歌曲", "", "文本文件 (*.txt)", options=options
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(','.join(self.selected_songs))
                QMessageBox.information(self, "成功", f"歌曲已保存到 {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败：{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont()
    font.setFamily("Microsoft YaHei" if sys.platform == "win32" else "Segoe UI")
    font.setPointSize(12)
    app.setFont(font)
    window = MaimaiDraw()
    window.show()
    sys.exit(app.exec_())
