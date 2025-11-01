#!/usr/bin/env python3
"""
お椀3Dモデルのスケール情報確認スクリプト
実物サイズ（絶対値）が保持されているかを検証
"""

import sys
import os
import numpy as np
import open3d as o3d
from pathlib import Path

def analyze_ply_file(ply_path):
    """
    .plyファイルを解析して実物サイズ情報を抽出

    Args:
        ply_path: .plyファイルパス

    Returns:
        dict: 分析結果
    """
    print(f"\n{'='*70}")
    print(f"分析: {ply_path.name}")
    print(f"{'='*70}")

    # メッシュ読み込み
    try:
        mesh = o3d.io.read_triangle_mesh(str(ply_path))

        if not mesh.has_vertices():
            print("❌ エラー: 頂点データなし")
            return None

    except Exception as e:
        print(f"❌ エラー: {e}")
        return None

    # 基本情報
    num_vertices = len(mesh.vertices)
    num_triangles = len(mesh.triangles)

    print(f"\n[基本情報]")
    print(f"  頂点数: {num_vertices:,}")
    print(f"  面数:   {num_triangles:,}")
    print(f"  法線:   {'✓' if mesh.has_vertex_normals() else '✗'}")
    print(f"  色:     {'✓' if mesh.has_vertex_colors() else '✗'}")

    # バウンディングボックス
    vertices = np.asarray(mesh.vertices)
    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    bbox_size = bbox_max - bbox_min
    bbox_center = (bbox_min + bbox_max) / 2

    print(f"\n[バウンディングボックス（単位不明）]")
    print(f"  最小値: [{bbox_min[0]:.6f}, {bbox_min[1]:.6f}, {bbox_min[2]:.6f}]")
    print(f"  最大値: [{bbox_max[0]:.6f}, {bbox_max[1]:.6f}, {bbox_max[2]:.6f}]")
    print(f"  サイズ: [{bbox_size[0]:.6f}, {bbox_size[1]:.6f}, {bbox_size[2]:.6f}]")
    print(f"  中心:   [{bbox_center[0]:.6f}, {bbox_center[1]:.6f}, {bbox_center[2]:.6f}]")

    # スケール推定（お椀の典型的なサイズから推測）
    # 仮定: お椀の直径は通常10-15cm程度
    max_dimension = bbox_size.max()

    print(f"\n[スケール分析]")
    print(f"  最大寸法: {max_dimension:.6f}")

    # 単位推定
    if 0.08 < max_dimension < 0.20:
        unit = "メートル (m)"
        diameter_mm = max_dimension * 1000
        print(f"  推定単位: {unit}")
        print(f"  ✓ 実物サイズ保持: YES")
        print(f"  推定直径: {diameter_mm:.1f} mm")
    elif 80 < max_dimension < 200:
        unit = "ミリメートル (mm)"
        diameter_mm = max_dimension
        print(f"  推定単位: {unit}")
        print(f"  ✓ 実物サイズ保持: YES")
        print(f"  推定直径: {diameter_mm:.1f} mm")
    elif 8 < max_dimension < 20:
        unit = "センチメートル (cm)"
        diameter_mm = max_dimension * 10
        print(f"  推定単位: {unit}")
        print(f"  ✓ 実物サイズ保持: YES")
        print(f"  推定直径: {diameter_mm:.1f} mm")
    else:
        unit = "不明（正規化済み？）"
        diameter_mm = None
        print(f"  推定単位: {unit}")
        print(f"  ⚠️ 実物サイズ保持: UNKNOWN")
        print(f"  ⚠️ スケール変換が必要な可能性あり")

    # PLYヘッダー確認
    print(f"\n[PLYヘッダー情報]")
    try:
        with open(ply_path, 'r', encoding='utf-8', errors='ignore') as f:
            header_lines = []
            for line in f:
                header_lines.append(line.strip())
                if line.strip() == "end_header":
                    break

            # コメント行にスケール情報があるか確認
            scale_info = []
            for line in header_lines:
                if 'scale' in line.lower() or 'unit' in line.lower() or 'mm' in line.lower():
                    scale_info.append(line)

            if scale_info:
                print("  スケール関連情報:")
                for info in scale_info:
                    print(f"    {info}")
            else:
                print("  ⚠️ スケール情報なし（ヘッダーコメント）")

    except Exception as e:
        print(f"  ヘッダー読み込みエラー: {e}")

    # 体積計算
    if mesh.is_watertight():
        volume = mesh.get_volume()
        print(f"\n[体積情報]")
        print(f"  メッシュ状態: ✓ Watertight")
        print(f"  体積: {volume:.6f} (単位^3)")

        if diameter_mm:
            # 実物サイズでの体積（cm^3 = ml）
            if unit == "メートル (m)":
                volume_ml = volume * 1e6  # m^3 -> cm^3
            elif unit == "ミリメートル (mm)":
                volume_ml = volume / 1000  # mm^3 -> cm^3
            elif unit == "センチメートル (cm)":
                volume_ml = volume  # cm^3 -> cm^3
            else:
                volume_ml = None

            if volume_ml:
                print(f"  実物体積: {volume_ml:.1f} ml (cm^3)")
    else:
        print(f"\n[体積情報]")
        print(f"  メッシュ状態: ⚠️ Not Watertight（穴あり）")
        print(f"  体積計算: 不可")

    return {
        "file": ply_path.name,
        "vertices": num_vertices,
        "triangles": num_triangles,
        "bbox_size": bbox_size,
        "max_dimension": max_dimension,
        "unit": unit,
        "diameter_mm": diameter_mm,
        "watertight": mesh.is_watertight()
    }


def main():
    """メイン処理"""

    print("="*70)
    print("お椀3Dモデル スケール情報検証")
    print("="*70)

    mesh_dir = Path("/Users/moei/program/D405/data/mesh_output")

    if not mesh_dir.exists():
        print(f"❌ エラー: {mesh_dir} が存在しません")
        sys.exit(1)

    # .plyファイル一覧
    ply_files = sorted(mesh_dir.glob("*.ply"))

    if not ply_files:
        print(f"❌ エラー: .plyファイルが見つかりません")
        sys.exit(1)

    print(f"\n検出: {len(ply_files)} 個の.plyファイル")

    # 各ファイルを分析
    results = []
    for ply_file in ply_files:
        result = analyze_ply_file(ply_file)
        if result:
            results.append(result)

    # サマリー
    print(f"\n{'='*70}")
    print("サマリー")
    print(f"{'='*70}")

    if results:
        print(f"\n{'ファイル':<25} {'直径(mm)':<12} {'単位':<15} {'Watertight'}")
        print("-" * 70)

        for r in results:
            diameter_str = f"{r['diameter_mm']:.1f}" if r['diameter_mm'] else "不明"
            watertight_str = "✓" if r['watertight'] else "✗"
            print(f"{r['file']:<25} {diameter_str:<12} {r['unit']:<15} {watertight_str}")

        # 実物サイズ保持判定
        has_scale = sum(1 for r in results if r['diameter_mm'] is not None)

        print(f"\n{'='*70}")
        if has_scale == len(results):
            print("✅ 結果: すべてのメッシュが実物サイズを保持しています")
        elif has_scale > 0:
            print(f"⚠️ 結果: {has_scale}/{len(results)} 個のメッシュが実物サイズを保持")
        else:
            print("❌ 結果: 実物サイズが保持されていません（スケール変換が必要）")
        print(f"{'='*70}")

    print("\n✓ 分析完了")


if __name__ == "__main__":
    main()
