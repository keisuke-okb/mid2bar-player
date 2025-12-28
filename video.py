import pygame
import time
import random
import cv2
import numpy as np

import settings_loader


class VideoPlayer:
    def __init__(self, video_paths, fixed_fps=0, shuffle=False, settings_json_path="settings.json"):
        self.s = settings_loader.load(settings_json_path)
        self.video_paths = list(video_paths or [])
        self.current_video_index = 0
        self.cap = None
        self.shuffle = shuffle
        self.fps = 30
        self.fixed_fps = fixed_fps if fixed_fps > 0 else None
        self.total_frames = 0
        self.frame = None
        self.start_time = 0
        self.frame_count = 0

        if self.video_paths:
            if self.shuffle:
                random.shuffle(self.video_paths)
            self.load_video(0)

    def load_video(self, index):
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_paths[index])
        self.fps = (
            self.cap.get(cv2.CAP_PROP_FPS) if self.fixed_fps is None else self.fixed_fps
        )
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.current_video_index = index
        self.frame_count = 0
        self.start_time = None

        ret, frame_data = self.cap.read()
        if ret:
            self.frame = self._frame_to_surface(frame_data)

    def _frame_to_surface(self, frame_data):
        # OpenCV BGR -> RGB, 90度回転＋上下反転（元コードのまま）
        frame_data = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
        frame_data = np.rot90(frame_data)
        frame_data = np.flipud(frame_data)
        surf = pygame.surfarray.make_surface(frame_data)
        return pygame.transform.scale(surf, (self.s.SCREEN_WIDTH, self.s.SCREEN_HEIGHT))

    def get_frame(self, current_time=None):
        if not self.cap or not self.cap.isOpened():
            return None, None

        if self.start_time is None:
            self.start_time = time.time()

        elapsed = (current_time if current_time is not None else time.time()) - self.start_time
        target_frame = int(elapsed * self.fps)

        if self.total_frames <= target_frame:
            # 次の動画へ
            self.current_video_index = (self.current_video_index + 1) % len(
                self.video_paths
            )
            self.load_video(self.current_video_index)
            return self.frame, self.start_time

        if self.total_frames > 0:
            target_frame %= self.total_frames

        frames_to_read = target_frame - self.frame_count

        if frames_to_read <= 0:
            return self.frame, self.start_time

        frame_data = None
        for _ in range(frames_to_read):
            ret, temp = self.cap.read()
            if not ret:
                # 次の動画へ
                self.current_video_index = (self.current_video_index + 1) % len(
                    self.video_paths
                )
                self.load_video(self.current_video_index)
                return self.frame, self.start_time

            if ret:
                frame_data = temp

        if frame_data is not None:
            self.frame = self._frame_to_surface(frame_data)
            self.frame_count = target_frame

        return self.frame, self.start_time

    def close(self):
        if self.cap:
            self.cap.release()
            self.cap = None
