import subprocess
import math
import pygame
import os
import sys
from datetime import datetime
from tkinter import messagebox


class PipeFrameRecorder:
    def __init__(self):
        self.proc = None
        self.fps = None
        self.width = None
        self.height = None
        self.audio_path = None
        self.frame_index = 0
        self.total_frames = None
        self.is_recording = False

    def _probe_audio_duration(self, audio_path):
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ]
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                check=True,
            )
            return float(res.stdout.strip())
        except Exception:
            return None

    def start(
        self,
        screen_size,
        fps,
        out_path=None,
        audio_path=None,
        duration=None,
        audio_codec="aac",
        audio_bps="320k",
        video_codec="h264_nvenc",
        video_bps="10M",
        crf=None,
    ):
        self.width, self.height = screen_size
        self.fps = int(fps)
        self.audio_path = audio_path
        self.frame_index = 0

        if duration is None:
            if audio_path is None:
                raise ValueError("duration or audio_path is required")
            duration = self._probe_audio_duration(audio_path)
            if duration is None:
                raise RuntimeError("cannot detect audio duration")

        self.total_frames = int(math.ceil(duration * self.fps))

        # ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",  # stdin
        ]

        if audio_path:
            cmd += ["-i", audio_path]

        quality = ["-crf", str(crf)] if crf is not None else ["-b:v", video_bps]
        cmd += [
            "-c:v",
            video_codec,  # "libx264", "h264_nvenc"...
            *quality,
            "-pix_fmt",
            "yuv420p",
        ]

        if audio_path:
            cmd += [
                "-c:a",
                audio_codec,
                "-b:a",
                audio_bps,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-shortest",
            ]

        if out_path is None:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = f"./recordings/{now_str}.mp4"

        self.out_path = out_path
        cmd += [out_path]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        # launch ffmpeg
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr
        )

        self.is_recording = True
        return {
            "fps": self.fps,
            "duration": duration,
            "total_frames": self.total_frames,
        }

    def next_timestamp(self):
        if not self.is_recording:
            self.finish()
        return self.frame_index / self.fps

    def push_frame(self, surface):
        if not self.is_recording:
            return False

        # Surface → RGB bytes
        frame = pygame.image.tostring(surface, "RGB")
        self.proc.stdin.write(frame)

        self.frame_index += 1
        if self.frame_index >= self.total_frames:
            self.is_recording = False
        return True

    def finish(self):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.wait()
            finally:
                self.proc = None
                self.is_recording = False
                messagebox.showinfo("info", f"Recording finished:\n{self.out_path}")
