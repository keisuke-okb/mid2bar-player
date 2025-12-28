import pygame
import csv
import time
import random
import os
import numpy as np
import pandas as pd

import lrc
import tools
import mid2csv
import settings_loader

from video import VideoPlayer
from particle import Particle, MicInputParticle
from fft import RealtimeFFTPitchDetector
from framerecorder import PipeFrameRecorder
from tools import get_lang_text_app

vec_mod12 = np.vectorize(tools.mod12_custom)


class Mid2barPlayerApp:
    def __init__(
        self,
        audio_path: str,
        mid_path: str,
        lrc_path: str,
        lrc_settings_path: str,
        video_paths: list = None,
        video_fixed_fps: int = 0,
        video_shuffle: bool = False,
        credit_text: str = None,
        splash_image: str = None,
        title_image: str = None,
        enable_mic_input: bool = False,
        mic_input_channel: int = 0,
        record: bool = False,
        settings_json_path: str = "settings.json",
        assets_json_path: str = "assets.json",
    ):
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption("MID2BAR-Player")

        self.setting_json_path = settings_json_path
        self.s = settings_loader.load(settings_json_path)
        self.window = pygame.display.set_mode(
            (self.s.WINDOW_WIDTH, self.s.WINDOW_HEIGHT), pygame.RESIZABLE
        )
        self.screen = pygame.Surface((self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT))

        if record:
            self.recorder = PipeFrameRecorder()
        else:
            self.recorder = None

        separator_csv = f"./data/marker.csv"
        note_csv = f"./data/note.csv"
        mid2csv.convert(mid_path, note_csv, separator_csv)

        self.audio_path = audio_path
        self.video_start_time = None
        self.current_time_diff = 0.0
        self.window_w, self.window_h = pygame.display.get_window_size()
        self.screen_scale = 1.0
        self.screen_offset_x = 0
        self.screen_offset_y = 0

        self.bar_auto_play = self.s.BAR_AUTO_PLAY
        self.enable_mic_input = enable_mic_input
        self.mic_input_channel = mic_input_channel
        self.music_volume = self.s.DEFAULT_VOLUME

        self.credit_text = credit_text
        self.splash_image = (
            tools.load_image(splash_image) if os.path.exists(splash_image) else None
        )
        self.title_image = (
            tools.load_image(title_image) if os.path.exists(title_image) else None
        )

        # Fonts
        self.font = pygame.font.Font(self.s.UI_FONT, 36)
        self.small_font = pygame.font.Font(self.s.UI_FONT, 28)
        self.large_font = pygame.font.Font(self.s.UI_FONT, 48)

        self.bar_count_font = pygame.font.Font(
            self.s.BAR_COUNT_FONT, self.s.BAR_COUNT_FONT_SIZE
        )

        # Init message
        self._flash_message(get_lang_text_app("generating subtitles"))

        # Load lyrics data
        lrc_filename = os.path.splitext(os.path.basename(lrc_path))[0]
        lyrics_json_path = f"./lyrics_images/{lrc_filename}.json"
        self.lyrics = lrc.load_lyrics(lrc_path, lrc_settings_path, lyrics_json_path)
        self.lyrics_types = [
            "background_main_lyric",
            "front_main_lyric",
            "background_ruby",
            "front_ruby",
        ]

        # Load images
        for i, lyric_data in enumerate(self.lyrics):
            for lyric_type in self.lyrics_types:
                lyric_data[lyric_type]["img"] = pygame.image.load(
                    lyric_data[lyric_type]["image"]
                ).convert_alpha()
            # Progress
            self._flash_message(f"{get_lang_text_app('loading subtitles')}...（{i+1}/{len(self.lyrics)}）")

        # Basic variables
        self.audio_path = audio_path
        self.separators = []
        self.notes = []
        self.particles = []
        self.mic_input_particles = []
        self.bar_count_particles = []
        self.bar_padding = 100
        self.pages = []
        self.page_scores = []
        self.scores = {}
        self.mic_inputs_df = None
        self.mic_notes = []
        self.mic_pages = []

        # Assets and video player
        from assets import Assets

        self.assets = Assets(settings_json_path, assets_json_path)
        self.video_player = VideoPlayer(
            video_paths or [],
            fixed_fps=video_fixed_fps,
            shuffle=video_shuffle,
            settings_json_path=settings_json_path,
        )

        # Menu
        self.menu_rect = pygame.Rect(
            0, self.s.SCREEN_HEIGHT - self.s.MENU_H, self.s.SCREEN_WIDTH, self.s.MENU_H
        )
        self.menu_visible = False
        self.menu_overlay = pygame.Surface(
            (self.s.SCREEN_WIDTH, self.s.MENU_H), pygame.SRCALPHA
        )
        self.menu_overlay.fill((0, 0, 0, 150))

        # CSV
        self.load_separator(separator_csv)
        self.load_notes(note_csv)

        # Audio
        sound = pygame.mixer.Sound(audio_path)
        self.song_duration = sound.get_length()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.set_volume(self.music_volume / 100)

        # Playing state
        self.playing = False
        self.start_time = 0
        self.current_time = 0
        self.time_scale = self.s.PLAYBACK_TIME_SCALE
        self.time_offset = 0.0
        self.current_section = 0
        self.now_bar_x = 0

        # Seek bar
        self.seek_position = 0

        # Pitch range
        pitches = [n["pitch"] for n in self.notes] if self.notes else [60, 84]
        self.min_pitch = min(pitches)
        self.max_pitch = max(pitches)
        self.pitch_range = self.max_pitch - self.min_pitch
        self.note_length_thre = np.percentile(
            [n["end"] - n["start"] for n in self.notes], 90
        )

        for i, note in enumerate(self.notes):
            if note["pitch"] == self.max_pitch:
                note["type"] = "max"
            elif note["pitch"] == self.min_pitch:
                note["type"] = "min"
            else:
                note["type"] = "normal"

            note["effects"] = []
            if (
                i + 1 < len(self.notes)
                and self.notes[i + 1]["pitch"] - self.notes[i]["pitch"]
                >= self.pitch_range / 2
            ):
                note["effects"].append("up")
            elif (
                i + 1 < len(self.notes)
                and self.notes[i + 1]["pitch"] - self.notes[i]["pitch"]
                <= -self.pitch_range / 2
            ):
                note["effects"].append("down")
            if note["end"] - note["start"] >= self.note_length_thre:
                note["effects"].append("long")

        if (self.max_pitch - self.min_pitch) < self.s.DISPLAY_PITCH_RANGE_MIN:
            delta = (
                self.s.DISPLAY_PITCH_RANGE_MIN - (self.max_pitch - self.min_pitch)
            ) // 2 + 1
            self.display_max_pitch = self.max_pitch + delta
            self.display_min_pitch = self.min_pitch - delta
        else:
            self.display_max_pitch = self.max_pitch
            self.display_min_pitch = self.min_pitch

        if (self.display_max_pitch - self.display_min_pitch) % 2 != 1:
            self.display_max_pitch += 1

        self.display_pitch_range = self.display_max_pitch - self.display_min_pitch
        self.bar_height = self.s.BAR_AREA_HEIGHT / (self.display_pitch_range - 1) * 2

        # assets scaling
        bar_h = (
            self.assets.bars[0]["normal"]["back_left"].get_height()
            - self.bar_padding * 2
        )
        scale = self.bar_height / bar_h
        self.bar_padding *= scale

        for ch_key, ch_dict in self.assets.bars.items():
            for type_key, part_dc in ch_dict.items():
                for part_key, surf in part_dc.items():
                    self.assets.bars[ch_key][type_key][
                        part_key
                    ] = tools.scale_with_aspect(surf, scale)

        # Calc pages
        self.calc_pages()

        # Mic input
        if self.enable_mic_input:
            self.detector = RealtimeFFTPitchDetector(settings_json_path=self.setting_json_path)
            self.detector.start()

    # ---------- I/O / Initialize ----------
    def _flash_message(self, text):
        surf = self.font.render(text, True, (255, 255, 255))
        rect = surf.get_rect(
            center=(self.s.SCREEN_WIDTH // 2, self.s.SCREEN_HEIGHT // 2)
        )
        self.screen.fill((0, 0, 0))
        self.screen.blit(surf, rect)
        self.update_screen()

    def load_separator(self, csv_path):
        """separator.csv"""
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                section_id = int(row[0])
                tick = int(row[1])
                time_str = row[3]
                time_sec = float(row[2])
                self.separators.append(
                    {
                        "id": section_id,
                        "tick": tick,
                        "time_str": time_str,
                        "time": time_sec,
                    }
                )
        if self.separators:
            last_time = self.separators[-1]["time"] + 10
            self.separators.append({"id": len(self.separators), "time": last_time})

    def load_notes(self, csv_path):
        """note.csv"""
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                note_id = int(row[0])
                start_time = float(row[5])
                end_time = float(row[6])
                octave = int(row[7])
                note_name = row[8]
                pitch = int(row[9])
                channel = int(row[10])
                self.notes.append(
                    {
                        "id": note_id,
                        "start": start_time,
                        "end": end_time,
                        "pitch": pitch,
                        "octave": octave,
                        "name": note_name,
                        "channel": channel,
                    }
                )

    # ---------- Pages ----------
    def calc_pages_mic(self):
        if len(self.pages) == 0:
            return

        self.mic_pages = []
        for i in range(len(self.pages)):
            start_time = self.pages[i]["start_time"]
            end_time = self.pages[i]["end_time"]
            duration = end_time - start_time
            notes = [
                n
                for n in self.mic_notes
                if start_time <= n["end"] and n["start"] <= end_time
            ]

            for note in notes:
                x_start = (
                    self.s.BAR_AREA_LEFT
                    + (note["start"] - start_time) / duration * self.s.BAR_AREA_WIDTH
                )
                x_end = (
                    self.s.BAR_AREA_LEFT
                    + (note["end"] - start_time) / duration * self.s.BAR_AREA_WIDTH
                )
                width = max(x_end - x_start, 3)
                y = (
                    self.s.BAR_AREA_TOP
                    + self.s.BAR_AREA_HEIGHT
                    - (note["pitch"] - self.display_min_pitch)
                    * self.s.BAR_AREA_HEIGHT
                    / (self.display_pitch_range - 1)
                )
                height = self.bar_height

                note.update(
                    {
                        "x_start": x_start,
                        "x_end": x_end,
                        "width": width,
                        "height": height,
                        "y": y,
                    }
                )

            self.mic_pages.append(
                {"start_time": start_time, "end_time": end_time, "notes": notes}
            )

    def calc_pages(self):
        self.pages = []
        for i in range(len(self.separators) - 1):
            start_time = self.separators[i]["time"]
            end_time = self.separators[i + 1]["time"]
            duration = end_time - start_time
            notes = [
                n
                for n in self.notes
                if start_time - 1e-5 <= n["start"] < end_time
                and end_time - n["start"] >= 1e-5
            ]
            if self.s.HIDE_NOW_BAR_WHEN_NO_NOTES and len(notes) == 0:
                continue

            for note in notes:
                x_start = (
                    self.s.BAR_AREA_LEFT
                    + (note["start"] - start_time) / duration * self.s.BAR_AREA_WIDTH
                )
                x_end = (
                    self.s.BAR_AREA_LEFT
                    + (note["end"] - start_time) / duration * self.s.BAR_AREA_WIDTH
                )
                width = max(x_end - x_start, 3)
                y = (
                    self.s.BAR_AREA_TOP
                    + self.s.BAR_AREA_HEIGHT
                    - (note["pitch"] - self.display_min_pitch)
                    * self.s.BAR_AREA_HEIGHT
                    / (self.display_pitch_range - 1)
                )
                height = self.bar_height
                note.update(
                    {
                        "x_start": x_start,
                        "x_end": x_end,
                        "width": width,
                        "height": height,
                        "y": y,
                    }
                )

            self.pages.append(
                {"start_time": start_time, "end_time": end_time, "notes": notes}
            )

        # Fade in and out
        for idx in range(len(self.pages)):
            fade_in_time = max(0, self.pages[idx]["start_time"] - self.s.PREVIEW_TIME)
            if idx != 0 and self.pages[idx - 1]["end_time"] > fade_in_time:
                fade_in_time = self.pages[idx - 1]["end_time"]
            self.pages[idx]["fade_in_time"] = fade_in_time

        for idx in range(len(self.pages)):
            fade_out_time = self.pages[idx]["end_time"] + self.s.REMAIN_TIME
            if (
                idx != len(self.pages) - 1
                and self.pages[idx + 1]["fade_in_time"] < fade_out_time
            ):
                fade_out_time = self.pages[idx + 1]["fade_in_time"]
            self.pages[idx]["fade_out_time"] = fade_out_time

        for idx in range(len(self.pages)):
            fade_in_time = max(0, self.pages[idx]["fade_in_time"] - self.s.FADE_TIME)
            self.pages[idx]["fade_in_time"] = fade_in_time

    def get_current_page_i(self):
        return [
            i
            for i, page in enumerate(self.pages)
            if page["fade_in_time"] <= self.current_time < page["fade_out_time"]
        ]

    def reset_mic_inputs(self):
        self.mic_inputs_df = None
        self.mic_notes = []
        self.mic_pages = []

    def update_mic_inputs(self):
        if not self.enable_mic_input:
            return

        mic_pitch = self.detector.get_latest()
        current_time_delay = self.current_time - self.s.MIC_INPUT_DELAY
        if mic_pitch["rms"] >= self.s.RMS_THRESHOLD and mic_pitch["midi"] is not None:
            data = [
                {
                    "time": current_time_delay,
                    "pitch": mic_pitch["midi"],
                    "octave": mic_pitch["octave"],
                    "name": mic_pitch["note_name"],
                    "channel": 0,
                }
            ]
            if self.mic_inputs_df is None:
                self.mic_inputs_df = pd.DataFrame(data)
            else:
                self.mic_inputs_df = pd.concat(
                    [self.mic_inputs_df, pd.DataFrame(data)], axis=0
                )

            return self.mic_inputs_df.iloc[-1].to_dict()

    def update_mic_notes(self):
        if not self.enable_mic_input or self.mic_inputs_df is None:
            return

        target_notes = [
            n
            for n in self.notes
            if n["start"] <= self.current_time - self.s.MIC_INPUT_DELAY
            and n["channel"] == self.mic_input_channel
        ]

        for i in range(len(target_notes)):
            if len(self.mic_notes) > 0:
                if self.mic_notes[-1]["end"] >= target_notes[i]["end"]:
                    continue

            start = target_notes[i]["start"]
            end = target_notes[i]["end"]
            target_pitch = target_notes[i]["pitch"]

            _matched = self.mic_inputs_df.loc[
                (self.mic_inputs_df["time"] >= start - self.s.MIC_INPUT_MARGIN)
                & (self.mic_inputs_df["time"] <= end + self.s.MIC_INPUT_MARGIN)
            ]
            if len(_matched) == 0:
                continue

            split_times = tools.split_range(
                start, end, self.s.MIC_INPUT_NOTE_CONNECT_DURATION
            )
            n = 0
            for j, (_start, _end) in enumerate(split_times):
                matched = self.mic_inputs_df.loc[
                    (self.mic_inputs_df["time"] >= _start - self.s.MIC_INPUT_MARGIN)
                    & (self.mic_inputs_df["time"] <= _end + self.s.MIC_INPUT_MARGIN)
                ]
                if len(matched) > 0:
                    pitch_diffs = vec_mod12(matched["pitch"].to_numpy() - target_pitch)
                    input_pitch = np.mean(pitch_diffs) + target_pitch
                else:
                    input_pitch = -j

                modi_pitch = tools.round_pitch(
                    input_pitch, target_pitch, self.s.MIC_INPUT_PITCH_TOLERANCE
                )

                if (
                    len(self.mic_notes) > 0
                    and len(split_times) > 1
                    and j > 0
                    and self.mic_notes[-1]["pitch"] == modi_pitch
                ):
                    self.mic_notes[-1]["end"] = _end
                    if (
                        j == len(split_times) - 1
                        and n == 0
                        and self.mic_notes[-1]["start"] == start
                        and modi_pitch == target_pitch
                    ):
                        # Full matched
                        self.mic_notes[-1]["type"] = "match_all"
                        self.mic_notes[-1]["efffects"] = target_notes[i]["effects"]

                elif input_pitch > 0:
                    if len(split_times) == 1 and target_pitch == modi_pitch:
                        typ = "match_all"
                        effects = target_notes[i]["effects"]
                    elif target_pitch == modi_pitch:
                        typ = "match"
                        effects = []
                    else:
                        typ = "unmatch"
                        effects = []

                    if len(self.mic_notes) == 0 or self.mic_notes[-1]["end"] <= _start:
                        self.mic_notes.append(
                            {
                                "start": _start,
                                "end": _end,
                                "pitch": modi_pitch,
                                "pitch_org": input_pitch,
                                "channel": self.mic_input_channel,
                                "type": typ,
                                "effects": effects,
                            }
                        )
                        n += 1

    # ---------- Real-time scoring ---------
    def compute_note_scores(self):
        if self.enable_mic_input:
            pages = []
            for p in self.pages:
                pages.append(
                    {
                        "start_time": p["start_time"],
                        "end_time": p["end_time"],
                        "duration": p["end_time"] - p["start_time"],
                        "notes": [
                            n
                            for n in p["notes"]
                            if n["channel"] == self.mic_input_channel
                        ],
                    }
                )

            mic_pages = self.mic_pages.copy()

            page_scores = []
            for page, mic_page in zip(pages, mic_pages):
                notes = page["notes"]
                mic_notes = mic_page["notes"]

                mic_starts = np.array([m["start"] for m in mic_notes], dtype=np.float64)
                mic_ends = np.array([m["end"] for m in mic_notes], dtype=np.float64)
                mic_pitches = np.array(
                    [m["pitch"] for m in mic_notes], dtype=np.float64
                )
                mic_pitch_org = np.array(
                    [m.get("pitch_org", m["pitch"]) for m in mic_notes],
                    dtype=np.float64,
                )

                mic_abs_diff = np.abs(mic_pitch_org - mic_pitches)
                mic_score_raw = np.where(
                    mic_abs_diff >= 6.0, 0.0, (6.0 - mic_abs_diff) / 6.0
                )

                for note in notes:
                    n_start = float(note["start"])
                    n_end = float(note["end"])
                    n_pitch = float(note["pitch"])
                    note_duration = max(0.0, n_end - n_start)
                    note["duration"] = note_duration
                    if note_duration <= 0.0:
                        note["match_ratio"] = 0.0
                        note["pitch_accuracy"] = 0.0
                        continue

                    overlap = np.minimum(n_end, mic_ends) - np.maximum(
                        n_start, mic_starts
                    )
                    overlap = np.maximum(overlap, 0.0)

                    mask = overlap > 0.0
                    total_overlap = overlap[mask].sum()

                    if total_overlap == 0.0:
                        note["match_ratio"] = 0.0
                        note["pitch_accuracy"] = 0.0
                        continue

                    equal_mask = (mic_pitches == n_pitch) & mask
                    equal_time = overlap[equal_mask].sum() if equal_mask.any() else 0.0
                    note["match_ratio"] = float(equal_time / note_duration)

                    scores = mic_score_raw[mask]
                    weights = overlap[mask]
                    weighted_score = (
                        float((scores * weights).sum() / weights.sum())
                        if weights.sum() > 0.0
                        else 0.0
                    )
                    note["pitch_accuracy"] = float(max(0.0, min(1.0, weighted_score)))

                note_duration_weights = np.array([m["duration"] for m in notes])
                if len(note_duration_weights) > 0:
                    score_pitch_match = (
                        np.average(
                            [m["match_ratio"] for m in notes],
                            weights=note_duration_weights,
                        )
                        * 100
                    )
                    score_pitch_accuracy = (
                        np.average(
                            [m["pitch_accuracy"] for m in notes],
                            weights=note_duration_weights,
                        )
                        * 100
                    )
                else:
                    score_pitch_match = 0.0
                    score_pitch_accuracy = 0.0

                page_scores.append(
                    {
                        "number_of_notes": len(notes),
                        "start_time": page["start_time"],
                        "end_time": page["end_time"],
                        "duration": page["duration"],
                        "pitch_match": score_pitch_match,
                        "pitch_accuracy": score_pitch_accuracy,
                        "weighted_score": self.s.PITCH_MATCH_SCORE_RATIO
                        * score_pitch_match
                        + self.s.PITCH_ACCURACY_SCORE_RATIO * score_pitch_accuracy,
                    }
                )

            self.page_scores = page_scores

    # ---------- Drawing helpers ----------
    def draw_background_lines(self):
        for i, pitch in enumerate(
            range(self.display_min_pitch, self.display_max_pitch + 1)
        ):
            y = (
                self.s.BAR_AREA_TOP
                + self.s.BAR_AREA_HEIGHT
                - (pitch - self.display_min_pitch)
                * self.s.BAR_AREA_HEIGHT
                / (self.display_pitch_range - 1)
            )
            if i % 2 == 0:
                sur = pygame.Surface((self.s.SCREEN_WIDTH, 2), pygame.SRCALPHA)
                sur.fill((255, 255, 255, 50))
                self.screen.blit(sur, (0, int(y)))

    def draw_now_bar(self):
        now_page_is = self.get_current_page_i()
        if not now_page_is:
            return
        now_page = self.pages[now_page_is[0]]
        start_time = now_page["start_time"]
        end_time = now_page["end_time"]
        x = (
            self.s.BAR_AREA_LEFT
            + (self.current_time - start_time)
            / (end_time - start_time)
            * self.s.BAR_AREA_WIDTH
        )
        self.now_bar_x = x
        x -= self.s.NOW_BAR_WIDTH / 2
        self.screen.blit(self.assets.scaled_now_bar, (x, self.s.NOW_BAR_TOP))

    def draw_notes(self):
        if self.enable_mic_input:
            # ===== Mic input =====
            self.update_mic_inputs()
            self.update_mic_notes()
            self.calc_pages_mic()

            now_page_is = self.get_current_page_i()
            for now_page_i in now_page_is:
                screen_note = pygame.Surface(
                    (self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT), pygame.SRCALPHA
                )
                now_page = self.pages[now_page_i]
                now_page_notes = now_page["notes"]

                fade_in_time = now_page["fade_in_time"]
                fade_out_time = now_page["fade_out_time"]

                start_time_delta = self.current_time - fade_in_time
                end_time_delta = self.current_time - fade_out_time

                if start_time_delta <= self.s.FADE_TIME:
                    display_width = (
                        self.s.BAR_AREA_WIDTH
                        * min(start_time_delta / self.s.FADE_TIME, 1)
                        + self.s.BAR_AREA_LEFT
                    )
                    alpha = int(min(start_time_delta / self.s.FADE_TIME, 1) * 255)
                    crop_bbox = [0, 0, display_width, self.s.SCREEN_HEIGHT]
                elif end_time_delta >= -self.s.FADE_TIME:
                    display_width = (
                        self.s.BAR_AREA_WIDTH
                        * min(-end_time_delta / self.s.FADE_TIME, 1)
                        + self.s.BAR_AREA_LEFT
                    )
                    alpha = int(min(-end_time_delta / self.s.FADE_TIME, 1) * 255)
                    crop_bbox = [
                        self.s.SCREEN_WIDTH - display_width,
                        0,
                        display_width,
                        self.s.SCREEN_HEIGHT,
                    ]
                else:
                    alpha = 255
                    crop_bbox = [0, 0, self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT]

                for note in now_page_notes:
                    tools.draw_stretchable_rounded_rect(
                        screen_note,
                        int(note["x_start"]),
                        int(note["y"] - note["height"] / 2),
                        int(note["width"]),
                        int(note["height"]),
                        self.assets.bars[note["channel"]][note["type"]]["back_left"],
                        self.assets.bars[note["channel"]][note["type"]]["back_mid"],
                        self.assets.bars[note["channel"]][note["type"]]["back_right"],
                        self.bar_padding,
                    )

                now_page_mic_notes = self.mic_pages[now_page_i]["notes"]
                for note in now_page_mic_notes:
                    tools.draw_stretchable_rounded_rect(
                        screen_note,
                        int(note["x_start"]),
                        int(note["y"] - note["height"] / 2),
                        int(note["width"]),
                        int(note["height"]),
                        self.assets.bars[note["channel"]][note["type"]]["passed_left"],
                        self.assets.bars[note["channel"]][note["type"]]["passed_mid"],
                        self.assets.bars[note["channel"]][note["type"]]["passed_right"],
                        self.bar_padding,
                    )
                    if (
                        note["type"] in ["match", "match_all"]
                        and random.random() < self.s.BAR_PASSED_PARTICLE_RAND
                    ):
                        px = random.uniform(note["x_start"], note["x_end"])
                        py = note["y"]
                        self.particles.append(Particle(px, py))

                    playing = (
                        note["start"]
                        <= self.current_time - self.s.MIC_INPUT_DELAY
                        <= note["end"]
                    )
                    if playing:
                        px = self.now_bar_x
                        py = random.uniform(
                            note["y"] - self.bar_height / 4,
                            note["y"] + self.bar_height / 4,
                        )
                        self.mic_input_particles.append(MicInputParticle(px, py))

                    # Impact draw effects
                    passed_time = self.current_time - note["end"]
                    if (
                        passed_time <= self.s.BAR_GLOW_DURATION
                        and note["type"] == "match_all"
                    ):
                        a = (
                            self.s.BAR_GLOW_DURATION - passed_time
                        ) / self.s.BAR_GLOW_DURATION
                        scale = (1 - a) * (self.s.BAR_GLOW_SCALE - 1) + 1
                        scaled_w = note["width"] * scale
                        scaled_h = note["height"] * scale

                        x_diff = (scaled_w - note["width"]) / 2
                        y_diff = (scaled_h - note["height"]) / 2
                        bar_glow = pygame.transform.smoothscale(
                            self.assets.bars[note["channel"]][note["type"]]["glow"],
                            (scaled_w, scaled_h),
                        )
                        bar_glow.set_alpha(int(a * 255))
                        screen_note.blit(
                            bar_glow,
                            (
                                note["x_start"] - x_diff,
                                note["y"] - note["height"] / 2 - y_diff,
                            ),
                        )

                    # Icons
                    for i, effect in enumerate(note["effects"]):
                        px = note["x_end"] - (i + 1) * self.s.BAR_PASSED_COUNT_ICON_SIZE
                        py = note["y"] - (
                            self.s.BAR_PASSED_COUNT_ICON_SIZE
                            + self.s.BAR_PASSED_COUNT_ICON_MARGIN
                        )
                        screen_note.blit(self.assets.icons[effect], (px, py))

                # Range gauges
                x1 = (
                    (
                        np.min([note["pitch"] for note in now_page_notes])
                        - self.min_pitch
                    )
                    / (self.pitch_range)
                    * self.s.RANGE_GAUGE_W
                )
                x2 = (
                    (
                        np.max([note["pitch"] for note in now_page_notes])
                        - self.min_pitch
                    )
                    / (self.pitch_range)
                    * self.s.RANGE_GAUGE_W
                )
                range_gauge = self.assets.range_gauge.subsurface(
                    pygame.Rect(x1, 0, x2 - x1, self.s.RANGE_GAUGE_H)
                )
                screen_note.blit(
                    range_gauge,
                    (self.s.RANGE_GAUGE_POS[0] + x1, self.s.RANGE_GAUGE_POS[1]),
                )

                # Finalize
                screen_note.set_alpha(alpha)
                screen_note_crop = screen_note.subsurface(pygame.Rect(*crop_bbox))
                self.screen.blit(screen_note_crop, (crop_bbox[0], 0))

            if len(now_page_is) > 0:
                for i in range(max(min(now_page_is) - 1, 0), max(now_page_is) + 1):
                    notes = self.mic_pages[i]["notes"]
                    for note in notes:
                        if note["type"] == "match_all":
                            passed_time = self.current_time - note["end"]
                            if passed_time >= 0:
                                # Count particles
                                if (
                                    0
                                    <= passed_time
                                    < self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                                ):
                                    prog = (
                                        passed_time
                                        / self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                                    )
                                    pos0 = (note["x_end"], note["y"])
                                    if note["pitch"] == self.max_pitch:
                                        note_typ = "max"
                                    elif note["pitch"] == self.min_pitch:
                                        note_typ = "min"
                                    else:
                                        note_typ = "normal"
                                    pos1 = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                        note_typ
                                    ]["pos"]
                                    col = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                        note_typ
                                    ]["colors"]
                                    pos = tools.point_on_curve_ratio(
                                        pos0,
                                        pos1,
                                        prog,
                                        self.s.BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH,
                                        self.s.BAR_PASSED_COUNT_ANIMATION_ACCEL,
                                    )

                                    self.bar_count_particles.append(
                                        Particle(
                                            pos[0],
                                            pos[1],
                                            size_range=(5, 8),
                                            life_decay=0.02,
                                            colors=col,
                                            v=0.5,
                                        )
                                    )

                                    for effect in note["effects"]:
                                        pos1 = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                            effect
                                        ]["pos"]
                                        col = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                            effect
                                        ]["colors"]
                                        pos = tools.point_on_curve_ratio(
                                            pos0,
                                            pos1,
                                            prog,
                                            self.s.BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH,
                                            self.s.BAR_PASSED_COUNT_ANIMATION_ACCEL,
                                        )

                                        self.bar_count_particles.append(
                                            Particle(
                                                pos[0],
                                                pos[1],
                                                size_range=(5, 8),
                                                life_decay=0.02,
                                                colors=col,
                                                v=0.5,
                                            )
                                        )

        else:
            # ===== Demo =====
            now_page_is = self.get_current_page_i()
            for now_page_i in now_page_is:
                screen_note = pygame.Surface(
                    (self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT), pygame.SRCALPHA
                )
                now_page = self.pages[now_page_i]
                now_page_notes = now_page["notes"]

                fade_in_time = now_page["fade_in_time"]
                fade_out_time = now_page["fade_out_time"]

                start_time_delta = self.current_time - fade_in_time
                end_time_delta = self.current_time - fade_out_time

                if start_time_delta <= self.s.FADE_TIME:
                    display_width = (
                        self.s.BAR_AREA_WIDTH
                        * min(start_time_delta / self.s.FADE_TIME, 1)
                        + self.s.BAR_AREA_LEFT
                    )
                    alpha = int(min(start_time_delta / self.s.FADE_TIME, 1) * 255)
                    crop_bbox = [0, 0, display_width, self.s.SCREEN_HEIGHT]
                elif end_time_delta >= -self.s.FADE_TIME:
                    display_width = (
                        self.s.BAR_AREA_WIDTH
                        * min(-end_time_delta / self.s.FADE_TIME, 1)
                        + self.s.BAR_AREA_LEFT
                    )
                    alpha = int(min(-end_time_delta / self.s.FADE_TIME, 1) * 255)
                    crop_bbox = [
                        self.s.SCREEN_WIDTH - display_width,
                        0,
                        display_width,
                        self.s.SCREEN_HEIGHT,
                    ]
                else:
                    alpha = 255
                    crop_bbox = [0, 0, self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT]

                for note in now_page_notes:
                    tools.draw_stretchable_rounded_rect(
                        screen_note,
                        int(note["x_start"]),
                        int(note["y"] - note["height"] / 2),
                        int(note["width"]),
                        int(note["height"]),
                        self.assets.bars[note["channel"]][note["type"]]["back_left"],
                        self.assets.bars[note["channel"]][note["type"]]["back_mid"],
                        self.assets.bars[note["channel"]][note["type"]]["back_right"],
                        self.bar_padding,
                    )

                    current_time_lag = self.current_time - self.s.LAG_TIME

                    if (
                        self.bar_auto_play
                        and note["channel"] in self.s.BAR_AUTO_PLAY_CHANNELS
                    ):
                        if current_time_lag >= note["end"]:
                            tools.draw_stretchable_rounded_rect(
                                screen_note,
                                int(note["x_start"]),
                                int(note["y"] - note["height"] / 2),
                                int(note["width"]),
                                int(note["height"]),
                                self.assets.bars[note["channel"]][note["type"]][
                                    "passed_left"
                                ],
                                self.assets.bars[note["channel"]][note["type"]][
                                    "passed_mid"
                                ],
                                self.assets.bars[note["channel"]][note["type"]][
                                    "passed_right"
                                ],
                                self.bar_padding,
                            )
                        elif current_time_lag > note["start"]:
                            w = (
                                (current_time_lag - note["start"])
                                / (note["end"] - note["start"])
                                * note["width"]
                            )
                            w = (
                                w
                                // self.s.BAR_PASSED_ROUGHNESS
                                * self.s.BAR_PASSED_ROUGHNESS
                            )
                            tools.draw_stretchable_rounded_rect(
                                screen_note,
                                int(note["x_start"]),
                                int(note["y"] - note["height"] / 2),
                                int(w),
                                int(note["height"]),
                                self.assets.bars[note["channel"]][note["type"]][
                                    "fill_left"
                                ],
                                self.assets.bars[note["channel"]][note["type"]][
                                    "fill_mid"
                                ],
                                self.assets.bars[note["channel"]][note["type"]][
                                    "fill_right"
                                ],
                                self.bar_padding,
                            )

                        # If playing, draw mic input particles
                        playing = note["start"] <= self.current_time < note["end"]
                        if playing:
                            px = self.now_bar_x
                            py = random.uniform(
                                note["y"] - self.bar_height / 4,
                                note["y"] + self.bar_height / 4,
                            )
                            self.mic_input_particles.append(MicInputParticle(px, py))

                        # Note particles including mic lag
                        passed_time = self.current_time - self.s.LAG_TIME - note["end"]
                        if passed_time >= 0:
                            # Particles for passed notes
                            if random.random() < self.s.BAR_PASSED_PARTICLE_RAND:
                                px = random.uniform(note["x_start"], note["x_end"])
                                py = note["y"]
                                self.particles.append(Particle(px, py))

                            # Impact glow effects
                            if passed_time <= self.s.BAR_GLOW_DURATION:
                                a = (
                                    self.s.BAR_GLOW_DURATION - passed_time
                                ) / self.s.BAR_GLOW_DURATION
                                scale = (1 - a) * (self.s.BAR_GLOW_SCALE - 1) + 1
                                scaled_w = note["width"] * scale
                                scaled_h = note["height"] * scale

                                x_diff = (scaled_w - note["width"]) / 2
                                y_diff = (scaled_h - note["height"]) / 2
                                bar_glow = pygame.transform.smoothscale(
                                    self.assets.bars[note["channel"]][note["type"]][
                                        "glow"
                                    ],
                                    (scaled_w, scaled_h),
                                )
                                bar_glow.set_alpha(int(a * 255))
                                screen_note.blit(
                                    bar_glow,
                                    (
                                        note["x_start"] - x_diff,
                                        note["y"] - note["height"] / 2 - y_diff,
                                    ),
                                )

                            # Icons
                            for i, effect in enumerate(note["effects"]):
                                px = (
                                    note["x_end"]
                                    - (i + 1) * self.s.BAR_PASSED_COUNT_ICON_SIZE
                                )
                                py = note["y"] - (
                                    self.s.BAR_PASSED_COUNT_ICON_SIZE
                                    + self.s.BAR_PASSED_COUNT_ICON_MARGIN
                                )
                                screen_note.blit(self.assets.icons[effect], (px, py))

                # Range gauge
                if len(now_page_notes) > 0:
                    x1 = (
                        (
                            np.min([note["pitch"] for note in now_page_notes])
                            - self.min_pitch
                        )
                        / (self.pitch_range)
                        * self.s.RANGE_GAUGE_W
                    )
                    x2 = (
                        (
                            np.max([note["pitch"] for note in now_page_notes])
                            - self.min_pitch
                        )
                        / (self.pitch_range)
                        * self.s.RANGE_GAUGE_W
                    )
                    range_gauge = self.assets.range_gauge.subsurface(
                        pygame.Rect(x1, 0, x2 - x1, self.s.RANGE_GAUGE_H)
                    )
                    screen_note.blit(
                        range_gauge,
                        (self.s.RANGE_GAUGE_POS[0] + x1, self.s.RANGE_GAUGE_POS[1]),
                    )

                    screen_note.set_alpha(alpha)
                    screen_note_crop = screen_note.subsurface(pygame.Rect(*crop_bbox))
                    self.screen.blit(screen_note_crop, (crop_bbox[0], 0))

            if len(now_page_is) > 0:
                for i in range(max(min(now_page_is) - 1, 0), max(now_page_is) + 1):
                    notes = self.pages[i]["notes"]
                    for note in notes:
                        if (
                            self.bar_auto_play
                            and note["channel"] in self.s.BAR_AUTO_PLAY_CHANNELS
                        ):
                            passed_time = (
                                self.current_time - self.s.LAG_TIME - note["end"]
                            )
                            if passed_time >= 0:
                                # Notes counter
                                if (
                                    0
                                    <= passed_time
                                    < self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                                ):
                                    prog = (
                                        passed_time
                                        / self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                                    )
                                    pos0 = (note["x_end"], note["y"])
                                    if note["pitch"] == self.max_pitch:
                                        note_typ = "max"
                                    elif note["pitch"] == self.min_pitch:
                                        note_typ = "min"
                                    else:
                                        note_typ = "normal"
                                    pos1 = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                        note_typ
                                    ]["pos"]
                                    col = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                        note_typ
                                    ]["colors"]
                                    pos = tools.point_on_curve_ratio(
                                        pos0,
                                        pos1,
                                        prog,
                                        self.s.BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH,
                                        self.s.BAR_PASSED_COUNT_ANIMATION_ACCEL,
                                    )

                                    self.bar_count_particles.append(
                                        Particle(
                                            pos[0],
                                            pos[1],
                                            size_range=(5, 8),
                                            life_decay=0.02,
                                            colors=col,
                                            v=0.5,
                                        )
                                    )

                                    for effect in note["effects"]:
                                        pos1 = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                            effect
                                        ]["pos"]
                                        col = self.s.BAR_PASSED_COUNT_ANIMATION_DICT[
                                            effect
                                        ]["colors"]
                                        pos = tools.point_on_curve_ratio(
                                            pos0,
                                            pos1,
                                            prog,
                                            self.s.BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH,
                                            self.s.BAR_PASSED_COUNT_ANIMATION_ACCEL,
                                        )

                                        self.bar_count_particles.append(
                                            Particle(
                                                pos[0],
                                                pos[1],
                                                size_range=(5, 8),
                                                life_decay=0.02,
                                                colors=col,
                                                v=0.5,
                                            )
                                        )

    def draw_menubar(self):
        self.screen.blit(self.menu_overlay, (0, self.s.SCREEN_HEIGHT - self.s.MENU_H))

    def draw_info(self):
        help_y = self.s.SEEKBAR_TOP + 80
        auto = get_lang_text_app("bar_auto_play")
        mic = get_lang_text_app("mic")
        play_pause = get_lang_text_app("play_pause")
        space = get_lang_text_app("space")
        up_down = get_lang_text_app("up_down")
        vol = get_lang_text_app("vol")
        restart = get_lang_text_app("restart")
        toggle_fullscreen = get_lang_text_app("toggle_fullscreen")
        _quit = get_lang_text_app("quit")
        help_texts = [
            f"[A]{auto}: {'ON' if self.bar_auto_play else 'OFF'}  [M]{mic}: {'ON' if self.enable_mic_input else 'OFF'}",
            f"[{space}]{play_pause}  [{up_down}]{vol}:{self.music_volume} [R]{restart}  [F11]{toggle_fullscreen}  [ESC]{_quit}",
        ]
        for i, text in enumerate(help_texts):
            help_surface = self.small_font.render(text, True, (200, 200, 200))
            self.screen.blit(help_surface, (self.s.BAR_AREA_LEFT, help_y + i * 40))

    def _update_particle_list(self, particle_list, screen):
        new_list = []
        for p in particle_list:
            p.update()
            if p.life > 0:
                p.draw(screen)
                new_list.append(p)
        return new_list

    def update_particles(self):
        self.particles = self._update_particle_list(self.particles, self.screen)
        self.mic_input_particles = self._update_particle_list(
            self.mic_input_particles, self.screen
        )
        self.bar_count_particles = self._update_particle_list(
            self.bar_count_particles, self.screen
        )

    def draw_title(self):
        if self.title_image is not None:
            img_rect = self.title_image.get_rect(
                center=(self.s.SCREEN_WIDTH // 2, self.s.SCREEN_HEIGHT // 2)
            )
            self.screen.blit(self.title_image, img_rect)

        if self.splash_image is not None:
            img_rect = self.splash_image.get_rect(
                center=(self.s.SCREEN_WIDTH // 2, self.s.SCREEN_HEIGHT // 2)
            )
            self.screen.blit(self.splash_image, img_rect)

        if self.credit_text is not None:
            texts = self.credit_text.split("\n")
            pos = list(self.screen.get_rect().bottomright)
            pos[0] += self.s.SPLASH_TEXT_X_OFFSET
            pos[1] += self.s.SPLASH_TEXT_Y_OFFSET - (self.s.SPLASH_TEXT_LINE_HEIGHT * (len(texts) - 1))
            for text in texts:
                text_surf = tools.render_outlined_text(
                    text,
                    self.large_font,
                    text_color=(255, 255, 255),
                    outline_color=(0, 0, 0),
                    outline_width=8,
                )
                rect = text_surf.get_rect(bottomright=pos)
                self.screen.blit(text_surf, rect)
                pos[1] += self.s.SPLASH_TEXT_LINE_HEIGHT

    # ---------- Audio control ----------
    def play(self):
        self.playing = True
        self.start_time = time.time()
        if self.recorder is None:
            pygame.mixer.music.play()
        else:
            self.recorder.start(
                screen_size=(self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT),
                fps=self.s.SCREEN_FPS,
                audio_path=self.audio_path,
                audio_codec=self.s.AUDIO_CODEC,
                audio_bps=self.s.AUDIO_BPS,
                video_codec=self.s.VIDEO_CODEC,
                video_bps=self.s.VIDEO_BPS,
                crf=None,
            )

    def pause(self):
        pygame.mixer.music.pause()
        self.playing = False

    def resume(self):
        pygame.mixer.music.unpause()
        self.playing = True
        sc = self.time_scale if self.recorder is None else 1
        self.start_time = time.time() - self.current_time * (1 / sc)

    def restart(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.play()
        self.playing = True
        self.start_time = time.time()
        self.current_time = 0
        self.particles.clear()
        self.reset_mic_inputs()

    def seek_to(self, time_sec):
        pygame.mixer.music.play(start=time_sec)
        if not self.playing:
            pygame.mixer.music.pause()
        self.current_time = time_sec
        sc = self.time_scale if self.recorder is None else 1
        self.start_time = time.time() - self.current_time * (1 / sc)
        self.particles.clear()
        self.reset_mic_inputs()

    def handle_seekbar_click(self, mouse_x, mouse_y):
        seekbar_click_area = pygame.Rect(
            self.s.SEEKBAR_LEFT,
            self.s.SEEKBAR_TOP - 10,
            self.s.SEEKBAR_WIDTH,
            self.s.SEEKBAR_HEIGHT + 20,
        )
        if seekbar_click_area.collidepoint(mouse_x, mouse_y):
            relative_x = mouse_x - self.s.SEEKBAR_LEFT
            ratio = max(0, min(1, relative_x / self.s.SEEKBAR_WIDTH))
            self.seek_position = ratio * self.song_duration
            self.seek_to(self.seek_position)
            return True
        return False

    def add_volume(self, value=1):
        vol = np.clip(self.music_volume + value, 0, 100)
        self.music_volume = vol
        pygame.mixer.music.set_volume(self.music_volume / 100)

    def update(self):
        if self.playing:
            if self.recorder is None:
                current_real_time = time.time()
                self.current_time = current_real_time - self.start_time
                self.current_time *= self.time_scale
                if self.current_time >= self.song_duration:
                    self.current_time = self.song_duration
                    return False

            else:
                self.current_time = self.recorder.next_timestamp()
                if self.current_time >= self.song_duration:
                    self.current_time = self.song_duration
                    if self.recorder.is_recording:
                        self.recorder.finish()
                    return True

        return False

    # ---------- Drawing flow ----------
    def draw_ready(self):
        if self.recorder is None:
            mes = get_lang_text_app('press space to play')
        else:
            mes = get_lang_text_app('press space to start recording')
        self._flash_message(mes)

    def draw_background(self):
        self.screen.blit(self.assets.project_back, (0, 0))
        tools.blit_with_alpha(
            self.screen, self.assets.range_gauge, self.s.RANGE_GAUGE_POS, alpha=0.2
        )

    def draw_front(self):
        self.screen.blit(self.assets.project_front, (0, 0))

    def draw_lyrics(self):
        for i in range(len(self.lyrics)):
            if "fade_in" in self.lyrics[i].keys():
                fade_start = self.lyrics[i]["fade_in"]["start"]
                fade_end = self.lyrics[i]["fade_in"]["end"]
                if fade_start <= self.current_time < fade_end:
                    fadein_alpha = (self.current_time - fade_start) / (
                        fade_end - fade_start
                    )
                else:
                    fadein_alpha = None
            else:
                fadein_alpha = None

            if "fade_out" in self.lyrics[i].keys():
                fade_start = self.lyrics[i]["fade_out"]["start"]
                fade_end = self.lyrics[i]["fade_out"]["end"]
                if fade_start <= self.current_time < fade_end:
                    fadeout_alpha = 1 - (self.current_time - fade_start) / (
                        fade_end - fade_start
                    )
                else:
                    fadeout_alpha = None
            else:
                fadeout_alpha = None

            for typ in self.lyrics_types:
                start = self.lyrics[i][typ]["start"]
                end = self.lyrics[i][typ]["end"]
                x = self.lyrics[i][typ]["x"]
                y = self.lyrics[i][typ]["y"]
                if start <= self.current_time < end:
                    for x_wipes in self.lyrics[i][typ]["x_wipes"]:
                        _start, _end = x_wipes[0], x_wipes[1]
                        if _start <= self.current_time < _end:
                            if _start == _end:
                                _clip_x = 0
                            else:
                                prog = (self.current_time - _start) / (_end - _start)
                                _clip_x = (x_wipes[3] - x_wipes[2]) * prog + x_wipes[2]

                            _clip_x = np.floor(_clip_x)
                            crop_rect = pygame.Rect(
                                _clip_x,
                                self.lyrics[i][typ]["clip_up"],
                                self.lyrics[i][typ]["img"].get_width() - _clip_x,
                                self.lyrics[i][typ]["img"].get_height()
                                - self.lyrics[i][typ]["clip_up"]
                                - self.lyrics[i][typ]["clip_bottom"],
                            )
                            if fadein_alpha is None and fadeout_alpha is None:
                                self.screen.blit(
                                    self.lyrics[i][typ]["img"],
                                    (x + _clip_x, y + self.lyrics[i][typ]["clip_up"]),
                                    crop_rect,
                                )

                            elif fadein_alpha is not None:
                                if "front" in typ:
                                    tools.blit_with_alpha(
                                        self.screen,
                                        self.lyrics[i][typ]["img"],
                                        (
                                            x + _clip_x,
                                            y + self.lyrics[i][typ]["clip_up"],
                                        ),
                                        crop_rect,
                                        fadein_alpha,
                                    )

                            elif fadeout_alpha is not None:
                                if "background" in typ:
                                    tools.blit_with_alpha(
                                        self.screen,
                                        self.lyrics[i][typ]["img"],
                                        (
                                            x + _clip_x,
                                            y + self.lyrics[i][typ]["clip_up"],
                                        ),
                                        crop_rect,
                                        fadeout_alpha,
                                    )

                            break

    def draw_bar_count(self):
        if self.enable_mic_input:
            passed_notes = [
                note
                for note in self.mic_notes
                if note["end"] + self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                <= self.current_time
                and note["type"] == "match_all"
            ]
        else:
            passed_notes = [
                note
                for note in self.notes
                if note["end"]
                + self.s.LAG_TIME
                + self.s.BAR_PASSED_COUNT_ANIMATION_TIME
                <= self.current_time
                and note["channel"] in self.s.BAR_AUTO_PLAY_CHANNELS
                and self.bar_auto_play
            ]

        n_passed_notes_max = sum(
            [note["pitch"] == self.max_pitch for note in passed_notes]
        )
        n_passed_notes_min = sum(
            [note["pitch"] == self.min_pitch for note in passed_notes]
        )
        n_passed_notes_normal = (
            len(passed_notes) - n_passed_notes_max - n_passed_notes_min
        )

        count_normal = self.bar_count_font.render(
            f"{n_passed_notes_normal}", True, self.s.BAR_COUNT_DICT["normal"]["color"]
        )
        x, y = self.s.BAR_COUNT_DICT["normal"]["pos"]
        rect = count_normal.get_rect(right=x, top=y)
        self.screen.blit(count_normal, rect)

        count_max = self.bar_count_font.render(
            f"{n_passed_notes_max}", True, self.s.BAR_COUNT_DICT["max"]["color"]
        )
        x, y = self.s.BAR_COUNT_DICT["max"]["pos"]
        rect = count_max.get_rect(right=x, top=y)
        self.screen.blit(count_max, rect)

        count_min = self.bar_count_font.render(
            f"{n_passed_notes_min}", True, self.s.BAR_COUNT_DICT["min"]["color"]
        )
        x, y = self.s.BAR_COUNT_DICT["min"]["pos"]
        rect = count_min.get_rect(right=x, top=y)
        self.screen.blit(count_min, rect)

        for effect in ["up", "down", "long"]:
            n = sum([effect in note["effects"] for note in passed_notes])
            count = self.bar_count_font.render(
                f"{n}", True, self.s.BAR_COUNT_DICT[effect]["color"]
            )
            x, y = self.s.BAR_COUNT_DICT[effect]["pos"]
            rect = count.get_rect(right=x, top=y)
            self.screen.blit(count, rect)

    def draw_seekbar(self):
        if self.enable_mic_input:
            scores = [s for s in self.page_scores if s["end_time"] < self.current_time and s["number_of_notes"] > 0]
            score = (
                np.array([s["weighted_score"] for s in scores]).mean()
                if len(scores) > 0
                else 0.0
            )
            page_score = scores[-1]["weighted_score"] if len(scores) > 0 else 0.0

            now_scores = [
                s
                for s in self.page_scores
                if s["start_time"] <= self.current_time
                and self.current_time < s["end_time"]
            ]
            now_score = now_scores[-1]["weighted_score"] if len(now_scores) > 0 else 0.0

            score_str = (
                f" {get_lang_text_app('total')}: {score:3.3f}, {get_lang_text_app('page')}: {page_score:3.3f}, {get_lang_text_app('now')}: {now_score:3.3f}"
            )
        else:
            score_str = ""

        pygame.draw.rect(
            self.screen,
            (80, 80, 80),
            (
                self.s.SEEKBAR_LEFT,
                self.s.SEEKBAR_TOP,
                self.s.SEEKBAR_WIDTH,
                self.s.SEEKBAR_HEIGHT,
            ),
            border_radius=5,
        )
        if self.song_duration > 0:
            progress = min(self.current_time / self.song_duration, 1.0)
            progress_width = int(self.s.SEEKBAR_WIDTH * progress)
            pygame.draw.rect(
                self.screen,
                (255, 100, 150),
                (
                    self.s.SEEKBAR_LEFT,
                    self.s.SEEKBAR_TOP,
                    progress_width,
                    self.s.SEEKBAR_HEIGHT,
                ),
                border_radius=5,
            )

            handle_x = self.s.SEEKBAR_LEFT + int(self.s.SEEKBAR_WIDTH * progress)
            handle_y = self.s.SEEKBAR_TOP + self.s.SEEKBAR_HEIGHT // 2
            pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, handle_y), 12)
            pygame.draw.circle(self.screen, (255, 100, 150), (handle_x, handle_y), 8)

            current_min = int(self.current_time // 60)
            current_sec = int(self.current_time % 60)
            total_min = int(self.song_duration // 60)
            total_sec = int(self.song_duration % 60)
            time_text = self.large_font.render(
                f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d} {score_str}",
                True,
                self.s.TEXT_COLOR,
            )
            self.screen.blit(
                time_text,
                (self.s.SEEKBAR_LEFT, self.s.SEEKBAR_TOP + self.s.SEEKBAR_HEIGHT + 5),
            )

    def draw(self):
        # Background video
        if self.video_start_time is None or self.recorder is None:
            cur = None
        else:
            cur = self.video_start_time + self.current_time - self.current_time_diff

        frame, video_start_time = (
            self.video_player.get_frame(current_time=cur)
            if self.video_player is not None
            else None
        )

        if video_start_time != self.video_start_time:
            self.current_time_diff = self.current_time
            self.video_start_time = video_start_time

        if frame:
            dark_surface = pygame.Surface((self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT))
            dark_surface.blit(frame, (0, 0))
            dark_surface.set_alpha(self.s.VIDEO_ALPHA)
            self.screen.fill(self.s.BG_COLOR)
            self.screen.blit(dark_surface, (0, 0))
        else:
            self.screen.fill(self.s.BG_COLOR)

        try:
            if self.current_time <= self.s.DISPLAY_TITLE_DURATION:
                self.draw_title()
            else:
                self.draw_background()
                self.draw_background_lines()
                self.draw_notes()
                self.draw_bar_count()
                self.draw_front()
                self.draw_now_bar()
                self.update_particles()
                self.draw_lyrics()

        except Exception as e:
            print(e)
            import traceback

            traceback.print_exc()

        if self.menu_visible:
            # UI
            self.draw_menubar()
            self.draw_seekbar()
            self.draw_info()

        self.update_screen()

    def update_screen(self):
        scale_x = self.window_w / self.s.SCREEN_WIDTH
        scale_y = self.window_h / self.s.SCREEN_HEIGHT
        self.screen_scale = min(scale_x, scale_y)

        scaled_w = int(self.s.SCREEN_WIDTH * self.screen_scale)
        scaled_h = int(self.s.SCREEN_HEIGHT * self.screen_scale)
        self.screen_offset_x = (self.window_w - scaled_w) // 2
        self.screen_offset_y = (self.window_h - scaled_h) // 2

        if (
            self.window_w == self.s.SCREEN_WIDTH
            and self.window_h == self.s.SCREEN_HEIGHT
        ):
            scaled_surface = self.screen
        else:
            scaled_surface = pygame.transform.smoothscale(
                self.screen, (scaled_w, scaled_h)
            )
        self.window.fill(self.s.WINDOW_BACKGROUND_COLOR)
        self.window.blit(scaled_surface, (self.screen_offset_x, self.screen_offset_y))
        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()

        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Finishing
                    self.video_player.close()
                    if self.enable_mic_input:
                        self.detector.stop()
                    pygame.quit()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        waiting = False

            try:
                self.draw_ready()
            except:
                return

        running = True
        play_init = False

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_SPACE:
                        if self.playing:
                            self.pause()
                        else:
                            if self.current_time == 0:
                                self.play()
                            else:
                                self.resume()
                    elif event.key == pygame.K_r:
                        self.restart()

                    elif event.key == pygame.K_a:
                        self.bar_auto_play = not self.bar_auto_play

                    elif event.key == pygame.K_m:
                        self.enable_mic_input = not self.enable_mic_input
                        if self.enable_mic_input:
                            self.bar_auto_play = False
                            self.detector = RealtimeFFTPitchDetector(settings_json_path=self.setting_json_path)
                            self.detector.start()

                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                        self.window_w, self.window_h = pygame.display.get_window_size()

                    elif event.key == pygame.K_DOWN:
                        self.add_volume(-1)

                    elif event.key == pygame.K_UP:
                        self.add_volume(1)

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_x, mouse_y = event.pos
                        mouse_x = (mouse_x - self.screen_offset_x) / self.screen_scale
                        mouse_y = (mouse_y - self.screen_offset_y) / self.screen_scale
                        self.handle_seekbar_click(mouse_x, mouse_y)

                        if self.menu_visible:
                            if self.menu_rect.collidepoint(mouse_x, mouse_y):
                                pass
                            else:
                                self.menu_visible = False
                        else:
                            self.menu_visible = True

                elif event.type == pygame.VIDEORESIZE:
                    pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.window_w, self.window_h = pygame.display.get_window_size()

            finished = self.update()
            self.draw()
            if self.enable_mic_input:
                self.compute_note_scores()

            if not play_init:
                play_init = True
                self.play()

            if self.recorder is None:
                clock.tick_busy_loop(self.s.SCREEN_FPS)
            else:
                if not self.recorder.push_frame(self.screen):
                    break

            if finished:
                break

        # Finishing
        if self.recorder is not None and self.recorder.is_recording:
            self.recorder.finish()

        self.video_player.close()
        if self.enable_mic_input:
            self.detector.stop()
        pygame.quit()
        return
