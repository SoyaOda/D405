#!/usr/bin/env python3
"""
Food Volume Calculation Module

深度データから食品の絶対体積（ml単位）を計算します。

手法:
1. ボクセル法: 点群をボクセルグリッドに変換して体積計算
2. メッシュ法: 点群からメッシュを生成して体積計算
3. 積分法: 高さマップから数値積分

参考:
- Nutrition5k: 深度マップから直接計算
- 食品体積推定研究: ボクセル法が主流
"""

import numpy as np
import open3d as o3d
from typing import Dict, Optional, Tuple
from scipy.spatial import Delaunay


class VolumeCalculator:
    """
    食品体積計算クラス

    深度点群から絶対体積（ml）を計算
    """

    def __init__(self, voxel_size_mm: float = 1.0):
        """
        Args:
            voxel_size_mm: ボクセルサイズ（mm）
        """
        self.voxel_size_mm = voxel_size_mm

        print(f"VolumeCalculator初期化")
        print(f"  ボクセルサイズ: {voxel_size_mm} mm")

    def calculate_volume_voxel(
        self,
        food_points: np.ndarray,
        scale_factor: float = 1.0
    ) -> Dict:
        """
        ボクセル法で体積計算

        Args:
            food_points: 食品点群 (N, 3) [x, y, z] in mm
            scale_factor: スケールファクター（お椀フィッティングから）

        Returns:
            result: {
                'volume_ml': 体積（ml）,
                'volume_cm3': 体積（cm³）,
                'num_voxels': ボクセル数,
                'voxel_size_mm': ボクセルサイズ（mm）
            }
        """
        print(f"\n体積計算（ボクセル法）...")
        print(f"  点群数: {len(food_points)}")
        print(f"  スケールファクター: {scale_factor:.4f}")

        # ボクセルグリッドに変換
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(food_points)

        voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(
            pcd,
            voxel_size=self.voxel_size_mm
        )

        # ボクセル数
        num_voxels = len(voxel_grid.get_voxels())

        # 体積計算（mm³単位）
        voxel_volume_mm3 = self.voxel_size_mm ** 3
        total_volume_mm3 = num_voxels * voxel_volume_mm3

        # スケール補正（3乗に注意！）
        corrected_volume_mm3 = total_volume_mm3 * (scale_factor ** 3)

        # ml単位に変換（1ml = 1000mm³ = 1cm³）
        volume_ml = corrected_volume_mm3 / 1000

        result = {
            'volume_ml': volume_ml,
            'volume_cm3': volume_ml,  # 1ml = 1cm³
            'num_voxels': num_voxels,
            'voxel_size_mm': self.voxel_size_mm,
            'scale_factor': scale_factor,
            'method': 'voxel'
        }

        print(f"  ✓ 体積計算完了")
        print(f"    ボクセル数: {num_voxels:,}")
        print(f"    補正前: {total_volume_mm3/1000:.1f} ml")
        print(f"    補正後: {volume_ml:.1f} ml")

        return result

    def calculate_volume_mesh(
        self,
        food_points: np.ndarray,
        scale_factor: float = 1.0
    ) -> Dict:
        """
        メッシュ法で体積計算（Alpha Shape使用）

        Args:
            food_points: 食品点群 (N, 3)
            scale_factor: スケールファクター

        Returns:
            result: 体積情報の辞書
        """
        print(f"\n体積計算（メッシュ法）...")

        try:
            # 点群からメッシュ生成（Alpha Shape）
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(food_points)

            # Alpha Shapeでメッシュ生成
            alpha = self.voxel_size_mm * 3  # Alpha値
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(
                pcd, alpha
            )

            # 体積計算
            volume_mm3 = mesh.get_volume()

            # スケール補正
            corrected_volume_mm3 = volume_mm3 * (scale_factor ** 3)
            volume_ml = corrected_volume_mm3 / 1000

            result = {
                'volume_ml': volume_ml,
                'volume_cm3': volume_ml,
                'num_triangles': len(mesh.triangles),
                'alpha': alpha,
                'scale_factor': scale_factor,
                'method': 'mesh'
            }

            print(f"  ✓ 体積計算完了")
            print(f"    三角形数: {len(mesh.triangles):,}")
            print(f"    補正後: {volume_ml:.1f} ml")

            return result

        except Exception as e:
            print(f"  ⚠️ メッシュ法失敗: {e}")
            print(f"    ボクセル法にフォールバック")
            return self.calculate_volume_voxel(food_points, scale_factor)

    def calculate_volume_heightmap(
        self,
        depth_image: np.ndarray,
        food_mask: np.ndarray,
        camera_intrinsics: Dict,
        reference_plane_z_mm: float,
        scale_factor: float = 1.0
    ) -> Dict:
        """
        高さマップ法で体積計算（Nutrition5k方式）

        Args:
            depth_image: 深度画像 (H, W) Nutrition5k形式（10000 units/m）
            food_mask: 食品マスク (H, W) bool配列
            camera_intrinsics: カメラ内部パラメータ
            reference_plane_z_mm: 基準面のZ座標（mm）
            scale_factor: スケールファクター

        Returns:
            result: 体積情報の辞書
        """
        print(f"\n体積計算（高さマップ法）...")

        # 深度を mm 単位に変換
        depth_scale_m = depth_image / 10000.0  # Nutrition5k形式
        depth_mm = depth_scale_m * 1000

        # 食品領域のみ
        food_depths = depth_mm[food_mask]

        # 基準面からの高さ
        heights_mm = food_depths - reference_plane_z_mm
        heights_mm = np.maximum(heights_mm, 0)  # 負の値は0に

        # ピクセル面積（mm²）
        fx = camera_intrinsics['fx']
        pixel_area_mm2 = (1000 / fx) ** 2  # 概算

        # 体積計算（数値積分）
        volume_mm3 = np.sum(heights_mm) * pixel_area_mm2

        # スケール補正
        corrected_volume_mm3 = volume_mm3 * (scale_factor ** 3)
        volume_ml = corrected_volume_mm3 / 1000

        result = {
            'volume_ml': volume_ml,
            'volume_cm3': volume_ml,
            'num_pixels': food_mask.sum(),
            'mean_height_mm': heights_mm.mean(),
            'max_height_mm': heights_mm.max(),
            'scale_factor': scale_factor,
            'method': 'heightmap'
        }

        print(f"  ✓ 体積計算完了")
        print(f"    ピクセル数: {food_mask.sum():,}")
        print(f"    平均高さ: {heights_mm.mean():.1f} mm")
        print(f"    最大高さ: {heights_mm.max():.1f} mm")
        print(f"    補正後: {volume_ml:.1f} ml")

        return result

    def estimate_mass_from_volume(
        self,
        volume_ml: float,
        food_density_g_per_ml: float = 0.7
    ) -> Dict:
        """
        体積から重量を推定

        Args:
            volume_ml: 体積（ml）
            food_density_g_per_ml: 食品密度（g/ml）
                - ご飯: 0.67 g/ml
                - 水: 1.0 g/ml
                - サラダ: 0.3-0.5 g/ml

        Returns:
            result: {
                'mass_g': 重量（g）,
                'volume_ml': 体積（ml）,
                'density_g_per_ml': 密度（g/ml）
            }
        """
        mass_g = volume_ml * food_density_g_per_ml

        result = {
            'mass_g': mass_g,
            'volume_ml': volume_ml,
            'density_g_per_ml': food_density_g_per_ml
        }

        print(f"\n重量推定:")
        print(f"  体積: {volume_ml:.1f} ml")
        print(f"  密度: {food_density_g_per_ml} g/ml")
        print(f"  重量: {mass_g:.1f} g")

        return result

    def calculate_volume_depth_difference(
        self,
        depth_image: np.ndarray,
        food_mask: np.ndarray,
        bowl_mesh_aligned: o3d.geometry.TriangleMesh,
        camera_intrinsics: Dict,
        depth_scale: float = 0.0001
    ) -> Dict:
        """
        深度差分積分法による体積計算

        お椀の3D形状を基準面として使用し、
        各ピクセルでお椀底面までの距離をレイキャストで取得して積分

        Args:
            depth_image: 深度画像 (H, W) 16-bit
            food_mask: 食品マスク (H, W) bool
            bowl_mesh_aligned: ICPで位置合わせ済みのお椀メッシュ
            camera_intrinsics: カメラ内部パラメータ
            depth_scale: 深度スケール（m/unit）

        Returns:
            result: {
                'volume_ml': 体積（ml）,
                'volume_cm3': 体積（cm³）,
                'method': 'depth_difference_integration',
                'num_pixels': 総ピクセル数,
                'num_valid_pixels': 有効ピクセル数,
                'mean_height_mm': 平均高さ（mm）,
                'max_height_mm': 最大高さ（mm）,
                'min_height_mm': 最小高さ（mm）
            }
        """
        # raycast_utilsをインポート
        from .raycast_utils import raycast_bowl_surface, compute_pixel_area

        print(f"\n体積計算（深度差分積分法）...")
        print(f"  方法: お椀3D形状を基準面として使用")

        h, w = depth_image.shape
        fx = camera_intrinsics['fx']

        # 1. 食品領域のピクセル座標取得
        v_coords, u_coords = np.where(food_mask)
        pixel_coords = np.column_stack([u_coords, v_coords])
        N = len(pixel_coords)

        print(f"  食品ピクセル数: {N:,}")

        if N == 0:
            print("  ⚠️ 食品ピクセルが見つかりません")
            return {
                'volume_ml': 0,
                'volume_cm3': 0,
                'method': 'depth_difference_integration',
                'num_pixels': 0,
                'num_valid_pixels': 0,
                'mean_height_mm': 0,
                'max_height_mm': 0,
                'min_height_mm': 0
            }

        # 2. 深度カメラから食品表面までの距離
        food_depths_mm = depth_image[v_coords, u_coords] * depth_scale * 1000

        # 3. お椀底面までの距離（レイキャスト）
        print(f"  レイキャスト実行中...")
        bowl_depths_mm, hit_mask = raycast_bowl_surface(
            bowl_mesh_aligned,
            pixel_coords,
            camera_intrinsics,
            verbose=True
        )

        # 4. 食品の高さ = お椀底面 - 食品表面
        food_heights_mm = bowl_depths_mm - food_depths_mm

        # 5. 有効な高さのみ（正の値 かつ レイがヒット）
        valid_mask = (food_heights_mm > 0) & hit_mask
        food_heights_valid = food_heights_mm[valid_mask]
        food_depths_valid = food_depths_mm[valid_mask]

        num_valid = valid_mask.sum()
        print(f"  有効ピクセル: {num_valid:,} / {N:,} ({num_valid/N*100:.1f}%)")

        if num_valid == 0:
            print("  ⚠️ 有効なピクセルがありません")
            return {
                'volume_ml': 0,
                'volume_cm3': 0,
                'method': 'depth_difference_integration',
                'num_pixels': N,
                'num_valid_pixels': 0,
                'mean_height_mm': 0,
                'max_height_mm': 0,
                'min_height_mm': 0
            }

        # 6. 各ピクセルの面積計算（距離依存）
        pixel_areas_mm2 = (food_depths_valid / fx) ** 2

        # 7. 体積積分
        volume_mm3 = np.sum(food_heights_valid * pixel_areas_mm2)
        volume_ml = volume_mm3 / 1000

        # 8. 統計情報
        result = {
            'volume_ml': volume_ml,
            'volume_cm3': volume_ml,
            'method': 'depth_difference_integration',
            'num_pixels': N,
            'num_valid_pixels': num_valid,
            'mean_height_mm': food_heights_valid.mean(),
            'max_height_mm': food_heights_valid.max(),
            'min_height_mm': food_heights_valid.min(),
            'std_height_mm': food_heights_valid.std()
        }

        print(f"  ✓ 体積計算完了")
        print(f"    体積: {volume_ml:.1f} ml")
        print(f"    平均高さ: {result['mean_height_mm']:.1f} mm")
        print(f"    最大高さ: {result['max_height_mm']:.1f} mm")
        print(f"    最小高さ: {result['min_height_mm']:.1f} mm")

        return result


def depth_to_pointcloud(
    depth_image: np.ndarray,
    mask: np.ndarray,
    camera_intrinsics: Dict,
    depth_scale: float = 0.0001
) -> np.ndarray:
    """
    深度画像を3D点群に変換

    Args:
        depth_image: 深度画像 (H, W) 16-bit
        mask: マスク (H, W) bool配列
        camera_intrinsics: {
            'fx': 焦点距離X,
            'fy': 焦点距離Y,
            'cx': 主点X,
            'cy': 主点Y
        }
        depth_scale: 深度スケール（RealSense: 0.0001 m/unit）

    Returns:
        points: 点群 (N, 3) [x, y, z] in mm
    """
    h, w = depth_image.shape
    fx = camera_intrinsics['fx']
    fy = camera_intrinsics['fy']
    cx = camera_intrinsics['cx']
    cy = camera_intrinsics['cy']

    # ピクセル座標
    v, u = np.where(mask)

    # 深度値（m単位）
    z = depth_image[v, u] * depth_scale

    # 3D座標計算（m単位）
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy

    # mm単位に変換
    points = np.stack([x * 1000, y * 1000, z * 1000], axis=1)

    return points


if __name__ == "__main__":
    # テスト用サンプル点群
    print("テスト用点群生成...")

    # 半径50mm、高さ30mmの円柱状の食品を模擬
    theta = np.linspace(0, 2*np.pi, 100)
    r = np.random.uniform(0, 50, 1000)
    z = np.random.uniform(0, 30, 1000)
    x = r * np.cos(theta[np.random.randint(0, 100, 1000)])
    y = r * np.sin(theta[np.random.randint(0, 100, 1000)])

    test_points = np.stack([x, y, z], axis=1)

    # 体積計算
    calculator = VolumeCalculator(voxel_size_mm=1.0)

    # ボクセル法
    result_voxel = calculator.calculate_volume_voxel(
        test_points,
        scale_factor=1.0
    )

    # 理論値との比較
    theoretical_volume = np.pi * 50**2 * 30 / 1000  # ml
    print(f"\n理論値: {theoretical_volume:.1f} ml")
    print(f"計算値: {result_voxel['volume_ml']:.1f} ml")
    print(f"誤差: {abs(result_voxel['volume_ml'] - theoretical_volume):.1f} ml")
