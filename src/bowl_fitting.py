#!/usr/bin/env python3
"""
Bowl 3D Model Fitting Module

ICP（Iterative Closest Point）アルゴリズムを使用して、
お椀の3Dモデルを深度点群にフィッティングし、
物理スケールファクターを推定します。

参考:
- Open3D ICP: http://www.open3d.org/docs/latest/tutorial/pipelines/icp_registration.html
- 食品体積推定研究: https://arxiv.org/html/2404.12257
"""

import numpy as np
import open3d as o3d
from typing import Tuple, Optional, Dict
from pathlib import Path


class BowlFitter:
    """
    お椀の3Dモデルフィッティングクラス

    深度点群にお椀の3Dモデルをフィッティングして、
    位置・姿勢・スケールを推定します。
    """

    def __init__(
        self,
        bowl_model_path: str,
        bowl_real_diameter_mm: float
    ):
        """
        Args:
            bowl_model_path: お椀の3Dモデルパス (.ply, .obj, .stl)
            bowl_real_diameter_mm: お椀の実際の直径（mm）
        """
        self.bowl_model_path = bowl_model_path
        self.bowl_real_diameter_mm = bowl_real_diameter_mm
        self.bowl_mesh = None
        self.bowl_pcd = None

        print(f"BowlFitter初期化中...")
        print(f"  3Dモデル: {bowl_model_path}")
        print(f"  実寸直径: {bowl_real_diameter_mm} mm")

        self._load_bowl_model()

    def _load_bowl_model(self):
        """お椀の3Dモデルをロード"""
        try:
            # メッシュ読み込み
            self.bowl_mesh = o3d.io.read_triangle_mesh(self.bowl_model_path)

            if not self.bowl_mesh.has_vertices():
                raise ValueError(f"メッシュに頂点がありません: {self.bowl_model_path}")

            # 法線計算
            self.bowl_mesh.compute_vertex_normals()

            # 点群に変換（サンプリング）
            self.bowl_pcd = self.bowl_mesh.sample_points_uniformly(
                number_of_points=10000
            )

            # モデル情報
            vertices = np.asarray(self.bowl_mesh.vertices)
            print(f"✓ 3Dモデルロード完了")
            print(f"    頂点数: {len(vertices)}")
            print(f"    点群数: {len(self.bowl_pcd.points)}")
            print(f"    Bounding Box: {vertices.min(axis=0)} ~ {vertices.max(axis=0)}")

        except Exception as e:
            print(f"エラー: 3Dモデルのロードに失敗: {e}")
            raise

    def fit_to_depth_points(
        self,
        depth_points: np.ndarray,
        max_iterations: int = 100,
        voxel_size: float = 2.0
    ) -> Dict:
        """
        深度点群にお椀の3Dモデルをフィッティング

        Args:
            depth_points: 深度点群 (N, 3) [x, y, z] in mm
            max_iterations: ICP最大反復回数
            voxel_size: ダウンサンプリングボクセルサイズ（mm）

        Returns:
            result: {
                'transformation': 変換行列 (4, 4),
                'scale_factor': スケールファクター,
                'fitness': フィッティングスコア,
                'measured_diameter_mm': 測定直径（mm）
            }
        """
        print(f"\nお椀の3Dモデルフィッティング...")
        print(f"  深度点群: {len(depth_points)} points")
        print(f"  ボクセルサイズ: {voxel_size} mm")

        # 深度点群をOpen3D形式に変換
        target_pcd = o3d.geometry.PointCloud()
        target_pcd.points = o3d.utility.Vector3dVector(depth_points)

        # ダウンサンプリング
        target_down = target_pcd.voxel_down_sample(voxel_size)
        source_down = self.bowl_pcd.voxel_down_sample(voxel_size)

        print(f"  ダウンサンプリング後: target={len(target_down.points)}, "
              f"source={len(source_down.points)}")

        # 初期位置推定（重心合わせ）
        target_center = target_down.get_center()
        source_center = source_down.get_center()
        initial_transform = np.eye(4)
        initial_transform[:3, 3] = target_center - source_center

        print(f"  初期変換: 重心オフセット = {target_center - source_center}")

        # 法線推定
        target_down.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=voxel_size * 2, max_nn=30
            )
        )
        source_down.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=voxel_size * 2, max_nn=30
            )
        )

        # ICP実行（Point-to-Plane）
        print(f"  ICP実行中（最大{max_iterations}回）...")
        icp_result = o3d.pipelines.registration.registration_icp(
            source_down,
            target_down,
            max_correspondence_distance=voxel_size * 3,
            init=initial_transform,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            criteria=o3d.pipelines.registration.ICPConvergenceCriteria(
                max_iteration=max_iterations
            )
        )

        print(f"  ✓ ICP完了")
        print(f"    Fitness: {icp_result.fitness:.4f}")
        print(f"    RMSE: {icp_result.inlier_rmse:.2f} mm")

        # スケールファクター推定
        scale_factor = self._estimate_scale_factor(
            depth_points,
            icp_result.transformation
        )

        # 測定直径計算
        measured_diameter_mm = self._measure_diameter(depth_points)

        result = {
            'transformation': icp_result.transformation,
            'scale_factor': scale_factor,
            'fitness': icp_result.fitness,
            'rmse': icp_result.inlier_rmse,
            'measured_diameter_mm': measured_diameter_mm,
            'scale_accuracy_percent': abs(1 - scale_factor) * 100
        }

        print(f"\n  【スケール推定結果】")
        print(f"    実寸直径: {self.bowl_real_diameter_mm:.1f} mm")
        print(f"    測定直径: {measured_diameter_mm:.1f} mm")
        print(f"    スケールファクター: {scale_factor:.4f}")
        print(f"    精度: ±{result['scale_accuracy_percent']:.2f}%")

        return result

    def _estimate_scale_factor(
        self,
        depth_points: np.ndarray,
        transformation: np.ndarray
    ) -> float:
        """
        スケールファクターを推定

        Args:
            depth_points: 深度点群 (N, 3)
            transformation: ICP変換行列 (4, 4)

        Returns:
            scale_factor: 実寸/測定値
        """
        # 深度点群の直径測定
        measured_diameter = self._measure_diameter(depth_points)

        # スケールファクター = 実寸 / 測定値
        scale_factor = self.bowl_real_diameter_mm / measured_diameter

        return scale_factor

    def _measure_diameter(self, points: np.ndarray) -> float:
        """
        点群の最大直径を測定

        Args:
            points: 点群 (N, 3)

        Returns:
            diameter: 直径（mm）
        """
        # XY平面での最大距離
        xy_points = points[:, :2]  # X, Y座標のみ

        # 重心
        center = xy_points.mean(axis=0)

        # 重心からの距離
        distances = np.linalg.norm(xy_points - center, axis=1)

        # 直径 = 最大半径 × 2
        diameter = distances.max() * 2

        return diameter

    def extract_food_points(
        self,
        depth_points: np.ndarray,
        transformation: np.ndarray,
        height_threshold_mm: float = 5.0
    ) -> np.ndarray:
        """
        お椀の内側の食品点群のみを抽出

        Args:
            depth_points: 深度点群 (N, 3)
            transformation: ICP変換行列 (4, 4)
            height_threshold_mm: お椀の底面からの高さ閾値（mm）

        Returns:
            food_points: 食品点群 (M, 3)
        """
        print(f"\n食品点群の抽出...")

        # お椀の底面のZ座標を取得（変換後）
        bowl_vertices = np.asarray(self.bowl_mesh.vertices)
        bowl_vertices_hom = np.hstack([
            bowl_vertices,
            np.ones((len(bowl_vertices), 1))
        ])
        transformed_vertices = (transformation @ bowl_vertices_hom.T).T[:, :3]

        bowl_bottom_z = transformed_vertices[:, 2].min()

        print(f"  お椀底面のZ座標: {bowl_bottom_z:.1f} mm")

        # お椀の底面より上の点のみ
        food_points = depth_points[
            depth_points[:, 2] > bowl_bottom_z + height_threshold_mm
        ]

        print(f"  ✓ 食品点群抽出完了")
        print(f"    全点群: {len(depth_points)} points")
        print(f"    食品点群: {len(food_points)} points "
              f"({len(food_points)/len(depth_points)*100:.1f}%)")

        return food_points

    def visualize_fitting(
        self,
        depth_points: np.ndarray,
        transformation: np.ndarray,
        output_path: Optional[str] = None
    ):
        """
        フィッティング結果を可視化

        Args:
            depth_points: 深度点群 (N, 3)
            transformation: 変換行列 (4, 4)
            output_path: 保存先（Noneなら表示のみ）
        """
        print(f"\nフィッティング可視化...")

        # 深度点群
        target_pcd = o3d.geometry.PointCloud()
        target_pcd.points = o3d.utility.Vector3dVector(depth_points)
        target_pcd.paint_uniform_color([1, 0, 0])  # 赤

        # 変換後のお椀モデル
        fitted_mesh = o3d.geometry.TriangleMesh(self.bowl_mesh)
        fitted_mesh.transform(transformation)
        fitted_mesh.paint_uniform_color([0, 1, 0])  # 緑

        # 可視化
        geometries = [target_pcd, fitted_mesh]

        if output_path:
            # スクリーンショット保存
            vis = o3d.visualization.Visualizer()
            vis.create_window(visible=False)
            for geo in geometries:
                vis.add_geometry(geo)
            vis.poll_events()
            vis.update_renderer()
            vis.capture_screen_image(output_path)
            vis.destroy_window()
            print(f"  ✓ 可視化保存: {output_path}")
        else:
            # インタラクティブ表示
            o3d.visualization.draw_geometries(
                geometries,
                window_name="Bowl Fitting Result",
                width=1024,
                height=768
            )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("使い方: python3 src/bowl_fitting.py <bowl_model.ply> <real_diameter_mm>")
        print("例: python3 src/bowl_fitting.py data/bowl.ply 120")
        sys.exit(1)

    bowl_model_path = sys.argv[1]
    real_diameter = float(sys.argv[2])

    # サンプル点群生成（テスト用）
    print("テスト用点群生成中...")
    test_points = np.random.randn(1000, 3) * 50  # ランダム点群

    # フィッティング
    fitter = BowlFitter(bowl_model_path, real_diameter)
    result = fitter.fit_to_depth_points(test_points)

    print(f"\n✓ フィッティング完了")
    print(f"  スケールファクター: {result['scale_factor']:.4f}")
    print(f"  精度: ±{result['scale_accuracy_percent']:.2f}%")
