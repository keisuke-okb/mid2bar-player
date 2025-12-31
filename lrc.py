import json
import os
import argparse
import chardet
from tqdm import tqdm

import lyrics


def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)

    encoding = result["encoding"]
    return encoding


def generate_lyrics(
    input_lrc_path,
    settings_path,
    json_output_path=None,
):
    with open(settings_path, "r", encoding=detect_encoding(settings_path)) as f:
        settings = json.load(f, object_hook=lyrics.DotDict)

    output_dir = (
        f"./lyrics_images/{os.path.splitext(os.path.basename(input_lrc_path))[0]}/"
    )
    os.makedirs(output_dir, exist_ok=True)

    lrc_org_data = open(
        input_lrc_path, "r", encoding=detect_encoding(input_lrc_path)
    ).readlines()
    is_extended_lrc = any(["@Ruby" in l for l in lrc_org_data])
    data = lyrics.lrc_tools.parse_lrc_texts(lrc_org_data)

    if is_extended_lrc:
        lyrics.lrc_tools.parse_complex_lyrics(
            open(
                input_lrc_path, "r", encoding=detect_encoding(input_lrc_path)
            ).readlines(),
            "./data/lyrics.lrc",
        )
        data_r = lyrics.lrc_tools.parse_lrc_texts(
            open(
                "./data/lyrics.lrc", "r", encoding=detect_encoding(input_lrc_path)
            ).readlines()
        )

        for i, seg in enumerate(tqdm(data)):
            d = lyrics.text_tools.draw_lyric_image_with_ruby(
                data=seg,
                settings=settings,
                output_path_1=os.path.join(output_dir, f"{i:04d}_1.png"),
                output_path_2=os.path.join(output_dir, f"{i:04d}_2.png"),
            )
            data[i] = d

        for i, seg in enumerate(tqdm(data_r)):
            d = lyrics.text_tools.draw_lyric_image_with_ruby(
                data=seg,
                settings=settings,
                output_path_1=os.path.join(output_dir, f"{i:04d}_1.png"),
                output_path_2=os.path.join(output_dir, f"{i:04d}_2.png"),
            )
            data_r[i] = d

        data = lyrics.time_tools.calc_display_time(data, settings=settings)
        data_r = lyrics.time_tools.calc_display_time(data_r, settings=settings)

        if json_output_path is not None:
            with open(json_output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        lyrics_data = lyrics.display_tools.generate_lyrics_data(
            data, data_r, settings=settings
        )

        if json_output_path is not None:
            with open(json_output_path, "w", encoding="utf-8") as f:
                json.dump(lyrics_data, f, ensure_ascii=False, indent=4)

    else:
        for i, seg in enumerate(tqdm(data)):
            d = lyrics.text_tools.draw_lyric_image_with_ruby(
                data=seg,
                settings=settings,
                output_path_1=os.path.join(output_dir, f"{i:04d}_1.png"),
                output_path_2=os.path.join(output_dir, f"{i:04d}_2.png"),
            )
            data[i] = d

        data = lyrics.time_tools.calc_display_time(data, settings=settings)
        lyrics_data = lyrics.display_tools.generate_lyrics_data(
            data, data, settings=settings
        )

        if json_output_path is not None:
            with open(json_output_path, "w", encoding="utf-8") as f:
                json.dump(lyrics_data, f, ensure_ascii=False, indent=4)

    return lyrics_data


def load_lyrics(input_lrc_path, settings_path, json_output_path):
    if os.path.exists(json_output_path):
        data = json.loads(open(json_output_path, "r", encoding="utf-8").read())

    else:
        data = generate_lyrics(input_lrc_path, settings_path, json_output_path)

    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LRC2EXO-Python")
    parser.add_argument(
        "--input_lrc_path", type=str, required=True, help="Lyrics file path"
    )
    parser.add_argument(
        "--settings_path", type=str, default="settings.json", help="Settings file path"
    )
    parser.add_argument(
        "--json_output_path", type=str, default=None, help="Output path"
    )

    args = parser.parse_args()
    generate_lyrics(**vars(args))
