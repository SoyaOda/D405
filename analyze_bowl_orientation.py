#!/usr/bin/env python3
"""
お椀メッシュの座標系と主軸分析
元の座標系とPCAを比較して、真っ直ぐかどうかを確認
"""

import numpy as np
import open3d as o3d
from pathlib import Path
from sklearn.decomposition import PCA

def analyze_bowl_orientation(ply_path):
    """
    お椀の向きを分析

    Args:
        ply_path: .plyファイルパス

    Returns:
        dict: 分析結果
    """
    print(f"\n{'='*70}")
    print(f"分析: {ply_path.name}")
    print(f"{'='*70}")

    # メッシュ読み込み
    print("\nメッシュ読み込み中...")
    mesh = o3d.io.read_triangle_mesh(str(ply_path))

    if not mesh.has_vertices():
        print("❌ エラー: 頂点データなし")
        return None

    vertices = np.asarray(mesh.vertices)
    num_vertices = len(vertices)

    print(f"頂点数: {num_vertices:,}")

    # ========================================
    # 1. 元の座標系での分析
    # ========================================
    print(f"\n{'='*70}")
    print("[1] 元の座標系分析")
    print(f"{'='*70}")

    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    bbox_size = bbox_max - bbox_min
    bbox_center = (bbox_min + bbox_max) / 2

    print(f"\nバウンディングボックス（mm）:")
    print(f"  最小値: [{bbox_min[0]:.2f}, {bbox_min[1]:.2f}, {bbox_min[2]:.2f}]")
    print(f"  最大値: [{bbox_max[0]:.2f}, {bbox_max[1]:.2f}, {bbox_max[2]:.2f}]")
    print(f"  サイズ: [{bbox_size[0]:.2f}, {bbox_size[1]:.2f}, {bbox_size[2]:.2f}]")
    print(f"  中心:   [{bbox_center[0]:.2f}, {bbox_center[1]:.2f}, {bbox_center[2]:.2f}]")

    # 各軸のサイズを比較
    print(f"\n各軸のサイズ比較:")
    print(f"  X軸（横）: {bbox_size[0]:.2f} mm ({bbox_size[0]/10:.1f} cm)")
    print(f"  Y軸（奥）: {bbox_size[1]:.2f} mm ({bbox_size[1]/10:.1f} cm)")
    print(f"  Z軸（高）: {bbox_size[2]:.2f} mm ({bbox_size[2]/10:.1f} cm)")

    # お椀の向き推定（元の座標系）
    # 通常のお椀: X, Yが直径（大）、Zが高さ（小）
    horizontal_size = max(bbox_size[0], bbox_size[1])
    vertical_size = bbox_size[2]

    print(f"\n向き推定（元の座標系）:")
    print(f"  水平方向サイズ: {horizontal_size:.2f} mm")
    print(f"  垂直方向サイズ: {vertical_size:.2f} mm")
    print(f"  アスペクト比: {horizontal_size/vertical_size:.2f}")

    # 真っ直ぐかどうか判定
    # お椀は通常、直径が高さの1.5-3倍程度
    is_upright_original = 1.5 < (horizontal_size / vertical_size) < 4.0

    if is_upright_original:
        print(f"  ✅ 判定: 真っ直ぐ（Z軸が垂直方向）")
        print(f"  → X-Y平面が水平、Z軸が垂直")
    else:
        print(f"  ⚠️ 判定: 傾いている可能性あり")

    # ========================================
    # 2. PCA（主成分分析）
    # ========================================
    print(f"\n{'='*70}")
    print("[2] PCA（主成分分析）")
    print(f"{'='*70}")

    # 中心化
    centered_vertices = vertices - bbox_center

    # PCA実行
    pca = PCA(n_components=3)
    pca.fit(centered_vertices)

    principal_axes = pca.components_
    explained_variance = pca.explained_variance_

    print(f"\n主成分軸:")
    for i in range(3):
        print(f"  PC{i+1}: [{principal_axes[i,0]:7.4f}, {principal_axes[i,1]:7.4f}, {principal_axes[i,2]:7.4f}]")
        print(f"       分散: {explained_variance[i]:.2f} mm²")

    # 主成分の大きさ（分散の平方根 = 標準偏差）
    principal_stds = np.sqrt(explained_variance)

    print(f"\n主成分の広がり（標準偏差）:")
    print(f"  PC1（最大）: {principal_stds[0]:.2f} mm ({principal_stds[0]/10:.1f} cm)")
    print(f"  PC2（中間）: {principal_stds[1]:.2f} mm ({principal_stds[1]/10:.1f} cm)")
    print(f"  PC3（最小）: {principal_stds[2]:.2f} mm ({principal_stds[2]/10:.1f} cm)")

    # PC3（最小主成分）が垂直方向のはず
    print(f"\nPCAによる向き推定:")
    print(f"  水平方向（PC1, PC2）: {principal_stds[0]:.2f}, {principal_stds[1]:.2f} mm")
    print(f"  垂直方向（PC3）: {principal_stds[2]:.2f} mm")

    # ========================================
    # 3. 元の座標系とPCAの比較
    # ========================================
    print(f"\n{'='*70}")
    print("[3] 座標系比較")
    print(f"{'='*70}")

    # 元のZ軸とPC3（垂直方向）の角度
    z_axis = np.array([0, 0, 1])
    pc3 = principal_axes[2]

    # 内積で角度計算
    dot_product = np.dot(z_axis, pc3)
    angle_deg = np.arccos(np.clip(dot_product, -1.0, 1.0)) * 180 / np.pi

    # 最小角度（逆向きも考慮）
    angle_deg = min(angle_deg, 180 - angle_deg)

    print(f"\n元のZ軸とPCA-PC3の角度:")
    print(f"  角度: {angle_deg:.2f}度")

    if angle_deg < 10:
        print(f"  ✅ 一致: Z軸が垂直方向（PCA不要）")
        alignment = "ALIGNED"
    elif angle_deg < 30:
        print(f"  ⚠️ ほぼ一致: 微調整が有効な可能性")
        alignment = "MOSTLY_ALIGNED"
    else:
        print(f"  ❌ 不一致: PCA補正が必要")
        alignment = "MISALIGNED"

    # X-Y平面の比較
    xy_ratio_original = bbox_size[0] / bbox_size[1]
    pc12_ratio = principal_stds[0] / principal_stds[1]

    print(f"\n水平面のアスペクト比:")
    print(f"  元のX/Y比: {xy_ratio_original:.2f}")
    print(f"  PCA PC1/PC2比: {pc12_ratio:.2f}")

    if 0.8 < xy_ratio_original < 1.2:
        print(f"  ✅ X-Y平面はほぼ円形（お椀の特徴）")

    # ========================================
    # 4. 直径と高さの計算
    # ========================================
    print(f"\n{'='*70}")
    print("[4] 直径と高さの計算")
    print(f"{'='*70}")

    # 元の座標系での計算
    diameter_original = horizontal_size
    height_original = vertical_size

    print(f"\n元の座標系:")
    print(f"  直径: {diameter_original:.2f} mm ({diameter_original/10:.1f} cm)")
    print(f"  高さ: {height_original:.2f} mm ({height_original/10:.1f} cm)")

    # PCAでの計算（水平方向の最大値を直径とする）
    diameter_pca = max(principal_stds[0], principal_stds[1]) * 2  # 標準偏差→直径
    height_pca = principal_stds[2] * 2

    print(f"\nPCA:")
    print(f"  直径: {diameter_pca:.2f} mm ({diameter_pca/10:.1f} cm)")
    print(f"  高さ: {height_pca:.2f} mm ({height_pca/10:.1f} cm)")

    # ========================================
    # 5. 推奨される使用方法
    # ========================================
    print(f"\n{'='*70}")
    print("[5] 推奨される使用方法")
    print(f"{'='*70}")

    if alignment == "ALIGNED":
        print(f"\n✅ 推奨: 元の座標系をそのまま使用")
        print(f"\n  理由:")
        print(f"    - Z軸が垂直方向と一致（角度差 {angle_deg:.2f}度）")
        print(f"    - PCA補正不要")
        print(f"    - 計算コスト削減")
        print(f"\n  使用する値:")
        print(f"    - 水平方向: X-Y平面")
        print(f"    - 垂直方向: Z軸")
        print(f"    - 直径: {diameter_original:.2f} mm")
        print(f"    - 高さ: {height_original:.2f} mm")

    elif alignment == "MOSTLY_ALIGNED":
        print(f"\n⚠️ 推奨: 元の座標系を使用（オプションでPCA）")
        print(f"\n  理由:")
        print(f"    - Z軸がほぼ垂直方向（角度差 {angle_deg:.2f}度）")
        print(f"    - PCA補正で精度向上の可能性あり")
        print(f"\n  使用する値（元の座標系）:")
        print(f"    - 直径: {diameter_original:.2f} mm")
        print(f"    - 高さ: {height_original:.2f} mm")

    else:
        print(f"\n❌ 推奨: PCA補正が必要")
        print(f"\n  理由:")
        print(f"    - Z軸が垂直方向とずれている（角度差 {angle_deg:.2f}度）")
        print(f"    - PCA補正で正しい向きを取得")
        print(f"\n  使用する値（PCA）:")
        print(f"    - 直径: {diameter_pca:.2f} mm")
        print(f"    - 高さ: {height_pca:.2f} mm")

    return {
        "file": ply_path.name,
        "alignment": alignment,
        "angle_deg": angle_deg,
        "diameter_original": diameter_original,
        "height_original": height_original,
        "diameter_pca": diameter_pca,
        "height_pca": height_pca,
        "original_axes": {
            "horizontal": ["X", "Y"],
            "vertical": "Z"
        },
        "pca_axes": {
            "PC1": principal_axes[0].tolist(),
            "PC2": principal_axes[1].tolist(),
            "PC3": principal_axes[2].tolist()
        }
    }


def main():
    """メイン処理"""

    print("="*70)
    print("お椀メッシュ 座標系・主軸分析")
    print("="*70)

    mesh_dir = Path("/Users/moei/program/D405/data/mesh_output")

    # 最初のファイルを分析
    ply_file = mesh_dir / "001_bowl_mesh.ply"

    if not ply_file.exists():
        print(f"❌ エラー: {ply_file} が存在しません")
        return

    result = analyze_bowl_orientation(ply_file)

    if result:
        print(f"\n{'='*70}")
        print("完了")
        print(f"{'='*70}")


if __name__ == "__main__":
    main()
