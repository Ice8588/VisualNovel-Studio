"""主視窗：二欄佈局（左：場景+角色 / 右：預覽+對話）、選單列、工具列。"""

import sys
from pathlib import Path

from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressDialog,
    QSplitter,
    QStatusBar,
)

from src.core.asset_manager import import_asset
from src.core.models import Project, Scene
from src.core.project_io import load_project, save_project
from src.core.text_parser import parse_file, _classify_lines
from src.ui import dialogs
from src.ui.center_panel import CenterPanel
from src.ui.left_panel import LeftPanel
from src.ui.theme import apply_theme, save_preference, load_preference


def _resource_root() -> Path:
    """支援 dev 與 PyInstaller 兩種模式的資源根目錄。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _design_icon(name: str) -> QIcon:
    """從 assets/design/icons/ 載入 SVG icon；缺檔回空 QIcon（不致命）。"""
    path = _resource_root() / "assets" / "design" / "icons" / f"{name}.svg"
    return QIcon(str(path)) if path.is_file() else QIcon()


class MainWindow(QMainWindow):
    """應用程式主視窗。"""

    _BASE_TITLE = "VisualNovel Studio v1.0.0"

    def __init__(self):
        super().__init__()
        self._project = Project()
        self._dirty = False
        self._theme_name, self._font_size = load_preference()
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()
        self._setup_status_bar()
        self._update_status()

    def _setup_ui(self) -> None:
        self.setWindowTitle(self._BASE_TITLE)
        self.resize(1280, 780)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()

        self.left_panel.setMinimumWidth(250)
        self.center_panel.setMinimumWidth(600)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.center_panel)

        # 左側 320px，右側佔滿
        splitter.setSizes([320, 960])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self.left_panel.set_project(self._project)
        self.center_panel.set_project(self._project)
        # B4：啟動時套用目前主題到預覽（後續 reload_preview 會以此注入 body class）
        self.center_panel.preview.set_theme(self._theme_name)

    def _setup_menu(self) -> None:
        menu_bar = QMenuBar()
        ico = _design_icon  # local alias

        # 檔案選單
        file_menu = menu_bar.addMenu("檔案")
        act_new = file_menu.addAction(ico("new"), "新增專案", self._on_new_project)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_open = file_menu.addAction(ico("open"), "開啟專案", self._on_open_project)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        act_save = file_menu.addAction(ico("save"), "儲存專案", self._on_save_project)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        file_menu.addAction(ico("save"), "另存專案", self._on_save_project_as)
        file_menu.addSeparator()
        file_menu.addAction(ico("import"), "匯入文字", self._on_import_text)
        file_menu.addSeparator()
        act_refresh = file_menu.addAction(ico("refresh"), "重新整理預覽", self._on_refresh_preview)
        act_refresh.setShortcut(QKeySequence("F5"))
        file_menu.addSeparator()
        file_menu.addAction(ico("close"), "結束", self.close)

        # 導出選單
        export_menu = menu_bar.addMenu("導出")
        export_menu.addAction(ico("export"), "導出網頁 (ZIP)", self._on_export_zip)
        export_menu.addAction(ico("export"), "導出單一 HTML", self._on_export_html)
        export_menu.addAction(ico("export"), "導出影片 (MP4)", self._on_export_video)

        # 外觀選單（獨立，即時套用）
        view_menu = menu_bar.addMenu("外觀")
        theme_menu = view_menu.addMenu("主題")
        self._act_dark = theme_menu.addAction("深色")
        self._act_dark.setCheckable(True)
        self._act_dark.setChecked(self._theme_name == "dark")
        self._act_dark.triggered.connect(lambda: self._apply_theme_immediate("dark"))
        self._act_light = theme_menu.addAction("淺色")
        self._act_light.setCheckable(True)
        self._act_light.setChecked(self._theme_name == "light")
        self._act_light.triggered.connect(lambda: self._apply_theme_immediate("light"))

        theme_menu.addSeparator()
        self._act_parchment = theme_menu.addAction("羊皮紙詩歌")
        self._act_parchment.setCheckable(True)
        self._act_parchment.setChecked(self._theme_name == "parchment")
        self._act_parchment.triggered.connect(
            lambda: self._apply_theme_immediate("parchment"))
        self._act_midnight = theme_menu.addAction("Midnight Ink")
        self._act_midnight.setCheckable(True)
        self._act_midnight.setChecked(self._theme_name == "midnight")
        self._act_midnight.triggered.connect(
            lambda: self._apply_theme_immediate("midnight"))
        self._act_figma_dark = theme_menu.addAction("Figma Dark")
        self._act_figma_dark.setCheckable(True)
        self._act_figma_dark.setChecked(self._theme_name == "figma-dark")
        self._act_figma_dark.triggered.connect(
            lambda: self._apply_theme_immediate("figma-dark"))
        self._act_ivory = theme_menu.addAction("Ivory Titanium")
        self._act_ivory.setCheckable(True)
        self._act_ivory.setChecked(self._theme_name == "ivory")
        self._act_ivory.triggered.connect(
            lambda: self._apply_theme_immediate("ivory"))

        font_menu = view_menu.addMenu("UI 字體大小")
        for size in [14, 16, 18, 20, 22, 24, 26, 28]:
            act = font_menu.addAction(f"{size}px")
            act.setCheckable(True)
            act.setChecked(size == self._font_size)
            act.triggered.connect(lambda _, s=size: self._apply_font_size_immediate(s))
        self._font_size_actions = font_menu.actions()

        view_menu.addSeparator()
        view_menu.addAction("恢復預設", self._on_restore_default_appearance)

        # 說明選單
        help_menu = menu_bar.addMenu("說明")
        help_menu.addAction(ico("help"), "使用教學", self._on_show_tutorial)
        help_menu.addAction(ico("seal"), "關於", self._on_show_about)
        help_menu.addSeparator()
        help_menu.addAction(ico("open"), "開啟 Log 資料夾", self._on_open_log_dir)

        self.setMenuBar(menu_bar)

    def _connect_signals(self) -> None:
        # 左側面板 → 場景切換
        self.left_panel.scene_selected.connect(self._on_scene_selected)
        self.left_panel.scene_added.connect(self._on_project_changed)
        self.left_panel.scene_removed.connect(self._on_scene_removed)
        self.left_panel.scenes_reordered.connect(self._on_project_changed)
        self.left_panel.scene_property_changed.connect(self._on_project_changed)

        # 左側面板 → 角色操作
        self.left_panel.character_add_requested.connect(self._on_add_character)
        self.left_panel.character_edit_requested.connect(self._on_edit_character)
        self.left_panel.character_remove_requested.connect(self._on_remove_character)
        self.left_panel.character_property_changed.connect(self._on_character_property_changed)
        self.left_panel.costume_edit_requested.connect(self._on_costume_edit)

        # 左側面板 → 素材匯入
        self.left_panel.bg_import_requested.connect(
            lambda: self._on_import_assets("backgrounds")
        )
        self.left_panel.music_import_requested.connect(
            lambda: self._on_import_assets("music")
        )

        # 中央面板 → 內容變更
        self.center_panel.project_changed.connect(self._on_project_changed)
        # 空狀態 CTA
        self.center_panel.empty_state_import_text.connect(self._on_import_text)
        self.center_panel.empty_state_add_scene.connect(self._on_empty_add_scene)

        # 預覽工具列按鈕
        self.center_panel.btn_refresh_preview.clicked.connect(self._on_refresh_preview)
        # 遊戲設定 SpinBox 即時同步
        self.center_panel.spin_dlg_font.valueChanged.connect(self._on_game_setting_changed)
        self.center_panel.spin_name_font.valueChanged.connect(self._on_game_setting_changed)
        self.center_panel.spin_opacity.valueChanged.connect(self._on_game_setting_changed)

    # ── 場景切換 ──

    def _on_scene_selected(self, index: int) -> None:
        """左側場景列表選取變更時，同步對話表格。"""
        self.center_panel.set_current_scene(index)

    def _on_scene_removed(self, _index: int) -> None:
        """場景被移除後更新。"""
        self._on_project_changed()
        # 同步中央面板
        new_index = self.left_panel.get_current_scene_index()
        self.center_panel.set_current_scene(new_index)

    def _on_empty_add_scene(self) -> None:
        """空狀態引導：新增第一個場景。"""
        scene_id = self._project.next_scene_id()
        self._project.scenes.append(Scene(id=scene_id))
        self.left_panel.refresh_scenes()
        self.left_panel.scene_list.setCurrentRow(0)
        self._on_project_changed()

    # ── 角色操作 ──

    def _on_add_character(self) -> None:
        from src.ui.dialogs import CharacterEditorDialog

        dlg = CharacterEditorDialog(project_dir=self._get_project_dir(), parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        char = dlg.get_character()
        self._project.characters.append(char)
        # 同步立繪到素材清單
        for sv in char.sprites:
            if sv.filename and sv.filename not in self._project.assets["sprites"]:
                self._project.assets["sprites"].append(sv.filename)
        self.left_panel.refresh_characters()
        self._on_project_changed()

    def _on_edit_character(self, index: int) -> None:
        if index < 0 or index >= len(self._project.characters):
            return
        from src.ui.dialogs import CharacterEditorDialog

        char = self._project.characters[index]
        dlg = CharacterEditorDialog(character=char, project_dir=self._get_project_dir(), parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        self._project.characters[index] = dlg.get_character()
        # 同步立繪到素材清單
        for sv in self._project.characters[index].sprites:
            if sv.filename and sv.filename not in self._project.assets["sprites"]:
                self._project.assets["sprites"].append(sv.filename)
        self.left_panel.refresh_characters(keep_tab=True)
        self.center_panel.refresh()
        self._on_project_changed()

    def _on_remove_character(self, index: int) -> None:
        if index < 0 or index >= len(self._project.characters):
            return
        name = self._project.characters[index].name
        affected = sum(
            1 for sc in self._project.scenes
            for dlg in sc.dialogues
            if dlg.character == name
        )
        detail = (
            f"\n{affected} 條對話將降級為旁白。"
            if affected else
            "\n此角色目前無對應對話。"
        )
        result = QMessageBox.question(
            self,
            "確認移除",
            f"確定要移除角色「{name}」嗎？{detail}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        # 軟性解綁：對話降級為旁白；stage 三 lane 清掉該角色的 segment
        for scene in self._project.scenes:
            for dlg in scene.dialogues:
                if dlg.character == name:
                    dlg.character = None
                    dlg.type = "narration"
            for lane in scene.all_stage_lanes().values():
                lane[:] = [seg for seg in lane if seg.character != name]
        self._project.characters.pop(index)
        self.left_panel.refresh_characters()
        self.center_panel.refresh()
        self._on_project_changed()

    def _on_costume_edit(self, char_index: int) -> None:
        if char_index < 0 or char_index >= len(self._project.characters):
            return
        from src.ui.dialogs import CostumeEditorDialog
        char = self._project.characters[char_index]
        dlg = CostumeEditorDialog(char, self._get_project_dir(), self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        char.costumes = dlg.get_costumes()
        for sv in char.sprites:
            if sv.filename and sv.filename not in self._project.assets["sprites"]:
                self._project.assets["sprites"].append(sv.filename)
        self.left_panel.refresh_characters(keep_tab=True)
        self.left_panel.refresh_costume_list()
        self.center_panel.refresh()
        self._on_project_changed()

    def _on_character_property_changed(self) -> None:
        self.left_panel.refresh_characters(keep_tab=True)
        self.center_panel.refresh()
        self._on_project_changed()

    # ── 主題 / 字體 ──

    def _apply_theme_immediate(self, theme: str) -> None:
        self._theme_name = theme
        for act, key in (
            (self._act_dark, "dark"),
            (self._act_light, "light"),
            (self._act_parchment, "parchment"),
            (self._act_midnight, "midnight"),
            (self._act_figma_dark, "figma-dark"),
            (self._act_ivory, "ivory"),
        ):
            act.setChecked(theme == key)
        app = QApplication.instance()
        apply_theme(app, self._theme_name, self._font_size)
        save_preference(self._theme_name, self._font_size)
        # B4：同步預覽主題並觸發重載
        self.center_panel.preview.set_theme(self._theme_name)

    def _apply_font_size_immediate(self, size: int) -> None:
        self._font_size = size
        for act in self._font_size_actions:
            act.setChecked(act.text() == f"{size}px")
        app = QApplication.instance()
        apply_theme(app, self._theme_name, self._font_size)
        save_preference(self._theme_name, self._font_size)

    def _on_restore_default_appearance(self) -> None:
        self._apply_theme_immediate("ivory")
        self._apply_font_size_immediate(18)

    def _on_show_tutorial(self) -> None:
        QMessageBox.information(
            self, "使用教學",
            "VisualNovel Studio 使用教學\n\n"
            "1. 新增專案或匯入文字\n"
            "2. 在場景列表中管理場景，設定背景、BGM、特效\n"
            "3. 在角色列表中新增角色，設定名稱、顏色、立繪差分\n"
            "4. 在文字列表中編輯文字，指定角色與差分\n"
            "5. 預覽畫面即時顯示效果\n"
            "6. 完成後導出為影片 (MP4) 或網頁 (ZIP/HTML)\n\n"
            "快捷鍵：\n"
            "  Ctrl+N — 新增專案\n"
            "  Ctrl+O — 開啟專案\n"
            "  Ctrl+S — 儲存專案\n"
            "  Delete — 刪除選取的對話\n"
            "  Ctrl+C/V — 複製/貼上對話"
        )

    def _on_show_about(self) -> None:
        QMessageBox.about(
            self, "關於",
            "VisualNovel Studio v1.0.0\n\n"
            "簡易視覺小說製作工具\n"
            "支援 MP4 影片導出、HTML5 網頁導出"
        )

    def _on_game_setting_changed(self) -> None:
        from src.core.models import GameSettings
        self._project.game_settings = GameSettings(
            dialogue_font_size=self.center_panel.spin_dlg_font.value(),
            name_font_size=self.center_panel.spin_name_font.value(),
            dialogue_box_opacity=self.center_panel.spin_opacity.value(),
        )
        self._on_project_changed()

    def _on_open_log_dir(self) -> None:
        import subprocess
        log_dir = str(Path.home() / ".vnstudio" / "logs")
        if sys.platform == "win32":
            subprocess.Popen(["explorer", log_dir])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", log_dir])
        else:
            subprocess.Popen(["xdg-open", log_dir])

    # ── 貼上文字 ──

    def _on_paste_text(self) -> None:
        dlg = dialogs.PasteTextDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        text = dlg.get_text()
        lines = text.splitlines()
        new_dialogues = _classify_lines(lines)

        if not new_dialogues:
            dialogs.show_info(self, "無可用內容", "貼上的文字中沒有可辨識的對話或旁白。")
            return

        # 確保有場景
        if not self._project.scenes:
            scene_id = self._project.next_scene_id()
            self._project.scenes.append(Scene(id=scene_id))
            self.left_panel.refresh_scenes()
            self.left_panel.scene_list.setCurrentRow(0)

        insert_after = None
        if dlg.is_insert_mode():
            insert_after = self.center_panel.get_selected_dialogue_index()

        self.center_panel.add_dialogues_to_current_scene(
            new_dialogues, insert_after=insert_after
        )

    # ── 檔案操作 ──

    def _on_new_project(self) -> None:
        if not self._confirm_discard():
            return
        self._project = Project()
        self._dirty = False
        self._rebuild_ui()

    def _on_open_project(self) -> None:
        if not self._confirm_discard():
            return
        path = dialogs.open_project_dialog(self)
        if not path:
            return
        try:
            self._project = load_project(path)
            self._dirty = False
            self._rebuild_ui()
        except (FileNotFoundError, ValueError) as e:
            dialogs.show_error(self, "開啟失敗", str(e))

    def _on_save_project(self) -> None:
        if self._project.project_path:
            self._save_to(self._project.project_path)
        else:
            self._on_save_project_as()

    def _on_save_project_as(self) -> None:
        path = dialogs.save_project_dialog(self)
        if path:
            self._save_to(path)

    def _save_to(self, path: Path) -> None:
        try:
            save_project(self._project, path)
            self._dirty = False
            self._update_title()
            dialogs.show_info(self, "儲存成功", f"專案已儲存至\n{path}")
        except OSError as e:
            dialogs.show_error(self, "儲存失敗", str(e))

    # ── 文字匯入 ──

    def _on_import_text(self) -> None:
        path = dialogs.open_text_file(self)
        if not path:
            return
        try:
            result = parse_file(path)
            # 確保有場景
            if not self._project.scenes:
                scene_id = self._project.next_scene_id()
                self._project.scenes.append(Scene(id=scene_id))
                self.left_panel.refresh_scenes()
                self.left_panel.scene_list.setCurrentRow(0)
            self.center_panel.add_dialogues_to_current_scene(result)
        except (ValueError, FileNotFoundError) as e:
            dialogs.show_error(self, "匯入失敗", str(e))

    # ── 素材操作 ──

    def _on_import_assets(self, category: str) -> None:
        if category == "music":
            paths = dialogs.open_audio_files(self)
        else:
            paths = dialogs.open_image_files(self)

        if not paths:
            return

        project_dir = self._get_project_dir()
        for path in paths:
            try:
                filename = import_asset(path, category, project_dir)
                self._project.assets[category].append(filename)
            except (ValueError, FileNotFoundError) as e:
                dialogs.show_error(self, "匯入失敗", str(e))

        self._sync_asset_lists()
        self._on_project_changed()

    # ── 預覽 ──

    def _on_project_changed(self) -> None:
        self._dirty = True
        self._update_title()
        self._update_status()
        self._on_refresh_preview()

    def _on_refresh_preview(self) -> None:
        self.center_panel.reload_preview(self._project)

    # ── 導出 ──

    def _has_dialogues(self) -> bool:
        return any(s.dialogues for s in self._project.scenes)

    def _check_export_ready(self) -> bool:
        if not self._project.scenes:
            dialogs.show_error(
                self, "無法導出", "專案中沒有任何場景。\n請先新增場景。"
            )
            return False
        if not self._has_dialogues():
            dialogs.show_error(
                self, "無法導出", "所有場景都沒有對話。\n請先匯入文字或新增對話。"
            )
            return False
        return True

    def _on_export_zip(self) -> None:
        if not self._check_export_ready():
            return
        path = dialogs.export_zip_dialog(self)
        if not path:
            return
        try:
            from src.core.exporter import export_zip

            export_zip(self._project, path)
            dialogs.show_info(self, "導出成功", f"已導出至\n{path}")
        except (FileNotFoundError, OSError) as e:
            dialogs.show_error(self, "導出失敗", str(e))

    def _on_export_html(self) -> None:
        if not self._check_export_ready():
            return

        # 估算大小，超過 30MB 警告
        from src.core.exporter_html import SIZE_THRESHOLD, estimate_export_size

        est_size = estimate_export_size(self._project)
        if est_size > SIZE_THRESHOLD:
            mb = est_size / (1024 * 1024)
            result = QMessageBox.warning(
                self,
                "檔案可能過大",
                f"估計導出大小約 {mb:.1f} MB，超過 30 MB 閾值。\n"
                "過大的檔案可能導致瀏覽器載入緩慢。\n\n"
                "是否繼續導出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        path, _ = QFileDialog.getSaveFileName(
            self, "導出單一 HTML", "", "HTML 檔案 (*.html)"
        )
        if not path:
            return

        try:
            from src.core.exporter_html import export_single_html

            export_single_html(self._project, Path(path))
            dialogs.show_info(self, "導出成功", f"已導出至\n{path}")
        except (FileNotFoundError, OSError) as e:
            dialogs.show_error(self, "導出失敗", str(e))

    def _on_export_video(self) -> None:
        if not self._check_export_ready():
            return

        # 檢查 FFmpeg 是否可用，不可用則提示下載
        from src.core.ffmpeg_manager import find_ffmpeg, download_ffmpeg

        if not find_ffmpeg():
            reply = QMessageBox.question(
                self,
                "需要 FFmpeg",
                "影片導出需要 FFmpeg（約 80 MB）。\n是否自動下載並安裝？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            dl_progress = QProgressDialog(
                "正在下載 FFmpeg…", "取消", 0, 100, self
            )
            dl_progress.setWindowTitle("下載 FFmpeg")
            dl_progress.setMinimumDuration(0)
            dl_progress.setValue(0)

            self._ffmpeg_worker = _FFmpegDownloadWorker()
            self._ffmpeg_worker.progress.connect(
                lambda d, t: dl_progress.setValue(
                    int(d / t * 100) if t > 0 else 0
                )
            )
            self._ffmpeg_worker.finished.connect(dl_progress.close)
            self._ffmpeg_worker.error.connect(
                lambda msg: self._on_ffmpeg_download_error(dl_progress, msg)
            )
            dl_progress.canceled.connect(
                self._ffmpeg_worker.requestInterruption
            )
            self._ffmpeg_worker.start()
            self._ffmpeg_worker.wait()  # 阻塞等待下載完成

            if not find_ffmpeg():
                return

        dlg = dialogs.VideoExportDialog(self._project, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        settings = dlg.get_settings()

        progress = QProgressDialog("正在導出影片…", "取消", 0, 100, self)
        progress.setWindowTitle("導出影片")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # v2：WebEngine 截幀（主執行緒）
        from src.ui.webengine_capture import WebEngineVideoExporter

        def update_progress(current: int, total: int) -> None:
            if total > 0:
                progress.setValue(int(current / total * 100))
            QApplication.processEvents()
            if progress.wasCanceled():
                raise InterruptedError("使用者取消導出。")

        try:
            exporter = WebEngineVideoExporter(
                self._project,
                settings["output_path"],
                resolution=settings["resolution"],
            )
            exporter.export(progress_callback=update_progress)
            self._on_video_export_done(progress, None)
        except InterruptedError:
            progress.close()
        except Exception as e:
            self._on_video_export_done(progress, str(e))
        finally:
            # 延遲刷新預覽，避免與 WebEngine 清理衝突
            QApplication.processEvents()
            QTimer.singleShot(500, self._on_refresh_preview)

    def _on_video_export_done(
        self, progress: QProgressDialog, error: str | None
    ) -> None:
        progress.close()
        if error:
            dialogs.show_error(self, "導出失敗", error)
        else:
            dialogs.show_info(self, "導出成功", "影片已成功導出。")

    def _on_ffmpeg_download_error(
        self, progress: QProgressDialog, error: str
    ) -> None:
        progress.close()
        dialogs.show_error(self, "下載失敗", error)

    # ── 內部工具 ──

    def _sync_asset_lists(self) -> None:
        self.left_panel.set_asset_lists(
            self._project.assets.get("backgrounds", []),
            self._project.assets.get("music", []),
        )

    def _rebuild_ui(self) -> None:
        self.left_panel.set_project(self._project)
        self.center_panel.set_project(self._project)
        self._sync_asset_lists()
        self._sync_game_settings_ui()
        self._on_refresh_preview()
        self._update_title()
        self._update_status()

    def _sync_game_settings_ui(self) -> None:
        gs = self._project.game_settings
        self.center_panel.spin_dlg_font.blockSignals(True)
        self.center_panel.spin_name_font.blockSignals(True)
        self.center_panel.spin_opacity.blockSignals(True)
        self.center_panel.spin_dlg_font.setValue(gs.dialogue_font_size)
        self.center_panel.spin_name_font.setValue(gs.name_font_size)
        self.center_panel.spin_opacity.setValue(gs.dialogue_box_opacity)
        self.center_panel.spin_dlg_font.blockSignals(False)
        self.center_panel.spin_name_font.blockSignals(False)
        self.center_panel.spin_opacity.blockSignals(False)

    def _update_title(self) -> None:
        title = self._BASE_TITLE
        if self._project.project_path:
            title += f" — {self._project.project_path.name}"
        if self._dirty:
            title += " *"
        self.setWindowTitle(title)

    def _setup_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self._lbl_stats = QLabel("")
        self._status_bar.addWidget(self._lbl_stats)
        self.setStatusBar(self._status_bar)

    def _update_status(self) -> None:
        """更新狀態列統計：場景數、對話數、估計總時長。"""
        if not self._project:
            self._lbl_stats.setText("")
            return
        scene_count = len(self._project.scenes)
        dlg_count = sum(len(s.dialogues) for s in self._project.scenes)
        # 使用與 engine.js / exporter_video.py 一致的估計公式（上限 8 秒）
        total_sec = 0.0
        for s in self._project.scenes:
            for d in s.dialogues:
                total_sec += max(1.5, min(1.0 + len(d.text) * 0.15, 8.0))
        minutes = int(total_sec // 60)
        seconds = int(total_sec % 60)
        self._lbl_stats.setText(
            f"場景 {scene_count} 個  │  對話 {dlg_count} 句  │  "
            f"估計時長 {minutes}:{seconds:02d}"
        )

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        result = QMessageBox.question(
            self,
            "未儲存的變更",
            "目前的變更尚未儲存，確定要放棄嗎？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if result == QMessageBox.StandardButton.Save:
            self._on_save_project()
            return not self._dirty
        return result == QMessageBox.StandardButton.Discard

    def _get_project_dir(self) -> Path:
        if self._project.project_path:
            return self._project.project_path.parent
        import tempfile

        return Path(tempfile.gettempdir()) / "vnstudio_unsaved"

    def closeEvent(self, event) -> None:
        if not self._confirm_discard():
            event.ignore()
            return
        self.center_panel.cleanup()
        super().closeEvent(event)


class _VideoExportWorker(QThread):
    """在背景執行影片導出。"""

    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, project: Project, settings: dict):
        super().__init__()
        self._project = project
        self._settings = settings

    def run(self) -> None:
        try:
            from src.core.exporter_video import VideoExporter

            exporter = VideoExporter(
                self._project,
                self._settings["output_path"],
                resolution=self._settings["resolution"],
            )
            exporter.export(
                progress_callback=lambda c, t: self.progress.emit(c, t)
            )
        except Exception as e:
            self.error.emit(str(e))


class _FFmpegDownloadWorker(QThread):
    """在背景下載 FFmpeg。"""

    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def run(self) -> None:
        try:
            from src.core.ffmpeg_manager import download_ffmpeg

            download_ffmpeg(
                progress_callback=lambda d, t: self.progress.emit(d, t)
            )
        except Exception as e:
            self.error.emit(str(e))
