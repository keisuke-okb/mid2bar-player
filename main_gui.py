import json
import os
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import shutil

from app import Mid2barPlayerApp
import mid2csv
from tools import get_lang_text, resource_path


# ---------- Helper functions ----------


def ask_file(parent, title, filetypes, initialdir=None, multiple=False):
    if multiple:
        paths = filedialog.askopenfilenames(
            parent=parent, title=title, filetypes=filetypes, initialdir=initialdir
        )
        return list(paths)
    else:
        path = filedialog.askopenfilename(
            parent=parent, title=title, filetypes=filetypes, initialdir=initialdir
        )
        return path


# ---------- Main GUI Class ----------
class ProjectEditorApp(ctk.CTk):
    DEFAULT_PROJECT_PATH = os.path.abspath("project.json")

    def __init__(self):
        super().__init__()
        self.title("MID2BAR-Player Project Editor")
        self.geometry("900x720")
        icon_path = resource_path("images/ui/MID2BAR.ico")
        self.iconbitmap(icon_path)

        # Variables
        self.editor_lang_var = ctk.StringVar()
        self.splash_image_var = ctk.StringVar()
        self.title_image_var = ctk.StringVar()
        self.audio_path_var = ctk.StringVar()
        self.mid_path_var = ctk.StringVar()
        self.lrc_path_var = ctk.StringVar()
        self.lrc_settings_path_var = ctk.StringVar()
        self.video_fixed_fps_var = ctk.StringVar()
        self.video_shuffle_var = ctk.BooleanVar(value=False)
        self.enable_mic_input_var = ctk.BooleanVar(value=False)
        self.mic_input_channel_var = ctk.StringVar(value="0")
        self.record_var = ctk.BooleanVar(value=False)
        self.settings_json_path_var = ctk.StringVar(value="app_settings/settings.json")
        self.assets_json_path_var = ctk.StringVar(value="app_settings/assets.json")
        self.font = ctk.CTkFont(family=get_lang_text("font_family"), size=11)

        # Video paths stored in list
        self.video_paths = []

        # Current project file path (for Save / Save As)
        self.current_project_path = None

        self._build_menu()
        self._build_body()

        # Load project.json if exists
        if os.path.exists(self.DEFAULT_PROJECT_PATH):
            try:
                self.load_project(self.DEFAULT_PROJECT_PATH)
                self.current_project_path = self.DEFAULT_PROJECT_PATH
            except Exception:
                print("Failed to load default project.json:", traceback.format_exc())

        # Setup traces for autosave on change
        for var in (
            self.editor_lang_var,
            self.splash_image_var,
            self.title_image_var,
            self.audio_path_var,
            self.mid_path_var,
            self.lrc_path_var,
            self.lrc_settings_path_var,
            self.video_fixed_fps_var,
            self.video_shuffle_var,
            self.enable_mic_input_var,
            self.mic_input_channel_var,
            self.record_var,
            self.settings_json_path_var,
            self.assets_json_path_var,
        ):
            try:
                var.trace_add("write", lambda *_: self._autosave())
            except Exception:
                # for BooleanVar, trace_add exists too; keep safe
                pass

        # Ensure window closes cleanly
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    # ---------- UI ----------
    def _build_menu(self):
        menubar = tk.Menu(self)
        filemenu = tk.Menu(menubar, tearoff=0, font=self.font)
        filemenu.add_command(label=get_lang_text("open..."), command=self.file_open)
        filemenu.add_command(label=get_lang_text("save"), command=self.file_save)
        filemenu.add_command(
            label=get_lang_text("save as..."), command=self.file_save_as
        )
        filemenu.add_separator()
        filemenu.add_command(label=get_lang_text("exit"), command=self.on_exit)
        menubar.add_cascade(label=get_lang_text("file"), menu=filemenu)
        self.config(menu=menubar)

    def _build_body(self):
        # Use grid with two columns: left form, right video list and actions
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(main_frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
        right = ctk.CTkFrame(main_frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)

        # Left: fields
        langs = [
            p.replace(".json", "")
            for p in os.listdir("./lang")
            if os.path.splitext(p)[1] == ".json"
        ]
        ctk.CTkLabel(left, font=self.font, text=get_lang_text("editor_lang")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        ctk.CTkComboBox(
            left,
            font=self.font,
            values=langs,
            command=self.set_editor_lang,
            variable=self.editor_lang_var,
        ).grid(row=0, column=0, sticky="w", padx=120, pady=(8, 8))

        # Splash text (multiline)
        ctk.CTkLabel(left, font=self.font, text=get_lang_text("splash_text")).grid(
            row=1, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        self.splash_textbox = ctk.CTkTextbox(left, font=self.font, width=420, height=90)
        self.splash_textbox.grid(row=2, column=0, padx=8, pady=(0, 12))
        self.splash_textbox.bind("<FocusOut>", lambda e: self._autosave())

        # Splash image
        self._make_path_row(
            left,
            row=3,
            label=get_lang_text("splash_image"),
            var=self.splash_image_var,
            filetypes=[("Image", "*.png;*.PNG;*.jpg;*.jpeg")],
        )
        # Title image
        self._make_path_row(
            left,
            row=4,
            label=get_lang_text("title_image"),
            var=self.title_image_var,
            filetypes=[("Image", "*.png;*.PNG;*.jpg;*.jpeg")],
        )
        # Audio
        self._make_path_row(
            left,
            row=5,
            label=get_lang_text("audio_path"),
            var=self.audio_path_var,
            filetypes=[("Audio", "*.mp3;*.wav;*.m4a;*.flac;*.ogg")],
        )
        # Midi
        self._make_path_row(
            left,
            row=6,
            label=get_lang_text("mid_path"),
            var=self.mid_path_var,
            filetypes=[("MIDI", "*.mid;*.midi")],
        )
        # lrc
        self._make_path_row(
            left,
            row=7,
            label=get_lang_text("lrc_path"),
            var=self.lrc_path_var,
            filetypes=[("LRC", "*.lrc;*.txt")],
        )
        # lrc settings
        self._make_path_row(
            left,
            row=8,
            label=get_lang_text("lrc_settings_path"),
            var=self.lrc_settings_path_var,
            filetypes=[("JSON", "*.json")],
        )

        # Additional settings requested
        # video_fixed_fps
        fps_frame = ctk.CTkFrame(left)
        fps_frame.grid(row=9, column=0, sticky="ew", padx=8, pady=6)
        fps_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            fps_frame, font=self.font, text=get_lang_text("video_fixed_fps")
        ).grid(row=0, column=0, sticky="w")
        fps_entry = ctk.CTkEntry(
            fps_frame, font=self.font, textvariable=self.video_fixed_fps_var
        )
        fps_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        # mic input channel
        mic_frame = ctk.CTkFrame(left)
        mic_frame.grid(row=10, column=0, sticky="ew", padx=8, pady=6)
        mic_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            mic_frame, font=self.font, text=get_lang_text("mic_input_channel")
        ).grid(row=0, column=0, sticky="w")
        mic_entry = ctk.CTkEntry(
            mic_frame, font=self.font, textvariable=self.mic_input_channel_var
        )
        mic_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        # settings_json_path and assets_json_path
        self._make_path_row(
            left,
            row=11,
            label=get_lang_text("settings_json_path"),
            var=self.settings_json_path_var,
            filetypes=[("JSON", "*.json")],
        )
        self._make_path_row(
            left,
            row=12,
            label=get_lang_text("assets_json_path"),
            var=self.assets_json_path_var,
            filetypes=[("JSON", "*.json")],
        )

        # video_shuffle, enable_mic_input, record (checkboxes)
        chk_frame = ctk.CTkFrame(left)
        chk_frame.grid(row=13, column=0, sticky="ew", padx=8, pady=6)
        chk_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkCheckBox(
            chk_frame,
            font=self.font,
            text=get_lang_text("video_shuffle"),
            variable=self.video_shuffle_var,
        ).grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkCheckBox(
            chk_frame,
            font=self.font,
            text=get_lang_text("enable_mic_input"),
            variable=self.enable_mic_input_var,
        ).grid(row=0, column=1, sticky="w", padx=4)
        ctk.CTkCheckBox(
            chk_frame,
            font=self.font,
            text=get_lang_text("record"),
            variable=self.record_var,
        ).grid(row=0, column=2, sticky="w", padx=4)

        # Start button
        start_btn = ctk.CTkButton(
            left,
            font=self.font,
            text=get_lang_text("run"),
            command=self.start_with_settings,
        )
        start_btn.grid(row=14, column=0, pady=12, padx=8, sticky="ew")

        # Right: video list editor
        ctk.CTkLabel(right, font=self.font, text=get_lang_text("video_paths")).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4)
        )

        list_frame = ctk.CTkFrame(right)
        list_frame.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="nsew")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Use regular tkinter Listbox for convenience
        self.video_listbox = tk.Listbox(
            list_frame, font=self.font, selectmode=tk.SINGLE
        )
        self.video_listbox.grid(row=0, column=0, sticky="nsew")

        # Scrollbar for listbox
        scrollbar = tk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.video_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.video_listbox.config(yscrollcommand=scrollbar.set)

        # Video list control buttons
        btn_frame = ctk.CTkFrame(right)
        btn_frame.grid(row=2, column=0, padx=8, pady=(0, 8), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        add_btn = ctk.CTkButton(
            btn_frame,
            font=self.font,
            text=get_lang_text("add..."),
            command=self.video_add,
        )
        add_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        remove_btn = ctk.CTkButton(
            btn_frame,
            font=self.font,
            text=get_lang_text("delete_selected"),
            command=self.video_remove,
        )
        remove_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        up_btn = ctk.CTkButton(
            btn_frame,
            font=self.font,
            text=get_lang_text("up"),
            width=40,
            command=lambda: self.video_move(-1),
        )
        up_btn.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        down_btn = ctk.CTkButton(
            btn_frame,
            font=self.font,
            text=get_lang_text("down"),
            width=40,
            command=lambda: self.video_move(1),
        )
        down_btn.grid(row=0, column=3, padx=4, pady=4, sticky="ew")

        # Quick buttons to add directory or multiple files
        extra_frame = ctk.CTkFrame(right)
        extra_frame.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="ew")
        add_multi_btn = ctk.CTkButton(
            extra_frame,
            font=self.font,
            text=get_lang_text("add_multi..."),
            command=self.video_add_multi,
        )
        add_multi_btn.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        add_dir_btn = ctk.CTkButton(
            extra_frame,
            font=self.font,
            text=get_lang_text("add_folder..."),
            command=self.video_add_from_dir,
        )
        add_dir_btn.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        # Bottom area: status
        self.status_var = ctk.StringVar(value="Ready")
        status = ctk.CTkLabel(
            self, font=self.font, textvariable=self.status_var, anchor="w"
        )
        status.pack(side="bottom", fill="x")

    def _make_path_row(self, parent, row, label, var, filetypes=None):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, font=self.font, text=label).grid(
            row=0, column=0, sticky="w"
        )
        entry = ctk.CTkEntry(frame, font=self.font, textvariable=var)
        entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))

        def on_browse():
            if filetypes is None:
                f = ask_file(
                    self, title=f"Select {label}", filetypes=[("All files", "*.*")]
                )
            else:
                f = ask_file(self, title=f"Select {label}", filetypes=filetypes)
            if f:
                if isinstance(f, (list, tuple)):
                    # store first selected if list
                    var.set(f[0])
                else:
                    var.set(f)
                self._autosave()

        browse_btn = ctk.CTkButton(
            frame, font=self.font, text="...", width=40, command=on_browse
        )
        browse_btn.grid(row=0, column=2, padx=(0, 4))

    # ---------- Video list operations ----------
    def video_add(self):
        paths = ask_file(
            self,
            title="Add video",
            filetypes=[("Video", "*.mp4;*.mov;*.mkv;*.avi")],
            multiple=True,
        )
        if not paths:
            return
        # askopenfilename with multiple returns tuple or list
        if isinstance(paths, (list, tuple)):
            added = list(paths)
        else:
            added = [paths]
        self.video_paths.extend(added)
        self._refresh_video_listbox()
        self._autosave()

    def video_add_multi(self):
        self.video_add()

    def video_add_from_dir(self):
        d = filedialog.askdirectory(
            parent=self, title="Select directory to add videos from"
        )
        if not d:
            return
        ok_ext = (".mp4", ".mov", ".mkv", ".avi")
        found = [
            os.path.join(d, f)
            for f in os.listdir(d)
            if os.path.splitext(f)[1].lower() in ok_ext
        ]
        found.sort()
        if found:
            self.video_paths.extend(found)
            self._refresh_video_listbox()
            self._autosave()

    def video_remove(self):
        sel = self.video_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.video_paths[idx]
        self._refresh_video_listbox()
        self._autosave()

    def video_move(self, delta):
        sel = self.video_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.video_paths):
            return
        self.video_paths[idx], self.video_paths[new_idx] = (
            self.video_paths[new_idx],
            self.video_paths[idx],
        )
        self._refresh_video_listbox()
        self.video_listbox.selection_clear(0, tk.END)
        self.video_listbox.selection_set(new_idx)
        self._autosave()

    def _refresh_video_listbox(self):
        self.video_listbox.delete(0, tk.END)
        for p in self.video_paths:
            self.video_listbox.insert(tk.END, p)

    # ---------- Project load/save ----------
    def collect_project_dict(self):
        proj = {
            "editor_lang": self.editor_lang_var.get() or "en",
            "splash_text": self.splash_textbox.get("0.0", "end-1c"),
            "splash_image": self.splash_image_var.get() or None,
            "title_image": self.title_image_var.get() or None,
            "audio_path": self.audio_path_var.get() or None,
            "mid_path": self.mid_path_var.get() or None,
            "lrc_path": self.lrc_path_var.get() or None,
            "lrc_settings_path": self.lrc_settings_path_var.get() or None,
            "video_paths": list(self.video_paths),
            "video_fixed_fps": self.video_fixed_fps_var.get() or "0",
            "video_shuffle": bool(self.video_shuffle_var.get()),
            "enable_mic_input": bool(self.enable_mic_input_var.get()),
            "mic_input_channel": int(self.mic_input_channel_var.get() or 0),
            "record": bool(self.record_var.get()),
            "settings_json_path": self.settings_json_path_var.get() or None,
            "assets_json_path": self.assets_json_path_var.get() or None,
        }
        return proj

    def apply_project_dict(self, proj: dict):
        # Defensive: use get with defaults
        self.editor_lang_var.set(proj.get("editor_lang") or "en")
        self.splash_textbox.delete("0.0", "end")
        if "splash_text" in proj and proj.get("splash_text") is not None:
            self.splash_textbox.insert("0.0", proj.get("splash_text"))
        self.splash_image_var.set(proj.get("splash_image") or "")
        self.title_image_var.set(proj.get("title_image") or "")
        self.audio_path_var.set(proj.get("audio_path") or "")
        self.mid_path_var.set(proj.get("mid_path") or "")
        self.lrc_path_var.set(proj.get("lrc_path") or "")
        self.lrc_settings_path_var.set(proj.get("lrc_settings_path") or "")
        self.video_fixed_fps_var.set(proj.get("video_fixed_fps") or 0)

        self.video_shuffle_var.set(bool(proj.get("video_shuffle", False)))
        self.enable_mic_input_var.set(bool(proj.get("enable_mic_input", False)))
        self.mic_input_channel_var.set(int(proj.get("mic_input_channel", 0)))
        self.record_var.set(bool(proj.get("record", False)))

        self.settings_json_path_var.set(
            proj.get("settings_json_path") or "app_settings/settings.json"
        )
        self.assets_json_path_var.set(
            proj.get("assets_json_path") or "app_settings/assets.json"
        )

        self.video_paths = list(proj.get("video_paths") or [])
        self._refresh_video_listbox()

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            proj = json.load(f)
        self.apply_project_dict(proj)
        self.current_project_path = path
        self.status_var.set(f"Loaded: {path}")

    def save_project(self, path):
        proj = self.collect_project_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(proj, f, ensure_ascii=False, indent=2)
        self.current_project_path = path
        self.status_var.set(f"Saved: {path}")

    def file_open(self):
        path = filedialog.askopenfilename(
            parent=self, title="Open project JSON", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        try:
            self.load_project(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project:{e}")

    def file_save(self):
        if self.current_project_path:
            try:
                self.save_project(self.current_project_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project:{e}")
        else:
            self.file_save_as()

    def file_save_as(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save project as",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        try:
            self.save_project(path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project:{e}")

    def _autosave(self):
        # Save to DEFAULT_PROJECT_PATH, but don't block UI
        try:
            self.save_project(self.DEFAULT_PROJECT_PATH)
        except Exception:
            # ignore autosave errors but print to console
            print("Autosave failed:", traceback.format_exc())

    def set_editor_lang(self, lang):
        self._autosave()
        messagebox.showinfo("Info", "Please restart app to change editor language.")

    # ---------- Start App ----------
    def start_with_settings(self):
        proj = self.collect_project_dict()
        if proj.get("record", False):
            if not shutil.which("ffmpeg"):
                messagebox.showerror("Error", get_lang_text("ffmpeg_error"))
                return

        # Check MIDI
        mid_path = proj.get("mid_path")
        separator_csv = f"./data/marker.csv"
        note_csv = f"./data/note.csv"
        mid2csv.convert(mid_path, note_csv, separator_csv)
        with open(separator_csv, "r", encoding="utf-8") as f:
            texts = f.readlines()
        if len(texts) < 3:
            messagebox.showerror("Error", get_lang_text("midi_marker_error"))
            return

        self._autosave()
        kwargs = {
            "audio_path": proj.get("audio_path"),
            "mid_path": proj.get("mid_path"),
            "lrc_path": proj.get("lrc_path"),
            "lrc_settings_path": proj.get("lrc_settings_path"),
            "video_paths": proj.get("video_paths", []),
            "video_fixed_fps": int(proj.get("video_fixed_fps")),
            "video_shuffle": proj.get("video_shuffle", False),
            "credit_text": proj.get("splash_text"),
            "splash_image": proj.get("splash_image"),
            "title_image": proj.get("title_image"),
            "enable_mic_input": proj.get("enable_mic_input", False),
            "mic_input_channel": int(proj.get("mic_input_channel", 0)),
            "record": proj.get("record", False),
            "settings_json_path": proj.get("settings_json_path")
            or "app_settings/settings.json",
            "assets_json_path": proj.get("assets_json_path")
            or "app_settings/assets.json",
        }

        try:
            app = Mid2barPlayerApp(**kwargs)
            try:
                self.iconify()
            except Exception:
                pass
            app.run()
            try:
                self.deiconify()
            except Exception:
                pass

        except Exception as e:
            tb = traceback.format_exc()
            messagebox.showerror(
                "Failed to launch MyApp", f"Error: {e} Traceback: {tb}"
            )
            messagebox.showinfo(
                "Launch args",
                f"Would have launched with:{json.dumps(kwargs, ensure_ascii=False, indent=2)}",
            )

    def on_exit(self):
        # autosave before exit
        try:
            self._autosave()
        except Exception:
            pass
        self.destroy()


# ---------- If run as script ----------
if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("dark-blue")
    app = ProjectEditorApp()
    app.mainloop()
