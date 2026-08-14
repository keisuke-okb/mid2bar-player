def calc_display_time(data, settings):
    """
    データのブロックの長さとタイミングに基づいて、各データの表示開始時間と終了時間、表示行を計算します。

    各データには、「times」（タイムスタンプのリスト）、「block_length」（ブロック全体の長さ）、
    「block_current」（現在のブロックのインデックス）が含まれており、これに基づいて時間の調整が行われます。

    設定値として、「DISPLAY_BEFORE_TIME」（表示開始前の調整時間）、「DISPLAY_AFTER_TIME」（表示終了後の調整時間）、
    「DISPLAY_CONNECT_THRESHOLD_TIME」（隣接するブロックと連結するかを判断するための閾値）などが用いられます。

    各ブロックの位置や表示の競合を避けるために、最大4つの行（0～3行）にデータを割り当て、行ごとに時間調整を行います。

    Args:
        data (list): 各ブロックに関する情報を持つ辞書のリスト
        settings (object): 設定オブジェクト

    Returns:
        list: 各ブロックに追加情報（display_start_time、display_end_time、display_row）を持つ更新済みデータ。
    """
    time_pos = [-1, -1, -1, -1]

    def adjust_block_start_time(index, start, display_row):
        """Prevent an upper row of a new block from appearing too early."""
        if index == 0 or data[index]["block_current"] != 1:
            return start

        previous_index = index - 1
        previous_block_start_index = (
            previous_index - data[previous_index]["block_current"] + 1
        )
        previous_display_row = 4 - data[previous_index]["block_length"]

        # Only constrain transitions to a block that starts on a higher row.
        if display_row >= previous_display_row:
            return start

        delay_s = getattr(settings.GENERAL, "DISPLAY_BLOCK_START_DELAY_S", 0.0) or 0.0
        previous_singing_start = data[previous_block_start_index]["times"][0][0]
        minimum_start = previous_singing_start + max(0, delay_s) * 1000
        return max(start, minimum_start)
    for i in range(len(data)):
        if data[i]["block_length"] == 1:
            display_start_time = (
                data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
            )
            if display_start_time < time_pos[3]:
                display_start_time = time_pos[3]
            elif (
                display_start_time - time_pos[3]
                <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
            ):
                display_start_time = time_pos[3]
            if display_start_time < 0:
                display_start_time = 0
            display_start_time = adjust_block_start_time(i, display_start_time, 3)
            display_end_time = (
                data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
            )
            data[i]["display_start_time"] = display_start_time
            data[i]["display_end_time"] = display_end_time
            data[i]["display_row"] = 3
            time_pos[3] = display_end_time

        elif data[i]["block_length"] == 2:
            if data[i]["block_current"] == 1:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[2]:
                    display_start_time = time_pos[2]
                # elif display_start_time - time_pos[2] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[2]
                if display_start_time < 0:
                    display_start_time = 0
                display_start_time = adjust_block_start_time(i, display_start_time, 2)
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 2
                time_pos[2] = display_end_time

            else:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[3]:
                    display_start_time = time_pos[3]
                elif (
                    display_start_time - time_pos[3]
                    <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
                ):
                    display_start_time = time_pos[3]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[3] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 3
                time_pos[3] = display_end_time

        elif data[i]["block_length"] == 3:
            if data[i]["block_current"] == 1:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[1]:
                    display_start_time = time_pos[1]
                # elif display_start_time - time_pos[1] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[1]
                if display_start_time < 0:
                    display_start_time = 0
                display_start_time = adjust_block_start_time(i, display_start_time, 1)
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 1
                time_pos[1] = display_end_time

            elif data[i]["block_current"] == 2:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[2]:
                    display_start_time = time_pos[2]
                # elif display_start_time - time_pos[2] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[2]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[2] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )

                # Adjast start time over rows
                if time_pos[2] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]

                elif (
                    data[i - 1]["display_start_time"] < time_pos[2]
                    and display_start_time - time_pos[2]
                    <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
                    and time_pos[2] < data[i - 1]["times"][0][0]
                ):
                    data[i - 1]["display_start_time"] = time_pos[2]
                    display_start_time = time_pos[2]

                elif (
                    data[i - 1]["display_start_time"] < display_start_time
                    and display_start_time < data[i - 1]["times"][0][0]
                ):
                    data[i - 1]["display_start_time"] = display_start_time

                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 2
                time_pos[2] = display_end_time

            else:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[3]:
                    display_start_time = time_pos[3]
                elif (
                    display_start_time - time_pos[3]
                    <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
                ):
                    display_start_time = time_pos[3]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[3] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 3
                time_pos[3] = display_end_time

        elif data[i]["block_length"] == 4:
            if data[i]["block_current"] == 1:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[0]:
                    display_start_time = time_pos[0]
                # elif display_start_time - time_pos[0] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[0]
                if display_start_time < 0:
                    display_start_time = 0
                display_start_time = adjust_block_start_time(i, display_start_time, 0)
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 0
                time_pos[0] = display_end_time

            elif data[i]["block_current"] == 2:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[1]:
                    display_start_time = time_pos[1]
                # elif display_start_time - time_pos[1] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[1]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[1] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )

                # Adjast start time over rows
                if time_pos[1] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]

                elif (
                    data[i - 1]["display_start_time"] < time_pos[1]
                    and display_start_time - time_pos[1]
                    <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
                    and time_pos[1] < data[i - 1]["times"][0][0]
                ):
                    data[i - 1]["display_start_time"] = time_pos[1]
                    display_start_time = time_pos[1]

                elif (
                    data[i - 1]["display_start_time"] < display_start_time
                    and display_start_time < data[i - 1]["times"][0][0]
                ):
                    data[i - 1]["display_start_time"] = display_start_time

                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 1
                time_pos[1] = display_end_time

            elif data[i]["block_current"] == 3:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[2]:
                    display_start_time = time_pos[2]
                # elif display_start_time - time_pos[2] <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME:
                #     display_start_time = time_pos[2]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[2] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 2
                time_pos[2] = display_end_time

            else:
                display_start_time = (
                    data[i]["times"][0][0] - settings.GENERAL.DISPLAY_BEFORE_TIME
                )
                if display_start_time < time_pos[3]:
                    display_start_time = time_pos[3]
                elif (
                    display_start_time - time_pos[3]
                    <= settings.GENERAL.DISPLAY_CONNECT_THRESHOLD_TIME
                ):
                    display_start_time = time_pos[3]
                if display_start_time < 0:
                    display_start_time = 0
                if time_pos[3] < data[i - 1]["display_start_time"]:
                    display_start_time = data[i - 1]["display_start_time"]
                display_end_time = (
                    data[i]["times"][-1][0] + settings.GENERAL.DISPLAY_AFTER_TIME
                )
                data[i]["display_start_time"] = display_start_time
                data[i]["display_end_time"] = display_end_time
                data[i]["display_row"] = 3
                time_pos[3] = display_end_time

        else:
            raise NotImplementedError(
                f"Not supported block_length: {data[i]['block_length']}"
            )

    # Row-order constraints can delay a short lyric past its natural end.
    # Never emit an inverted display interval.
    for entry in data:
        if entry["display_start_time"] > entry["display_end_time"]:
            entry["display_start_time"] = entry["display_end_time"]

    return data
