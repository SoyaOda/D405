#!/usr/bin/env python3
"""
アライメント精度検証スクリプト

カラー画像と深度画像の位置合わせ精度を視覚的に確認する
使い方: sudo /Users/moei/program/D405/venv/bin/python3 test_alignment.py
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
from datetime import datetime

SAVE_DIR = "/Users/moei/program/D405/alignment_test"
os.makedirs(SAVE_DIR, exist_ok=True)

def test_alignment():
    print("=" * 70)
    print("RealSense D405 アライメント精度検証")
    print("=" * 70)

    # パイプライン設定
    pipeline = rs.pipeline()
    config = rs.config()
    # 1280x720: FOVが一致、最高品質
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    print("\nパイプライン開始...")
    profile = pipeline.start(config)

    # アライメントオブジェクト作成
    align_to_color = rs.align(rs.stream.color)

    # ウォームアップ
    for _ in range(30):
        pipeline.wait_for_frames()

    print("フレーム取得中...")

    try:
        # テスト1: アライメントなし
        frames = pipeline.wait_for_frames()
        depth_frame_raw = frames.get_depth_frame()
        color_frame_raw = frames.get_color_frame()

        depth_raw = np.asanyarray(depth_frame_raw.get_data())
        color_raw = np.asanyarray(color_frame_raw.get_data())

        # テスト2: アライメントあり
        aligned_frames = align_to_color.process(frames)
        aligned_depth_frame = aligned_frames.get_depth_frame()
        aligned_color_frame = aligned_frames.get_color_frame()

        depth_aligned = np.asanyarray(aligned_depth_frame.get_data())
        color_aligned = np.asanyarray(aligned_color_frame.get_data())

        # 深度スケール取得
        depth_sensor = profile.get_device().first_depth_sensor()
        depth_scale = depth_sensor.get_depth_scale()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # === 保存1: アライメントなし ===
        print("\n[アライメントなし]")
        print(f"  深度サイズ: {depth_raw.shape}")
        print(f"  カラーサイズ: {color_raw.shape}")

        depth_colormap_raw = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_raw, alpha=0.03),
            cv2.COLORMAP_JET
        )

        # サイズ調整が必要な場合
        if color_raw.shape[:2] != depth_colormap_raw.shape[:2]:
            depth_colormap_raw = cv2.resize(
                depth_colormap_raw,
                (color_raw.shape[1], color_raw.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

        combined_raw = np.hstack([color_raw, depth_colormap_raw])
        cv2.putText(combined_raw, "WITHOUT Alignment",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        path_raw = os.path.join(SAVE_DIR, f"no_align_{timestamp}.png")
        cv2.imwrite(path_raw, combined_raw)
        print(f"  保存: {path_raw}")

        # === 保存2: アライメントあり ===
        print("\n[アライメントあり]")
        print(f"  深度サイズ: {depth_aligned.shape}")
        print(f"  カラーサイズ: {color_aligned.shape}")

        depth_colormap_aligned = cv2.applyColorMap(
            cv2.convertScaleAbs(depth_aligned, alpha=0.03),
            cv2.COLORMAP_JET
        )

        combined_aligned = np.hstack([color_aligned, depth_colormap_aligned])
        cv2.putText(combined_aligned, "WITH Alignment",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        path_aligned = os.path.join(SAVE_DIR, f"with_align_{timestamp}.png")
        cv2.imwrite(path_aligned, combined_aligned)
        print(f"  保存: {path_aligned}")

        # === 保存3: オーバーレイ比較 ===
        # カラー画像に深度をオーバーレイ
        depth_overlay = depth_colormap_aligned.copy()
        alpha = 0.6
        overlay = cv2.addWeighted(color_aligned, alpha, depth_overlay, 1-alpha, 0)

        # 画面中央に十字線を追加
        h, w = overlay.shape[:2]
        cv2.line(overlay, (w//2 - 20, h//2), (w//2 + 20, h//2), (0, 255, 0), 2)
        cv2.line(overlay, (w//2, h//2 - 20), (w//2, h//2 + 20), (0, 255, 0), 2)

        # 中央の深度値
        center_depth = depth_aligned[h//2, w//2] * depth_scale
        cv2.putText(overlay, f"Center: {center_depth:.3f}m",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(overlay, "Overlay: Color + Depth",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        path_overlay = os.path.join(SAVE_DIR, f"overlay_{timestamp}.png")
        cv2.imwrite(path_overlay, overlay)
        print(f"\n[オーバーレイ]")
        print(f"  保存: {path_overlay}")

        # === 保存4: 生データ ===
        np.save(os.path.join(SAVE_DIR, f"depth_raw_{timestamp}.npy"), depth_aligned)
        np.save(os.path.join(SAVE_DIR, f"color_raw_{timestamp}.npy"), color_aligned)

        # === 統計情報 ===
        valid_depths = depth_aligned[depth_aligned > 0] * depth_scale

        print("\n" + "=" * 70)
        print("統計情報:")
        print("=" * 70)
        print(f"有効ピクセル数: {len(valid_depths)} / {depth_aligned.size}")
        print(f"有効率: {100*len(valid_depths)/depth_aligned.size:.1f}%")
        if len(valid_depths) > 0:
            print(f"深度範囲: {valid_depths.min():.3f}m ~ {valid_depths.max():.3f}m")
            print(f"平均深度: {valid_depths.mean():.3f}m")
            print(f"中央深度: {center_depth:.3f}m")

        print("\n" + "=" * 70)
        print("検証完了！")
        print(f"保存先: {SAVE_DIR}")
        print("=" * 70)
        print("\n画像を確認して、カラーと深度が正しく位置合わせされているか確認してください。")
        print("特に「overlay」画像で、物体のエッジがカラーと深度で一致しているかチェック！")

    finally:
        pipeline.stop()

if __name__ == "__main__":
    test_alignment()
