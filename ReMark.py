import os
import sys
import json
import warnings
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QCheckBox,
    QSizePolicy,
    QComboBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QEasingCurve
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QFontDatabase, QPixmap
from pycmarkgfm import gfm_to_html
from docutils.core import publish_parts
from MangoUI import Button, Slider


def get_relative_path(path, ref=__file__):
    script_dir = os.path.dirname(os.path.realpath(ref))

    return os.path.join(script_dir, path)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_config()
        self.fetch_css()
        self.init_ui()
        self.render_styles()

    def init_config(self):
        self.CONFIG = {
            'DIMENSIONS': [1400, 750],
            'LOCATION': [250, 200],
            'CONFIG_CACHE_FILE_PATH': '.configcache',
            'PREVIEW_MODE': 'LIGHT_MODE',
            'LOGO_FILE_PATH': 'static/logo_small.png',
            'LIGHT_MODE_PREVIEW_CSS_FILE_PATH': 'static/light-mode.css',
            'DARK_MODE_PREVIEW_CSS_FILE_PATH': 'static/dark-mode.css',
            'GITHUB_MARKDOWN_CSS_FILE_PATH': 'static/github-markdown.css',
            'EDITOR_DEFAULT_CONTENTS_MARKDOWN_FILE_PATH': 'static/editor-default-contents.md',
            'EDITOR_DEFAULT_CONTENTS_RESTRUCTUREDTEXT_FILE_PATH': 'static/editor-default-contents.rst',
            'EXPORT_FILE_DEST': 'README.txt',
            'UI_MODE': 'DARK_MODE',
            'LIGHT_MODE_UI_COLORS': {
                'PRIMARY_BACKGROUND_COLOR': 'rgb(242, 244, 253)',
                'SECONDARY_BACKGROUND_COLOR': 'rgb(246, 240, 249)',
                'PRIMARY_COLOR': 'rgb(241, 247, 249)',
                'SECONDARY_COLOR': 'rgb(0, 0, 102)',
                'TEXT_COLOR': 'rgb(12, 12, 39)',
                'BORDER_COLOR': 'rgb(0, 43, 128)',
                'DIVIDER_COLOR': 'rgb(179, 179, 204)',
            },
            'DARK_MODE_UI_COLORS': {
                'PRIMARY_BACKGROUND_COLOR': 'rgb(10, 20, 41)',
                'SECONDARY_BACKGROUND_COLOR': 'rgb(26, 0, 51)',
                'PRIMARY_COLOR': 'rgb(0, 0, 26)',
                'SECONDARY_COLOR': 'rgb(102, 102, 255)',
                'TEXT_COLOR': 'rgb(77, 184, 255)',
                'BORDER_COLOR': 'rgb(77, 184, 255)',
                'DIVIDER_COLOR': 'rgb(0, 0, 153)',
            },
            'BORDER_WIDTH': 1,
            'BORDER_RADIUS': 3,
            'FONT_FAMILY': 'Verdana',
            'FONT_SIZE': 12,
            'ENGINE': 'Markdown',
            'AVAILABLE_ENGINES': ['Markdown', 'reStructuredText'],
        }

        config_cache = self.get_config_cache()
        for key, value in config_cache.items():
            self.CONFIG[key] = value

    def get_config_cache(self):
        try:
            with open(get_relative_path(self.CONFIG['CONFIG_CACHE_FILE_PATH']), 'r') as f:
                config_cache = json.load(f)
        except IOError:
            return {}

        return config_cache

    def set_config_cache(self, **kwargs):
        config_cache = self.get_config_cache()
        for key, value in kwargs.items():
            config_cache[key] = value

        with open(get_relative_path(self.CONFIG['CONFIG_CACHE_FILE_PATH']), 'w') as f:
            json.dump(config_cache, f, indent=4, sort_keys=True)

    def fetch_css(self):
        self.CSS = {}

        with open(get_relative_path(self.CONFIG['GITHUB_MARKDOWN_CSS_FILE_PATH']), 'r') as f:
            self.CSS['GITHUB'] = f.read()

        with open(get_relative_path(self.CONFIG['LIGHT_MODE_PREVIEW_CSS_FILE_PATH']), 'r') as f:
            self.CSS['LIGHT_MODE'] = f.read()

        with open(get_relative_path(self.CONFIG['DARK_MODE_PREVIEW_CSS_FILE_PATH']), 'r') as f:
            self.CSS['DARK_MODE'] = f.read()

        self.CSS['PREVIEW_MODE'] = 'LIGHT_MODE'

    def init_ui(self):
        self.setGeometry(
            *self.CONFIG['LOCATION'],
            *self.CONFIG['DIMENSIONS'],
        )
        self.setWindowTitle('ReMark')

        self.slider = Slider(
            slideDirection = Qt.Orientation.Horizontal,
            animationDuration = 500,
            animationType = QEasingCurve.Type.OutQuad,
            wrapAround = False,
        )

        # navbar
        self.logo_pixmap = QPixmap(self.CONFIG['LOGO_FILE_PATH'])

        self.logo_label = QLabel()
        self.logo_label.setScaledContents(True)
        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setMaximumHeight(25)
        self.logo_label.setMaximumWidth(int((25 / self.logo_pixmap.height()) * self.logo_pixmap.width()))

        self.navigate_dashboard_button = Button()
        self.navigate_dashboard_button.setText('Dashboard')
        self.navigate_dashboard_button.clicked.connect(self.slider.slidePrevious)

        self.navigate_settings_button = Button()
        self.navigate_settings_button.setText('Settings')
        self.navigate_settings_button.clicked.connect(self.slider.slideNext)

        self.navbar_layout = QHBoxLayout()
        self.navbar_layout.addWidget(self.logo_label)
        self.navbar_layout.addStretch()
        self.navbar_layout.addWidget(self.navigate_dashboard_button)
        self.navbar_layout.addWidget(self.navigate_settings_button)

        # dashboard slide
        # editor & preview
        self.editor_label = QLabel()
        self.editor_label.setText('Editor')

        with open(self.CONFIG['EDITOR_DEFAULT_CONTENTS_' + self.CONFIG['ENGINE'].upper() + '_FILE_PATH'], 'r') as f:
            editor_default_contents = f.read()

        self.editor_textbox = QPlainTextEdit()
        self.editor_textbox.setPlainText(editor_default_contents)
        self.editor_textbox.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.editor_textbox.textChanged.connect(self.refresh_preview)

        self.preview_label = QLabel()
        self.preview_label.setText('Preview')

        self.preview_outer_widget = QWidget()
        self.preview_inner_layout = QVBoxLayout()
        self.preview_browser = QWebEngineView()
        self.preview_browser.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.preview_inner_layout.addWidget(self.preview_browser)
        self.preview_outer_widget.setLayout(self.preview_inner_layout)
        self.refresh_preview()

        self.editor_layout = QVBoxLayout()
        self.editor_layout.addWidget(self.editor_label)
        self.editor_layout.addWidget(self.editor_textbox)

        self.preview_layout = QVBoxLayout()
        self.preview_layout.addWidget(self.preview_label)
        self.preview_layout.addWidget(self.preview_outer_widget)

        self.editor_preview_column_view_layout = QHBoxLayout()
        self.editor_preview_column_view_layout.addLayout(self.editor_layout)
        self.editor_preview_column_view_layout.addLayout(self.preview_layout)

        # action buttons
        self.refresh_preview_button = Button()
        self.refresh_preview_button.setText('Update Preview')
        self.refresh_preview_button.clicked.connect(self.refresh_preview)

        self.export_html_button = Button()
        self.export_html_button.setText('Export HTML')
        self.export_html_button.clicked.connect(self.export_HTML)

        self.action_buttons_layout = QHBoxLayout()
        self.action_buttons_layout.addWidget(self.refresh_preview_button)
        self.action_buttons_layout.addWidget(self.export_html_button)
        self.action_buttons_layout.addStretch()

        self.dashboard_layout = QVBoxLayout()
        self.dashboard_layout.addLayout(self.editor_preview_column_view_layout)
        self.dashboard_layout.addLayout(self.action_buttons_layout)

        self.dashboard_slide = QWidget()
        self.dashboard_slide.setLayout(self.dashboard_layout)

        # settings slide
        self.ui_mode_button = QCheckBox()
        self.ui_mode_button.setChecked(self.CONFIG['UI_MODE'] == 'DARK_MODE')
        self.ui_mode_button.setText('Dark Mode UI')
        self.ui_mode_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.ui_mode_button.toggled.connect(self.update_ui_mode)

        self.preview_mode_button = QCheckBox()
        self.preview_mode_button.setChecked(self.CONFIG['PREVIEW_MODE'] == 'DARK_MODE')
        self.preview_mode_button.setText('Dark Mode Preview')
        self.preview_mode_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.preview_mode_button.toggled.connect(self.change_preview_mode)

        self.font_family_label = QLabel()
        self.font_family_label.setText('Font Family')

        font_families = QFontDatabase.families()
        self.CONFIG['FONT_FAMILY'] = self.CONFIG['FONT_FAMILY'] if self.CONFIG['FONT_FAMILY'] in font_families else font_families[0]
        self.font_family_select = QComboBox()
        self.font_family_select.addItems(font_families)
        self.font_family_select.setCurrentIndex(self.font_family_select.findText(self.CONFIG['FONT_FAMILY']))
        self.font_family_select.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.font_family_select.currentIndexChanged.connect(self.render_font)

        self.engine_label = QLabel()
        self.engine_label.setText('Compilation Engine')

        self.engine_select = QComboBox()
        self.engine_select.addItems(self.CONFIG['AVAILABLE_ENGINES'])
        self.engine_select.setCurrentIndex(self.engine_select.findText(self.CONFIG['ENGINE']))
        self.engine_select.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.engine_select.currentIndexChanged.connect(self.change_engine)

        self.settings_left_column_layout = QVBoxLayout()
        self.settings_left_column_layout.addWidget(self.ui_mode_button)
        self.settings_left_column_layout.addWidget(self.preview_mode_button)
        self.settings_left_column_layout.addWidget(self.font_family_label)
        self.settings_left_column_layout.addWidget(self.font_family_select)
        self.settings_left_column_layout.addStretch()

        self.settings_right_column_layout = QVBoxLayout()
        self.settings_right_column_layout.addWidget(self.engine_label)
        self.settings_right_column_layout.addWidget(self.engine_select)
        self.settings_right_column_layout.addStretch()

        self.settings_layout = QHBoxLayout()
        self.settings_layout.addLayout(self.settings_left_column_layout)
        self.settings_layout.addLayout(self.settings_right_column_layout)

        self.settings_slide = QWidget()
        self.settings_slide.setLayout(self.settings_layout)

        self.slider.addWidget(self.dashboard_slide)
        self.slider.addWidget(self.settings_slide)

        self.central_layout = QVBoxLayout()
        self.central_layout.addLayout(self.navbar_layout)
        self.central_layout.addWidget(self.slider)

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.central_layout)
        self.setCentralWidget(self.central_widget)

        self.show()

    def render_styles(self):
        ui_colors = self.CONFIG[self.CONFIG['UI_MODE'] + '_UI_COLORS']
        primary_background_color = ui_colors['PRIMARY_BACKGROUND_COLOR']
        secondary_background_color = ui_colors['SECONDARY_BACKGROUND_COLOR']
        primary_color = ui_colors['PRIMARY_COLOR']
        secondary_color = ui_colors['SECONDARY_COLOR']
        text_color = ui_colors['TEXT_COLOR']
        border_color = ui_colors['BORDER_COLOR']
        divider_color = ui_colors['DIVIDER_COLOR']
        border_width = self.CONFIG['BORDER_WIDTH']
        border_radius = self.CONFIG['BORDER_RADIUS']
        font_family = self.CONFIG['FONT_FAMILY']
        font_size = self.CONFIG['FONT_SIZE']

        gradient = f'x1:0 y1:0, x2:1 y2:0, stop:0 {primary_background_color}, stop:1 {secondary_background_color}'
        self.setStyleSheet(f'''
            QMainWindow {{
                background: QLinearGradient({gradient});
            }}
        ''')

        labels = [self.editor_label, self.preview_label, self.font_family_label, self.engine_label]
        for label in labels:
            label.setStyleSheet(f'''
                QLabel {{
                    color: {text_color};
                    font-size: {font_size}pt;
                    font-family: {font_family};
                }}
            ''')

        self.editor_textbox.setStyleSheet(f'''
            QPlainTextEdit {{
                color: {text_color};
                background-color: {primary_color};
                font-size: {font_size}pt;
                font-family: {font_family};
                border: {border_width} solid {border_color};
                border-radius: {border_radius}px;
            }}
        ''')

        self.preview_outer_widget.setStyleSheet(f'''
            * {{
                border: 1px solid {border_color};
                border-radius: {border_radius}px;
            }}
        ''')

        mangoui_buttons_left = [self.refresh_preview_button, self.export_html_button]
        for button in mangoui_buttons_left:
            button.setColors(
                primaryColor=secondary_color,
                secondaryColor=primary_background_color,
                parentBackgroundColor=primary_color,
            )
            button.setBorder(
                borderRadius=border_radius,
                borderWidth=border_width,
            )
            button.setFont(
                fontSize=font_size,
                fontFamily=font_family,
            )

        mangoui_buttons_right = [self.navigate_dashboard_button, self.navigate_settings_button]
        for button in mangoui_buttons_right:
            button.setColors(
                primaryColor=secondary_color,
                secondaryColor=secondary_background_color,
                parentBackgroundColor=primary_color,
            )
            button.setBorder(
                borderRadius=border_radius,
                borderWidth=border_width,
            )
            button.setFont(
                fontSize=font_size,
                fontFamily=font_family,
            )

        toggle_buttons = [self.ui_mode_button, self.preview_mode_button]
        for toggle_button in toggle_buttons:
            toggle_button.setStyleSheet(f'''
                QCheckBox {{
                    color: {primary_background_color};
                    background-color: {secondary_color};
                    font-size: {font_size}pt;
                    font-family: {font_family};
                    border-radius: {border_radius}px;
                    padding: 1px 3px 1px 2px;
                }}
            ''')

        selects = [self.font_family_select, self.engine_select]
        for select in selects:
            select.setStyleSheet(f'''
                QComboBox {{
                    color: {text_color};
                    selection-color: {primary_color};
                    selection-background-color: {secondary_color};
                    font-size: {font_size}pt;
                    font-family: {font_family};
                }}

                QComboBox:editable {{
                    color: {text_color};
                    background-color: yellow;
                }}

                QComboBox QAbstractItemView {{
                    background-color: {secondary_background_color};
                }}
            ''')

        self.slider.setStyleSheet((f'''
            QStackedWidget {{
                border-top: 1px solid {divider_color};
            }}
        '''))

    def render_font(self):
        self.CONFIG['FONT_FAMILY'] = self.font_family_select.currentText()
        self.set_config_cache(FONT_FAMILY=self.CONFIG['FONT_FAMILY'])
        self.render_styles()

    def get_compiled_html(self):
        css = self.CSS[self.CONFIG['PREVIEW_MODE']] + '\n\n' + self.CSS['GITHUB']
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                body = self.get_engine_func()(self.editor_textbox.toPlainText())
            except:
                body = '<p style="color: red;">[Compilation Error:]</p>'

        return f"""
            <!DOCTYPE html>
            <html>
            <style>
                {css}
            </style>
            <body>
            <div style="padding: 10px 20px 10px 20px;">
                {body}
            </div>
            </body>
            </html>
        """

    def refresh_preview(self):
        self.preview_browser.setHtml(self.get_compiled_html())

    def export_HTML(self):
        dest, _ = QFileDialog.getSaveFileName(self, 'Export HTML', self.CONFIG['EXPORT_FILE_DEST'])
        if len(dest) > 0:
            with open(dest, 'w') as f:
                f.write(self.get_compiled_html())

            self.set_config_cache(EXPORT_FILE_DEST=dest)

    def get_engine_func(self):
        ENGINE_FUNC = {
            'MARKDOWN': gfm_to_html,
            'RESTRUCTUREDTEXT': lambda s: publish_parts(s, writer_name='html', settings_overrides={'report_level':'quiet'})['html_body'],
        }

        return ENGINE_FUNC[self.CONFIG['ENGINE'].upper()]

    def change_engine(self):
        self.CONFIG['ENGINE'] = self.engine_select.currentText()
        self.set_config_cache(ENGINE=self.CONFIG['ENGINE'])
        self.refresh_preview()

    def change_preview_mode(self):
        self.CONFIG['PREVIEW_MODE'] = 'DARK_MODE' if self.preview_mode_button.isChecked() else 'LIGHT_MODE'
        self.set_config_cache(PREVIEW_MODE=self.CONFIG['PREVIEW_MODE'])
        self.refresh_preview()

    def update_ui_mode(self):
        self.CONFIG['UI_MODE'] = 'DARK_MODE' if self.ui_mode_button.isChecked() else 'LIGHT_MODE'
        self.set_config_cache(UI_MODE=self.CONFIG['UI_MODE'])
        self.render_styles()

    def resizeEvent(self, a0):
        self.set_config_cache(DIMENSIONS=[
            a0.size().width(),
            a0.size().height(),
        ])

        return super().resizeEvent(a0)

    def moveEvent(self, a0):
        self.set_config_cache(LOCATION=[
            a0.pos().x(),
            a0.pos().y(),
        ])

        return super().moveEvent(a0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    sys.exit(app.exec())
