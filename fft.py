import math
import queue
import threading
import time
import numpy as np
import sounddevice as sd

import settings_loader


# --------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------


def freq_to_midi(freq):
    if freq is None or freq <= 0:
        return None
    return 69.0 + 12.0 * math.log2(freq / 440.0)


def midi_to_note_name(settings, midi_float):
    if midi_float is None:
        return None
    midi = int(round(midi_float))
    name = settings.NOTE_NAMES[midi % 12]
    octave = (midi // 12) - 1
    return f"{name}{octave}"


def parabolic_interpolation(mag, peak_index):
    if peak_index <= 0 or peak_index >= len(mag) - 1:
        return float(peak_index), mag[peak_index]
    alpha = mag[peak_index - 1]
    beta = mag[peak_index]
    gamma = mag[peak_index + 1]
    denom = alpha - 2 * beta + gamma
    if denom == 0:
        return float(peak_index), beta
    p = 0.5 * (alpha - gamma) / denom
    refined_index = peak_index + p
    refined_mag = beta - 0.25 * (alpha - gamma) * p
    return refined_index, refined_mag


# --------------------------------------------------------------
# Main class
# --------------------------------------------------------------


class RealtimeFFTPitchDetector:
    def __init__(
        self,
        settings_json_path,
    ):
        self.s = settings_loader.load(settings_json_path)
        self.sample_rate = self.s.DEFAULT_SAMPLE_RATE
        self.block_size = self.s.DEFAULT_BLOCK_SIZE
        self.channels = self.s.DEFAULT_CHANNELS
        self.rms_threshold = self.s.RMS_THRESHOLD

        self.window = np.hanning(self.block_size)
        self.audio_queue = queue.Queue(maxsize=8)
        self.stop_event = threading.Event()

        self.stream = None

        # latest processed info
        self.latest_freq = None
        self.latest_mag = None
        self.latest_rms = 0
        self.latest_time = 0

    # ---------------------- Audio callback ----------------------
    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            pass
        try:
            data = indata[:, 0].copy()
            self.audio_queue.put_nowait(data)
        except queue.Full:
            pass

    # ---------------------- Processing --------------------------
    def _process_block(self, block):
        if len(block) < self.block_size:
            block = np.pad(block, (0, self.block_size - len(block)))

        windowed = block * self.window
        fft = np.fft.rfft(windowed)
        mag = np.abs(fft)
        mag[0] = 0.0

        rms = float(np.sqrt(np.mean(block * block)))
        if rms < self.rms_threshold:
            return None, None, rms

        peak_idx = int(np.argmax(mag))
        if peak_idx <= 0:
            return None, None, rms

        refined_idx, refined_mag = parabolic_interpolation(mag, peak_idx)
        freq = refined_idx * (self.sample_rate / self.block_size)
        return freq, refined_mag, rms

    # ---------------------- Public API --------------------------
    def start(self):
        if self.stream is not None:
            return
        try:
            self.stream = sd.InputStream(
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                callback=self._audio_callback,
            )
            self.stream.start()
        except Exception as e:
            print("Failed to start audio stream:", e)
            self.stream = None

        # start background thread to process
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def _processing_loop(self):
        while not self.stop_event.is_set():
            try:
                block = self.audio_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            freq, mag, rms = self._process_block(block)
            self.latest_freq = freq
            self.latest_mag = mag
            self.latest_rms = rms
            self.latest_time = time.time()

    def get_latest(self):
        freq = self.latest_freq
        midi = freq_to_midi(freq) + self.s.MIC_INPUT_OFFSET if freq else None
        note_name = midi_to_note_name(self.s, midi) if midi else None

        return {
            "freq": freq,
            "midi": midi,
            "note_name": note_name,
            "octave": (int(round(midi)) // 12 - 1) if midi else None,
            "rms": self.latest_rms,
            "peak_mag": self.latest_mag,
            "timestamp": self.latest_time,
        }
