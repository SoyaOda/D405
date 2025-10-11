#!/usr/bin/env python3
"""
RealSense D405 Tare Calibration スクリプト

カメラを固定した後、テーブル面（参照平面）に対してTare Calibrationを実行します。
これにより深度精度が向上し、食材の体積計算が正確になります。

使い方:
  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py [ground_truth_mm]

例:
  # レーザー距離計で測定した距離が300mmの場合
  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py 300

  # 自動計算モード（平らな白い面を使用）
  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py auto
"""

import pyrealsense2 as rs
import numpy as np
import sys
import json
import os
from datetime import datetime

CALIBRATION_DIR = "/Users/moei/program/D405/calibration_data"
os.makedirs(CALIBRATION_DIR, exist_ok=True)

def progress_callback(progress):
    """キャリブレーション進捗表示"""
    print(f"進捗: {progress:.1f}%", end='\r')

def calculate_target_distance_auto(pipeline, target_width_mm=200, target_height_mm=200):
    """
    自動的にターゲット距離を計算

    カメラを平らな白い面（例：A4用紙、白い壁）に向けて使用

    Args:
        pipeline: RealSenseパイプライン
        target_width_mm: ターゲットの幅（mm）
        target_height_mm: ターゲットの高さ（mm）

    Returns:
        計算されたターゲット距離（mm）
    """
    print("\n自動距離計算モード")
    print("=" * 70)
    print("指示: カメラを平らな白い面に向けてください")
    print("     （例：A4用紙、白い壁、白いテーブル）")
    print("     面はカメラと平行で、画面中央に配置してください")
    print("=" * 70)
    input("\n準備ができたらEnterキーを押してください...")

    # フレームキュー作成
    q = rs.frame_queue(50)

    # 30フレーム取得
    print("\nフレーム取得中...")
    for i in range(30):
        frames = pipeline.wait_for_frames()
        q.enqueue(frames)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/30 フレーム...")

    # デバイス取得
    profile = pipeline.get_active_profile()
    dev = profile.get_device()
    adev = dev.as_auto_calibrated_device()

    # 自動計算
    print("\n距離を自動計算中...")
    target_z = adev.calculate_target_z(q, target_width_mm, target_height_mm,
                                       rs.calibration_type.manual_depth_to_rgb)

    print(f"✓ 計算完了: {target_z:.1f}mm ({target_z/10:.1f}cm)")
    return target_z

def calculate_target_distance_manual(pipeline):
    """
    複数フレームから中央深度の平均を計算

    Returns:
        平均深度（mm）
    """
    print("\n手動距離計算モード")
    print("=" * 70)
    print("30フレーム取得して中央深度の平均を計算します...")
    print("=" * 70)

    # 深度スケール取得
    profile = pipeline.get_active_profile()
    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()

    depths = []
    for i in range(30):
        frames = pipeline.wait_for_frames()
        depth_frame = frames.get_depth_frame()
        if not depth_frame:
            continue

        depth_image = np.asanyarray(depth_frame.get_data())
        h, w = depth_image.shape
        center_depth = depth_image[h//2, w//2]

        if center_depth > 0:
            depths.append(center_depth)

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/30 フレーム...")

    # 中央値計算（mm単位）
    median_depth = np.median(depths)
    median_depth_mm = median_depth * depth_scale * 1000

    print(f"✓ 計算完了: {median_depth_mm:.1f}mm ({median_depth_mm/10:.1f}cm)")
    return median_depth_mm

def run_tare_calibration(ground_truth_mm_input=None):
    """
    Tare Calibration実行

    Args:
        ground_truth_mm_input: Ground truth距離（mm）
                               'auto' = 自動計算
                               数値 = 指定値
                               None = 手動計算
    """
    print("=" * 70)
    print("RealSense D405 Tare Calibration")
    print("=" * 70)
    print("\n重要: カメラを固定位置に設置してください")
    print("      平らな面（テーブル/白い紙）に向けてください")
    print("      面はカメラと平行にしてください")
    print("\nこのキャリブレーションにより：")
    print("  - 深度測定精度が向上します")
    print("  - テーブル面を参照平面として記録します")
    print("  - 食材の高さ・体積計算が正確になります")
    print("=" * 70)

    # パイプライン設定
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 1280, 720, rs.format.z16, 30)
    config.enable_stream(rs.stream.color, 1280, 720, rs.format.bgr8, 30)

    print("\nパイプライン開始...")
    profile = pipeline.start(config)

    # デバイス取得
    dev = profile.get_device()
    depth_sensor = dev.first_depth_sensor()

    # カメラ設定
    if depth_sensor.supports(rs.option.visual_preset):
        depth_sensor.set_option(rs.option.visual_preset, 3)  # High Accuracy

    depth_scale = depth_sensor.get_depth_scale()
    print(f"✓ RealSense深度スケール: {depth_scale}")

    # ウォームアップ
    print("\nウォームアップ中...")
    for _ in range(30):
        pipeline.wait_for_frames()
    print("✓ 準備完了\n")

    try:
        # Ground Truth距離の決定
        if ground_truth_mm_input == 'auto':
            target_z = calculate_target_distance_auto(pipeline)
        elif ground_truth_mm_input is not None:
            target_z = float(ground_truth_mm_input)
            print(f"\n指定されたGround Truth: {target_z:.1f}mm ({target_z/10:.1f}cm)")
        else:
            target_z = calculate_target_distance_manual(pipeline)

        # Ground Truth範囲チェック
        if target_z < 60 or target_z > 10000:
            print(f"\nエラー: Ground Truthは60-10000mmの範囲である必要があります")
            print(f"現在値: {target_z:.1f}mm")
            return False

        # Tare Calibration設定
        print("\n" + "=" * 70)
        print("Tare Calibration実行中...")
        print("=" * 70)
        print(f"Ground Truth: {target_z:.1f}mm ({target_z/10:.1f}cm)")
        print("Accuracy: High")
        print("タイムアウト: 30秒")
        print("\n処理には数秒〜数十秒かかります。お待ちください...")

        # キャリブレーション設定（JSON）
        calibration_config = {
            "accuracy": "high",  # high, medium, low
            "scan": "standard",  # standard, white_wall
        }
        args = json.dumps(calibration_config)

        # auto_calibrated_device取得
        adev = dev.as_auto_calibrated_device()

        # Tare Calibration実行
        print("\nキャリブレーション実行中...\n")
        table, health = adev.run_tare_calibration(
            target_z,
            args,
            progress_callback,
            30000  # 30秒タイムアウト
        )

        print("\n\n✓ キャリブレーション完了!")
        print(f"Health Check: {health}")

        # キャリブレーション適用
        print("\nキャリブレーションをデバイスに適用中...")
        adev.set_calibration_table(table)
        adev.write_calibration()
        print("✓ キャリブレーションが保存されました")

        # メタデータ保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        metadata_path = os.path.join(CALIBRATION_DIR, f"calibration_{timestamp}.json")

        metadata = {
            "timestamp": datetime.now().isoformat(),
            "ground_truth_mm": target_z,
            "ground_truth_cm": target_z / 10,
            "ground_truth_m": target_z / 1000,
            "health": health,
            "depth_scale": depth_scale,
            "accuracy": calibration_config["accuracy"],
            "scan_type": calibration_config["scan"],
            "device_serial": dev.get_info(rs.camera_info.serial_number),
            "firmware_version": dev.get_info(rs.camera_info.firmware_version),
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\nメタデータ保存: {metadata_path}")

        # 検証: キャリブレーション後の深度測定
        print("\n" + "=" * 70)
        print("キャリブレーション結果を検証中...")
        print("=" * 70)

        # 10フレーム取得して平均
        depths = []
        for _ in range(10):
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_image = np.asanyarray(depth_frame.get_data())
                h, w = depth_image.shape
                center_depth = depth_image[h//2, w//2] * depth_scale * 1000
                if center_depth > 0:
                    depths.append(center_depth)

        measured_mm = np.mean(depths)
        error_mm = measured_mm - target_z
        error_percent = (error_mm / target_z) * 100

        print(f"\nGround Truth: {target_z:.1f}mm")
        print(f"測定値:       {measured_mm:.1f}mm")
        print(f"誤差:         {error_mm:+.1f}mm ({error_percent:+.2f}%)")

        if abs(error_percent) < 1.0:
            print("\n✅ キャリブレーション精度: 優秀 (<1%)")
        elif abs(error_percent) < 2.0:
            print("\n✅ キャリブレーション精度: 良好 (<2%)")
        else:
            print("\n⚠️  キャリブレーション精度: 要改善 (>2%)")
            print("   再度キャリブレーションを実行することを推奨します")

        print("\n" + "=" * 70)
        print("✓ Tare Calibration完了!")
        print("=" * 70)
        print("\n次のステップ:")
        print("  1. カメラを動かさないでください")
        print("  2. nutrition5k_style_scanner.pyで食材をスキャンしてください")
        print("  3. キャリブレーション情報がメタデータに記録されます")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        pipeline.stop()

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'auto':
            ground_truth_mm = 'auto'
        else:
            try:
                ground_truth_mm = float(arg)
            except ValueError:
                print("使い方: sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py [ground_truth_mm|auto]")
                print("\n例:")
                print("  # レーザー距離計で測定した距離を使用（推奨）")
                print("  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py 300")
                print("\n  # 自動計算モード")
                print("  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py auto")
                print("\n  # 手動計算モード（引数なし）")
                print("  sudo /Users/moei/program/D405/venv/bin/python3 calibrate_realsense.py")
                sys.exit(1)
    else:
        ground_truth_mm = None  # 手動計算モード

    success = run_tare_calibration(ground_truth_mm)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
