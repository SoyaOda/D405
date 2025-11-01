#!/usr/bin/env python3
"""
カメラのキャリブレーションをファクトリー設定にリセット
使い方:
  sudo /Users/moei/program/D405/venv/bin/python3 scripts/reset_calibration.py
"""
import pyrealsense2 as rs
import sys

def reset_calibration():
    """カメラのキャリブレーションをファクトリー設定にリセット"""
    print("=" * 70)
    print("Intel RealSense D405 - キャリブレーションリセット")
    print("=" * 70)
    print()

    try:
        # コンテキストを作成
        ctx = rs.context()
        devices = ctx.query_devices()

        if len(devices) == 0:
            print("[エラー] カメラが検出されませんでした")
            print("\n対処法:")
            print("  1. USBケーブルが接続されているか確認")
            print("  2. sudo権限で実行しているか確認")
            return False

        # 最初のデバイスを取得
        device = devices[0]
        print(f"✓ デバイス検出: {device.get_info(rs.camera_info.name)}")
        print(f"  シリアル番号: {device.get_info(rs.camera_info.serial_number)}")
        print()

        # ファクトリーキャリブレーションにリセット
        print("ファクトリーキャリブレーションにリセット中...")
        print("※ この処理には数秒かかります")
        print()

        # デバイスをリセット
        device.hardware_reset()

        print("=" * 70)
        print("✓ リセット完了")
        print("=" * 70)
        print()
        print("次のステップ:")
        print("  1. カメラのUSBケーブルを抜き差ししてください")
        print("  2. 5秒待ってください")
        print("  3. 以下のコマンドでキャリブレーションを実行:")
        print()
        print("     sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374")
        print()

        return True

    except Exception as e:
        print(f"[エラー] リセット失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = reset_calibration()
    sys.exit(0 if success else 1)
