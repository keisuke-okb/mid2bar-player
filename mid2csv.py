import py_midicsv as pm
import argparse
import pandas as pd
import os


def midi_to_csv(input_path):
    csv_string = pm.midi_to_csv(input_path, strict=False)
    df = pd.DataFrame([data.strip().split(", ") for data in csv_string]).applymap(
        lambda x: x.replace('"', "") if isinstance(x, str) else x
    )
    df = df.applymap(lambda x: x.replace('"', "") if isinstance(x, str) else x)
    df.loc[(df[2] == "Note_on_c") & (df[5] == "0"), 2] = "Note_off_c"
    df.loc[df.loc[df[2] == "End_track"].index[:-1], 2] = "End_track_others"
    return df


def get_time(x):
    m = int(x // 60)
    s = x - (m * 60)
    s_f = int(s // 1)
    ss = int((s - s_f) * 100)
    return f"{m:0d}:{s_f:02d}:{ss:02d}"


def convert(
    input_midi_path,
    output_note_path="./data/note.csv",
    output_marker_path="./data/marker.csv",
    output_text_path="./data/text.csv",
):
    os.makedirs(os.path.dirname(output_note_path), exist_ok=True)
    df = midi_to_csv(input_midi_path)
    df[1] = df[1].astype(int)

    # Convert MIDI data to custom data
    d = 0  # Duration for a quarter note
    beat_n, beat_b = 0, 0
    tempo = 0.0

    t_now_d = 0
    t_now_s = 0.0
    t_d_1bar = 0
    bar = 0

    bars_data = []

    # Extract info except notes
    for idx, row in df.iterrows():
        # ===== Header =====
        if row[2] == "Header":
            d = int(row[5])
            continue

        elif row[2] == "Title_t":
            title = str(row[3])
            continue

        # ===== Content =====
        if row[2] == "Tempo":
            tempo = float(60 / (int(row[3]) * (10**-6)))

        elif row[2] == "Time_signature":
            if t_d_1bar != 0:
                t_delta = int(row[1]) - t_now_d
                bars = t_delta // t_d_1bar
                for i in range(bars):
                    bar += 1
                    bars_data.append(
                        [bar, t_now_d + i * t_d_1bar, beat_n, beat_b, t_d_1bar]
                    )

            beat_n = int(row[3])
            beat_b = int(2 ** int(row[4]))
            t_d_1bar = int(d / (beat_b / 4) * beat_n)
            t_now_d = int(row[1])

        elif row[2] == "End_track":
            if t_d_1bar != 0:
                t_delta = int(row[1]) - t_now_d
                bars = t_delta // t_d_1bar
                for i in range(bars + 10):
                    bar += 1
                    bars_data.append(
                        [bar, t_now_d + i * t_d_1bar, beat_n, beat_b, t_d_1bar]
                    )

            t_now_d = int(row[1])
            break

    df_tempo = df[df[2] == "Tempo"].copy()
    df_tempo["v"] = df_tempo[3].apply(lambda x: round(60 / (int(x) * (10**-6)), 2))
    df_tempo = df_tempo[[1, "v"]].reset_index(drop=True)
    df_tempo["next_change"] = list(df_tempo[1].values[1:]) + [9999999]
    df_tempo["next_change"] = df_tempo["next_change"].astype(int)
    df_tempo[1] = df_tempo[1].astype(int)

    bars_tempo_data = []
    tempo = 0.0
    t_now_d = 0
    chou = 0
    major = 0

    for idx, tempo_data in df_tempo.iterrows():
        t_now_d = int(tempo_data[1])
        tempo = tempo_data["v"]
        next_change = tempo_data["next_change"]

        if not t_now_d in [data[1] for data in bars_data]:
            for i in range(len(bars_data)):
                if bars_data[i][1] > t_now_d:
                    bar_t = i - 1
                    break

            d_tick = bars_data[bar_t][4] / bars_data[bar_t][2]
            delta = t_now_d - bars_data[bar_t][1]
            ticks = int(delta // d_tick) + 1
            d_ = int(delta - ((ticks - 1) * d_tick))
            b_0 = bars_data[bar_t][0]
            b_1 = ticks
            bars_tempo_data.append(
                [
                    f"{b_0}.{b_1}.{d_}",
                    t_now_d,
                    *bars_data[bar_t][2:],
                    tempo,
                    chou,
                    major,
                ]
            )

        for bar_data in bars_data:
            if t_now_d <= bar_data[1] < next_change:
                if (
                    len(df[(df[1] == int(bar_data[1])) & (df[2] == "Key_signature")])
                    == 1
                ):
                    chou = int(
                        df[(df[1] == int(bar_data[1])) & (df[2] == "Key_signature")][
                            3
                        ].values[0]
                    )
                    major = df[
                        (df[1] == int(bar_data[1])) & (df[2] == "Key_signature")
                    ][4].values[0]
                bars_tempo_data.append(
                    [f"{bar_data[0]}.1.0", *bar_data[1:], tempo, chou, major]
                )

    bars_tempo_time_data = []
    t_now_s = 0.0

    for i in range(len(bars_tempo_data)):
        if i == 0:
            bars_tempo_time_data.append([*bars_tempo_data[i], 0.0])
            continue

        d_delta = bars_tempo_data[i][1] - bars_tempo_data[i - 1][1]
        tempo = bars_tempo_data[i - 1][5]

        haku = d_delta / d
        t_s_per_4 = 60.0 / tempo
        time = t_s_per_4 * haku
        t_now_s += time

        bars_tempo_time_data.append([*bars_tempo_data[i], t_now_s])

    df_hyousi_and_tempo = pd.DataFrame(
        bars_tempo_time_data,
        columns=["拍子位置", "時間", "拍子分子", "拍子分母", "1小節長さ", "テンポ", "調", "長調/短調", "絶対時間"],
    )

    def get_times_t_d(t_d):
        j_bar = 0
        j = 0
        for j in range(len(bars_tempo_time_data)):
            if bars_tempo_time_data[j][1] > t_d:
                j -= 1
                j_bar = j
                while not ".1.0" in bars_tempo_time_data[j_bar][0]:
                    j_bar -= 1
                break

        d_delta = t_d - bars_tempo_time_data[j][1]
        tempo = bars_tempo_time_data[j][5]
        haku = d_delta / d
        t_s_per_4 = 60.0 / tempo
        time_s = t_s_per_4 * haku

        t_zettai = bars_tempo_time_data[j][8] + time_s

        bar = bars_tempo_time_data[j_bar][0].replace(".1.0", "")
        d_delta = t_d - bars_tempo_time_data[j_bar][1]
        d_haku = bars_tempo_time_data[j_bar][4] / bars_tempo_time_data[j_bar][2]
        haku = int(d_delta // d_haku)
        remain = int(d_delta - (d_haku * haku))

        t_hyousi = f"{bar}.{haku+1}.{remain}"
        return t_zettai, t_hyousi

    # ===== Notes =====
    notes_data = []

    for _, row in df[df[2] == "Note_on_c"].iterrows():
        t_note_on = int(row[1])
        channel = int(row[3])
        pitch = int(row[4])

        for _, row2 in df[df[1] > t_note_on].iterrows():
            if int(row2[1]) <= t_note_on:
                continue
            elif (
                row2[2] == "Note_off_c"
                and int(row2[3]) == channel
                and int(row2[4]) == pitch
            ):
                t_note_off = int(row2[1])
                break

        t_zettai_note_on, hyousi_note_on = get_times_t_d(t_note_on)
        t_zettai_note_off, hyousi_note_off = get_times_t_d(t_note_off)

        pi_dict_normal = {
            0: "C",
            1: "C#",
            2: "D",
            3: "Eb",
            4: "E",
            5: "F",
            6: "F#",
            7: "G",
            8: "G#",
            9: "A",
            10: "Bb",
            11: "B",
        }
        pi_dict_sharp = {
            0: "C",
            1: "C#",
            2: "D",
            3: "D#",
            4: "E",
            5: "F",
            6: "F#",
            7: "G",
            8: "G#",
            9: "A",
            10: "A#",
            11: "B",
        }
        pi_dict_flat = {
            0: "C",
            1: "Db",
            2: "D",
            3: "Eb",
            4: "E",
            5: "F",
            6: "Gb",
            7: "G",
            8: "Ab",
            9: "A",
            10: "Bb",
            11: "B",
        }
        oc = pitch // 12 - 1

        _chou = df_hyousi_and_tempo[df_hyousi_and_tempo["時間"] <= t_note_on].iloc[-1][
            "調"
        ]
        if _chou > 0:
            pi_dict = pi_dict_sharp
        elif _chou < 0:
            pi_dict = pi_dict_flat
        else:
            pi_dict = pi_dict_normal

        pi = pi_dict[pitch % 12]

        notes_data.append(
            [
                t_note_on,
                t_note_off,
                hyousi_note_on,
                hyousi_note_off,
                t_zettai_note_on,
                t_zettai_note_off,
                oc,
                pi,
                pitch,
                channel,
            ]
        )

    df_notes = pd.DataFrame(notes_data)
    # channels = sorted(df_notes[9].unique()[:4])
    # df_notes[9] = df_notes[9].apply(lambda c: channels.index(c))
    df_notes.to_csv(output_note_path)

    # ===== Texts =====
    text_data = []
    for _, row in df[df[2] == "Text_t"].iterrows():
        t = int(row[1])
        text = row[3]
        t_zettai, hyousi = get_times_t_d(t)
        text_data.append([t, t_zettai, get_time(t_zettai), hyousi, text])
    pd.DataFrame(text_data).to_csv(output_text_path)

    # ===== Markers =====
    text_data = []
    for _, row in df[df[2] == "Marker_t"].iterrows():
        t = int(row[1])
        text = row[3]
        t_zettai, hyousi = get_times_t_d(t)
        text_data.append([t, t_zettai, get_time(t_zettai), hyousi, text])
    pd.DataFrame(text_data).to_csv(output_marker_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MIDI to CSV utility based on py_midicsv library"
    )
    parser.add_argument("-i", "--input", required=True, help="Input path")
    args = parser.parse_args()
    try:
        convert(args.input)
        print("Converted.")
    except Exception as e:
        print(e)
        print("Error has occered.")
