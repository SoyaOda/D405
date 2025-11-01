#!/usr/bin/env python3
"""
リム直径測定のテスト

修正した_measure_diameter()メソッドが正しく動作するか検証
"""

import numpy as np
import open3d as o3d
import sys
sys.path.insert(0, '/Users/moei/program/D405')

from src.bowl_fitting import BowlFitter


def test_rim_diameter_measurement():
    """リム直径測定のテスト"""

    print("=" * 70)
    print("リム直径測定テスト")
    print("=" * 70)

    bowl_mesh_path = "data/mesh_output/001_bowl_mesh.ply"
    expected_diameter_mm = 165.0  # ユーザー実測値

    print(f"\n対象メッシュ: {bowl_mesh_path}")
    print(f"期待される直径: {expected_diameter_mm} mm")

    # BowlFitter初期化
    print("\nBowlFitter初期化...")
    fitter = BowlFitter(
        bowl_model_path=bowl_mesh_path,
        bowl_real_diameter_mm=expected_diameter_mm
    )

    # メッシュの頂点を取得
    vertices = np.asarray(fitter.bowl_mesh.vertices)

    # 直径測定（新しい実装）
    print("\n新しい実装でリム直径を測定...")
    measured_diameter = fitter._measure_diameter(vertices)

    # 結果
    print("\n" + "=" * 70)
    print("測定結果")
    print("=" * 70)

    error_mm = abs(measured_diameter - expected_diameter_mm)
    error_percent = (error_mm / expected_diameter_mm) * 100

    print(f"\n期待値: {expected_diameter_mm:.1f} mm")
    print(f"測定値: {measured_diameter:.1f} mm")
    print(f"誤差:   {error_mm:.1f} mm ({error_percent:.1f}%)")

    # 評価
    print("\n" + "=" * 70)
    print("評価")
    print("=" * 70)

    if error_percent < 5:
        print(f"✅ 優秀: 誤差 {error_percent:.1f}% < 5%")
        status = "PASS"
    elif error_percent < 10:
        print(f"✅ 良好: 誤差 {error_percent:.1f}% < 10%")
        status = "PASS"
    elif error_percent < 20:
        print(f"⚠️ 許容: 誤差 {error_percent:.1f}% < 20%")
        status = "ACCEPTABLE"
    else:
        print(f"❌ 要改善: 誤差 {error_percent:.1f}% >= 20%")
        status = "FAIL"

    # 比較: 旧実装（重心ベース）
    print("\n" + "=" * 70)
    print("旧実装との比較")
    print("=" * 70)

    # 旧実装をシミュレート
    center = vertices.mean(axis=0)
    xy_points = vertices[:, :2]
    center_xy = center[:2]
    distances = np.linalg.norm(xy_points - center_xy, axis=1)
    old_diameter = distances.max() * 2
    old_error_percent = abs(old_diameter - expected_diameter_mm) / expected_diameter_mm * 100

    print(f"\n旧実装（重心ベース）:")
    print(f"  測定値: {old_diameter:.1f} mm")
    print(f"  誤差:   {old_error_percent:.1f}%")

    print(f"\n新実装（リムベース）:")
    print(f"  測定値: {measured_diameter:.1f} mm")
    print(f"  誤差:   {error_percent:.1f}%")

    improvement = old_error_percent - error_percent
    print(f"\n改善度: {improvement:.1f}ポイント")

    return {
        'measured_diameter_mm': measured_diameter,
        'expected_diameter_mm': expected_diameter_mm,
        'error_percent': error_percent,
        'status': status,
        'old_diameter_mm': old_diameter,
        'old_error_percent': old_error_percent,
        'improvement': improvement
    }


if __name__ == "__main__":
    print("リム直径測定 修正版テスト")
    print("=" * 70)
    print("このテストでは:")
    print("  1. 実際のお椀メッシュをロード")
    print("  2. 新しいリム直径測定アルゴリズムを実行")
    print("  3. ユーザー実測値（165mm）と比較")
    print("  4. 旧実装との改善度を評価")
    print("=" * 70)

    try:
        result = test_rim_diameter_measurement()

        print("\n" + "=" * 70)
        print("✓ テスト完了")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
