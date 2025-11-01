#!/usr/bin/env python3
"""
Intel RealSense D405 Food Scanner
食品スキャン最適化フィルターパイプライン（Nutrition5k準拠）

食品スキャン最適化フィルター順序（シングルフレームモード用）:
  1. Threshold (7-50cm有効範囲)
  2. Decimation (無効化)
  3. Depth2Disparity
  4. Spatial (delta=32でエッジ保存強化)
  5. Temporal (静的シーン用)
  6. Disparity2Depth
  7. Hole Filling (mode=2でエッジ形状保持)

複数フレーム平均化モード（デフォルト）:
- フィルタ不使用（20フレームメディアンが強力なノイズ除去効果）
- フィルタの内部状態競合を回避

最適化内容:
- Spatial Filter delta: 20→32（皿/お椀のエッジ保存強化）
- Hole Filling mode: 1→2（円形エッジの角張り防止）
- Threshold Filter追加（D405有効範囲7-50cm）

参考:
- https://github.com/IntelRealSense/librealsense/blob/master/doc/post-processing-filters.md
- D405最適解像度: 848x480
- Visual Preset: High Accuracy
- Nutrition5k準拠: 16-bit, 10000 units/m

使い方:
  sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py salmon_salad

出力:
  nutrition5k_data/imagery/realsense_overhead/
    ├── rgb_salmon_salad_YYYYMMDD_HHMMSS.png
    ├── depth_raw_salmon_salad_YYYYMMDD_HHMMSS.png (16-bit, 10000 units/m)
    ├── depth_colorized_salmon_salad_YYYYMMDD_HHMMSS.png
    └── metadata_salmon_salad_YYYYMMDD_HHMMSS.json
"""

import pyrealsense2 as rs
import numpy as np
import cv2
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Nutrition5k互換設定
DEPTH_SCALE_FACTOR = 10000  # 1m = 10,000 units

# D405最適設定（Intel推奨）
D405_OPTIMAL_WIDTH = 848
D405_OPTIMAL_HEIGHT = 480
D405_OPTIMAL_FPS = 60

# 出力ディレクトリ
BASE_DIR = Path("/Users/moei/program/D405")
OUTPUT_DIR = BASE_DIR / "nutrition5k_data" / "imagery" / "realsense_overhead"


class IntelFilterPipeline:
    """食品スキャン最適化フィルターパイプライン（Intel公式推奨ベース）"""

    def __init__(self, enable_temporal=True):
        """
        フィルターパイプライン初期化

        食品スキャン最適化順序:
        1. Threshold Filter (D405有効範囲: 7-50cm)
        2. Decimation Filter (D405では無効化)
        3. Depth to Disparity Transform
        4. Spatial Edge-Preserving Filter (delta=32でエッジ保存強化)
        5. Temporal Filter (静的シーン用)
        6. Disparity to Depth Transform
        7. Hole Filling Filter (mode=2でエッジ形状保持)
        """

        # 1. Threshold Filter（D405有効範囲のみ: 7cm～50cm）
        # 無効な深度値を除去（トレイエッジのノイズ除去に重要）
        self.threshold = rs.threshold_filter()
        self.threshold.set_option(rs.option.min_distance, 0.07)  # 7cm
        self.threshold.set_option(rs.option.max_distance, 0.50)  # 50cm

        # 2. Decimation Filter（解像度削減）
        # D405は既に848x480なので、使用しない（デフォルト: magnitude=1）
        self.decimation = rs.decimation_filter()
        self.decimation.set_option(rs.option.filter_magnitude, 1)  # スキップ

        # 3. Depth to Disparity Transform
        self.depth_to_disparity = rs.disparity_transform(True)

        # 4. Spatial Edge-Preserving Filter（食品スキャン最適化）
        self.spatial = rs.spatial_filter()
        self.spatial.set_option(rs.option.filter_magnitude, 2)
        self.spatial.set_option(rs.option.filter_smooth_alpha, 0.5)
        # delta: エッジ判定のしきい値（大きいほどエッジ保存が強い）
        # 食品の皿/お椀のエッジ保存のため、20→32に変更
        self.spatial.set_option(rs.option.filter_smooth_delta, 32)
        self.spatial.set_option(rs.option.holes_fill, 0)

        # 5. Temporal Filter（静止シーン用）
        self.enable_temporal = enable_temporal
        if enable_temporal:
            self.temporal = rs.temporal_filter()
            self.temporal.set_option(rs.option.filter_smooth_alpha, 0.4)
            self.temporal.set_option(rs.option.filter_smooth_delta, 20)

        # 6. Disparity to Depth Transform
        self.disparity_to_depth = rs.disparity_transform(False)

        # 7. Hole Filling Filter
        self.hole_filling = rs.hole_filling_filter()
        # mode=2: nearest from around（エッジ保存に最適）
        # mode=1 (farest) は円形物体のエッジを角張らせるため、mode=2を使用
        self.hole_filling.set_option(rs.option.holes_fill, 2)

    def process(self, depth_frame, use_temporal=None):
        """
        食品スキャン最適化フィルターパイプラインを適用

        Args:
            depth_frame: 入力深度フレーム
            use_temporal: Temporal Filter使用フラグ（Noneの場合はself.enable_temporalを使用）
                         複数フレーム平均化時はFalseを推奨

        Returns:
            filtered_frame: フィルター適用後の深度フレーム
        """
        frame = depth_frame

        # Temporal Filter使用判定
        # 複数フレーム平均化では既に時間的ノイズ除去が行われるため不要
        apply_temporal = use_temporal if use_temporal is not None else self.enable_temporal

        # 食品スキャン最適化順序で適用
        frame = self.threshold.process(frame)        # 1. 有効範囲のみ
        frame = self.decimation.process(frame)       # 2. (スキップ)
        frame = self.depth_to_disparity.process(frame)  # 3. D→D変換
        frame = self.spatial.process(frame)          # 4. エッジ保存平滑化

        if apply_temporal:
            frame = self.temporal.process(frame)     # 5. 時間的ノイズ除去

        frame = self.disparity_to_depth.process(frame)  # 6. D→D変換
        frame = self.hole_filling.process(frame)     # 7. ホール埋め

        return frame


class D405FoodScanner:
    """Intel RealSense D405 食材スキャナー"""

    def __init__(self):
        """スキャナー初期化"""

        print("=" * 70)
        print("Intel RealSense D405 Food Scanner")
        print("=" * 70)

        # パイプライン設定
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        # D405最適設定（Intel推奨）
        self.config.enable_stream(
            rs.stream.depth,
            D405_OPTIMAL_WIDTH,
            D405_OPTIMAL_HEIGHT,
            rs.format.z16,
            D405_OPTIMAL_FPS
        )
        self.config.enable_stream(
            rs.stream.color,
            D405_OPTIMAL_WIDTH,
            D405_OPTIMAL_HEIGHT,
            rs.format.rgb8,
            D405_OPTIMAL_FPS
        )

        # パイプライン開始
        print("カメラ初期化中...")
        self.profile = self.pipeline.start(self.config)

        # Depth sensorの最適設定
        device = self.profile.get_device()
        depth_sensor = device.first_depth_sensor()

        # Depth scale取得
        self.depth_scale = depth_sensor.get_depth_scale()
        print(f"✓ Depth Scale: {self.depth_scale} (m/unit)")

        # Visual Preset: High Accuracy（Intel推奨）
        if depth_sensor.supports(rs.option.visual_preset):
            depth_sensor.set_option(rs.option.visual_preset, 3)  # High Accuracy
            print("✓ Visual Preset: High Accuracy")

        # RGB-Depth Alignment
        self.align = rs.align(rs.stream.color)

        # Intel公式フィルターパイプライン
        self.filters = IntelFilterPipeline(enable_temporal=True)
        print("✓ Intel推奨フィルターパイプライン初期化完了")

        # ウォームアップ
        print("ウォームアップ中...")
        for _ in range(30):
            self.pipeline.wait_for_frames()

        print("✓ 準備完了")
        print("=" * 70)

    def capture_frame(self, num_frames=20):
        """
        高品質キャプチャ（複数フレーム平均）

        Args:
            num_frames: 平均化するフレーム数

        Returns:
            (rgb_image, depth_n5k): RGB画像とNutrition5k形式の深度データ
        """

        depth_frames = []
        color_frame = None

        print(f"\nキャプチャ中（{num_frames}フレーム平均）...")

        for i in range(num_frames):
            frames = self.pipeline.wait_for_frames()

            # RGB-Depth Alignment
            aligned_frames = self.align.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            if not depth_frame or not color_frame:
                continue

            # 深度データ取得
            # 複数フレーム平均化では、20フレームのメディアン処理が強力なノイズ除去効果を持つため
            # フィルタは不要（内部状態を持つフィルタが複数フレーム処理で競合する問題も回避）
            # .copy()でフレームメモリへの参照を切断（メモリロック回避）
            depth_data = np.asanyarray(depth_frame.get_data()).copy()
            depth_frames.append(depth_data)

            if (i + 1) % 5 == 0:
                print(f"  {i + 1}/{num_frames} フレーム...")

        # RGB画像（最後のフレームを使用）
        # .copy()でフレームメモリへの参照を切断
        rgb_image = np.asanyarray(color_frame.get_data()).copy()

        # 深度フレーム平均化（中央値フィルター）
        depth_stack = np.stack(depth_frames, axis=0)
        masked_depth = np.ma.masked_equal(depth_stack, 0)
        depth_avg = np.ma.median(masked_depth, axis=0).filled(0).astype(np.uint16)

        # Nutrition5k形式に変換
        depth_n5k = (depth_avg * self.depth_scale * DEPTH_SCALE_FACTOR).astype(np.uint16)

        print(f"✓ キャプチャ完了")
        print(f"  解像度: {rgb_image.shape[1]}x{rgb_image.shape[0]}")
        print(f"  深度範囲: {depth_n5k.min()} - {depth_n5k.max()} units")

        return rgb_image, depth_n5k

    def save_scan(self, food_name, rgb_image, depth_n5k):
        """
        スキャン結果をNutrition5k形式で保存

        Args:
            food_name: 食材名
            rgb_image: RGB画像
            depth_n5k: Nutrition5k形式の深度データ
        """

        # 出力ディレクトリ作成
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # タイムスタンプ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ファイル名ベース
        base_name = f"{food_name}_{timestamp}"

        # 1. RGB画像保存
        rgb_path = OUTPUT_DIR / f"rgb_{base_name}.png"
        cv2.imwrite(str(rgb_path), cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR))

        # 2. Raw深度保存（16-bit PNG, Nutrition5k互換）
        depth_raw_path = OUTPUT_DIR / f"depth_raw_{base_name}.png"
        cv2.imwrite(str(depth_raw_path), depth_n5k)

        # 3. カラー深度可視化
        depth_colorized = self.colorize_depth(depth_n5k)
        depth_color_path = OUTPUT_DIR / f"depth_colorized_{base_name}.png"
        cv2.imwrite(str(depth_color_path), depth_colorized)

        # 4. メタデータ
        metadata = {
            'food_name': food_name,
            'timestamp': timestamp,
            'resolution': {'width': rgb_image.shape[1], 'height': rgb_image.shape[0]},
            'depth_encoding': '16-bit PNG, 10000 units/meter',
            'depth_scale_factor': DEPTH_SCALE_FACTOR,
            'camera_depth_scale': float(self.depth_scale),
            'depth_range_units': {'min': int(depth_n5k.min()), 'max': int(depth_n5k.max())},
            'calibration': 'Intel Tare Calibration applied (stored in camera EEPROM)'
        }

        metadata_path = OUTPUT_DIR / f"metadata_{base_name}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n✓ 保存完了:")
        print(f"  RGB:         {rgb_path.name}")
        print(f"  Depth Raw:   {depth_raw_path.name}")
        print(f"  Depth Color: {depth_color_path.name}")
        print(f"  Metadata:    {metadata_path.name}")

    def colorize_depth(self, depth_n5k):
        """深度データをカラーマップで可視化"""

        # 動的範囲正規化
        depth_valid = depth_n5k[depth_n5k > 0]
        if len(depth_valid) > 0:
            min_depth = np.percentile(depth_valid, 1)
            max_depth = np.percentile(depth_valid, 99)
        else:
            min_depth, max_depth = 0, 6000

        # 正規化してJETカラーマップ
        normalized = np.clip((depth_n5k - min_depth) / (max_depth - min_depth) * 255, 0, 255).astype(np.uint8)
        colorized = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

        return colorized

    def run_interactive(self, food_name):
        """インタラクティブモード"""

        print(f"\n食材名: {food_name}")
        print("\n操作:")
        print("  's' キー: 高品質スキャン（20フレーム平均）")
        print("  'c' キー: クイックスキャン（1フレーム）")
        print("  'q' キー: 終了")
        print("")

        cv2.namedWindow('D405 Food Scanner - Preview', cv2.WINDOW_AUTOSIZE)

        try:
            while True:
                # プレビュー取得
                frames = self.pipeline.wait_for_frames()
                aligned_frames = self.align.process(frames)

                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                if not depth_frame or not color_frame:
                    continue

                # プレビュー用フィルター適用
                filtered_depth = self.filters.process(depth_frame)

                # 画像変換
                depth_image = np.asanyarray(filtered_depth.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # 深度カラー化
                depth_n5k_preview = (depth_image * self.depth_scale * DEPTH_SCALE_FACTOR).astype(np.uint16)
                depth_colorized = self.colorize_depth(depth_n5k_preview)

                # プレビュー結合
                preview = np.hstack([
                    cv2.cvtColor(color_image, cv2.COLOR_RGB2BGR),
                    depth_colorized
                ])

                # 情報オーバーレイ
                cv2.putText(preview, f"Food: {food_name}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(preview, "Press 's'=Scan 'c'=Quick 'q'=Quit", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                cv2.imshow('D405 Food Scanner - Preview', preview)

                # キー入力
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    print("\n終了...")
                    break

                elif key == ord('s'):
                    # 高品質スキャン
                    rgb, depth = self.capture_frame(num_frames=20)
                    self.save_scan(food_name, rgb, depth)

                elif key == ord('c'):
                    # クイックスキャン
                    rgb, depth = self.capture_frame(num_frames=1)
                    self.save_scan(food_name, rgb, depth)

        finally:
            cv2.destroyAllWindows()
            self.pipeline.stop()
            print("✓ 終了")


def main():
    """メイン関数"""

    if len(sys.argv) < 2:
        print("使い方: sudo ... scan.py [食材名]", file=sys.stderr)
        print("\n例:", file=sys.stderr)
        print("  sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py salmon_salad", file=sys.stderr)
        sys.exit(1)

    food_name = sys.argv[1]

    # スキャナー起動
    scanner = D405FoodScanner()
    scanner.run_interactive(food_name)


if __name__ == "__main__":
    main()
