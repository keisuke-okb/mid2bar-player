
def calc_margin_x(w, w1, w2, settings):
    if w1 + w2 >= w * settings.GENERAL.PROJECT_LYRIC_X_OVERLAP_FACTOR:
        return 0
    else:
        return (w * settings.GENERAL.PROJECT_LYRIC_X_OVERLAP_FACTOR - (w1 + w2)) // 2

def convert_x(x, settings):
    return int(x - settings.GENERAL.PROJECT_WIDTH // 2)

def divide_segments(x_start, x_end, division_points):
    total_ratio = sum(division_points)
    if total_ratio == 0:
        return [x_start, x_end]
    segment_length = (x_end - x_start) / total_ratio
    
    x_coords = [x_start]
    current_x = x_start
    
    for ratio in division_points:
        current_x += ratio * segment_length
        x_coords.append(current_x)
    
    return x_coords

def generate_lyrics_data(data, data_r, settings):
    assert len(data) == len(data_r)
    lyrics = []

    for i, (dc, dc_r) in enumerate(zip(data, data_r)):

        # background main lyric
        display_row = dc["display_row"]
        block_length = dc['block_length']
        block_start = dc["display_start_time"] / 100
        block_end = dc["display_end_time"] / 100

        x = settings.GENERAL.PROJECT_MARGIN_X

        if display_row == 0:
            y = settings.GENERAL.PROJECT_Y_0_LYRIC
            overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i + 1]["x_length"], dc["x_length"], settings)
            x = settings.GENERAL.PROJECT_MARGIN_X + overlap_margin_x

        elif display_row == 1:
            y = settings.GENERAL.PROJECT_Y_1_LYRIC
            if block_length == 3:
                overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i + 1]["x_length"], dc["x_length"], settings)
                x = settings.GENERAL.PROJECT_MARGIN_X + overlap_margin_x
            elif block_length == 4:
                overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i - 1]["x_length"], dc["x_length"], settings)
                x = settings.GENERAL.PROJECT_WIDTH - settings.GENERAL.PROJECT_MARGIN_X - dc["x_length"] - overlap_margin_x

        elif display_row == 2:
            y = settings.GENERAL.PROJECT_Y_2_LYRIC
            if block_length == 2 or block_length == 4:
                overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i + 1]["x_length"], dc["x_length"], settings)
                x = settings.GENERAL.PROJECT_MARGIN_X + overlap_margin_x
            elif block_length == 3:
                overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i - 1]["x_length"], dc["x_length"], settings)
                x = settings.GENERAL.PROJECT_WIDTH - settings.GENERAL.PROJECT_MARGIN_X - dc["x_length"] - overlap_margin_x

        elif display_row == 3:
            y = settings.GENERAL.PROJECT_Y_3_LYRIC
            if block_length == 1 or block_length == 3:
                x = settings.GENERAL.PROJECT_WIDTH / 2 - dc["x_length"] / 2
            elif block_length == 2 or block_length == 4:
                overlap_margin_x = calc_margin_x(settings.GENERAL.PROJECT_WIDTH, data[i - 1]["x_length"], dc["x_length"], settings)
                x = settings.GENERAL.PROJECT_WIDTH - settings.GENERAL.PROJECT_MARGIN_X - dc["x_length"] - overlap_margin_x

        background_main_lyric = {
            "x": x,
            "y": y,
            "image": dc["image_2"],
            "start": block_start,
            "end": block_end,
            "clip_up": settings.GENERAL.Y_LYRIC - settings.LYRIC.STROKE_WIDTH,
            "clip_bottom": 0,
            "x_wipes": [[block_start, block_end, 0, 0]]
        }

        # Front main lyric
        start_ = dc["display_start_time"] / 100
        end = dc["times"][0][0] / 100

        x_wipes = [[start_, end, 0, 0]]

        # Front main lyric chain
        for j in range(len(dc["times"]) - 1):

            delta_time_s = (dc["times"][j + 1][0] - dc["times"][j][0]) / 100
            
            if len(dc["times"][j]) == 1 and delta_time_s >= settings.LYRIC.ADJUST_WIPE_SPEED_THRESHOLD_S:
                # ルビの文字単位でのワイプ定義がない and ワイプ速度有効の場合：設定に沿ってワイプ速度を変更
                division_times = divide_segments(dc["times"][j][0], dc["times"][j + 1][0], settings.LYRIC.ADJUST_WIPE_SPEED_DIVISION_TIMES)
                division_xs = divide_segments(dc["x_start_lyric"][j][0], dc["x_end_lyric"][j][0], settings.LYRIC.ADJUST_WIPE_SPEED_DIVISION_POINTS)

                for k in range(len(division_times) - 1):
                    start = division_times[k] / 100
                    end = division_times[k + 1] / 100
                    left = division_xs[k] // 1
                    right = division_xs[k + 1] // 1
                    x_wipes.append([start, end, left, right])
            
            elif len(dc["times"][j]) > 1 and settings.LYRIC.SYNC_WIPE_WITH_RUBY:
                # ルビの文字単位でのワイプ定義がある and ルビ・歌詞のワイプ同期ONの場合：ルビのワイプに合わせて歌詞もワイプ

                _time_deltas = [
                    (dc["times"][j][k+1] if k+1 < len(dc["times"][j]) else dc["times"][j + 1][0]) - dc["times"][j][k]
                    for k in range(len(dc["times"][j]))
                ]
                _x_deltas = [
                    (dc["x_start_ruby"][j][k+1] if k+1 < len(dc["x_start_ruby"][j]) else dc["x_end_ruby"][j][-1]) - dc["x_start_ruby"][j][k]
                    for k in range(len(dc["x_start_ruby"][j]))
                ]

                division_times = divide_segments(dc["times"][j][0], dc["times"][j + 1][0], _time_deltas)
                division_xs = divide_segments(dc["x_start_lyric"][j][0], dc["x_end_lyric"][j][0], _x_deltas)

                for k in range(len(division_times) - 1):

                    _delta_time_s = (division_times[k + 1] - division_times[k]) / 100

                    # ルビの文字でワイプ速度有効の場合は、歌詞のワイプもルビに合わせる
                    if _delta_time_s >= settings.RUBY.ADJUST_WIPE_SPEED_THRESHOLD_S:
                        _division_times = divide_segments(division_times[k], division_times[k + 1], settings.RUBY.ADJUST_WIPE_SPEED_DIVISION_TIMES)
                        _division_xs = divide_segments(division_xs[k], division_xs[k + 1], settings.RUBY.ADJUST_WIPE_SPEED_DIVISION_POINTS)
                        
                        for l in range(len(_division_times) - 1):
                            start = _division_times[l] / 100
                            end = _division_times[l + 1] / 100
                            left = _division_xs[l] // 1
                            right = _division_xs[l + 1] // 1

                            x_wipes.append([start, end, left, right])
                        
                        continue

                    start = division_times[k] / 100
                    end = division_times[k + 1] / 100
                    left = division_xs[k] // 1
                    right = division_xs[k + 1] // 1
                    x_wipes.append([start, end, left, right])

            else:
                # ルビの文字単位でのワイプ定義がない or ワイプ速度調整無効の場合：等速でワイプ
                start = dc["times"][j][0] / 100
                end = dc["times"][j + 1][0] / 100
                left = dc["x_start_lyric"][j][0]
                right = dc["x_end_lyric"][j][0]

                x_wipes.append([start, end, left, right])

        front_main_lyric = {
            "x": x,
            "y": y,
            "image": dc["image_1"],
            "start": start_,
            "end": end,
            "clip_up": settings.GENERAL.Y_LYRIC - settings.LYRIC.STROKE_WIDTH,
            "clip_bottom": 0,
            "x_wipes": x_wipes
        }

        # back ruby
        display_row = dc_r["display_row"]
        if display_row == 0:
            y = settings.GENERAL.PROJECT_Y_0_RUBY
        elif display_row == 1:
            y = settings.GENERAL.PROJECT_Y_1_RUBY
        elif display_row == 2:
            y = settings.GENERAL.PROJECT_Y_2_RUBY
        elif display_row == 3:
            y = settings.GENERAL.PROJECT_Y_3_RUBY
        
        start = dc_r["display_start_time"]
        end = dc_r["display_end_time"]

        background_ruby = {
            "x": x,
            "y": y,
            "image": dc_r["image_2"],
            "start": dc_r["display_start_time"] / 100,
            "end": dc_r["display_end_time"] / 100,
            "clip_up": 0,
            "clip_bottom": settings.GENERAL.HEIGHT - (settings.GENERAL.Y_RUBY + settings.RUBY.FONT_SIZE + settings.RUBY.STROKE_WIDTH),
            "x_wipes": [[dc["display_start_time"] / 100, dc["display_end_time"] / 100, 0, 0]]
        }

        # Front ruby
        start_ = dc_r["display_start_time"] / 100
        end = dc_r["times"][0][0] / 100
        file = dc_r["image_1"]
        clip_up = 0
        clip_bottom = settings.GENERAL.HEIGHT - (settings.GENERAL.Y_RUBY + settings.RUBY.FONT_SIZE + settings.RUBY.STROKE_WIDTH)

        x_wipes = [[start_, end, 0, 0]]

        _dc_ruby = {
            "times": [x for sub in dc_r["times"] for x in sub],
            "x_start_ruby": [x for sub in dc_r["x_start_ruby"] for x in sub],
            "x_end_ruby": [x for sub in dc_r["x_end_ruby"] for x in sub],
        }

        # Front ruby chain
        for j in range(len(_dc_ruby["times"]) - 1):
            delta_time_s = (_dc_ruby["times"][j + 1] - _dc_ruby["times"][j]) / 100
            if delta_time_s >= settings.RUBY.ADJUST_WIPE_SPEED_THRESHOLD_S:
                division_times = divide_segments(_dc_ruby["times"][j], _dc_ruby["times"][j + 1], settings.RUBY.ADJUST_WIPE_SPEED_DIVISION_TIMES)
                division_xs = divide_segments(_dc_ruby["x_start_ruby"][j], _dc_ruby["x_end_ruby"][j], settings.RUBY.ADJUST_WIPE_SPEED_DIVISION_POINTS)

                for k in range(len(division_times) - 1):
                    start = division_times[k] / 100
                    end = division_times[k + 1] / 100
                    left = division_xs[k] // 1
                    right = division_xs[k + 1] // 1

                    x_wipes.append([start, end, left, right])

            else:
                start = _dc_ruby["times"][j] / 100
                end = _dc_ruby["times"][j + 1] / 100
                left = _dc_ruby["x_start_ruby"][j]
                right = _dc_ruby["x_end_ruby"][j]

                x_wipes.append([start, end, left, right])

        front_ruby = {
            "x": x,
            "y": y,
            "image": dc["image_1"],
            "start": start_,
            "end": end,
            "clip_up": 0,
            "clip_bottom": settings.GENERAL.HEIGHT - (settings.GENERAL.Y_RUBY + settings.RUBY.FONT_SIZE + settings.RUBY.STROKE_WIDTH),
            "x_wipes": x_wipes
        }

        lyrics.append({
            "lyric": "".join(["".join(l) for l in dc['lyrics']]),
            "display_row": display_row,
            "block_start": block_start,
            "block_end": block_end,
            "background_main_lyric": background_main_lyric,
            "front_main_lyric": front_main_lyric,
            "background_ruby": background_ruby,
            "front_ruby": front_ruby,
        })

    # 字幕表示時間調整
    lyric_types = ["background_main_lyric", "front_main_lyric", "background_ruby", "front_ruby"]

    for i, current_lyric in enumerate(lyrics):
        if current_lyric["display_row"] == 1:
            if i == 0 or lyrics[i - 1]["display_row"] != 0:
                next_block_start = None
                for j in range(i + 1, len(lyrics) - 1):
                    if lyrics[j]["display_row"] == 1:
                        next_block_start = lyrics[j]["block_start"]
                        break
                if next_block_start is None or lyrics[i + 1]["block_end"] <= next_block_start:
                    end = lyrics[i + 1]["block_end"]
                    current_lyric["block_end"] = end
                    for typ in ["background_main_lyric", "background_ruby"]:
                        current_lyric[typ]["end"] = end
                        current_lyric[typ]["x_wipes"][-1][1] = end

        elif current_lyric["display_row"] == 2:
            if i > 0 and lyrics[i - 1]["display_row"] == 1: # 上の行がある場合
                prev_block_end = 0
                for j in range(i - 1, -1, -1):
                    if lyrics[j]["display_row"] == 2:
                        prev_block_end = lyrics[j]["block_end"]
                        break
                start = max(lyrics[i - 1]["block_start"], prev_block_end)
                current_lyric["block_start"] = start
                for typ in lyric_types:
                    current_lyric[typ]["start"] = start
                    current_lyric[typ]["x_wipes"][0][0] = start

            if i == 0 or lyrics[i - 1]["display_row"] != 1:
                next_block_start = None
                for j in range(i + 1, len(lyrics) - 1):
                    if lyrics[j]["display_row"] == 2:
                        next_block_start = lyrics[j]["block_start"]
                        break

                if next_block_start is None or lyrics[i + 1]["block_end"] <= next_block_start:
                    end = lyrics[i + 1]["block_end"]
                    current_lyric["block_end"] = end
                    for typ in ["background_main_lyric", "background_ruby"]:
                        current_lyric[typ]["end"] = end
                        current_lyric[typ]["x_wipes"][-1][1] = end

        elif current_lyric["display_row"] == 3:
            if i > 0 and lyrics[i - 1]["display_row"] == 2: # 上の行がある場合
                prev_block_end = 0
                for j in range(i - 1, -1, -1):
                    if lyrics[j]["display_row"] == 3:
                        prev_block_end = lyrics[j]["block_end"]
                        break

                start = max(lyrics[i - 1]["block_start"], prev_block_end)
                current_lyric["block_start"] = start
                for typ in lyric_types:
                    current_lyric[typ]["start"] = start
                    current_lyric[typ]["x_wipes"][0][0] = start

    # フェードイン
    i = 0
    while i < len(lyrics):
        if lyrics[i]["display_row"] == 0: # 4行一斉表示
            if lyrics[i]["block_start"] == lyrics[i + 1]["block_start"] == lyrics[i + 2]["block_start"] == lyrics[i + 3]["block_start"]:
                for j in range(i, i + 4):
                    lyrics[j]["fade_in"] = {
                        "start": lyrics[j]["block_start"],
                        "end": lyrics[j]["block_start"] + settings.GENERAL.FADE_TIME / 100
                    }
            i += 4
        
        elif lyrics[i]["display_row"] == 1: # 3行一斉表示
            if (i == 0) or (lyrics[i - 1]["display_row"] != 0):
                if lyrics[i]["block_start"] == lyrics[i + 1]["block_start"] == lyrics[i + 2]["block_start"]:
                    for j in range(i, i + 3):
                        lyrics[j]["fade_in"] = {
                            "start": lyrics[j]["block_start"],
                            "end": lyrics[j]["block_start"] + settings.GENERAL.FADE_TIME / 100
                        }
            i += 3
        
        elif lyrics[i]["display_row"] == 2: # 2行一斉表示
            if (i == 0) or (lyrics[i - 1]["display_row"] != 1):
                if lyrics[i]["block_start"] == lyrics[i + 1]["block_start"]:
                    for j in range(i, i + 2):
                        lyrics[j]["fade_in"] = {
                            "start": lyrics[j]["block_start"],
                            "end": lyrics[j]["block_start"] + settings.GENERAL.FADE_TIME / 100
                        }
            i += 2

        elif lyrics[i]["display_row"] == 3:
            is_fadein = i == 0
            if i > 0 and lyrics[i - 1]["display_row"] != 2:
                prev_block_end = 0
                for j in range(i - 1, -1, -1):
                    if lyrics[j]["display_row"] == 3:
                        prev_block_end = lyrics[j]["block_end"]
                        break

                if prev_block_end < lyrics[i]["block_start"] - 0.1:
                    is_fadein = True

            if is_fadein:
                lyrics[i]["fade_in"] = {
                    "start": lyrics[i]["block_start"],
                    "end": lyrics[i]["block_start"] + settings.GENERAL.FADE_TIME / 100
                }
            i += 1

        else:
            raise ValueError(i)
        
    # フェードアウト
    for i in range(len(lyrics)):
        if lyrics[i]["display_row"] == 3:
            current_block_end = lyrics[i]["block_end"]
            next_block_start = 0
            for j in range(i + 1, len(lyrics) - 1):
                if lyrics[j]["display_row"] >= 0:
                    next_block_start = lyrics[j]["block_start"]
                    break
            
            if i == len(lyrics) - 1 or current_block_end + settings.GENERAL.FADE_TIME / 100 < next_block_start:
                new_end = current_block_end + settings.GENERAL.FADE_TIME / 100
                for j in range(i, -1, -1):
                    if lyrics[j]["block_end"] == current_block_end:
                        lyrics[j]["fade_out"] = {
                            "start": current_block_end,
                            "end": new_end
                        }
                        for typ in ["background_main_lyric", "background_ruby"]:
                            lyrics[j][typ]["end"] = new_end
                            lyrics[j][typ]["x_wipes"][-1][1] = new_end

    return lyrics