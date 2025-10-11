#!/usr/bin/env python3
"""
保存された深度データの解析スクリプト

使い方: python3 analyze_depth.py <depth_raw_*.npy のパス>
"""

import numpy as np
import cv2
import sys
import os

def analyze_depth_data(npy_path):
    """深度データを解析して表示"""

    if not os.path.exists(npy_path):
        print(f"エラー: ファイルが見つかりません: {npy_path}")
        return

    # 深度データの読み込み
    depth_data = np.load(npy_path)

    print("=" * 60)
    print(f"深度データ解析: {os.path.basename(npy_path)}")
    print("=" * 60)

    # 基本情報
    print(f"\n[基本情報]")
    print(f"  形状: {depth_data.shape}")
    print(f"  データ型: {depth_data.dtype}")

    # 統計情報（0 を除外）
    valid_depths = depth_data[depth_data > 0]

    if len(valid_depths) > 0:
        print(f"\n[深度統計（単位: mm）]")
        print(f"  最小値: {valid_depths.min()} mm ({valid_depths.min()/1000:.3f} m)")
        print(f"  最大値: {valid_depths.max()} mm ({valid_depths.max()/1000:.3f} m)")
        print(f"  平均値: {valid_depths.mean():.1f} mm ({valid_depths.mean()/1000:.3f} m)")
        print(f"  中央値: {np.median(valid_depths):.1f} mm ({np.median(valid_depths)/1000:.3f} m)")
        print(f"  有効ピクセル数: {len(valid_depths)} / {depth_data.size} ({100*len(valid_depths)/depth_data.size:.1f}%)")

    # 画面中央の深度
    h, w = depth_data.shape
    center_depth = depth_data[h//2, w//2]
    print(f"\n[中央の深度]")
    print(f"  {center_depth} mm ({center_depth/1000:.3f} m)")

    # 深度ヒストグラム（簡易版）
    if len(valid_depths) > 0:
        print(f"\n[深度分布（単位: mm）]")
        bins = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, float('inf')]
        hist, _ = np.histogram(valid_depths, bins=bins)

        for i in range(len(hist)):
            if i < len(bins) - 2:
                range_str = f"{bins[i]:4.0f} - {bins[i+1]:4.0f}"
            else:
                range_str = f"{bins[i]:4.0f}+"

            bar_length = int(hist[i] / valid_depths.size * 50)
            bar = "█" * bar_length
            percentage = 100 * hist[i] / len(valid_depths)
            print(f"  {range_str} mm: {bar} {percentage:5.1f}%")

    # 可視化
    print(f"\n深度マップを表示中... (任意のキーで閉じる)")

    # カラーマップ適用
    depth_colormap = cv2.applyColorMap(
        cv2.convertScaleAbs(depth_data, alpha=0.03),
        cv2.COLORMAP_JET
    )

    # テキストオーバーレイ
    cv2.putText(depth_colormap, f"Min: {valid_depths.min() if len(valid_depths) > 0 else 0} mm",
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(depth_colormap, f"Max: {valid_depths.max() if len(valid_depths) > 0 else 0} mm",
               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(depth_colormap, f"Center: {center_depth} mm",
               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow('Depth Analysis', depth_colormap)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python3 analyze_depth.py <depth_raw_*.npy のパス>")
        print("\n例:")
        print("  python3 analyze_depth.py captured_images/depth_raw_20251010_120000.npy")
        sys.exit(1)

    analyze_depth_data(sys.argv[1])
