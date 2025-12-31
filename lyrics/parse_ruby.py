import re
import sys


def parse_ruby_definitions(lines):
    ruby_defs = []
    for line in lines:
        if line.startswith("@Ruby"):
            # Format: @RubyN=base,ruby,[start],[end]
            _, rest = line.split("=", 1)
            parts = rest.strip().split(",")
            base = parts[0]
            ruby_text = parts[1]
            start = parts[2] if len(parts) > 2 and parts[2] else "00:00:00"
            end = parts[3] if len(parts) > 3 and parts[3] else "99:59:99"
            ruby_defs.append(
                {"base": base, "ruby": ruby_text, "start": start, "end": end}
            )
    return ruby_defs


def process_line(line, ruby_defs):
    # 同一タイムタグの重複を除去するユーティリティ
    def collapse_tags(s):
        return re.sub(r"(\[[0-9]{2}:[0-9]{2}:[0-9]{2}\])(?:\1)+", r"\1", s)

    processed = line
    for rd in ruby_defs:
        base = rd["base"]
        # base の各文字前にタイムタグがあってもマッチ
        pattern = "".join(r"(?:\[[^\]]+\])*" + re.escape(ch) for ch in base)
        regex = re.compile(pattern)

        def repl(m):
            span = m.group(0)
            tags = re.findall(r"\[[^\]]+\]", span)
            start_tag = tags[0] if tags else ""
            rest = processed[m.end() :]
            m2 = re.search(r"\[[^\]]+\]", rest)
            end_tag = m2.group(0) if m2 else ""
            return f"{start_tag}{base}{end_tag}"

        # 最初のひとつを置換
        processed = regex.sub(repl, processed, count=1)
    # 重複タグは collapse_tags でまとめる
    processed = collapse_tags(processed)
    return processed


def main(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ruby_defs = parse_ruby_definitions(lines)

    with open(output_file, "w", encoding="utf-8") as f:
        for line in lines:
            # 改行文字を残したまま処理
            if line.startswith("@Ruby"):
                f.write(line)
            else:
                text = line.rstrip("\n")
                # 空行はそのまま
                if not text:
                    f.write("\n")
                else:
                    processed = process_line(text, ruby_defs)
                    f.write(processed + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ruby_processor.py input.txt output.txt")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
