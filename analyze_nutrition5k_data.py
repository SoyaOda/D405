#!/usr/bin/env python3
"""
Nutrition5k形式データ解析ツール

nutrition5k_style_scanner.pyで保存したデータを解析・可視化

使い方: python3 analyze_nutrition5k_data.py [dish_id]
      または: python3 analyze_nutrition5k_data.py [食材名]
"""

import numpy as np
import cv2
import os
import sys
import glob

BASE_DIR = "/Users/moei/program/D405/nutrition5k_data/imagery/realsense_overhead"
DEPTH_SCALE_FACTOR = 10000  # 1m = 10,000 units
MAX_DEPTH_UNITS = 4000      # 0.4m

def load_metadata(metadata_path):
    """メタデータ読み込み"""
    if not os.path.exists(metadata_path):
        return None

    metadata = {}
    with open(metadata_path, 'r') as f:
        for line in f:
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()
    return metadata

def analyze_dish(dish_id):
    """個別dish解析"""
    print("=" * 70)
    print(f"Nutrition5k データ解析: {dish_id}")
    print("=" * 70)

    # ファイルパス
    rgb_path = os.path.join(BASE_DIR, f"rgb_{dish_id}.png")
    depth_raw_path = os.path.join(BASE_DIR, f"depth_raw_{dish_id}.png")
    depth_color_path = os.path.join(BASE_DIR, f"depth_colorized_{dish_id}.png")
    metadata_path = os.path.join(BASE_DIR, f"metadata_{dish_id}.txt")

    # 存在確認
    if not os.path.exists(depth_raw_path):
        print(f"エラー: {dish_id} が見つかりません")
        return

    # メタデータ表示
    metadata = load_metadata(metadata_path)
    if metadata:
        print("\n[メタデータ]")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

    # 画像読み込み
    rgb = cv2.imread(rgb_path)
    depth_raw = cv2.imread(depth_raw_path, cv2.IMREAD_ANYDEPTH)  # 16-bit
    depth_color = cv2.imread(depth_color_path)

    print(f"\n[画像情報]")
    print(f"  RGB形状: {rgb.shape}")
    print(f"  深度形状: {depth_raw.shape}")
    print(f"  深度データ型: {depth_raw.dtype}")

    # 深度統計（Nutrition5k形式: ユニット）
    valid_depths_units = depth_raw[depth_raw > 0]

    print(f"\n[深度統計（Nutrition5k形式）]")
    print(f"  深度エンコーディング: {DEPTH_SCALE_FACTOR} units/meter")
    if len(valid_depths_units) > 0:
        print(f"  最小: {valid_depths_units.min()} units ({valid_depths_units.min()/DEPTH_SCALE_FACTOR:.4f}m)")
        print(f"  最大: {valid_depths_units.max()} units ({valid_depths_units.max()/DEPTH_SCALE_FACTOR:.4f}m)")
        print(f"  平均: {valid_depths_units.mean():.1f} units ({valid_depths_units.mean()/DEPTH_SCALE_FACTOR:.4f}m)")
        print(f"  中央値: {np.median(valid_depths_units):.1f} units ({np.median(valid_depths_units)/DEPTH_SCALE_FACTOR:.4f}m)")
        print(f"  標準偏差: {valid_depths_units.std():.1f} units ({valid_depths_units.std()/DEPTH_SCALE_FACTOR:.4f}m)")
        print(f"  有効ピクセル率: {100*len(valid_depths_units)/depth_raw.size:.1f}%")

    # 深度分布ヒストグラム（メートル）
    valid_depths_m = valid_depths_units / DEPTH_SCALE_FACTOR

    print(f"\n[深度分布ヒストグラム（メートル）]")
    bins = [0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    hist, _ = np.histogram(valid_depths_m, bins=bins)

    for i in range(len(hist)):
        if hist[i] == 0:
            continue
        if i < len(bins) - 1:
            range_str = f"{bins[i]:.2f}-{bins[i+1]:.2f}"
        else:
            range_str = f"{bins[i]:.2f}+"

        bar_length = int(hist[i] / len(valid_depths_m) * 50)
        bar = "█" * bar_length
        percentage = 100 * hist[i] / len(valid_depths_m)
        print(f"  {range_str}m: {bar} {percentage:5.1f}%")

    # 可視化
    print(f"\n画像を表示中（任意のキーで閉じる）...")

    # 3画像を横並び
    h, w = rgb.shape[:2]
    if depth_color.shape[:2] != (h, w):
        depth_color = cv2.resize(depth_color, (w, h))

    # 統計オーバーレイ
    overlay = rgb.copy()
    y_pos = 30
    info_lines = [
        f"Dish: {dish_id}",
        f"Min: {valid_depths_units.min()}u ({valid_depths_units.min()/DEPTH_SCALE_FACTOR:.3f}m)",
        f"Max: {valid_depths_units.max()}u ({valid_depths_units.max()/DEPTH_SCALE_FACTOR:.3f}m)",
        f"Avg: {valid_depths_units.mean():.0f}u ({valid_depths_units.mean()/DEPTH_SCALE_FACTOR:.3f}m)",
        f"Valid: {100*len(valid_depths_units)/depth_raw.size:.1f}%"
    ]

    for line in info_lines:
        cv2.putText(overlay, line,
                   (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        y_pos += 25

    # 3画像結合
    combined = np.hstack([overlay, depth_color])

    # 画面中央に十字線
    h, w = depth_color.shape[:2]
    cv2.line(depth_color, (w//2 - 20, h//2), (w//2 + 20, h//2), (0, 255, 0), 2)
    cv2.line(depth_color, (w//2, h//2 - 20), (w//2, h//2 + 20), (0, 255, 0), 2)

    # ウィンドウ表示
    cv2.namedWindow('Nutrition5k Analysis', cv2.WINDOW_NORMAL)
    cv2.imshow('Nutrition5k Analysis', combined)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("=" * 70)

def list_dishes(food_name=None):
    """保存されたdishをリスト表示"""

    # 全dishを検索
    all_depths = sorted(glob.glob(os.path.join(BASE_DIR, "depth_raw_*.png")))

    if not all_depths:
        print("データが見つかりません")
        return []

    # dish_id抽出
    dish_ids = []
    for path in all_depths:
        filename = os.path.basename(path)
        dish_id = filename.replace('depth_raw_', '').replace('.png', '')

        # 食材名でフィルター
        if food_name and not dish_id.startswith(food_name):
            continue

        dish_ids.append(dish_id)

    if not dish_ids:
        print(f"食材 '{food_name}' のデータが見つかりません")
        return []

    print("=" * 70)
    if food_name:
        print(f"食材 '{food_name}' のdish一覧")
    else:
        print("全dishの一覧")
    print("=" * 70)

    for i, dish_id in enumerate(dish_ids, 1):
        # メタデータから情報取得
        metadata_path = os.path.join(BASE_DIR, f"metadata_{dish_id}.txt")
        metadata = load_metadata(metadata_path)

        print(f"\n[Dish {i}]")
        print(f"  ID: {dish_id}")
        if metadata:
            if 'Timestamp' in metadata:
                print(f"  タイムスタンプ: {metadata['Timestamp']}")
            if 'Frames Averaged' in metadata:
                print(f"  平均化フレーム数: {metadata['Frames Averaged']}")

    print("\n" + "=" * 70)
    print(f"総dish数: {len(dish_ids)}")
    print("=" * 70)

    return dish_ids

def main():
    if len(sys.argv) < 2:
        print("使い方: python3 analyze_nutrition5k_data.py [dish_id または 食材名]")
        print("\n例:")
        print("  python3 analyze_nutrition5k_data.py apple_20251010_120000")
        print("  python3 analyze_nutrition5k_data.py apple  # 食材名で検索")
        print("\n利用可能なデータ:")

        # 食材別にグループ化
        all_depths = sorted(glob.glob(os.path.join(BASE_DIR, "depth_raw_*.png")))
        foods = {}
        for path in all_depths:
            filename = os.path.basename(path)
            dish_id = filename.replace('depth_raw_', '').replace('.png', '')
            food = dish_id.split('_')[0]
            foods[food] = foods.get(food, 0) + 1

        for food, count in sorted(foods.items()):
            print(f"  - {food} ({count} dish)")

        sys.exit(1)

    arg = sys.argv[1]

    # dish_idとして直接指定された場合
    depth_path = os.path.join(BASE_DIR, f"depth_raw_{arg}.png")
    if os.path.exists(depth_path):
        analyze_dish(arg)
    else:
        # 食材名として検索
        dish_ids = list_dishes(arg)

        if dish_ids:
            print("\n解析したいdishを選択してください（番号入力、Enter=最新、'all'=全比較）:")
            choice = input("> ").strip()

            if choice.lower() == 'all':
                # 全dishの統計比較
                print("\n" + "=" * 70)
                print("全dish比較")
                print("=" * 70)
                for dish_id in dish_ids:
                    depth_raw = cv2.imread(os.path.join(BASE_DIR, f"depth_raw_{dish_id}.png"),
                                          cv2.IMREAD_ANYDEPTH)
                    valid = depth_raw[depth_raw > 0]
                    print(f"\n{dish_id}:")
                    print(f"  平均深度: {valid.mean()/DEPTH_SCALE_FACTOR:.4f}m")
                    print(f"  有効率: {100*len(valid)/depth_raw.size:.1f}%")

            elif choice == '' or choice == '0':
                analyze_dish(dish_ids[-1])  # 最新
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(dish_ids):
                        analyze_dish(dish_ids[idx])
                    else:
                        print("無効な番号")
                except ValueError:
                    print("無効な入力")

if __name__ == "__main__":
    main()
