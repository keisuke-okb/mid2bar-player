import pygame
import settings_loader
from assets_loader import load_assets


class Assets:
    def __init__(
        self,
        settings_json_path: str = "settings.json",
        assets_json_path: str = "assets.json",
    ):
        # settings
        self.settings = settings_loader.load(settings_json_path)
        s = self.settings

        # assets.json
        raw = load_assets(assets_json_path)

        # ========= project images =========
        self.project_front = raw["project_front"]
        self.project_back = raw["project_back"]

        # ========= now bar =========
        self.now_bar = raw["now_bar"]
        self.scaled_now_bar = pygame.transform.smoothscale(
            self.now_bar,
            (s.NOW_BAR_WIDTH, s.NOW_BAR_HEIGHT),
        )

        # ========= icons =========
        self.icons = {
            k: pygame.transform.smoothscale(
                img,
                (s.BAR_PASSED_COUNT_ICON_SIZE, s.BAR_PASSED_COUNT_ICON_SIZE),
            )
            for k, img in raw["icons"].items()
        }

        # ========= range gauge =========
        self.range_gauge = pygame.transform.smoothscale(
            raw["range_gauge"],
            (s.RANGE_GAUGE_W, s.RANGE_GAUGE_H),
        )

        # ========= bars =========
        self.bars = raw["bars"]
