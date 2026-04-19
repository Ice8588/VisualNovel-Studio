"""影片導出：Pillow 幀合成 + ffmpeg 編碼為 MP4。"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.core.models import Project

logger = logging.getLogger(__name__)


def _get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent

# ── 視覺常數（對應 engine style.css） ──

DEFAULT_BG_COLOR = (42, 42, 62)  # #2a2a3e — 新版深靛色背景
BOX_HEIGHT = 140
BOX_COLOR = (20, 20, 40, 217)  # rgba(20,20,40,0.85)
NAMEPLATE_RADIUS = 6
TEXT_COLOR = (238, 238, 238)  # #eee
NAME_COLOR = (255, 255, 255)
MARGIN_X = 30
MARGIN_Y = 20

# 立繪位置映射（對應 Character.position）
SPRITE_POSITIONS = {
    "left": 0.25,
    "center": 0.50,
    "right": 0.75,
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """將 #RRGGBB 轉換為 (R, G, B) 元組。"""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (70, 130, 180)  # fallback: 鋼藍色
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _calc_duration(text: str) -> float:
    """依字數計算停留秒數，與前端 Auto 模式邏輯一致。"""
    duration = 1.0 + len(text) * 0.15
    return max(1.5, min(duration, 8.0))


def find_ffmpeg() -> Path:
    """搜尋 ffmpeg 執行檔。向後相容包裝。"""
    from src.core.ffmpeg_manager import ensure_ffmpeg_or_raise
    return ensure_ffmpeg_or_raise()


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """載入中文字體，多層 fallback。"""
    candidates = [
        "msjh.ttc",  # Microsoft JhengHei（正黑體）
        "msyh.ttc",  # Microsoft YaHei（雅黑）
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    logger.warning("找不到中文字體，使用 Pillow 預設字體（中文可能顯示異常）")
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """中文逐字斷行。"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


class FrameRenderer:
    """Pillow 幀合成器：背景 + 立繪 + 對話框 + 名稱牌 + 文字。"""

    def __init__(self, resolution: tuple[int, int] = (1920, 1080)):
        self.width, self.height = resolution
        # 根據解析度縮放字體大小
        scale = self.height / 1080
        self._text_font = _load_font(max(12, int(24 * scale)))
        self._name_font = _load_font(max(10, int(20 * scale)))
        self._box_height = int(BOX_HEIGHT * scale)
        self._margin_x = int(MARGIN_X * scale)
        self._margin_y = int(MARGIN_Y * scale)
        self._bg_cache: dict[str, Image.Image] = {}

    def render_frame(
        self,
        background_path: Path | None,
        sprite_path: Path | None,
        character_name: str | None,
        text: str,
        dialogue_type: str,
        name_color: str | None = None,
        position: str = "center",
    ) -> Image.Image:
        """合成一幀：背景 + 立繪 + 對話框 + 名稱牌 + 文字。

        Args:
            name_color: 角色名牌顏色（#RRGGBB），None 使用預設鋼藍色。
            position: 立繪位置（left/center/right）。
        """
        # 1. 背景
        frame = self._get_background(background_path)

        # 2. 立繪（依位置放置）
        if sprite_path and Path(sprite_path).exists():
            frame = self._overlay_sprite(frame, Path(sprite_path), position)

        # 3. 對話框（半透明覆蓋）
        frame = self._draw_dialogue_box(frame)

        # 4 & 5. 名稱牌 + 文字
        draw = ImageDraw.Draw(frame)
        text_y = self.height - self._box_height + self._margin_y

        if character_name:
            plate_color = _hex_to_rgb(name_color) if name_color else (70, 130, 180)
            text_y = self._draw_name_plate(draw, character_name, text_y, plate_color)

        self._draw_text(draw, text, text_y)

        return frame

    def _get_background(self, path: Path | None) -> Image.Image:
        """取得背景圖，快取已載入的背景。"""
        if path is None or not Path(path).exists():
            return Image.new("RGBA", (self.width, self.height), DEFAULT_BG_COLOR + (255,))

        key = str(path)
        if key not in self._bg_cache:
            img = Image.open(path).convert("RGBA")
            img = img.resize((self.width, self.height), Image.LANCZOS)
            self._bg_cache[key] = img
        return self._bg_cache[key].copy()

    def _overlay_sprite(
        self, frame: Image.Image, sprite_path: Path, position: str = "center"
    ) -> Image.Image:
        """將立繪等比縮放後貼到底部，依 position 定位。"""
        sprite = Image.open(sprite_path).convert("RGBA")

        max_h = int(self.height * 0.8)
        max_w = int(self.width * 0.6)
        ratio = min(max_w / sprite.width, max_h / sprite.height, 1.0)
        new_w = int(sprite.width * ratio)
        new_h = int(sprite.height * ratio)
        sprite = sprite.resize((new_w, new_h), Image.LANCZOS)

        # 依位置決定水平中心點
        center_ratio = SPRITE_POSITIONS.get(position, 0.5)
        x = int(self.width * center_ratio) - new_w // 2
        x = max(0, min(x, self.width - new_w))
        y = self.height - new_h
        frame.paste(sprite, (x, y), sprite)
        return frame

    def _draw_dialogue_box(self, frame: Image.Image) -> Image.Image:
        """繪製底部半透明對話框。"""
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        box_top = self.height - self._box_height
        draw.rectangle(
            [(0, box_top), (self.width, self.height)],
            fill=BOX_COLOR,
        )
        return Image.alpha_composite(frame, overlay).convert("RGB")

    def _draw_name_plate(
        self, draw: ImageDraw.ImageDraw, name: str, y: int,
        plate_rgb: tuple[int, int, int] = (70, 130, 180),
    ) -> int:
        """繪製名稱牌，回傳文字起始 Y 座標。"""
        bbox = draw.textbbox((0, 0), name, font=self._name_font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x, pad_y = 16, 4

        plate_x = self._margin_x
        plate_y = y
        plate_w = text_w + pad_x * 2
        plate_h = text_h + pad_y * 2

        draw.rounded_rectangle(
            [(plate_x, plate_y), (plate_x + plate_w, plate_y + plate_h)],
            radius=NAMEPLATE_RADIUS,
            fill=plate_rgb,
        )
        draw.text(
            (plate_x + pad_x, plate_y + pad_y),
            name,
            font=self._name_font,
            fill=NAME_COLOR,
        )
        return plate_y + plate_h + 8

    def _draw_text(self, draw: ImageDraw.ImageDraw, text: str, y: int) -> None:
        """繪製對話文字，自動換行。"""
        max_width = self.width - self._margin_x * 2
        lines = _wrap_text(draw, text, self._text_font, max_width)

        for line in lines:
            draw.text(
                (self._margin_x, y),
                line,
                font=self._text_font,
                fill=TEXT_COLOR,
            )
            bbox = draw.textbbox((0, 0), line, font=self._text_font)
            line_h = bbox[3] - bbox[1]
            y += int(line_h * 1.6)


def render_transition_frame(
    frame1: Image.Image, frame2: Image.Image, alpha: float
) -> Image.Image:
    """交叉淡入：alpha=0 時為 frame1，alpha=1 時為 frame2。"""
    return Image.blend(frame1.convert("RGB"), frame2.convert("RGB"), alpha)


class VideoExporter:
    """將 Project 導出為 MP4 影片。"""

    def __init__(
        self,
        project: Project,
        output_path: Path,
        resolution: tuple[int, int] = (1920, 1080),
        transition_duration: float = 0.5,
        fps: int = 30,
    ):
        self._project = project
        self._output_path = Path(output_path)
        self._resolution = resolution
        self._transition_duration = transition_duration
        self._fps = fps
        self._renderer = FrameRenderer(resolution)
        self._ffmpeg = find_ffmpeg()

    def export(self, progress_callback=None) -> None:
        """執行完整導出管線。progress_callback(current, total)。"""
        scenes = self._project.scenes
        if not scenes:
            raise ValueError("專案中沒有場景，無法導出影片。")

        # 計算總對話數（用於進度）
        total_dialogues = sum(len(s.dialogues) for s in scenes)
        if total_dialogues == 0:
            raise ValueError("專案中沒有對話內容，無法導出影片。")

        temp_dir = Path(tempfile.mkdtemp(prefix="vnstudio_video_"))
        try:
            # Phase 1 & 2: 生成幀 + concat 文件
            concat_entries, audio_timeline = self._generate_frames(
                temp_dir, progress_callback, total_dialogues
            )

            # 寫入 concat 文件
            concat_path = temp_dir / "concat.txt"
            self._write_concat_file(concat_path, concat_entries)

            # Phase 3 & 4: ffmpeg 編碼
            self._encode_video(concat_path, audio_timeline, temp_dir)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _generate_frames(self, temp_dir, progress_callback, total_dialogues):
        """生成所有幀圖片，回傳 concat 條目和音訊時間軸。"""
        concat_entries = []  # [(filename, duration)]
        audio_timeline = []  # [(bgm_path, start_time, end_time)]
        frame_idx = 0
        current_time = 0.0
        progress_count = 0
        last_frame_path = None
        prev_bg = None

        for scene_idx, scene in enumerate(self._project.scenes):
            if not scene.dialogues:
                continue

            # 場景轉場（非首場景且背景變化時）
            if scene_idx > 0 and last_frame_path and scene.background != prev_bg:
                frame_idx, current_time = self._add_transition_frames(
                    temp_dir, last_frame_path, scene, frame_idx,
                    current_time, concat_entries
                )

            prev_bg = scene.background

            # BGM 時間軸起始
            bgm_start = current_time
            bgm_path = self._resolve_asset(scene.bgm) if scene.bgm else None

            for dlg in scene.dialogues:
                # 依字數計算停留時間
                duration = _calc_duration(dlg.text)

                # 合成幀
                bg_path = self._resolve_asset(scene.background)
                # Phase 1：Dialogue.sprite 已移除；Phase 3 改為查 scene_state.state_at(scene, idx)
                # 取出該列 active 的 stage segment 的 sprite。暫時 None 讓影片仍可導出（無立繪）。
                sprite_path = None

                # 查找角色資訊
                name_color = None
                position = "center"
                if dlg.character:
                    for c in self._project.characters:
                        if c.name == dlg.character:
                            name_color = c.name_color
                            position = c.position
                            break

                frame = self._renderer.render_frame(
                    bg_path, sprite_path, dlg.character, dlg.text, dlg.type,
                    name_color=name_color, position=position,
                )

                frame_filename = f"frame_{frame_idx:05d}.png"
                frame_path = temp_dir / frame_filename
                frame.save(frame_path)
                last_frame_path = frame_path

                concat_entries.append((frame_filename, duration))
                current_time += duration
                frame_idx += 1

                # 進度回報
                progress_count += 1
                if progress_callback:
                    progress_callback(progress_count, total_dialogues)

            # BGM 時間軸結束
            if bgm_path and bgm_path.exists():
                audio_timeline.append((bgm_path, bgm_start, current_time))

        return concat_entries, audio_timeline

    def _add_transition_frames(self, temp_dir, last_frame_path, scene, frame_idx,
                                current_time, concat_entries):
        """在場景之間插入淡入淡出幀。"""
        n_frames = max(1, int(self._transition_duration * self._fps))
        frame_duration = self._transition_duration / n_frames

        last_frame = Image.open(last_frame_path).convert("RGB")
        black = Image.new("RGB", self._resolution, DEFAULT_BG_COLOR)

        # 淡出到黑
        for i in range(n_frames):
            alpha = (i + 1) / n_frames
            blended = render_transition_frame(last_frame, black, alpha)
            filename = f"frame_{frame_idx:05d}.png"
            blended.save(temp_dir / filename)
            concat_entries.append((filename, frame_duration))
            frame_idx += 1
            current_time += frame_duration

        return frame_idx, current_time

    def _write_concat_file(self, path: Path, entries: list[tuple[str, float]]) -> None:
        """寫入 ffmpeg concat demuxer 格式文件。"""
        lines = []
        for filename, duration in entries:
            lines.append(f"file '{filename}'")
            lines.append(f"duration {duration:.4f}")
        # ffmpeg concat 需要最後一個 file 行（不帶 duration）
        if entries:
            lines.append(f"file '{entries[-1][0]}'")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _encode_video(self, concat_path, audio_timeline, temp_dir):
        """用 ffmpeg 將幀序列 + 音訊編碼為 MP4。"""
        cmd = [
            str(self._ffmpeg),
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
        ]

        # 音訊處理
        audio_path = None
        if audio_timeline:
            audio_path = self._build_audio_track(audio_timeline, temp_dir)
            if audio_path and audio_path.exists():
                cmd.extend(["-i", str(audio_path)])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", str(self._fps),
        ])

        if audio_path and audio_path.exists():
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
            ])

        cmd.append(str(self._output_path))

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 編碼失敗：\n{result.stderr[-500:]}")

    def _build_audio_track(self, timeline, temp_dir) -> Path | None:
        """將 BGM 時間軸合併為單一音訊檔案。"""
        if not timeline:
            return None

        # 簡單情境：只有一個 BGM，直接使用
        if len(timeline) == 1:
            return timeline[0][0]

        # 多段 BGM：用 ffmpeg 拼接
        total_duration = max(end for _, _, end in timeline)
        filter_parts = []
        inputs = []

        for i, (bgm_path, start, end) in enumerate(timeline):
            inputs.extend(["-i", str(bgm_path)])
            duration = end - start
            # 裁切並定位到對應時間點
            filter_parts.append(
                f"[{i}:a]atrim=0:{duration:.4f},asetpts=PTS-STARTPTS,"
                f"adelay={int(start * 1000)}|{int(start * 1000)}[a{i}]"
            )

        # 混合所有音軌
        mix_inputs = "".join(f"[a{i}]" for i in range(len(timeline)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(timeline)}:duration=longest[aout]"
        )

        audio_out = temp_dir / "audio_mixed.wav"
        cmd = [str(self._ffmpeg), "-y"]
        cmd.extend(inputs)
        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", "[aout]",
            str(audio_out),
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            logger.warning("BGM 混合失敗，將導出無音訊影片：%s", result.stderr[-200:])
            return None
        return audio_out

    def _resolve_asset(self, filename: str | None) -> Path | None:
        """將素材檔名解析為完整路徑。"""
        if not filename:
            return None
        if self._project.project_path:
            path = self._project.project_path.parent / "assets" / filename
            if path.exists():
                return path
        # 未儲存的專案
        unsaved = Path(tempfile.gettempdir()) / "vnstudio_unsaved" / "assets" / filename
        if unsaved.exists():
            return unsaved
        return None
