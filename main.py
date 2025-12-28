import os
from app import Mid2barPlayerApp

if __name__ == "__main__":
    splash_text = "作詞作曲：森田交一\nボーカル：詩歩、ベース&ギター：森田交一\n【音楽：魔王魂】"
    splash_image = "images/title/splash.png"
    title_image = "images/title/シャイニングスター.png"

    audio_path = "sample/【音楽：魔王魂】シャイニングスター（ショート）_inst.mp3"
    mid_path = "sample/【音楽：魔王魂】シャイニングスター（ショート）.mid"
    lrc_path = "sample/【音楽：魔王魂】シャイニングスター（ショート）.lrc"
    lrc_settings_path = f"./lyrics_settings/settings_default.json"
    video_paths = [
        "videos/green_pentagon.mp4",
        "videos/orange_square.mp4",
        "videos/red_star.mp4",
    ]

    app = Mid2barPlayerApp(
        audio_path,
        mid_path,
        lrc_path,
        lrc_settings_path,
        video_paths,
        video_fixed_fps=0,
        video_shuffle=False,
        credit_text=splash_text,
        splash_image=splash_image,
        title_image=title_image,
        enable_mic_input=False,
        mic_input_channel=0,
        record=False,
        settings_json_path="app_settings/settings.json",
        assets_json_path="app_settings/assets.json",
    )
    app.run()