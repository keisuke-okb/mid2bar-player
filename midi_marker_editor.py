import os
import math
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import customtkinter as ctk
import mido
import pygame

# -------------------------
# Tempo map utility
# -------------------------
class TempoMap:
    """Map ticks <-> seconds based on tempo (set_tempo) events."""

    def __init__(self, mid: mido.MidiFile):
        self.ticks_per_beat = mid.ticks_per_beat
        merged = mido.merge_tracks(mid.tracks)
        self.segments = []  # {'start_tick','start_time','tempo'}
        cur_tick = 0
        cur_time = 0.0
        tempo = 500000  # default 120 BPM
        self.segments.append({"start_tick": 0, "start_time": 0.0, "tempo": tempo})
        for msg in merged:
            dt = msg.time
            if dt:
                dt_seconds = dt * (tempo / 1_000_000.0) / self.ticks_per_beat
                cur_time += dt_seconds
                cur_tick += dt
            if msg.type == "set_tempo":
                tempo = msg.tempo
                self.segments.append(
                    {"start_tick": cur_tick, "start_time": cur_time, "tempo": tempo}
                )

    def ticks_to_seconds(self, tick: int) -> float:
        seg = None
        for s in reversed(self.segments):
            if tick >= s["start_tick"]:
                seg = s
                break
        if seg is None:
            seg = self.segments[0]
        dt_ticks = tick - seg["start_tick"]
        dt_seconds = dt_ticks * (seg["tempo"] / 1_000_000.0) / self.ticks_per_beat
        return seg["start_time"] + dt_seconds

    def seconds_to_ticks(self, seconds: float) -> int:
        seg = None
        for s in reversed(self.segments):
            if seconds >= s["start_time"]:
                seg = s
                break
        if seg is None:
            seg = self.segments[0]
        dt_seconds = seconds - seg["start_time"]
        dt_ticks = dt_seconds * self.ticks_per_beat * 1_000_000.0 / seg["tempo"]
        return int(round(seg["start_tick"] + dt_ticks))


# -------------------------
# Time signature (measure) map
# -------------------------
class TimeSigMap:
    """Collect time_signature meta messages and allow computing measure start ticks/seconds."""

    def __init__(self, mid: mido.MidiFile, tempo_map: TempoMap):
        self.ticks_per_beat = mid.ticks_per_beat
        self.tempo_map = tempo_map
        merged = mido.merge_tracks(mid.tracks)
        self.segments = []  # {'start_tick','start_time','numerator','denominator'}
        cur_tick = 0
        cur_time = 0.0
        # default 4/4
        cur_num, cur_den = 4, 4
        self.segments.append(
            {
                "start_tick": 0,
                "start_time": 0.0,
                "numerator": cur_num,
                "denominator": cur_den,
            }
        )
        tempo = 500000
        for msg in merged:
            dt = msg.time
            if dt:
                # advance time using current tempo
                dt_seconds = dt * (tempo / 1_000_000.0) / self.ticks_per_beat
                cur_time += dt_seconds
                cur_tick += dt
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type == "time_signature":
                cur_num = msg.numerator
                cur_den = msg.denominator
                self.segments.append(
                    {
                        "start_tick": cur_tick,
                        "start_time": cur_time,
                        "numerator": cur_num,
                        "denominator": cur_den,
                    }
                )

    def measure_ticks_length(self, numerator: int, denominator: int) -> int:
        # measure ticks = ticks_per_beat * numerator * (4/denominator)
        return int(round(self.ticks_per_beat * numerator * (4.0 / denominator)))

    def get_measure_start_seconds(self, length_seconds: float) -> list:
        """Return list of measure start times in seconds up to length_seconds."""
        results = []
        # Determine overall end tick using tempo_map
        end_tick = self.tempo_map.seconds_to_ticks(length_seconds + 1.0)
        # Walk across time signature segments and emit measure starts
        for i, seg in enumerate(self.segments):
            seg_start_tick = seg["start_tick"]
            seg_end_tick = (
                self.segments[i + 1]["start_tick"]
                if i + 1 < len(self.segments)
                else end_tick + 1
            )
            measure_ticks = self.measure_ticks_length(
                seg["numerator"], seg["denominator"]
            )
            if measure_ticks <= 0:
                continue
            tick = seg_start_tick
            while tick <= seg_end_tick:
                sec = self.tempo_map.ticks_to_seconds(tick)
                if sec > length_seconds:
                    break
                results.append(sec)
                tick += measure_ticks
        # deduplicate & sort
        results = sorted(list(dict.fromkeys(results)))
        return results


# -------------------------
# Main application
# -------------------------
class MidiMarkerEditor(ctk.CTk):
    CANVAS_HEIGHT = 520
    ROW_HEIGHT = 8
    PITCH_MIN = 21
    PITCH_MAX = 108

    # Channel colors (16 channels)
    CHANNEL_COLORS = [
        "#3aa6ff",
        "#ff6b6b",
        "#4ecdc4",
        "#ffe66d",
        "#a8e6cf",
        "#ff8b94",
        "#c7ceea",
        "#ffd3b6",
        "#dcedc1",
        "#ffaaa5",
        "#b4a7d6",
        "#ffc8a2",
        "#d5aaff",
        "#85e3ff",
        "#ffd97d",
        "#aaffc3",
    ]

    def __init__(self):
        super().__init__()
        self.title("MIDI Marker Editor")
        self.geometry("1000x500")
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("dark-blue")

        # state
        self.mid = None
        self.tempo_map = None
        self.timesig_map = None
        self.note_events = []
        self.length_seconds = 60.0

        # markers: list of dicts {'time': float, 'label': str}
        self.markers = []

        # audio
        pygame.mixer.init()
        self.audio_path = None

        # playback
        self.is_playing = False
        self.is_paused = False
        self.play_start_time = 0.0
        self.play_offset = 0.0
        self.update_job = None

        # drawing / zoom
        self.px_per_second = 150
        self.total_width = 2000
        self.total_height = 400

        # snap mode
        self.snap_mode = "Free"  # options: Free, 1/4, 1/8, 1/16, 1/32

        # mouse position for hover line
        self.mouse_time = 0.0

        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        self.draw_empty()

    # -------------------------
    # UI: menu / toolbar / layout
    # -------------------------
    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open MIDI...", command=self.load_midi)
        filemenu.add_command(
            label="Save MIDI with markers...", command=self.save_midi_with_markers
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Set reference audio...", command=self.set_reference_audio
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Export markers to JSON...", command=self.export_markers_json
        )
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.config(menu=menubar)

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, height=44)
        toolbar.pack(fill="x", padx=8, pady=6)

        self.play_btn = ctk.CTkButton(
            toolbar, text="▶ Play", width=84, command=self.play
        )
        self.play_btn.pack(side="left", padx=6)
        self.pause_btn = ctk.CTkButton(
            toolbar, text="⏸ Pause", width=84, command=self.pause
        )
        self.pause_btn.pack(side="left", padx=6)
        self.stop_btn = ctk.CTkButton(
            toolbar, text="■ Stop", width=84, command=self.stop
        )
        self.stop_btn.pack(side="left", padx=6)

        ctk.CTkButton(
            toolbar, text="＋ Add Marker", width=120, command=self.add_marker_dialog
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            toolbar,
            text="－ Delete Nearest",
            width=140,
            command=self.delete_nearest_marker,
        ).pack(side="left", padx=8)

        # Snap selector
        snap_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        snap_frame.pack(side="left", padx=8)
        ctk.CTkLabel(snap_frame, text="Cursor Snap:").pack(side="left", padx=(0, 6))
        self.snap_menu = ctk.CTkOptionMenu(
            snap_frame,
            values=["Free", "1/4", "1/8", "1/16", "1/32"],
            command=self.on_snap_change,
        )
        self.snap_menu.set(self.snap_mode)
        self.snap_menu.pack(side="left")

        # Zoom slider
        zoom_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        zoom_frame.pack(side="right", padx=6)
        ctk.CTkLabel(zoom_frame, text="Time zoom").pack(side="left", padx=(0, 6))
        self.zoom_slider = ctk.CTkSlider(
            zoom_frame,
            from_=50,
            to=400,
            number_of_steps=350,
            width=180,
            command=self.on_zoom_change,
        )
        self.zoom_slider.set(self.px_per_second)
        self.zoom_slider.pack(side="left")

        # time label
        self.time_label = ctk.CTkLabel(toolbar, text="00:00 / 00:00")
        self.time_label.pack(side="right", padx=10)

    def _build_main_area(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # left: canvas + scrollbars
        left_frame = tk.Frame(main)
        left_frame.pack(side="left", fill="both", expand=True)

        self.h_scroll = tk.Scrollbar(left_frame, orient="horizontal")
        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll = tk.Scrollbar(left_frame, orient="vertical")
        self.v_scroll.pack(side="right", fill="y")

        self.canvas = tk.Canvas(
            left_frame,
            bg="#0b0b0b",
            height=self.CANVAS_HEIGHT,
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
        )
        self.canvas.pack(fill="both", expand=True)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-1>", self.on_double_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows / macOS
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux (scroll up)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux (scroll down)

        # right: side panel for markers
        side = ctk.CTkFrame(main, width=320)
        side.pack(side="right", fill="y", padx=(8, 0))

        ctk.CTkLabel(
            side, text="Markers", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(8, 4))

        # Treeview for markers
        self.marker_tree = ttk.Treeview(
            side,
            columns=("time", "label"),
            show="headings",
            selectmode="browse",
            height=20,
        )
        self.marker_tree.heading("time", text="Time")
        self.marker_tree.heading("label", text="Label")
        self.marker_tree.column("time", width=100, anchor="center")
        self.marker_tree.column("label", width=200, anchor="w")
        self.marker_tree.pack(fill="y", padx=8, pady=(0, 8))
        self.marker_tree.bind("<Double-1>", self.on_marker_tree_double)

        # side buttons
        btn_frame = ctk.CTkFrame(side, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(6, 0), padx=8)
        ctk.CTkButton(
            btn_frame, text="Jump to", width=90, command=self.jump_to_selected_marker
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Edit", width=90, command=self.edit_selected_marker
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Delete", width=90, command=self.delete_selected_marker
        ).pack(side="left", padx=4)

        # tempo legend
        ctk.CTkLabel(side, text="Tempo Map", font=ctk.CTkFont(size=14)).pack(
            pady=(12, 6)
        )
        self.tempo_listbox = tk.Listbox(side, height=6)
        self.tempo_listbox.pack(fill="x", padx=8, pady=(0, 8))

    def _build_statusbar(self):
        status = ctk.CTkFrame(self, height=24)
        status.pack(fill="x", side="bottom", padx=8, pady=(0, 8))
        self.status_label = ctk.CTkLabel(status, text="No file loaded")
        self.status_label.pack(side="left", padx=6)

    def on_mouse_wheel(self, event):
        """
        Mouse wheel horizontal scroll for piano roll.
        Wheel up   -> scroll left (earlier time)
        Wheel down -> scroll right (later time)
        """
        # --- scroll direction ---
        if hasattr(event, "delta") and event.delta != 0:
            # Windows / macOS
            steps = -1 if event.delta > 0 else 1
        else:
            # Linux (Button-4 / Button-5)
            if event.num == 4:
                steps = -1
            elif event.num == 5:
                steps = 1
            else:
                return "break"

        # --- horizontal scroll ---
        self.canvas.xview_scroll(steps, "units")

        # 再生ヘッド・ホバー線を再描画（ズレ防止）
        if self.mid:
            self._draw_hover_line()
            self.draw_playhead(self._current_play_time())

        return "break"

    # -------------------------
    # MIDI load / save
    # -------------------------
    def load_midi(self):
        path = filedialog.askopenfilename(
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            mid = mido.MidiFile(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open MIDI: {e}")
            return

        self.mid = mid
        self.tempo_map = TempoMap(mid)
        self.timesig_map = TimeSigMap(mid, self.tempo_map)

        # build note events (merge tracks, compute absolute ticks -> seconds, track channel)
        merged = mido.merge_tracks(mid.tracks)
        abs_tick = 0
        ongoing = {}  # key: (note, channel)
        events = []
        self.markers = []
        for msg in merged:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                key = (msg.note, msg.channel)
                ongoing.setdefault(key, []).append(abs_tick)
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                key = (msg.note, msg.channel)
                if key in ongoing and ongoing[key]:
                    start_tick = ongoing[key].pop(0)
                    start_sec = self.tempo_map.ticks_to_seconds(start_tick)
                    end_sec = self.tempo_map.ticks_to_seconds(abs_tick)
                    events.append(
                        {
                            "start_sec": start_sec,
                            "end_sec": end_sec,
                            "note": msg.note,
                            "channel": msg.channel,
                        }
                    )
            elif msg.type == "marker":
                sec = self.tempo_map.ticks_to_seconds(abs_tick)
                self.markers.append({"time": sec, "label": msg.text})

        self.note_events = events

        # Calculate length_seconds considering both note events and markers
        max_time = 0.0
        if events:
            max_time = max(e["end_sec"] for e in events)
        if self.markers:
            max_marker_time = max(m["time"] for m in self.markers)
            max_time = max(max_time, max_marker_time)

        if max_time > 0:
            self.length_seconds = max_time + 10.0
        else:
            total_ticks = sum(m.time for m in merged)
            self.length_seconds = self.tempo_map.ticks_to_seconds(total_ticks)

        self.audio_path = None
        self.status_label.configure(text=os.path.basename(path))
        self._populate_tempo_panel()
        self._refresh_marker_list()
        self.draw_pianoroll()
        self._update_time_label(0.0)
        self.title(f"MIDI Marker Editor: {os.path.basename(path)}")

    def save_midi_with_markers(self):
        if not self.mid:
            messagebox.showinfo("No MIDI", "Load a MIDI file first.")
            return
        if not self.markers:
            messagebox.showinfo("No markers", "No markers to save.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".mid", filetypes=[("MIDI files", "*.mid")]
        )
        if not save_path:
            return
        new_mid = mido.MidiFile()
        new_mid.ticks_per_beat = self.mid.ticks_per_beat
        for track in self.mid.tracks:
            new_mid.tracks.append(track.copy())
        marker_track = mido.MidiTrack()
        ticks = [
            self.tempo_map.seconds_to_ticks(m["time"])
            for m in sorted(self.markers, key=lambda x: x["time"])
        ]
        prev = 0
        for idx, t in enumerate(ticks):
            delta = t - prev
            label = sorted(self.markers, key=lambda x: x["time"])[idx]["label"]
            msg = mido.MetaMessage("marker", text=label or "Marker", time=delta)
            marker_track.append(msg)
            prev = t
        marker_track.append(mido.MetaMessage("end_of_track", time=0))
        new_mid.tracks.append(marker_track)
        try:
            new_mid.save(save_path)
            messagebox.showinfo("Saved", f"Saved MIDI with markers to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    # -------------------------
    # Audio
    # -------------------------
    def set_reference_audio(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.ogg *.flac"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        try:
            pygame.mixer.music.load(path)
            self.audio_path = path
            self.status_label.configure(text=f"Audio: {os.path.basename(path)}")
            messagebox.showinfo(
                "Reference audio set",
                f"Reference audio set to:\n{path}\nIt will be played on Play.",
            )
        except Exception as e:
            messagebox.showerror("Audio load failed", str(e))
            self.audio_path = None

    # -------------------------
    # Playback control
    # -------------------------
    def play(self):
        if not self.mid:
            messagebox.showinfo("No MIDI", "Load a MIDI file first.")
            return
        if self.is_playing and not self.is_paused:
            return
        if self.is_paused:
            self.play_start_time = time.time()
            self.is_paused = False
            self.is_playing = True
            if self.audio_path:
                try:
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
        else:
            self.play_start_time = time.time()
            self.is_playing = True
            self.is_paused = False
            if self.audio_path:
                try:
                    pygame.mixer.music.play(loops=0, start=self.play_offset)
                except Exception:
                    pygame.mixer.music.play()
        self._schedule_update()

    def pause(self):
        if not self.is_playing:
            return
        elapsed = time.time() - self.play_start_time
        self.play_offset += elapsed
        self.is_playing = False
        self.is_paused = True
        if self.audio_path:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass
        self._cancel_update()
        self._update_time_label(self.play_offset)

    def stop(self):
        if not self.mid:
            return
        self.is_playing = False
        self.is_paused = False
        self.play_offset = 0.0
        if self.audio_path:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._cancel_update()
        self.draw_pianoroll()
        self._update_time_label(0.0)

    def _schedule_update(self):
        self._cancel_update()
        self._update_frame()
        self.update_job = self.after(30, self._schedule_update)

    def _cancel_update(self):
        if self.update_job:
            try:
                self.after_cancel(self.update_job)
            except Exception:
                pass
            self.update_job = None

    def _update_frame(self):
        if not self.is_playing:
            return
        elapsed = time.time() - self.play_start_time
        current_time = self.play_offset + elapsed
        if current_time >= self.length_seconds:
            self.stop()
            return
        self.draw_playhead(current_time)
        self._update_time_label(current_time)

    # -------------------------
    # Drawing / canvas
    # -------------------------
    def draw_empty(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            12,
            12,
            anchor="nw",
            text="Load a MIDI file from File → Open MIDI...",
            fill="#eee",
        )

    def draw_pianoroll(self):
        self.canvas.delete("all")
        px = self.px_per_second
        total_w = int(self.length_seconds * px) + 500
        height = (self.PITCH_MAX - self.PITCH_MIN + 1) * self.ROW_HEIGHT
        self.canvas.config(scrollregion=(0, 0, total_w, height + 40))

        # vertical grid lines (seconds)
        for s in range(0, int(math.ceil(self.length_seconds)) + 1):
            x = s * px
            color = "#262626" if s % 5 else "#333333"
            self.canvas.create_line(x, 0, x, height, fill=color)
            if s % 5 == 0:
                self.canvas.create_text(
                    x + 2, 2, anchor="nw", text=str(s), fill="#777", font=("Arial", 8)
                )

        # draw measure lines using time signature map
        if self.timesig_map:
            measure_times = self.timesig_map.get_measure_start_seconds(
                self.length_seconds
            )
            for mt in measure_times:
                mx = mt * px
                self.canvas.create_line(mx, 0, mx, height, fill="#4444ff", width=2)
                # small label
                self.canvas.create_text(
                    mx + 4,
                    height - 18,
                    anchor="sw",
                    text=f"Bar",
                    fill="#4444ff",
                    font=("Arial", 9),
                )

        # horizontal pitch rows
        for p in range(self.PITCH_MIN, self.PITCH_MAX + 1):
            y = (self.PITCH_MAX - p) * self.ROW_HEIGHT
            fill = "#0b0b0b" if (p % 2 == 0) else "#0a0a12"
            self.canvas.create_rectangle(
                0, y, total_w, y + self.ROW_HEIGHT, fill=fill, outline=""
            )
            if p % 12 in (0, 2, 4, 5, 7, 9, 11):
                self.canvas.create_text(
                    2, y + 1, anchor="nw", text=str(p), fill="#666", font=("Arial", 7)
                )

        # tempo visualization: vertical lines and BPM labels
        if self.tempo_map:
            for seg in self.tempo_map.segments:
                t = seg["start_time"]
                x = t * px
                bpm = int(round(60_000_000 / seg["tempo"]))
                self.canvas.create_line(
                    x, 0, x, height, fill="#ffdd33", width=2, dash=(4, 2)
                )
                self.canvas.create_text(
                    x + 4,
                    height - 32,
                    anchor="sw",
                    text=f"BPM:{bpm}",
                    fill="#ffdd33",
                    font=("Arial", 9),
                )

        # draw notes with channel-based colors
        for ev in self.note_events:
            start_x = ev["start_sec"] * px
            end_x = ev["end_sec"] * px
            note = ev["note"]
            channel = ev.get("channel", 0)
            y = (self.PITCH_MAX - note) * self.ROW_HEIGHT

            # Get color for channel
            color = self.CHANNEL_COLORS[channel % len(self.CHANNEL_COLORS)]
            # Calculate darker outline color
            outline_color = self._darken_color(color)

            self.canvas.create_rectangle(
                start_x,
                y,
                end_x,
                y + self.ROW_HEIGHT - 1,
                fill=color,
                outline=outline_color,
            )

        # markers
        for m in self.markers:
            self._draw_marker(m, px, height)

        # playhead
        self.total_width = total_w
        self.total_height = height
        self.draw_playhead(self._current_play_time())

        # draw hover line if mouse is over canvas
        self._draw_hover_line()

    def _darken_color(self, hex_color: str, factor: float = 0.6) -> str:
        """Darken a hex color for outline."""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def draw_playhead(self, current_time):
        self.canvas.delete("playhead")
        x = current_time * self.px_per_second
        self.canvas.create_line(
            x, 0, x, self.total_height, fill="#ff4444", width=2, tags=("playhead",)
        )
        # auto scroll
        canvas_w = self.canvas.winfo_width()
        x0 = self.canvas.canvasx(0)
        x1 = x0 + canvas_w
        if x < x0 + 80:
            self.canvas.xview_moveto(max(0, (x - 80) / max(1, self.total_width)))
        elif x > x1 - 80:
            self.canvas.xview_moveto(min(1.0, (x - 80) / max(1, self.total_width)))

    def _draw_marker(self, marker_dict, px, height):
        t = marker_dict["time"]
        label = marker_dict.get("label", "")
        x = t * px
        self.canvas.create_line(
            x, 0, x, height, fill="#ff77aa", width=2, tags=("marker",)
        )
        txt = label if label else f"M{int(t)}"
        self.canvas.create_text(
            x + 6,
            6,
            anchor="nw",
            text=txt,
            fill="#ff77aa",
            font=("Arial", 9),
            tags=("marker",),
        )

    def _draw_hover_line(self):
        """Draw hover line at mouse position with snap applied."""
        self.canvas.delete("hover_line")
        if hasattr(self, "mouse_time") and self.mid:
            snapped_time = self._apply_snap(self.mouse_time)
            x = snapped_time * self.px_per_second
            self.canvas.create_line(
                x,
                0,
                x,
                self.total_height,
                fill="#666666",
                width=1,
                dash=(2, 2),
                tags=("hover_line",),
            )

    # -------------------------
    # Mouse events & snapping
    # -------------------------
    def on_click(self, event):
        x = self.canvas.canvasx(event.x)
        t = x / self.px_per_second
        t = max(0.0, min(t, self.length_seconds))
        t = self._apply_snap(t)

        # Jump to playback position
        self._jump_to_time(t)

        # If playing, seek audio immediately
        if self.is_playing and self.audio_path:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.play(start=t)
            except Exception:
                pygame.mixer.music.play()

            self.play_offset = t
            self.play_start_time = time.time()

        self.mouse_time = t

    def on_double_click(self, event):
        x = self.canvas.canvasx(event.x)
        t = x / self.px_per_second
        t = max(0.0, min(t, self.length_seconds))
        # apply snap
        t = self._apply_snap(t)
        # search nearest marker within threshold
        nearest = None
        nearest_d = 1e9
        for m in self.markers:
            d = abs(m["time"] - t)
            if d < nearest_d:
                nearest_d = d
                nearest = m
        if nearest is not None and nearest_d <= 0.3:
            # delete
            self.markers.remove(nearest)
            self._refresh_marker_list()
            self.draw_pianoroll()
        else:
            # insert with label dialog
            label = simpledialog.askstring(
                "Marker label", "Enter marker label (optional):", parent=self
            )
            self.markers.append({"time": t, "label": label or ""})
            self.markers.sort(key=lambda x: x["time"])
            self._refresh_marker_list()
            self.draw_pianoroll()

    def on_motion(self, event):
        x = self.canvas.canvasx(event.x)
        if hasattr(self, "px_per_second") and 0 <= x <= self.total_width:
            t = x / self.px_per_second
            self.mouse_time = t
            # Update hover line
            if self.mid:
                self._draw_hover_line()
            self.time_label.configure(
                text=f"{self._fmt_time(self._current_play_time())} / {self._fmt_time(self.length_seconds)}  (hover {self._fmt_time(t)})"
            )

    def on_snap_change(self, val):
        self.snap_mode = val

    def _apply_snap(self, t: float) -> float:
        """If snap_mode is Free, return t. Else quantize to closest note division based on current ticks_per_beat."""
        if not self.mid or not self.tempo_map:
            return t
        if self.snap_mode == "Free":
            return t
        denom_map = {"1/4": 1, "1/8": 2, "1/16": 4, "1/32": 8}
        key = self.snap_mode
        if key not in denom_map:
            return t
        factor = denom_map[key]
        ticks = self.tempo_map.seconds_to_ticks(t)
        quant_ticks = self.mid.ticks_per_beat / factor  # float
        if quant_ticks <= 0:
            return t
        snapped_ticks = int(round(ticks / quant_ticks) * quant_ticks)
        snapped_time = self.tempo_map.ticks_to_seconds(int(round(snapped_ticks)))
        # clamp
        return max(0.0, min(snapped_time, self.length_seconds))

    # -------------------------
    # Marker list actions
    # -------------------------
    def _refresh_marker_list(self):
        for item in self.marker_tree.get_children():
            self.marker_tree.delete(item)
        for idx, m in enumerate(sorted(self.markers, key=lambda x: x["time"])):
            tid = f"m{idx}"
            self.marker_tree.insert(
                "", "end", iid=tid, values=(self._fmt_time(m["time"]), m["label"])
            )

    def jump_to_selected_marker(self):
        sel = self.marker_tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a marker in the list first.")
            return
        iid = sel[0]
        idx = int(iid[1:])
        m = sorted(self.markers, key=lambda x: x["time"])[idx]
        self._jump_to_time(m["time"])

    def edit_selected_marker(self):
        sel = self.marker_tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a marker in the list first.")
            return
        iid = sel[0]
        idx = int(iid[1:])
        sorted_markers = sorted(self.markers, key=lambda x: x["time"])
        m = sorted_markers[idx]
        new_label = simpledialog.askstring(
            "Edit label",
            "Edit marker label:",
            initialvalue=m.get("label", ""),
            parent=self,
        )
        if new_label is not None:
            # update original marker
            self.markers.remove(m)
            m["label"] = new_label
            self.markers.append(m)
            self.markers.sort(key=lambda x: x["time"])
            self._refresh_marker_list()
            self.draw_pianoroll()

    def delete_selected_marker(self):
        sel = self.marker_tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a marker in the list first.")
            return
        iid = sel[0]
        idx = int(iid[1:])
        m = sorted(self.markers, key=lambda x: x["time"])[idx]
        self.markers.remove(m)
        self._refresh_marker_list()
        self.draw_pianoroll()

    def add_marker_dialog(self):
        t = simpledialog.askfloat(
            "Add marker",
            "Time (seconds):",
            minvalue=0.0,
            maxvalue=self.length_seconds,
            parent=self,
        )
        if t is None:
            return
        # apply snap to inserted time as well
        t = self._apply_snap(t)
        label = simpledialog.askstring(
            "Label (optional)", "Label for marker:", parent=self
        )
        self.markers.append({"time": t, "label": label or ""})
        self.markers.sort(key=lambda x: x["time"])
        self._refresh_marker_list()
        self.draw_pianoroll()

    def on_marker_tree_double(self, event):
        sel = self.marker_tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = int(iid[1:])
        m = sorted(self.markers, key=lambda x: x["time"])[idx]
        self._jump_to_time(m["time"])

    def _jump_to_time(self, t):
        self.play_offset = max(0.0, min(t, self.length_seconds))

        if self.is_playing:
            # If playing, reset play start time (draw_playhead handles auto-scroll)
            self.play_start_time = time.time()
        else:
            # If not playing/paused, don't scroll (to avoid confusing the user)
            self.is_paused = False

        # Draw playhead (auto-scroll occurs inside draw_playhead if playing)
        self.draw_playhead(self.play_offset)
        self._update_time_label(self.play_offset)

    def delete_nearest_marker(self):
        if not hasattr(self, "mouse_time"):
            messagebox.showinfo(
                "No cursor", "Click on the piano roll to pick a position first."
            )
            return
        t = self.mouse_time
        if not self.markers:
            messagebox.showinfo("No markers", "No markers to delete.")
            return
        nearest = min(self.markers, key=lambda m: abs(m["time"] - t))
        if abs(nearest["time"] - t) <= 0.7:
            self.markers.remove(nearest)
            self._refresh_marker_list()
            self.draw_pianoroll()
        else:
            messagebox.showinfo(
                "No nearby marker", "No marker within 0.7 seconds of cursor."
            )

    # -------------------------
    # Zoom handling
    # -------------------------
    def on_zoom_change(self, val):
        try:
            v = float(val)
        except Exception:
            return
        canvas_w = self.canvas.winfo_width() or 800
        center_x = self.canvas.canvasx(canvas_w / 2)
        center_time = center_x / self.px_per_second if self.px_per_second else 0.0
        self.px_per_second = v
        self.draw_pianoroll()
        new_center_x = center_time * self.px_per_second
        self.canvas.xview_moveto(
            max(0, (new_center_x - canvas_w / 2) / max(1, self.total_width))
        )

    # -------------------------
    # Tempo panel & helpers
    # -------------------------
    def _populate_tempo_panel(self):
        self.tempo_listbox.delete(0, tk.END)
        if not self.tempo_map:
            return
        for seg in self.tempo_map.segments:
            bpm = round(60_000_000 / seg["tempo"], 2)
            self.tempo_listbox.insert(tk.END, f"t={seg['start_time']:.3f}s  BPM={bpm}")

    def _fmt_time(self, t):
        if t is None:
            return "00:00.000"
        mm = int(t // 60)
        ss = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{mm:02d}:{ss:02d}.{ms:03d}"

    def _current_play_time(self):
        if self.is_playing:
            elapsed = time.time() - self.play_start_time
            return min(self.play_offset + elapsed, self.length_seconds)
        elif self.is_paused:
            return self.play_offset
        else:
            return self.play_offset if self.play_offset else 0.0

    def _update_time_label(self, current_time):
        self.time_label.configure(
            text=f"{self._fmt_time(current_time)} / {self._fmt_time(self.length_seconds)}"
        )

    # -------------------------
    # Export markers JSON
    # -------------------------
    def export_markers_json(self):
        if not self.markers:
            messagebox.showinfo("No markers", "No markers to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        import json

        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                sorted(self.markers, key=lambda x: x["time"]),
                f,
                ensure_ascii=False,
                indent=2,
            )
        messagebox.showinfo("Exported", f"Markers exported to {path}")


# -------------------------
# Run
# -------------------------
def main():
    app = MidiMarkerEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
