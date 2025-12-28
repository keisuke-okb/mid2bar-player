from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional


@dataclass(frozen=True)
class AnimationEntry:
    pos: Tuple[int, int]
    colors: Optional[Tuple[Tuple[int, int, int], ...]]


@dataclass(frozen=True)
class BarCountEntry:
    pos: Tuple[int, int]
    color: Tuple[int, int, int]


@dataclass(frozen=True)
class SettingsSchema:
    # ===== 画面設定 =====
    SCREEN_WIDTH: int = 1920
    SCREEN_HEIGHT: int = 1080
    WINDOW_WIDTH: int = 1920
    WINDOW_HEIGHT: int = 1080
    FULL_SCREEN: bool = False
    SCREEN_FPS: int = 60
    MENU_H: int = 300
    WINDOW_BACKGROUND_COLOR: Tuple[int, int, int] = (10, 10, 10)

    # ===== UI =====
    UI_LANG: str = "ja"
    UI_FONT: str = "./fonts/NotoSansJP-Medium.ttf"
    DEFAULT_VOLUME: int = 80
    PLAYBACK_TIME_SCALE: float = 1.0

    # ===== タイトル =====
    DISPLAY_TITLE_DURATION: float = 2.0
    SPLASH_TEXT_X_OFFSET: int = -50
    SPLASH_TEXT_Y_OFFSET: int = -50
    SPLASH_TEXT_LINE_HEIGHT: int = 80

    # ===== 色 =====
    BG_COLOR: Tuple[int, int, int] = (20, 20, 40)
    VIDEO_ALPHA: int = 210
    LINE_COLOR: Tuple[int, int, int, int] = (100, 100, 100, 200)
    NOTE_COLOR: Tuple[int, int, int] = (100, 100, 100)
    CURRENT_POS_COLOR: Tuple[int, int, int] = (255, 50, 50)
    PASSED_NOTE_COLOR: Tuple[int, int, int] = (255, 200, 100)
    TEXT_COLOR: Tuple[int, int, int] = (255, 255, 255)

    # ===== 音程バー領域 =====
    BAR_AREA_TOP: int = 50
    BAR_AREA_WIDTH: int = 1720
    BAR_AREA_HEIGHT: int = 250
    BAR_AREA_LEFT: int = 100

    DISPLAY_PITCH_RANGE_MIN: int = 23
    NOW_BAR_TOP: int = 34
    NOW_BAR_WIDTH: int = 200
    NOW_BAR_HEIGHT: int = 286

    HIDE_NOW_BAR_WHEN_NO_NOTES: bool = True
    BAR_AUTO_PLAY: bool = True
    BAR_AUTO_PLAY_CHANNELS: Tuple[int, ...] = (0, 1, 2)

    # ===== バー通過演出 =====
    BAR_PASSED_ROUGHNESS: int = 10
    BAR_PASSED_PARTICLE_RAND: float = 0.7
    BAR_PASSED_COUNT_ANIMATION_TIME: float = 0.8

    BAR_PASSED_COUNT_ANIMATION_DICT: Dict[str, AnimationEntry] = field(
        default_factory=lambda: {
            "normal": AnimationEntry((200, 360), None),
            "max": AnimationEntry((420, 360), ((255, 239, 85),)),
            "min": AnimationEntry((640, 360), ((161, 110, 241),)),
            "up": AnimationEntry((870, 360), ((230, 89, 37),)),
            "down": AnimationEntry((1010, 360), ((45, 153, 232),)),
            "long": AnimationEntry((1190, 360), ((101, 227, 94),)),
        }
    )

    BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH: float = -0.1
    BAR_PASSED_COUNT_ANIMATION_ACCEL: float = 3.0
    BAR_PASSED_COUNT_ICON_SIZE: int = 40
    BAR_PASSED_COUNT_ICON_MARGIN: int = 10

    # ===== 音数カウント =====
    BAR_COUNT_FONT: str = "./fonts/NotoSansJP-Black.ttf"
    BAR_COUNT_FONT_SIZE: int = 30

    BAR_COUNT_DICT: Dict[str, BarCountEntry] = field(
        default_factory=lambda: {
            "normal": BarCountEntry((210, 342), (241, 125, 166)),
            "max": BarCountEntry((430, 342), (255, 239, 85)),
            "min": BarCountEntry((650, 342), (161, 110, 241)),
            "up": BarCountEntry((850, 342), (230, 89, 37)),
            "down": BarCountEntry((1020, 342), (45, 153, 232)),
            "long": BarCountEntry((1200, 342), (101, 227, 94)),
        }
    )

    BAR_GLOW_DURATION: float = 0.3
    BAR_GLOW_SCALE: float = 3.0

    # ===== レンジゲージ =====
    RANGE_GAUGE_POS: Tuple[int, int] = (1480, 354)
    RANGE_GAUGE_W: int = 390
    RANGE_GAUGE_H: int = 23

    # ===== 表示 =====
    PREVIEW_TIME: float = 2.0
    REMAIN_TIME: float = 3.0
    FADE_TIME: float = 0.5
    LAG_TIME: float = 0.3

    # ===== シークバー =====
    SEEKBAR_TOP: int = 850
    SEEKBAR_LEFT: int = 100
    SEEKBAR_WIDTH: int = 1720
    SEEKBAR_HEIGHT: int = 10

    # ===== 採点 =====
    PITCH_MATCH_SCORE_RATIO: float = 0.3
    PITCH_ACCURACY_SCORE_RATIO: float = 0.7

    # ===== FFT / マイク =====
    RMS_THRESHOLD: float = 0.02
    MIC_INPUT_DURATION: float = 0.0
    MIC_INPUT_DELAY: float = 0.17
    MIC_INPUT_OFFSET: float = 0.2
    MIC_INPUT_PITCH_TOLERANCE: float = 0.8
    MIC_INPUT_NOTE_CONNECT_DURATION: float = 0.1
    MIC_INPUT_MARGIN: float = 0.01

    DEFAULT_SAMPLE_RATE: int = 44100
    DEFAULT_BLOCK_SIZE: int = 4096
    DEFAULT_CHANNELS: int = 1

    NOTE_NAMES: Tuple[str, ...] = (
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    )

    # ===== 録画 =====
    AUDIO_CODEC: str = "aac"
    AUDIO_BPS: str = "320k"
    VIDEO_CODEC: str = "h264_nvenc"
    VIDEO_BPS: str = "10M"
