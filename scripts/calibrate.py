#!/usr/bin/env python3
"""
Intel RealSense D405 Tare Calibration (公式手法)

Intel公式のTare Calibration APIを使用して、深度測定の精度を改善します。
1点のground truth（定規測定値）を入力するだけで、カメラ内部で
slope + offsetの補正を自動計算し、EEPROMに保存します。

参考: Intel RealSense Self-Calibration Documentation
https://github.com/IntelRealSense/librealsense/blob/master/wrappers/python/examples/depth_auto_calibration_example.py

使い方:
  sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 445

  445: カメラから基準面（トレイ面）までの定規測定値（mm）

必須:
  - 平らな基準面（トレイの底面など）
  - 定規で正確に測定した距離
  - カメラを固定（三脚推奨）
"""

import pyrealsense2 as rs
import sys
import json
import time

# Tare精度設定（Intel公式マッピング）
TARE_ACCURACY_MAP = {
    'very_high': 0,  # 最も高精度（時間がかかる）
    'high': 1,       # 高精度（推奨）
    'medium': 2,     # 中精度
    'low': 3         # 低精度
}

# スキャンパラメータ
SCAN_MAP = {
    'intrinsic': 0,  # 内部パラメータ
    'extrinsic': 1   # 外部パラメータ
}


def progress_callback(progress):
    """キャリブレーション進捗コールバック"""
    print(f'\r進捗: {progress}%... ', end='', flush=True)


def run_tare_calibration(ground_truth_mm, accuracy='high', scan_type='intrinsic'):
    """
    Intel公式Tare Calibrationを実行

    Args:
        ground_truth_mm: 定規で測定した実際の距離（mm）
        accuracy: キャリブレーション精度（'very_high', 'high', 'medium', 'low'）
        scan_type: スキャンタイプ（'intrinsic' or 'extrinsic'）
    """

    print("=" * 70)
    print("Intel RealSense D405 Tare Calibration（公式手法）")
    print("=" * 70)
    print(f"Ground Truth: {ground_truth_mm}mm ({ground_truth_mm/1000:.4f}m)")
    print(f"精度設定:     {accuracy}")
    print(f"スキャンタイプ: {scan_type}")
    print("=" * 70)

    # キャリブレーションパラメータJSON作成
    calibration_params = {
        'scan parameter': SCAN_MAP[scan_type],
        'accuracy': TARE_ACCURACY_MAP[accuracy]
    }
    params_json = json.dumps(calibration_params)

    # パイプライン設定（Intel推奨: D405最適解像度）
    print("\nカメラ初期化中...")
    config = rs.config()
    # D405推奨解像度: 848x480 @ 60fps
    config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 60)

    # パイプライン開始
    pipeline = rs.pipeline()
    try:
        profile = pipeline.start(config)

        # ウォームアップ（Intel推奨: より長い時間）
        print("ウォームアップ中（90フレーム、約1.5秒）...")
        for _ in range(90):
            pipeline.wait_for_frames()

        # デバイス安定化のための追加待機
        import time
        print("デバイス安定化待機中（3秒）...")
        time.sleep(3)

        # デバイス取得
        device = profile.get_device()

        # Depth sensorの設定（Intel推奨: High Accuracy preset）
        depth_sensor = device.first_depth_sensor()

        # Visual Presetを確認・設定
        if depth_sensor.supports(rs.option.visual_preset):
            # High Accuracy preset (3)
            depth_sensor.set_option(rs.option.visual_preset, 3)
            print("✓ Visual Preset: High Accuracy設定済み")

        print("\n" + "=" * 70)
        print("Tare Calibration実行中...")
        print("=" * 70)
        print("※ この処理には30秒～1分程度かかります")
        print("※ カメラと基準面を動かさないでください")
        print("")

        # Auto Calibrated Deviceとして取得
        auto_calib_dev = device.as_auto_calibrated_device()

        # Tare Calibration実行（Intel公式API）
        start_time = time.time()

        # リトライ機能（Intel公式推奨: 繰り返し試すと成功する）
        max_retries = 3
        retry_delay = 5  # 秒

        for attempt in range(1, max_retries + 1):
            try:
                print(f"\n試行 {attempt}/{max_retries}...")

                calibration_table, health_metrics = auto_calib_dev.run_tare_calibration(
                    ground_truth_mm,
                    params_json,
                    progress_callback,
                    60000  # タイムアウト: 60秒
                )

                # 成功したらループを抜ける
                break

            except RuntimeError as e:
                if "HW not ready" in str(e):
                    print(f"\n⚠️ 試行 {attempt} 失敗: HW not ready", file=sys.stderr)

                    if attempt < max_retries:
                        print(f"\n{retry_delay}秒待機してリトライします...", file=sys.stderr)
                        import time
                        time.sleep(retry_delay)
                        # リトライ前にパイプラインを再起動
                        pipeline.stop()
                        time.sleep(2)
                        profile = pipeline.start(config)
                        device = profile.get_device()
                        depth_sensor = device.first_depth_sensor()
                        if depth_sensor.supports(rs.option.visual_preset):
                            depth_sensor.set_option(rs.option.visual_preset, 3)
                        auto_calib_dev = device.as_auto_calibrated_device()
                        print("\n再試行中...")
                    else:
                        print("\n\n[エラー] 最大リトライ回数に達しました", file=sys.stderr)
                        print("\n推奨される対処法:", file=sys.stderr)
                        print("  1. pyrealsense2を2.49.0にダウングレード:", file=sys.stderr)
                        print("     pip uninstall pyrealsense2", file=sys.stderr)
                        print("     pip install pyrealsense2==2.49.0", file=sys.stderr)
                        print("\n  2. RealSense Viewerを使用（GUI）", file=sys.stderr)
                        print("\n  3. macOSを再起動してから再実行", file=sys.stderr)
                        print("\n技術情報（GitHub Issue #13340）:", file=sys.stderr)
                        print("  - pyrealsense2 2.50.0以降でHW not readyエラーが頻発", file=sys.stderr)
                        print("  - 2.49.0までは正常に動作", file=sys.stderr)
                        raise
                else:
                    raise

        elapsed_time = time.time() - start_time

        print(f"\n\n✓ Tare Calibration完了（{elapsed_time:.1f}秒）")

        # ヘルスメトリクス表示
        if health_metrics:
            print(f"\n【キャリブレーション品質】")
            print(f"  Health: {health_metrics}")

        # キャリブレーションテーブルをデバイスに設定
        print("\nキャリブレーション結果をカメラに書き込み中...")
        auto_calib_dev.set_calibration_table(calibration_table)

        # EEPROMに永続保存
        auto_calib_dev.write_calibration()

        print("\n" + "=" * 70)
        print("✓ キャリブレーション完了")
        print("=" * 70)
        print("補正データがカメラのEEPROMに保存されました。")
        print("今後のスキャンで自動的に補正が適用されます。")
        print("=" * 70)

    except Exception as e:
        print(f"\n[エラー] キャリブレーション失敗: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        pipeline.stop()
        print("\n✓ 終了")


def main():
    """メイン関数"""

    if len(sys.argv) < 2:
        print("使い方: sudo ... calibrate.py [定規測定値mm]", file=sys.stderr)
        print("\n例:", file=sys.stderr)
        print("  sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 445", file=sys.stderr)
        print("\n説明:", file=sys.stderr)
        print("  445: カメラから基準面までの距離（mm単位）", file=sys.stderr)
        sys.exit(1)

    # Ground truth取得
    try:
        ground_truth_mm = float(sys.argv[1])

        # 有効範囲チェック（Intel公式: 60mm - 10000mm）
        if ground_truth_mm < 60 or ground_truth_mm > 10000:
            print(f"[エラー] Ground truthは60-10000mmの範囲で指定してください", file=sys.stderr)
            print(f"入力値: {ground_truth_mm}mm", file=sys.stderr)
            sys.exit(1)

    except ValueError:
        print(f"[エラー] 無効な数値: {sys.argv[1]}", file=sys.stderr)
        sys.exit(1)

    # Tare Calibration実行
    run_tare_calibration(
        ground_truth_mm=ground_truth_mm,
        accuracy='high',  # Intel推奨: 高精度
        scan_type='intrinsic'
    )


if __name__ == "__main__":
    main()
