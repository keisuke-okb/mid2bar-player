from PIL import Image
import numpy as np
import os
import argparse
from tqdm import tqdm


def is_within_color_range(pixel_array, target_color, tolerance):
    """
    ピクセルが指定された色範囲内かどうかをチェックする関数。
    tolerance: 0～1で許容範囲を設定
    """
    # RGB各色について許容範囲内かどうかをベクトル化して判定
    diff = np.abs(pixel_array - target_color) / 255.0
    return np.all(diff <= tolerance, axis=-1)


def apply_color_mask_and_overlay(img_a, img_b, target_color, tolerance=0.1):
    """
    透過PNG画像Aの特定の色の領域をマスクし、画像Bをその領域に重ねて新しい画像Cを作成する関数。
    :param img_a: 画像A
    :param img_b: 画像B
    :param target_color: 色範囲に一致するRGBのタプル (r, g, b)
    :param tolerance: 色の許容範囲 (0～1)
    :return: 新しい透過PNG画像
    """
    # 画像AとBを読み込む
    # img_a = Image.open(image_a_path).convert("RGBA")
    # img_b = Image.open(image_b_path).convert("RGBA")

    # 画像AとBのサイズが一致することを確認
    if img_a.size != img_b.size:
        raise ValueError("画像Aと画像Bのサイズが一致していません")

    # 画像Aのピクセルデータを取得
    img_a_data = np.array(img_a)
    img_b_data = np.array(img_b)

    # 画像Aの透明度が0でない領域をマスクし、指定色範囲に一致する領域を見つける
    alpha_mask = img_a_data[:, :, 3] > 0  # 透過していない部分
    color_mask = is_within_color_range(img_a_data[:, :, :3], target_color, tolerance)

    # 両方の条件（透過していない + 色範囲一致）を満たす領域を選択
    combined_mask = np.logical_and(alpha_mask, color_mask)

    # 画像Aの指定領域を画像Bで置き換える
    img_c_data = img_a_data.copy()
    img_c_data[combined_mask] = img_b_data[combined_mask]

    # 結果を新しい画像として保存
    img_c = Image.fromarray(img_c_data)
    return img_c

    # # 新しい画像Cを作成 (画像Aをベースにする)
    # img_c_data = img_a_data.copy()

    # # 画像Aのピクセルをチェックして、指定された色に一致する領域を見つける
    # for y in range(img_a_data.shape[0]):
    #     for x in range(img_a_data.shape[1]):
    #         pixel = img_a_data[y, x]
    #         # ピクセルのアルファ値を確認し、透明でない場合にのみ処理
    #         if pixel[3] > 0:  # 透過していない部分
    #             if is_within_color_range(pixel[:3], target_color, tolerance):
    #                 # 対象の色に一致する場合、画像Bの同じ位置を上書き
    #                 img_c_data[y, x] = img_b_data[y, x]

    # # 結果を新しい画像として保存
    # img_c = Image.fromarray(img_c_data)
    # return img_c


def test():
    # 使用例
    image_a_path = 'path_to_image_a.png'  # 透過PNG画像Aのパス
    image_b_path = 'path_to_image_b.png'  # 置き換え用PNG画像Bのパス
    target_color = (255, 0, 0)  # 置き換え対象の色 (RGB)
    tolerance = 0.1  # 色の許容範囲 (0～1)

    # 新しい画像Cを作成
    new_image = apply_color_mask_and_overlay(image_a_path, image_b_path, target_color, tolerance)

    # 結果を保存
    new_image.save('output_image.png')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LRC2EXO-Python Synthesis')
    parser.add_argument('--input_dir', type=str, required=True, help='歌詞画像のパス')
    parser.add_argument('--output_dir', type=str, default='output_synthesis', help='出力ディレクトリのパス')
    parser.add_argument('--before', action="store_true")
    parser.add_argument('--after', action="store_true")

    target_colors_before = [[255, 0, 0], [0, 255, 0]]
    target_colors_after = [[255, 0, 0], [0, 255, 0]]
    overlay_image_paths_before = ["./images/fill_before_himari_mitsuki.png", "./images/fill_before_himari_mitsuki_tsumugi.png"]
    overlay_image_paths_after = ["./images/fill_after_himari_mitsuki.png", "./images/fill_after_himari_mitsuki_tsumugi.png"]
    tolerance = 0.6  # 色の許容範囲 (0～1)

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    
    images = [f for f in os.listdir(args.input_dir) if f.endswith(".png")]
    for image in tqdm(images):
        src_image_path = os.path.join(args.input_dir, image)
        dst_image_path = os.path.join(args.output_dir, image)

        img_a = Image.open(src_image_path).convert("RGBA")
        
        # 新しい画像Cを作成
        if image.endswith("_1.png") and args.before:
            img_a = Image.open(src_image_path).convert("RGBA")
            for i in range(len(target_colors_before)):
                img_b = Image.open(overlay_image_paths_before[i]).convert("RGBA")
                img_a = apply_color_mask_and_overlay(img_a, img_b, target_colors_before[i], tolerance)

        elif args.after:
            img_a = Image.open(src_image_path).convert("RGBA")
            for i in range(len(target_colors_after)):
                img_b = Image.open(overlay_image_paths_after[i]).convert("RGBA")
                img_a = apply_color_mask_and_overlay(img_a, img_b, target_colors_after[i], tolerance)

        # 結果を保存
        img_a.save(dst_image_path)

