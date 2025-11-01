#!/usr/bin/env python3
"""
お椀メッシュの実物サイズ検証（Open3D使用）
1つのファイルのみを詳細分析
"""

import numpy as np
import open3d as o3d
from pathlib import Path

def verify_bowl_mesh():
    """お椀メッシュの実物サイズ検証"""

    print("="*70)
    print("お椀3Dモデル 実物サイズ検証")
    print("="*70)

    # 最初のファイルを分析
    ply_path = Path("/Users/moei/program/D405/data/mesh_output/001_bowl_mesh.ply")

    if not ply_path.exists():
        print(f"❌ エラー: {ply_path} が存在しません")
        return

    print(f"\n分析対象: {ply_path.name}")
    print("\nメッシュ読み込み中...")

    # メッシュ読み込み
    mesh = o3d.io.read_triangle_mesh(str(ply_path))

    if not mesh.has_vertices():
        print("❌ エラー: 頂点データなし")
        return

    # 基本情報
    num_vertices = len(mesh.vertices)
    num_triangles = len(mesh.triangles)

    print(f"\n[基本情報]")
    print(f"  頂点数: {num_vertices:,}")
    print(f"  面数:   {num_triangles:,}")

    # バウンディングボックス
    vertices = np.asarray(mesh.vertices)
    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    bbox_size = bbox_max - bbox_min
    bbox_center = (bbox_min + bbox_max) / 2

    print(f"\n[バウンディングボックス（ヘッダーによればmm単位）]")
    print(f"  最小値: [{bbox_min[0]:.2f}, {bbox_min[1]:.2f}, {bbox_min[2]:.2f}] mm")
    print(f"  最大値: [{bbox_max[0]:.2f}, {bbox_max[1]:.2f}, {bbox_max[2]:.2f}] mm")
    print(f"  サイズ: [{bbox_size[0]:.2f}, {bbox_size[1]:.2f}, {bbox_size[2]:.2f}] mm")
    print(f"  中心:   [{bbox_center[0]:.2f}, {bbox_center[1]:.2f}, {bbox_center[2]:.2f}] mm")

    # 実物サイズ確認
    width_mm = bbox_size[0]
    depth_mm = bbox_size[1]
    height_mm = bbox_size[2]

    # 直径推定（X-Y平面の最大値）
    diameter_mm = max(width_mm, depth_mm)

    print(f"\n[推定実物サイズ]")
    print(f"  直径: {diameter_mm:.1f} mm ({diameter_mm/10:.1f} cm)")
    print(f"  高さ: {height_mm:.1f} mm ({height_mm/10:.1f} cm)")

    # 妥当性チェック（お椀の典型的サイズ: 直径10-15cm, 高さ5-8cm）
    diameter_cm = diameter_mm / 10
    height_cm = height_mm / 10

    print(f"\n[妥当性チェック]")
    print(f"  お椀の典型的サイズ:")
    print(f"    直径: 10-15 cm")
    print(f"    高さ: 5-8 cm")
    print(f"")

    diameter_ok = 8 < diameter_cm < 20
    height_ok = 3 < height_cm < 12

    if diameter_ok and height_ok:
        print(f"  ✅ 直径: {diameter_cm:.1f} cm - OK（範囲内）")
        print(f"  ✅ 高さ: {height_cm:.1f} cm - OK（範囲内）")
        print(f"\n  ✅ 結論: 実物サイズ（mm単位）で保持されています")
    elif diameter_ok:
        print(f"  ✅ 直径: {diameter_cm:.1f} cm - OK（範囲内）")
        print(f"  ⚠️ 高さ: {height_cm:.1f} cm - 範囲外（要確認）")
        print(f"\n  ⚠️ 結論: 直径は妥当、高さは要確認")
    elif height_ok:
        print(f"  ⚠️ 直径: {diameter_cm:.1f} cm - 範囲外（要確認）")
        print(f"  ✅ 高さ: {height_cm:.1f} cm - OK（範囲内）")
        print(f"\n  ⚠️ 結論: 高さは妥当、直径は要確認")
    else:
        print(f"  ❌ 直径: {diameter_cm:.1f} cm - 範囲外")
        print(f"  ❌ 高さ: {height_cm:.1f} cm - 範囲外")
        print(f"\n  ❌ 結論: スケール変換が必要な可能性あり")

    # 体積計算
    if mesh.is_watertight():
        volume_mm3 = mesh.get_volume()
        volume_ml = volume_mm3 / 1000  # mm^3 -> cm^3 (ml)

        print(f"\n[体積情報]")
        print(f"  メッシュ状態: ✓ Watertight（密閉）")
        print(f"  体積: {volume_mm3:.1f} mm³")
        print(f"  体積: {volume_ml:.1f} ml (cm³)")

        # お椀の典型的容量: 100-300ml
        if 50 < volume_ml < 500:
            print(f"  ✅ お椀の典型的容量範囲内（50-500ml）")
        else:
            print(f"  ⚠️ 範囲外（要確認）")
    else:
        print(f"\n[体積情報]")
        print(f"  メッシュ状態: ⚠️ Not Watertight（穴あり）")
        print(f"  体積計算: 不可")
        print(f"  ※ 体積推定時にメッシュ修復が必要な可能性")

    print(f"\n{'='*70}")
    print("検証完了")
    print(f"{'='*70}")


if __name__ == "__main__":
    verify_bowl_mesh()
