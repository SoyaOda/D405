#!/usr/bin/env python3
"""
RealSense D405 食材スキャン専用スクリプト（改良版）

ベストプラクティスに基づいた設定：
- D405の最適範囲：7-50cm
- High Accuracy プリセット
- 推奨ポストプロセッシングフィルター適用
- Color-Depth アライメント
- 複数フレーム時間平均（中央値フィルター）でノイズ削減

使い方:
  sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py [食材名] [平均化フレーム数]

例:
  sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py apple
  sudo /Users/moei/program/D405/venv/bin/python3 food_scanner.py tomato 30

平均化フレーム数のガイドライン:
  - テクスチャのある表面: 10-15フレーム
  - 白い/滑らかな表面: 20-30フレーム
  - デフォルト: 20フレーム

操作方法:
  's' キー: 複数フレームをキャプチャして保存（高品質）
  'q' キー: 終了
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import os
import sys
from datetime import datetime

# 保存先ディレクトリの作成
SAVE_DIR = "/Users/moei/program/D405/food_scans"
os.makedirs(SAVE_DIR, exist_ok=True)

def setup_filters():
    """
    ポストプロセッシングフィルターの設定（公式推奨順序）

    注意: Decimation Filterは解像度を変更するため、アライメントと
    組み合わせると問題が発生しやすい。D405は近距離用で高精度が必要なため、
    Decimation Filterは使用せず、他のフィルターのみ適用する。
    """

    # 1. Depth to Disparity Transform
    depth_to_disparity = rs.disparity_transform(True)

    # 2. Spatial Filter - 深度データの平滑化（エッジ保持）
    spatial = rs.spatial_filter()
    spatial.set_option(rs.option.filter_magnitude, 2)
    spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
    spatial.set_option(rs.option.filter_smooth_delta, 20)
    spatial.set_option(rs.option.holes_fill, 0)  # 0 = 穴埋めしない

    # 3. Temporal Filter - フレーム間の一貫性向上
    temporal = rs.temporal_filter()
    temporal.set_option(rs.option.filter_smooth_alpha, 0.4)
    temporal.set_option(rs.option.filter_smooth_delta, 20)

    # 4. Disparity to Depth Transform
    disparity_to_depth = rs.disparity_transform(False)

    # 5. Hole Filling Filter - 欠損値の補完（最後に適用）
    hole_filling = rs.hole_filling_filter()
    hole_filling.set_option(rs.option.holes_fill, 1)  # 1 = farest-from-around

    return {
        'depth_to_disparity': depth_to_disparity,
        'spatial': spatial,
        'temporal': temporal,
        'disparity_to_depth': disparity_to_depth,
        'hole_filling': hole_filling
    }

def apply_filters(depth_frame, filters):
    """
    フィルターを公式推奨順序で適用

    順序: Depth2Disparity → Spatial → Temporal → Disparity2Depth → Hole Filling
    """
    frame = depth_frame

    # 公式推奨フィルター順序（Decimation除く）
    frame = filters['depth_to_disparity'].process(frame)
    frame = filters['spatial'].process(frame)
    frame = filters['temporal'].process(frame)
    frame = filters['disparity_to_depth'].process(frame)
    frame = filters['hole_filling'].process(frame)

    return frame

def capture_multi_frame_average(pipeline, filters, align_to_color, num_frames=20, use_median=True):
    """
    複数フレームをキャプチャして時間平均を取得（ノイズ削減）

    Args:
        pipeline: RealSense パイプライン
        filters: ポストプロセッシングフィルター
        align_to_color: アライメントオブジェクト
        num_frames: 平均化するフレーム数（デフォルト20）
        use_median: True なら中央値、False なら平均値
    """
    print(f"\n{'中央値' if use_median else '平均値'}フィルター適用中（{num_frames}フレーム）...")

    depth_frames = []
    color_frames = []

    for i in range(num_frames):
        frames = pipeline.wait_for_frames()

        # ステップ1: アライメント適用（位置合わせ優先）
        aligned_frames = align_to_color.process(frames)
        aligned_depth = aligned_frames.get_depth_frame()
        aligned_color = aligned_frames.get_color_frame()

        if not aligned_depth or not aligned_color:
            continue

        # ステップ2: フィルター適用（アライメント後の深度に）
        filtered_depth = apply_filters(aligned_depth, filters)

        depth_frames.append(np.asanyarray(filtered_depth.get_data()))
        color_frames.append(np.asanyarray(aligned_color.get_data()))

        if (i + 1) % 5 == 0:
            print(f"  {i + 1}/{num_frames} フレーム取得...")

    # カラーは最新フレームを使用（または平均）
    color_image = color_frames[-1]

    # 深度データの時間平均/中央値
    depth_stack = np.stack(depth_frames, axis=0)

    if use_median:
        # 中央値フィルター（推奨：動く物体でもアーティファクトなし）
        # 0（無効値）をマスクして中央値計算
        masked_depth = np.ma.masked_equal(depth_stack, 0)
        depth_image = np.ma.median(masked_depth, axis=0).filled(0).astype(np.uint16)
    else:
        # 平均値フィルター
        # 0（無効値）を除外して平均
        masked_depth = np.ma.masked_equal(depth_stack, 0)
        depth_image = np.ma.mean(masked_depth, axis=0).filled(0).astype(np.uint16)

    print("✓ フレーム平均化完了")

    return color_image, depth_image

def save_food_scan(color_image, depth_image, depth_colormap, food_name, depth_scale, num_frames_averaged):
    """食材スキャンデータの保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 食材名でサブディレクトリを作成
    food_dir = os.path.join(SAVE_DIR, food_name)
    os.makedirs(food_dir, exist_ok=True)

    # ファイルパス
    color_path = os.path.join(food_dir, f"color_{timestamp}.png")
    depth_vis_path = os.path.join(food_dir, f"depth_vis_{timestamp}.png")
    depth_raw_path = os.path.join(food_dir, f"depth_raw_{timestamp}.npy")
    metadata_path = os.path.join(food_dir, f"metadata_{timestamp}.txt")

    # 画像の保存
    cv2.imwrite(color_path, color_image)
    cv2.imwrite(depth_vis_path, depth_colormap)
    np.save(depth_raw_path, depth_image)

    # メタデータの保存
    h, w = depth_image.shape
    valid_depths = depth_image[depth_image > 0] * depth_scale

    with open(metadata_path, 'w') as f:
        f.write(f"食材名: {food_name}\n")
        f.write(f"撮影日時: {timestamp}\n")
        f.write(f"解像度: {w}x{h}\n")
        f.write(f"深度スケール: {depth_scale}\n")
        f.write(f"平均化フレーム数: {num_frames_averaged}\n")
        f.write(f"フィルター: 中央値フィルター適用\n")
        f.write(f"\n[深度統計（メートル）]\n")
        if len(valid_depths) > 0:
            f.write(f"  最小距離: {valid_depths.min():.4f} m\n")
            f.write(f"  最大距離: {valid_depths.max():.4f} m\n")
            f.write(f"  平均距離: {valid_depths.mean():.4f} m\n")
            f.write(f"  標準偏差: {valid_depths.std():.4f} m\n")
            f.write(f"  中央値: {np.median(valid_depths):.4f} m\n")
            f.write(f"  有効ピクセル率: {100*len(valid_depths)/depth_image.size:.1f}%\n")

        # 画面中央の深度
        center_depth = depth_image[h//2, w//2] * depth_scale
        f.write(f"\n[中央の深度]\n")
        f.write(f"  {center_depth:.4f} m\n")

    print(f"\n✓ スキャンデータを保存しました:")
    print(f"  カラー画像: {color_path}")
    print(f"  深度画像: {depth_vis_path}")
    print(f"  深度データ: {depth_raw_path}")
    print(f"  メタデータ: {metadata_path}")
    print(f"  保存先: {food_dir}\n")

def main():
    # コマンドライン引数から食材名と設定を取得
    food_name = sys.argv[1] if len(sys.argv) > 1 else "unknown_food"
    num_frames_to_average = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    print("=" * 70)
    print("RealSense D405 食材スキャンシステム（改良版）")
    print("=" * 70)
    print(f"食材名: {food_name}")
    print(f"保存先: {SAVE_DIR}/{food_name}/")
    print(f"平均化フレーム数: {num_frames_to_average} フレーム（中央値フィルター）")
    print("\n[D405 最適設定]")
    print("  推奨距離: 7-50 cm")
    print("  Visual Preset: High Accuracy")
    print("  フィルター: Spatial, Temporal, Hole Filling 適用済み")
    print("  アライメント: Color-Depth 位置合わせ有効")
    print("  時間平均: 複数フレームの中央値で高品質化")
    print("\n操作方法:")
    print("  's' キー: 複数フレームをキャプチャして保存（高品質）")
    print("  'q' キー: 終了")
    print("=" * 70)

    # パイプラインの設定
    pipeline = rs.pipeline()
    config = rs.config()

    # D405推奨設定：1280x720で最高品質（FOV一致、位置合わせ精度向上）
    # 注意: 640x480ではFOV差が大きく、深度が拡大して見える問題があるため
    # 1280x720または640x360を推奨（FOVがほぼ一致）
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    print("\nパイプラインを開始中...")
    profile = pipeline.start(config)

    # High Accuracy プリセットを設定
    depth_sensor = profile.get_device().first_depth_sensor()

    # Visual Preset を High Accuracy に設定
    if depth_sensor.supports(rs.option.visual_preset):
        depth_sensor.set_option(rs.option.visual_preset, 3)  # 3 = High Accuracy
        print("✓ Visual Preset: High Accuracy を適用")

    # 深度スケールの取得
    depth_scale = depth_sensor.get_depth_scale()
    print(f"✓ 深度スケール: {depth_scale}")

    # アライメントオブジェクト作成（深度をカラーに合わせる）
    align_to_color = rs.align(rs.stream.color)

    # ポストプロセッシングフィルターの設定
    filters = setup_filters()
    print("✓ ポストプロセッシングフィルター準備完了")

    print("\nウィンドウが表示されます...\n")

    # 最初の数フレームは安定しないのでスキップ
    for _ in range(30):
        pipeline.wait_for_frames()

    try:
        frame_count = 0
        saved_count = 0

        while True:
            # フレームの取得
            frames = pipeline.wait_for_frames()

            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # 実用的なアプローチ：アライメント → フィルター
            # 注意: 公式推奨は「フィルター → アライメント」だが、
            # pyrealsense2のAPI制限により、位置合わせの精度を優先して
            # この順序を採用（多くのユーザーが採用している方法）

            # ステップ1: アライメント適用（深度をカラーに合わせる）
            aligned_frames = align_to_color.process(frames)
            aligned_depth = aligned_frames.get_depth_frame()
            aligned_color = aligned_frames.get_color_frame()

            # ステップ2: ポストプロセッシングフィルター適用
            filtered_depth = apply_filters(aligned_depth, filters)

            # NumPy配列に変換
            depth_image = np.asanyarray(filtered_depth.get_data())
            color_image = np.asanyarray(aligned_color.get_data())

            # 深度画像を可視化
            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth_image, alpha=0.03),
                cv2.COLORMAP_JET
            )

            # サイズが異なる場合はリサイズ（Decimation Filter の影響対策）
            if color_image.shape[:2] != depth_colormap.shape[:2]:
                depth_colormap = cv2.resize(depth_colormap,
                                           (color_image.shape[1], color_image.shape[0]),
                                           interpolation=cv2.INTER_NEAREST)

            # 画像を横に並べて表示
            images = np.hstack((color_image, depth_colormap))

            # 中央の深度を取得
            h, w = depth_image.shape
            center_depth = depth_image[h//2, w//2] * depth_scale

            # 深度範囲チェック（D405の最適範囲: 7-50cm）
            if 0.07 <= center_depth <= 0.50:
                range_status = "OPTIMAL RANGE"
                color = (0, 255, 0)  # 緑
            elif center_depth < 0.07:
                range_status = "TOO CLOSE"
                color = (0, 165, 255)  # オレンジ
            else:
                range_status = "TOO FAR"
                color = (0, 0, 255)  # 赤

            # オーバーレイ表示
            cv2.putText(images, f"Food: {food_name}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(images, f"Center Depth: {center_depth:.3f} m [{range_status}]",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(images, "Press 's' to save, 'q' to quit",
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(images, f"Saved: {saved_count}",
                       (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 画像を表示
            cv2.imshow('D405 Food Scanner - Color | Depth', images)

            # キー入力
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n終了します...")
                break
            elif key == ord('s'):
                # 複数フレームをキャプチャして平均化
                avg_color, avg_depth = capture_multi_frame_average(
                    pipeline, filters, align_to_color, num_frames_to_average
                )

                # 平均化した深度データを可視化
                avg_depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(avg_depth, alpha=0.03),
                    cv2.COLORMAP_JET
                )

                # 保存
                save_food_scan(avg_color, avg_depth, avg_depth_colormap,
                              food_name, depth_scale, num_frames_to_average)
                saved_count += 1

            frame_count += 1

    finally:
        # 後処理
        pipeline.stop()
        cv2.destroyAllWindows()
        print("\n" + "=" * 70)
        print(f"✓ スキャンセッション終了")
        print(f"  食材名: {food_name}")
        print(f"  総フレーム数: {frame_count}")
        print(f"  保存した画像セット: {saved_count}")
        print(f"  保存先: {SAVE_DIR}/{food_name}/")
        print("=" * 70)

if __name__ == "__main__":
    main()
