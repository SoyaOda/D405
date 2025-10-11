#!/usr/bin/env python3
"""
食材スキャンデータの解析・可視化スクリプト

使い方: python3 analyze_food_scan.py [食材名]
      または: python3 analyze_food_scan.py [food_scans/食材名/depth_raw_*.npy]
"""

import numpy as np
import cv2
import sys
import os
import glob
from datetime import datetime

SAVE_DIR = "/Users/moei/program/D405/food_scans"

def load_metadata(metadata_path):
    """メタデータファイルを読み込む"""
    if not os.path.exists(metadata_path):
        return None

    metadata = {}
    with open(metadata_path, 'r') as f:
        for line in f:
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

    return metadata

def analyze_food_scan(scan_path):
    """個別スキャンの詳細解析"""

    # パスから対応するファイルを特定
    base_path = scan_path.replace('depth_raw_', '').replace('.npy', '')
    timestamp = os.path.basename(base_path)

    dir_path = os.path.dirname(scan_path)
    food_name = os.path.basename(dir_path)

    color_path = os.path.join(dir_path, f"color_{timestamp}.png")
    depth_vis_path = os.path.join(dir_path, f"depth_vis_{timestamp}.png")
    metadata_path = os.path.join(dir_path, f"metadata_{timestamp}.txt")

    print("=" * 70)
    print(f"食材スキャン解析: {food_name}")
    print("=" * 70)

    # メタデータ表示
    metadata = load_metadata(metadata_path)
    if metadata:
        print("\n[メタデータ]")
        for key, value in metadata.items():
            print(f"  {key}: {value}")

    # 深度データ読み込み
    depth_data = np.load(scan_path)
    print(f"\n[深度データ解析]")
    print(f"  形状: {depth_data.shape}")
    print(f"  データ型: {depth_data.dtype}")

    # 統計情報
    valid_depths = depth_data[depth_data > 0]

    if len(valid_depths) > 0:
        print(f"\n[深度統計（生データ、単位: mm）]")
        print(f"  最小値: {valid_depths.min()} mm")
        print(f"  最大値: {valid_depths.max()} mm")
        print(f"  平均値: {valid_depths.mean():.1f} mm")
        print(f"  標準偏差: {valid_depths.std():.1f} mm")
        print(f"  中央値: {np.median(valid_depths):.1f} mm")
        print(f"  有効ピクセル率: {100*len(valid_depths)/depth_data.size:.1f}%")

    # 深度分布
    print(f"\n[深度分布ヒストグラム（単位: mm）]")
    bins = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500, float('inf')]
    hist, _ = np.histogram(valid_depths, bins=bins)

    for i in range(len(hist)):
        if hist[i] == 0:
            continue
        if i < len(bins) - 2:
            range_str = f"{bins[i]:3.0f}-{bins[i+1]:3.0f}"
        else:
            range_str = f"{bins[i]:3.0f}+"

        bar_length = int(hist[i] / len(valid_depths) * 50)
        bar = "█" * bar_length
        percentage = 100 * hist[i] / len(valid_depths)
        print(f"  {range_str} mm: {bar} {percentage:5.1f}%")

    # 画像の読み込みと表示
    print(f"\n画像を表示中... (任意のキーで閉じる)")

    color_img = cv2.imread(color_path) if os.path.exists(color_path) else None
    depth_vis = cv2.imread(depth_vis_path) if os.path.exists(depth_vis_path) else None

    if color_img is not None and depth_vis is not None:
        # 統計情報をオーバーレイ
        stats_overlay = color_img.copy()
        y_pos = 30

        info_lines = [
            f"Food: {food_name}",
            f"Min: {valid_depths.min():.0f}mm",
            f"Max: {valid_depths.max():.0f}mm",
            f"Avg: {valid_depths.mean():.1f}mm",
            f"Valid: {100*len(valid_depths)/depth_data.size:.1f}%"
        ]

        for line in info_lines:
            cv2.putText(stats_overlay, line,
                       (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_pos += 30

        # 横に並べて表示
        combined = np.hstack([stats_overlay, depth_vis])
        cv2.imshow('Food Scan Analysis - Color | Depth', combined)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    print("=" * 70)

def list_food_scans(food_name):
    """特定の食材のすべてのスキャンをリスト表示"""
    food_dir = os.path.join(SAVE_DIR, food_name)

    if not os.path.exists(food_dir):
        print(f"エラー: 食材 '{food_name}' のスキャンが見つかりません")
        print(f"保存先: {SAVE_DIR}")
        return []

    scan_files = sorted(glob.glob(os.path.join(food_dir, "depth_raw_*.npy")))

    if not scan_files:
        print(f"'{food_name}' のスキャンデータが見つかりません")
        return []

    print("=" * 70)
    print(f"食材 '{food_name}' のスキャン一覧")
    print("=" * 70)

    for i, scan_file in enumerate(scan_files, 1):
        timestamp = os.path.basename(scan_file).replace('depth_raw_', '').replace('.npy', '')
        file_size = os.path.getsize(scan_file) / 1024  # KB

        # メタデータから情報取得
        metadata_path = scan_file.replace('depth_raw_', 'metadata_').replace('.npy', '.txt')
        metadata = load_metadata(metadata_path)

        print(f"\n[スキャン {i}]")
        print(f"  ファイル: {os.path.basename(scan_file)}")
        print(f"  タイムスタンプ: {timestamp}")
        print(f"  サイズ: {file_size:.1f} KB")

        if metadata and '撮影日時' in metadata:
            print(f"  撮影日時: {metadata['撮影日時']}")

    print("\n" + "=" * 70)
    print(f"総スキャン数: {len(scan_files)}")
    print("=" * 70)

    return scan_files

def compare_scans(scan_files):
    """複数のスキャンを比較"""
    if len(scan_files) < 2:
        print("比較するには2つ以上のスキャンが必要です")
        return

    print("\n" + "=" * 70)
    print("スキャン比較")
    print("=" * 70)

    depths_data = []
    for scan_file in scan_files:
        depth_data = np.load(scan_file)
        valid_depths = depth_data[depth_data > 0]
        depths_data.append(valid_depths)

        timestamp = os.path.basename(scan_file).replace('depth_raw_', '').replace('.npy', '')
        print(f"\n{timestamp}:")
        print(f"  平均深度: {valid_depths.mean():.1f} mm")
        print(f"  標準偏差: {valid_depths.std():.1f} mm")
        print(f"  有効ピクセル率: {100*len(valid_depths)/depth_data.size:.1f}%")

    print("\n" + "=" * 70)

def main():
    if len(sys.argv) < 2:
        print("使い方: python3 analyze_food_scan.py [食材名]")
        print("       または: python3 analyze_food_scan.py [スキャンファイルのパス]")
        print("\n例:")
        print("  python3 analyze_food_scan.py apple")
        print("  python3 analyze_food_scan.py food_scans/apple/depth_raw_20251010_120000.npy")
        print("\n利用可能な食材:")

        if os.path.exists(SAVE_DIR):
            foods = [d for d in os.listdir(SAVE_DIR) if os.path.isdir(os.path.join(SAVE_DIR, d))]
            for food in sorted(foods):
                scan_count = len(glob.glob(os.path.join(SAVE_DIR, food, "depth_raw_*.npy")))
                print(f"  - {food} ({scan_count} スキャン)")

        sys.exit(1)

    arg = sys.argv[1]

    # .npy ファイルのパスが指定された場合
    if arg.endswith('.npy') and os.path.exists(arg):
        analyze_food_scan(arg)

    # 食材名が指定された場合
    else:
        scan_files = list_food_scans(arg)

        if scan_files:
            print("\n解析したいスキャンを選択してください（番号を入力、Enter で最新、'all' で比較）:")
            choice = input("> ").strip()

            if choice.lower() == 'all':
                compare_scans(scan_files)
            elif choice == '' or choice == '0':
                analyze_food_scan(scan_files[-1])  # 最新
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(scan_files):
                        analyze_food_scan(scan_files[idx])
                    else:
                        print("無効な番号です")
                except ValueError:
                    print("無効な入力です")

if __name__ == "__main__":
    main()
