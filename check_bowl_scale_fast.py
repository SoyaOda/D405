#!/usr/bin/env python3
"""
お椀3Dモデルのスケール情報確認スクリプト（高速版）
PLYヘッダーと頂点データのサンプリングで分析
"""

import sys
import numpy as np
from pathlib import Path

def parse_ply_header(ply_path):
    """PLYヘッダーを解析"""
    header_info = {
        "format": None,
        "vertices": 0,
        "faces": 0,
        "properties": [],
        "comments": []
    }

    with open(ply_path, 'rb') as f:
        line = f.readline().decode('utf-8', errors='ignore').strip()
        if line != "ply":
            return None

        while True:
            line = f.readline().decode('utf-8', errors='ignore').strip()

            if line.startswith("format"):
                header_info["format"] = line.split()[1]

            elif line.startswith("comment"):
                header_info["comments"].append(line)

            elif line.startswith("element vertex"):
                header_info["vertices"] = int(line.split()[2])

            elif line.startswith("element face"):
                header_info["faces"] = int(line.split()[2])

            elif line.startswith("property"):
                header_info["properties"].append(line)

            elif line == "end_header":
                break

    return header_info


def sample_vertices(ply_path, num_samples=1000):
    """
    頂点データをサンプリング

    Args:
        ply_path: .plyファイルパス
        num_samples: サンプル数

    Returns:
        numpy.ndarray: サンプル頂点座標 (N, 3)
    """
    vertices = []

    with open(ply_path, 'rb') as f:
        # ヘッダースキップ
        while True:
            line = f.readline().decode('utf-8', errors='ignore').strip()
            if line == "end_header":
                break

        # 頂点データ読み込み（最初のnum_samples個のみ）
        for i in range(num_samples):
            line = f.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                break

            try:
                parts = line.split()
                # x, y, z座標を抽出（最初の3列）
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                vertices.append([x, y, z])
            except (ValueError, IndexError):
                continue

    return np.array(vertices) if vertices else None


def analyze_bowl_ply(ply_path):
    """お椀PLYファイルを分析"""

    print(f"\n{'='*70}")
    print(f"分析: {ply_path.name}")
    print(f"{'='*70}")

    # ヘッダー解析
    header = parse_ply_header(ply_path)

    if not header:
        print("❌ エラー: 有効なPLYファイルではありません")
        return None

    print(f"\n[基本情報]")
    print(f"  頂点数: {header['vertices']:,}")
    print(f"  面数:   {header['faces']:,}")
    print(f"  形式:   {header['format']}")

    # コメント情報
    if header['comments']:
        print(f"\n[コメント情報]")
        for comment in header['comments']:
            print(f"  {comment}")

            # スケール情報検出
            if any(keyword in comment.lower() for keyword in ['scale', 'unit', 'mm', 'cm', 'meter']):
                print(f"  ⚠️ スケール関連情報検出!")

    # 頂点サンプリング
    print(f"\n[頂点サンプリング（1000点）]")
    vertices = sample_vertices(ply_path, num_samples=1000)

    if vertices is None or len(vertices) == 0:
        print("❌ エラー: 頂点データ読み込み失敗")
        return None

    print(f"  サンプル数: {len(vertices)}")

    # バウンディングボックス
    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    bbox_size = bbox_max - bbox_min
    bbox_center = (bbox_min + bbox_max) / 2

    print(f"\n[バウンディングボックス]")
    print(f"  最小値: [{bbox_min[0]:.6f}, {bbox_min[1]:.6f}, {bbox_min[2]:.6f}]")
    print(f"  最大値: [{bbox_max[0]:.6f}, {bbox_max[1]:.6f}, {bbox_max[2]:.6f}]")
    print(f"  サイズ: [{bbox_size[0]:.6f}, {bbox_size[1]:.6f}, {bbox_size[2]:.6f}]")
    print(f"  中心:   [{bbox_center[0]:.6f}, {bbox_center[1]:.6f}, {bbox_center[2]:.6f}]")

    # スケール推定
    max_dimension = bbox_size.max()
    print(f"\n[スケール推定]")
    print(f"  最大寸法: {max_dimension:.6f}")

    # 単位判定（お椀の典型的サイズ: 直径10-15cm, 高さ5-8cm）
    diameter_mm = None
    unit = None
    scale_ok = False

    if 0.08 < max_dimension < 0.20:
        unit = "メートル (m)"
        diameter_mm = max_dimension * 1000
        scale_ok = True
    elif 80 < max_dimension < 200:
        unit = "ミリメートル (mm)"
        diameter_mm = max_dimension
        scale_ok = True
    elif 8 < max_dimension < 20:
        unit = "センチメートル (cm)"
        diameter_mm = max_dimension * 10
        scale_ok = True
    else:
        unit = "不明（正規化済み？）"
        scale_ok = False

    print(f"  推定単位: {unit}")

    if scale_ok:
        print(f"  ✅ 実物サイズ保持: YES")
        print(f"  推定直径: {diameter_mm:.1f} mm ({diameter_mm/10:.1f} cm)")
        print(f"  推定高さ: {bbox_size[2] if unit == 'ミリメートル (mm)' else bbox_size[2]*1000 if unit == 'メートル (m)' else bbox_size[2]*10:.1f} mm")
    else:
        print(f"  ❌ 実物サイズ保持: NO")
        print(f"  ⚠️ スケール変換が必要")

    return {
        "file": ply_path.name,
        "vertices": header['vertices'],
        "faces": header['faces'],
        "bbox_size": bbox_size,
        "max_dimension": max_dimension,
        "unit": unit,
        "diameter_mm": diameter_mm,
        "scale_ok": scale_ok
    }


def main():
    """メイン処理"""

    print("="*70)
    print("お椀3Dモデル スケール情報検証（高速版）")
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
        result = analyze_bowl_ply(ply_file)
        if result:
            results.append(result)

    # サマリー
    print(f"\n{'='*70}")
    print("サマリー")
    print(f"{'='*70}\n")

    if results:
        print(f"{'ファイル':<25} {'頂点数':<12} {'直径(mm)':<12} {'単位':<15} {'スケール'}")
        print("-" * 80)

        for r in results:
            diameter_str = f"{r['diameter_mm']:.1f}" if r['diameter_mm'] else "不明"
            scale_str = "✅" if r['scale_ok'] else "❌"
            print(f"{r['file']:<25} {r['vertices']:>10,}  {diameter_str:<12} {r['unit']:<15} {scale_str}")

        # 実物サイズ保持判定
        scale_ok_count = sum(1 for r in results if r['scale_ok'])

        print(f"\n{'='*70}")
        if scale_ok_count == len(results):
            print("✅ 結論: すべてのメッシュが実物サイズ（絶対値）を保持しています")
            print("")
            print("  → 体積推定パイプラインで使用可能")
            print("  → スケール参照用のお椀として利用可能")
        elif scale_ok_count > 0:
            print(f"⚠️ 結論: {scale_ok_count}/{len(results)} 個のメッシュが実物サイズを保持")
            print("")
            print("  → スケール保持メッシュを使用してください")
        else:
            print("❌ 結論: 実物サイズが保持されていません")
            print("")
            print("  → Blenderでスケール変換が必要")
            print("  → または実寸測定してスケール係数を適用")
        print(f"{'='*70}")

    print("\n✓ 分析完了")


if __name__ == "__main__":
    main()
