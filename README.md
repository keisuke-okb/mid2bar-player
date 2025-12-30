<div align="center">
  <img src="./images/ui/MID2BAR.ico" alt="Repository Icon" width="100" />
  <p style="font-weight: bold;">MID2BAR-Player</p>
</div>

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.9~-blue.svg)](https://www.python.org/)
[![Code style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![GitHub Release](https://img.shields.io/github/v/release/keisuke-okb/mid2bar-player)](https://github.com/keisuke-okb/mid2bar-player/releases)
[![Downloads](https://img.shields.io/github/downloads/keisuke-okb/mid2bar-player/total)](https://github.com/keisuke-okb/mid2bar-player/releases)
[![English](https://img.shields.io/badge/README-English-green)](README.md)
[![日本語](https://img.shields.io/badge/README-日本語-blue)](./README_ja.md)

</div>

👉 [日本語版 READMEはこちら(README_ja.md)](./README_ja.md)

# MID2BAR-Player

A standalone karaoke player that generates karaoke subtitle videos with pitch guide bar using ruby-annotated LRC lyric files, melody MIDI data, and background videos. 

- **IMPORTANT**: This software is designed primarily for generating subtitles for Japanese lyrics and English lyrics with Japanese ruby annotations. Subtitles for other languages may not work as intended and could result in unexpected bugs or issues.

- You may upload videos created with this repository (including modified code or the prebuilt packages) to video-sharing sites; please credit the software as **MID2BAR-Player**. The author assumes no responsibility for issues arising from uploading created videos.

## Overview

* **MID2BAR-Player**: A standalone player that visualizes karaoke by combining melody MIDI data, LRC lyrics (with ruby/furigana support), and optional background video/audio.
* **Main features**: Synced display of melody MIDI files (with measure/page markers) and lyrics, visual effects (note bars, glow, particles), real-time microphone input scoring (this is FFT-based pitch matching only — not equivalent to commercial karaoke scoring; use for reference), video overlay, and recording (export) functionality.

---

## Supported Platforms

* OS: Windows / macOS* / Linux*

  * If the pitch-bar page transition causes screen flicker, set `FADE_TIME` to `0.0` in `app_settings/settings.json`.
* External software: `ffmpeg` (required for screen recording). Put `ffmpeg.exe` and `ffprobe.exe` in a folder on your PATH or place them in the same folder as this application.

---

## Quick tutorial using the sample project (example: Windows prebuilt package)

1. Launch `MID2BAR-Player.exe`.
2. From the menu **File > Open Project**, load `sample/sample_project.json`. This will set up the sample music with these assets:

   * Audio file (e.g., WAV / MP3)
   * MIDI file (.mid)
   * Lyrics file (LRC, extended ruby format)
   * Background video (optional)
3. Click **Apply Settings and Prepare Playback** at the bottom of the window. The player will start preparing the karaoke subtitle video. When loading finishes, initial processing like lyric preview generation runs (status messages appear during generation).
4. When preparation is complete, press the Space key to start playback.

---

## Usage (from source)

1. Create a Python virtual environment for MID2BAR-Player:

```powershell
PS> git clone https://github.com/keisuke-okb/mid2bar-player
PS> cd mid2bar-player
PS> python -m venv venv
PS> .\venv\Scripts\Activate.ps1
```

```powershell
(venv) PS> pip install -r requirements.txt
```

2. Run the player with:

```powershell
python main_gui.py
```

This launches the player with the same configuration flow as the prebuilt package.

3. You can also call MID2BAR-Player from other Python programs; see `main.py` as a reference.

---

## How to create a karaoke video from your own assets

### 1. Create an LRC lyric file with ruby/furigana

Use a sample LRC or a tool such as **RhythmicaLyrics** to create an extended ruby-format LRC file.
**If you wrap tokens like “①”, “②” with time tags, the software recognizes them as part switches (part markers).**
Icons and colors used for part markers can be changed in the lyrics settings file (default: `lyrics_settings/settings_default.json`).

* `sample/【音楽：魔王魂】シャイニングスター（ショート）.lrc`: normal lyrics file
* `【音楽：魔王魂】シャイニングスター（ショート）_パート字幕.lrc`: part-separated subtitle example (for notation reference; not necessarily matching the original song)

The player recognizes blank lines as lyric block separators. For example, the first two lines below are treated as a single block:

```
[00:09:65]た[00:09:83]だ[00:10:39]風[00:10:39]([00:10:39]かぜ[00:11:17])[00:11:17]に[00:11:37]揺[00:11:37]([00:11:37]ゆ[00:11:54])[00:11:54]ら[00:11:71]れ[00:11:90]て[00:12:48]
[00:12:66]何[00:12:66]([00:12:66]なに[00:13:02])[00:13:02]も[00:13:19]考[00:13:19]([00:13:19]かんが[00:14:19])[00:14:19]え[00:14:57]ず[00:14:75]に[00:15:48]
```

Three consecutive lines without blank lines are treated as a single block:

```
[00:35:29]シャ[00:35:45]イ[00:35:61]ニ[00:35:76]ン[00:35:94]グ[00:36:09]ス[00:36:24]ター[00:36:58]綴[00:36:58]([00:36:58]つづ[00:37:30])[00:37:30]れ[00:37:49]ば[00:37:94]
[00:38:10]夢[00:38:10]([00:38:10]ゆめ[00:38:46])[00:38:46]に[00:38:66]眠[00:38:66]([00:38:66]ねむ[00:39:22])[00:39:22]る[00:39:64]幻[00:39:64]([00:39:64]まぼろし[00:40:77])[00:40:77]が[00:41:00][00:41:38]掌[00:41:38]([00:41:38]てのひら[00:42:29])[00:42:29]に[00:42:67]降[00:42:67]([00:42:67]ふ[00:43:04])[00:43:04]り[00:43:41]注[00:43:41]([00:43:41]そそ[00:43:96])[00:43:96]ぐ[00:44:44]
[00:44:56]新[00:44:56]([00:44:56]あら[00:44:91])[00:44:91]た[00:45:29]な[00:45:66]世[00:45:66]([00:45:66]せ[00:46:07])[00:46:07]界[00:46:07]([00:46:07]かい[00:46:63])[00:46:63]へ[00:47:19]
```

---

### 2. Insert page/measure markers for pitch-bar display in the melody MIDI

* **The player recognizes MIDI “markers” as page/section boundaries for the pitch-bar display.**
* Insert markers using any MIDI editor or use the bundled `MIDI Marker Editor.exe`.

Steps with `MIDI Marker Editor.exe`:

1. Launch `MIDI Marker Editor.exe` and use **File > Open MIDI...** to load the melody MIDI line you want to display. **To avoid misbehavior, set the main melody’s MIDI channel to 0.**
2. Select the reference audio under **File > Set reference audio...**, press play, and verify the audio plays and the playback position moves.
3. Double-click where you want the start/end boundaries for the pitch-bar display to insert markers.
4. Save the MIDI with markers via **File > Save MIDI with markers...**.
5. In MID2BAR-Player, point to the MIDI file you saved with markers.

---

### 3. (Optional) Prepare images and setting files

You can customize images and various settings used by the player:

* Splash image: shown across the player at the start of playback
* Title logo: centered at the start (intended for song title)
* Audio source: MP3 or other music file to play in the player
* Karaoke subtitle generation settings: detailed subtitle generation options (default: `lyrics_settings/settings_default.json`)
* Player general settings: overall MID2BAR-Player settings (default: `app_settings/settings.json`)
* Image/assets settings: image assets list used by MID2BAR-Player (default: `app_settings/assets.json`)

---

## Basic controls (keyboard & mouse)

* **Space**: Play / Pause
* **R**: Restart (play from beginning)
* **A**: Toggle Bar Auto Play (automatic bar progression)
* **M**: Toggle microphone input (real-time scoring)
* **F11**: Toggle fullscreen
* **Up / Down**: Volume up / down
* **Esc**: Exit
* **Left mouse click**: Open menus / seek playback position (on the seek bar)

---

## Recording (video export)

* The player can export video (MP4) using `ffmpeg`.
* If recording is enabled at startup, the player will combine the current video and audio into an output file while playing.
* Please avoid interacting with the screen while recording.

---

## Troubleshooting

* No sound: Check system volume, the audio device used by Pygame, and file format compatibility.
* Microphone not responding: Ensure the microphone is enabled in the OS and the application has permission to use it.

---

## Microphone input and real-time scoring (reference-only feature)

* Enable microphone input in settings or toggle it during playback with `M`. The player analyzes your singing using FFT-based pitch detection and computes pitch-match and pitch-accuracy scores per page.
* Click the screen to open the menu and see real-time scoring.
* Microphone thresholds and delay compensation settings are adjustable in `app_settings/settings.json`.

---

## License

* Files in this repository are governed by the repository `LICENSE`, unless a file explicitly states a different license.
* Sample music under `sample/` is copyrighted by [森田交一 (魔王魂)](https://maou.audio/).
* You may upload videos created with this repository (including modified code or the prebuilt packages) to video-sharing sites; please credit the software as **MID2BAR-Player**. The author assumes no responsibility for issues arising from uploading created videos.

---

# Configuration reference

## Player general settings: `app_settings/settings.json`

### Screen & window settings

| Key                       | Default      | Description                       |
| ------------------------- | ------------ | --------------------------------- |
| `SCREEN_WIDTH`            | 1920         | Width of the rendering area (px)  |
| `SCREEN_HEIGHT`           | 1080         | Height of the rendering area (px) |
| `WINDOW_WIDTH`            | 1920         | Initial window width (px)         |
| `WINDOW_HEIGHT`           | 1080         | Initial window height (px)        |
| `FULL_SCREEN`             | false        | Start in fullscreen mode          |
| `SCREEN_FPS`              | 60           | Frame rate (FPS)                  |
| `MENU_H`                  | 300          | Menu bar height (px)              |
| `WINDOW_BACKGROUND_COLOR` | [10, 10, 10] | Window background color (RGB)     |

### UI & fonts

| Key                   | Default                         | Description                                 |
| --------------------- | ------------------------------- | ------------------------------------------- |
| `UI_LANG`             | "ja"                            | UI language ("ja": Japanese, "en": English) |
| `UI_FONT`             | "./fonts/NotoSansJP-Medium.ttf" | Path to UI font file                        |
| `BAR_COUNT_FONT`      | "./fonts/NotoSansJP-Black.ttf"  | Font path for bar count display             |
| `BAR_COUNT_FONT_SIZE` | 30                              | Font size for bar count                     |

### Playback settings

| Key                      | Default | Description                                                                                                                       |
| ------------------------ | ------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `PLAYBACK_TIME_SCALE`    | 1.001   | Playback speed correction (1.0 = normal). Used to correct drift between audio and subtitles/pitch bars. (Ignored when recording.) |
| `DEFAULT_VOLUME`         | 80      | Initial volume (0–100)                                                                                                            |
| `DISPLAY_TITLE_DURATION` | 2.0     | Title screen display time (seconds)                                                                                               |

### Color settings

| Key                 | Default              | Description                            |
| ------------------- | -------------------- | -------------------------------------- |
| `BG_COLOR`          | [20, 20, 40]         | Background color (RGB)                 |
| `VIDEO_ALPHA`       | 210                  | Background video opacity (0–255)       |
| `LINE_COLOR`        | [100, 100, 100, 200] | Guideline color (RGBA)                 |
| `NOTE_COLOR`        | [100, 100, 100]      | Note color (RGB)                       |
| `CURRENT_POS_COLOR` | [255, 50, 50]        | Current position indicator color (RGB) |
| `PASSED_NOTE_COLOR` | [255, 200, 100]      | Color for passed notes (RGB)           |
| `TEXT_COLOR`        | [255, 255, 255]      | Text color (RGB)                       |

### Splash screen settings

| Key                       | Default | Description                 |
| ------------------------- | ------- | --------------------------- |
| `SPLASH_TEXT_X_OFFSET`    | -50     | X offset for splash text    |
| `SPLASH_TEXT_Y_OFFSET`    | -50     | Y offset for splash text    |
| `SPLASH_TEXT_LINE_HEIGHT` | 80      | Line height for splash text |

### Bar display area settings

| Key                       | Default | Description                                |
| ------------------------- | ------- | ------------------------------------------ |
| `BAR_AREA_TOP`            | 50      | Top position of the bar display area (px)  |
| `BAR_AREA_HEIGHT`         | 250     | Height of the bar display area (px)        |
| `BAR_AREA_LEFT`           | 100     | Left position of the bar display area (px) |
| `BAR_AREA_WIDTH`          | 1720    | Width of the bar display area (px)         |
| `DISPLAY_PITCH_RANGE_MIN` | 23      | Minimum pitch range to display (semitones) |

### Now bar (current position) settings

| Key                          | Default | Description                              |
| ---------------------------- | ------- | ---------------------------------------- |
| `NOW_BAR_TOP`                | 34      | Top position of the now bar (px)         |
| `NOW_BAR_WIDTH`              | 200     | Width of the now bar (px)                |
| `NOW_BAR_HEIGHT`             | 286     | Height of the now bar (px)               |
| `HIDE_NOW_BAR_WHEN_NO_NOTES` | true    | Hide the now bar when there are no notes |

### Bar auto-play settings

| Key                      | Default   | Description                          |
| ------------------------ | --------- | ------------------------------------ |
| `BAR_AUTO_PLAY`          | true      | Enable bar auto-play mode            |
| `BAR_AUTO_PLAY_CHANNELS` | [0, 1, 2] | MIDI channels targeted for auto-play |
| `BAR_PASSED_ROUGHNESS`   | 10        | Roughness (smoothness) of bar fill   |

### Effects & animation

| Key                                         | Default | Description                           |
| ------------------------------------------- | ------- | ------------------------------------- |
| `BAR_PASSED_PARTICLE_RAND`                  | 0.7     | Particle spawn probability (0.0–1.0)  |
| `BAR_PASSED_COUNT_ANIMATION_TIME`           | 0.8     | Count animation time (seconds)        |
| `BAR_PASSED_COUNT_ANIMATION_CURVE_STRENGTH` | -0.1    | Curve strength for count animation    |
| `BAR_PASSED_COUNT_ANIMATION_ACCEL`          | 3.0     | Acceleration for count animation      |
| `BAR_PASSED_COUNT_ICON_SIZE`                | 40      | Count icon size (px)                  |
| `BAR_PASSED_COUNT_ICON_MARGIN`              | 10      | Count icon margin (px)                |
| `BAR_GLOW_DURATION`                         | 0.3     | Duration of bar glow effect (seconds) |
| `BAR_GLOW_SCALE`                            | 3.0     | Scale factor during bar glow          |

### Count display

| Key                               | Default | Description                                             |
| --------------------------------- | ------- | ------------------------------------------------------- |
| `BAR_PASSED_COUNT_ANIMATION_DICT` | {...}   | Animation settings per note type (position & color)     |
| `BAR_COUNT_DICT`                  | {...}   | Count display settings per note type (position & color) |

#### Note types used in `BAR_PASSED_COUNT_ANIMATION_DICT` / `BAR_COUNT_DICT`

* `normal`: regular note
* `max`: highest note
* `min`: lowest note
* `up`: rapidly rising note
* `down`: rapidly falling note
* `long`: long note

### Range gauge

| Key               | Default     | Description                        |
| ----------------- | ----------- | ---------------------------------- |
| `RANGE_GAUGE_POS` | [1480, 354] | Position of the range gauge [x, y] |
| `RANGE_GAUGE_W`   | 390         | Range gauge width (px)             |
| `RANGE_GAUGE_H`   | 23          | Range gauge height (px)            |

### Timing

| Key            | Default | Description                |
| -------------- | ------- | -------------------------- |
| `PREVIEW_TIME` | 2.0     | Bar preview time (seconds) |
| `REMAIN_TIME`  | 3.0     | Bar remain time (seconds)  |
| `FADE_TIME`    | 0.5     | Fade in/out time (seconds) |
| `LAG_TIME`     | 0.3     | Display lag time (seconds) |

### Seek bar

| Key              | Default | Description                        |
| ---------------- | ------- | ---------------------------------- |
| `SEEKBAR_TOP`    | 850     | Top position of the seek bar (px)  |
| `SEEKBAR_LEFT`   | 100     | Left position of the seek bar (px) |
| `SEEKBAR_WIDTH`  | 1720    | Seek bar width (px)                |
| `SEEKBAR_HEIGHT` | 10      | Seek bar height (px)               |

### Scoring

| Key                          | Default | Description                     |
| ---------------------------- | ------- | ------------------------------- |
| `PITCH_MATCH_SCORE_RATIO`    | 0.3     | Weight for pitch-match score    |
| `PITCH_ACCURACY_SCORE_RATIO` | 0.7     | Weight for pitch-accuracy score |

### Microphone input

| Key                               | Default | Description                                      |
| --------------------------------- | ------- | ------------------------------------------------ |
| `RMS_THRESHOLD`                   | 0.02    | Microphone RMS threshold                         |
| `MIC_INPUT_DURATION`              | 0.0     | Microphone input duration (seconds)              |
| `MIC_INPUT_DELAY`                 | 0.17    | Delay compensation for mic input (seconds)       |
| `MIC_INPUT_OFFSET`                | 0.2     | Microphone input offset (seconds)                |
| `MIC_INPUT_PITCH_TOLERANCE`       | 0.8     | Pitch tolerance (semitones)                      |
| `MIC_INPUT_NOTE_CONNECT_DURATION` | 0.1     | Max time gap to connect detected notes (seconds) |
| `MIC_INPUT_MARGIN`                | 0.01    | Mic input margin time (seconds)                  |

### Audio

| Key                   | Default          | Description                                                              |
| --------------------- | ---------------- | ------------------------------------------------------------------------ |
| `DEFAULT_SAMPLE_RATE` | 44100            | Default sample rate (Hz) — **verify your microphone device sample rate** |
| `DEFAULT_BLOCK_SIZE`  | 4096             | Audio block size (samples)                                               |
| `DEFAULT_CHANNELS`    | 1                | Default channels (1: mono, 2: stereo)                                    |
| `NOTE_NAMES`          | ["C", "C#", ...] | Array of note names                                                      |

### Screen recording & encoding

| Key           | Default   | Description                                                  |
| ------------- | --------- | ------------------------------------------------------------ |
| `AUDIO_CODEC` | "aac"     | Audio codec                                                  |
| `AUDIO_BPS`   | "320k"    | Audio bitrate                                                |
| `VIDEO_CODEC` | "libx264" | Video codec (for GPU encoding, change to `h264_nvenc`, etc.) |
| `VIDEO_BPS`   | "10M"     | Video bitrate                                                |

### Notes & cautions

* Coordinates and sizes are relative to `SCREEN_WIDTH` and `SCREEN_HEIGHT`.
* Colors are `[R, G, B]` or `[R, G, B, A]`, 0–255.
* Timing values are in seconds.
* Microphone settings may require tuning depending on environment and microphone quality.

---

## Image assets: `app_settings/assets.json`

### Overview

`assets.json` defines image asset paths used by MID2BAR-Player.

### Basic UI images

| Key             | Example path                  | Description                                    |
| --------------- | ----------------------------- | ---------------------------------------------- |
| `project_front` | "images/ui/project_front.png" | Project front UI image (foreground layer)      |
| `project_back`  | "images/ui/project_back.png"  | Project background UI image (background layer) |
| `now_bar`       | "images/ui/now_bar.png"       | Image for the current position indicator       |
| `range_gauge`   | "images/ui/range_gauge.png"   | Image for the range gauge                      |

### Icon images

The `icons` object defines icon images that indicate note features.

| Key          | Example path            | Description                   |
| ------------ | ----------------------- | ----------------------------- |
| `icons.up`   | "images/pitch/up.png"   | Icon for rapidly rising note  |
| `icons.down` | "images/pitch/down.png" | Icon for rapidly falling note |
| `icons.long` | "images/pitch/long.png" | Icon for a long note          |

### Bar images (`bars`)

`bars` defines note-bar images per MIDI channel. Each channel contains multiple note types and parts.

#### Structure

```
bars
├── "0" (channel 0)
│   ├── normal
│   ├── max
│   ├── min
│   ├── match
│   ├── match_all
│   └── unmatch
├── "1" (channel 1)
│   └── ...
└── "2" (channel 2)
    └── ...
```

#### Note types

| Type        | Description                       | Use case                              |
| ----------- | --------------------------------- | ------------------------------------- |
| `normal`    | Regular note (not highest/lowest) | Default                               |
| `max`       | Highest note in the piece         | Highlight highest pitch               |
| `min`       | Lowest note in the piece          | Highlight lowest pitch                |
| `match`     | Partial match (mic mode)          | Pitch roughly matches but not perfect |
| `match_all` | Perfect match (mic mode)          | Pitch and timing are both correct     |
| `unmatch`   | Mismatch (mic mode)               | Pitch does not match                  |

#### Bar parts

Each note type uses the following image parts. Bars are stretchable with three segments (left, middle, right).

##### Background parts (`back`)

| Part         | Example path                          | Description                      |
| ------------ | ------------------------------------- | -------------------------------- |
| `back_left`  | "images/bar/1_winered/back_left.png"  | Left edge of the bar background  |
| `back_mid`   | "images/bar/1_winered/back_mid.png"   | Middle (stretchable) background  |
| `back_right` | "images/bar/1_winered/back_right.png" | Right edge of the bar background |

##### Fill parts (`fill`)

| Part         | Example path                          | Description                      |
| ------------ | ------------------------------------- | -------------------------------- |
| `fill_left`  | "images/bar/1_winered/fill_left.png"  | Left edge of the fill (progress) |
| `fill_mid`   | "images/bar/1_winered/fill_mid.png"   | Middle (stretchable) fill        |
| `fill_right` | "images/bar/1_winered/fill_right.png" | Right edge of the fill           |

##### Passed parts (`passed`)

| Part           | Example path                            | Description                           |
| -------------- | --------------------------------------- | ------------------------------------- |
| `passed_left`  | "images/bar/1_winered/passed_left.png"  | Left edge after completion            |
| `passed_mid`   | "images/bar/1_winered/passed_mid.png"   | Middle (stretchable) after completion |
| `passed_right` | "images/bar/1_winered/passed_right.png" | Right edge after completion           |

##### Effect parts

| Part   | Example path                    | Description                         |
| ------ | ------------------------------- | ----------------------------------- |
| `glow` | "images/bar/1_winered/glow.png" | Glow effect shown when a bar passes |

---

## Customization examples

### Adding a new channel

For multi-part songs you can set different colors/designs per MIDI channel:

```json
{
  "bars": {
    "0": { "normal": { /* wine-red bar */ } },
    "1": { "normal": { /* blue bar */ } },
    "2": { "normal": { /* green bar */ } }
  }
}
```

### Bar designs for mic input

`match`, `match_all`, and `unmatch` are used in microphone input mode:

* **match_all**: Perfect singing → vivid gradient
* **match**: Almost correct → flat/single color
* **unmatch**: Out of pitch → warning color (e.g., red)

### Image specs

#### Recommended sizes

* **Bar part images**: Keep heights consistent. Left/right edge widths are fixed; the middle part can be 1px wide (it will be stretched).
* **now_bar**: Match `NOW_BAR_WIDTH` × `NOW_BAR_HEIGHT` in `settings.json`.
* **Icons**: Square sized according to `BAR_PASSED_COUNT_ICON_SIZE` in `settings.json`.

#### File formats

* PNG recommended (supports alpha/transparency).
* Use images with transparent background for nicer overlays.

### Notes

* Provide images for all required channels, types, and parts.
* Use relative paths from the project root.
* Missing images will cause errors at application startup.
* The widths of left/right bar parts are auto-adjusted by calculations inside `settings.json`.

---

## Karaoke subtitle generation settings: `lyrics_settings/settings_default.json`

### General subtitle settings

| Variable                                  | Type         | Description                                                                                |
| ----------------------------------------- | ------------ | ------------------------------------------------------------------------------------------ |
| `GENERAL.WIDTH`                           | int          | Image width for one subtitle line                                                          |
| `GENERAL.HEIGHT`                          | int          | Image height for one subtitle line                                                         |
| `GENERAL.X_BASE_INIT`                     | int          | Default X coordinate for the first character (origin = top-left of subtitle image)         |
| `GENERAL.Y_LYRIC`                         | int          | Y coordinate for the lyric (origin = top-left of subtitle image)                           |
| `GENERAL.Y_RUBY`                          | int          | Y coordinate for ruby/furigana                                                             |
| `GENERAL.COLOR_FILL_BEFORE`               | int[R,G,B,A] | Text color before wipe                                                                     |
| `GENERAL.COLOR_STROKE_FILL_BEFORE`        | int[R,G,B,A] | Outline color before wipe                                                                  |
| `GENERAL.COLOR_FILL_AFTER`                | int[R,G,B,A] | Text color after wipe                                                                      |
| `GENERAL.COLOR_STROKE_FILL_AFTER`         | int[R,G,B,A] | Outline color after wipe                                                                   |
| `GENERAL.COLOR_FILL_BEFORE_CHORUS`        | int[R,G,B,A] | Text color before wipe for chorus/response                                                 |
| `GENERAL.COLOR_STROKE_FILL_BEFORE_CHORUS` | int[R,G,B,A] | Outline color before wipe for chorus/response                                              |
| `GENERAL.COLOR_FILL_AFTER_CHORUS`         | int[R,G,B,A] | Text color after wipe for chorus/response                                                  |
| `GENERAL.COLOR_STROKE_FILL_AFTER_CHORUS`  | int[R,G,B,A] | Outline color after wipe for chorus/response                                               |
| `GENERAL.DISABLE_STROKE_ANTIALIASING`     | bool         | Disable stroke antialiasing (useful to avoid transparent outlines when layering subtitles) |

### Part/chorus mode settings

| Variable                                | Type               | Description                               |
| --------------------------------------- | ------------------ | ----------------------------------------- |
| `GENERAL.CHANGE_TO_CHORUS_STR`          | str[]              | Strings that trigger chorus/response mode |
| `GENERAL.CHANGE_TO_MAIN_STR`            | str[]              | Strings that return to main mode          |
| `GENERAL.CHANGE_TO_PART_STR`            | str[]              | Strings that trigger part-mode            |
| `GENERAL.PART_ICON`                     | str[]              | List of paths for part icons              |
| `GENERAL.PART_ICON_HEIGHT`              | int                | Height of part icon                       |
| `GENERAL.PART_ICON_OFFSET_X`            | int                | X offset for part icon                    |
| `GENERAL.PART_ICON_OFFSET_Y`            | int                | Y offset for part icon                    |
| `GENERAL.PART_ICON_MARGIN_X`            | int                | X margin for part icon                    |
| `GENERAL.COLOR_FILL_BEFORE_PART`        | list[int[R,G,B,A]] | Text colors (before wipe) for part mode   |
| `GENERAL.COLOR_STROKE_FILL_BEFORE_PART` | list[int[R,G,B,A]] | Stroke colors (before wipe) for part mode |
| `GENERAL.COLOR_FILL_AFTER_PART`         | list[int[R,G,B,A]] | Text colors (after wipe) for part mode    |
| `GENERAL.COLOR_STROKE_FILL_AFTER_PART`  | list[int[R,G,B,A]] | Stroke colors (after wipe) for part mode  |

### Subtitle display settings

| Variable                                 | Type               | Description                                      |
| ---------------------------------------- | ------------------ | ------------------------------------------------ |
| `GENERAL.DISPLAY_BEFORE_TIME`            | int (units: 10 ms) | Time to start showing text before wipe           |
| `GENERAL.DISPLAY_AFTER_TIME`             | int (units: 10 ms) | Residual time to show text after wipe            |
| `GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME` | int (units: 10 ms) | Threshold to judge continuous subtitle switching |
| `GENERAL.PROJECT_WIDTH`                  | int (px)           | Target video width                               |
| `GENERAL.PROJECT_HEIGHT`                 | int (px)           | Target video height                              |
| `GENERAL.PROJECT_MARGIN_X`               | int (px)           | X margin from left edge for subtitles            |
| `GENERAL.PROJECT_LYRIC_X_OVERLAP_FACTOR` | float              | Overlap factor when centering multi-line lyrics  |
| `GENERAL.PROJECT_Y_0_LYRIC`              | int (px)           | Y coordinate for line 1 lyrics                   |
| `GENERAL.PROJECT_Y_1_LYRIC`              | int (px)           | Y coordinate for line 2 lyrics                   |
| `GENERAL.PROJECT_Y_2_LYRIC`              | int (px)           | Y coordinate for line 3 lyrics                   |
| `GENERAL.PROJECT_Y_3_LYRIC`              | int (px)           | Y coordinate for line 4 lyrics                   |
| `GENERAL.PROJECT_Y_0_RUBY`               | int (px)           | Y coordinate for line 1 ruby                     |
| `GENERAL.PROJECT_Y_1_RUBY`               | int (px)           | Y coordinate for line 2 ruby                     |
| `GENERAL.PROJECT_Y_2_RUBY`               | int (px)           | Y coordinate for line 3 ruby                     |
| `GENERAL.PROJECT_Y_3_RUBY`               | int (px)           | Y coordinate for line 4 ruby                     |

### Lyric settings (`LYRIC.*`)

(Chorus/parenthetical lyrics can use `LYRIC_CHORUS.*` overrides.)

| Variable                                  | Type        | Description                                               |
| ----------------------------------------- | ----------- | --------------------------------------------------------- |
| `LYRIC.FONT_PATH`                         | str         | Path to lyric font                                        |
| `LYRIC.FONT_SIZE`                         | int (px)    | Font size                                                 |
| `LYRIC.STROKE_WIDTH`                      | int (px)    | Stroke width for outline                                  |
| `LYRIC.MARGIN_SPACE`                      | int (px)    | Margin for half-width spaces                              |
| `LYRIC.MARGIN_HALF`                       | int (px)    | Margin for half-width characters                          |
| `LYRIC.MARGIN_FULL`                       | int (px)    | Margin for full-width characters                          |
| `LYRIC.TEXT_WIDTH_MIN`                    | int (px)    | Minimum character width                                   |
| `LYRIC.Y_DRAW_OFFSET`                     | int (px)    | Y offset to correct font drawing alignment                |
| `LYRIC.ADJUST_WIPE_SPEED_THRESHOLD_S`     | float (sec) | Threshold time to adjust wipe speed between time tags     |
| `LYRIC.ADJUST_WIPE_SPEED_DIVISION_POINTS` | float[]     | Relative division points for wipe X coordinates           |
| `LYRIC.ADJUST_WIPE_SPEED_DIVISION_TIMES`  | float[]     | Relative division points for wipe times                   |
| `LYRIC.SYNC_WIPE_WITH_RUBY`               | bool        | If ruby has per-character wipes, sync lyric wipes to ruby |

### Ruby settings (`RUBY.*`)

(Chorus ruby can use `RUBY_CHORUS.*` overrides.)

| Variable                                 | Type        | Description                                     |
| ---------------------------------------- | ----------- | ----------------------------------------------- |
| `RUBY.FONT_PATH`                         | str         | Path to ruby font                               |
| `RUBY.FONT_SIZE`                         | int (px)    | Font size                                       |
| `RUBY.STROKE_WIDTH`                      | int (px)    | Stroke width                                    |
| `RUBY.MARGIN_SPACE`                      | int (px)    | Margin for half-width spaces                    |
| `RUBY.MARGIN_HALF`                       | int (px)    | Margin for half-width characters                |
| `RUBY.MARGIN_FULL`                       | int (px)    | Margin for full-width characters                |
| `RUBY.TEXT_WIDTH_MIN`                    | int (px)    | Minimum character width                         |
| `RUBY.Y_DRAW_OFFSET`                     | int (px)    | Y offset to correct drawing alignment           |
| `RUBY.ADJUST_WIPE_SPEED_THRESHOLD_S`     | float (sec) | Threshold to adjust wipe speed                  |
| `RUBY.ADJUST_WIPE_SPEED_DIVISION_POINTS` | float[]     | Relative division points for wipe X coordinates |
| `RUBY.ADJUST_WIPE_SPEED_DIVISION_TIMES`  | float[]     | Relative division points for wipe times         |

---

### About `ADJUST_WIPE_SPEED_XXX` parameters

* These parameters adjust wipe speed behavior when the time between time-tags is large (e.g., long tones) and a slow wipe would otherwise occur.
* They take effect when the interval to the next time-tag (in seconds) exceeds `ADJUST_WIPE_SPEED_THRESHOLD_S`.

![Wipe speed adjustment](./images/ui/ADJUST_WIPE_SPEED.jpg)
