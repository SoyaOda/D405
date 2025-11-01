#!/usr/bin/env python3
"""
Food Volume Estimation Pipeline

SAM2.1 + ICP + お椀の3Dモデルを使用した食品体積推定パイプライン

パイプライン:
1. RGB画像からお椀をセグメント（SAM2.1）
2. 深度点群を生成
3. お椀の3Dモデルをフィッティング（ICP）
4. スケールファクター推定
5. 食品点群抽出
6. 絶対体積計算（ml単位）

使い方:
  python3 scripts/estimate_food_volume.py \\
    --rgb nutrition5k_data/imagery/realsense_overhead/rgb_food_*.png \\
    --depth nutrition5k_data/imagery/realsense_overhead/depth_raw_food_*.png \\
    --bowl-model data/bowl.ply \\
    --bowl-diameter 120 \\
    --output results/volume_food.json

必須:
  - SAM2.1インストール済み
  - Open3Dインストール済み
  - お椀の3Dモデル（.ply形式）
  - Tare Calibration実行済み
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import json
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

# 自作モジュール
from src.segmentation import SAM2Segmentor
from src.bowl_fitting import BowlFitter
from src.volume_calculation import VolumeCalculator, depth_to_pointcloud


def load_nutrition5k_depth(depth_path: str) -> np.ndarray:
    """
    Nutrition5k形式の深度画像をロード

    Args:
        depth_path: 深度画像パス（16-bit PNG, 10000 units/m）

    Returns:
        depth_image: (H, W) 16-bit配列
    """
    depth_image = cv2.imread(depth_path, cv2.IMREAD_ANYDEPTH)
    if depth_image is None:
        raise FileNotFoundError(f"深度画像が見つかりません: {depth_path}")
    return depth_image


def load_camera_intrinsics(metadata_path: str) -> dict:
    """
    メタデータからカメラ内部パラメータをロード

    Args:
        metadata_path: メタデータJSONパス

    Returns:
        intrinsics: {fx, fy, cx, cy}
    """
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    intrinsics = metadata.get('camera_intrinsics', {
        'fx': 424.0,  # D405 @ 848x480のデフォルト値
        'fy': 424.0,
        'cx': 424.0,
        'cy': 240.0
    })

    return intrinsics


def estimate_food_volume_pipeline(
    rgb_path: str,
    depth_path: str,
    bowl_model_path: str,
    bowl_diameter_mm: float,
    output_dir: str = "results",
    visualize: bool = True
) -> dict:
    """
    食品体積推定パイプライン

    Args:
        rgb_path: RGB画像パス
        depth_path: 深度画像パス
        bowl_model_path: お椀3Dモデルパス
        bowl_diameter_mm: お椀の実寸直径（mm）
        output_dir: 出力ディレクトリ
        visualize: 可視化するか

    Returns:
        result: 推定結果の辞書
    """
    print("=" * 70)
    print("Food Volume Estimation Pipeline")
    print("=" * 70)
    print(f"RGB画像: {rgb_path}")
    print(f"深度画像: {depth_path}")
    print(f"お椀モデル: {bowl_model_path}")
    print(f"お椀直径: {bowl_diameter_mm} mm")
    print("=" * 70)

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    # ===== ステップ1: RGB画像からお椀をセグメント =====
    print("\n【ステップ1】お椀のセグメンテーション（SAM2.1）")
    print("-" * 70)

    rgb_image = cv2.imread(rgb_path)
    if rgb_image is None:
        raise FileNotFoundError(f"RGB画像が見つかりません: {rgb_path}")
    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)

    segmentor = SAM2Segmentor()
    bowl_mask = segmentor.segment_bowl_automatic(rgb_image)

    if bowl_mask is None:
        raise RuntimeError("お椀のセグメンテーションに失敗しました")

    # マスク可視化
    if visualize:
        overlay = segmentor.visualize_mask(rgb_image, bowl_mask)
        overlay_path = os.path.join(output_dir, "bowl_segmented.png")
        cv2.imwrite(overlay_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
        print(f"  ✓ セグメント可視化: {overlay_path}")

    # ===== ステップ2: 深度点群を生成 =====
    print("\n【ステップ2】深度点群生成")
    print("-" * 70)

    depth_image = load_nutrition5k_depth(depth_path)

    # メタデータからカメラ内部パラメータ取得
    metadata_path = depth_path.replace('depth_raw_', 'metadata_').replace('.png', '.json')
    if os.path.exists(metadata_path):
        camera_intrinsics = load_camera_intrinsics(metadata_path)
    else:
        # デフォルト値（D405 @ 848x480）
        camera_intrinsics = {
            'fx': 424.0,
            'fy': 424.0,
            'cx': 424.0,
            'cy': 240.0
        }
        print(f"  ⚠️ メタデータなし、デフォルト値使用")

    print(f"  カメラ内部パラメータ: fx={camera_intrinsics['fx']:.1f}, "
          f"fy={camera_intrinsics['fy']:.1f}")

    # Nutrition5k形式: 10000 units/m → depth_scale = 0.0001 m/unit
    bowl_points = depth_to_pointcloud(
        depth_image,
        bowl_mask,
        camera_intrinsics,
        depth_scale=0.0001
    )

    print(f"  ✓ 点群生成完了: {len(bowl_points)} points")

    # ===== ステップ3: お椀の3Dモデルをフィッティング =====
    print("\n【ステップ3】お椀3Dモデルフィッティング（ICP）")
    print("-" * 70)

    fitter = BowlFitter(bowl_model_path, bowl_diameter_mm)
    fitting_result = fitter.fit_to_depth_points(bowl_points)

    scale_factor = fitting_result['scale_factor']

    # フィッティング可視化
    if visualize:
        fitting_vis_path = os.path.join(output_dir, "bowl_fitting.png")
        fitter.visualize_fitting(
            bowl_points,
            fitting_result['transformation'],
            output_path=fitting_vis_path
        )

    # ===== ステップ4: 食品点群を抽出 =====
    print("\n【ステップ4】食品点群抽出")
    print("-" * 70)

    food_points = fitter.extract_food_points(
        bowl_points,
        fitting_result['transformation'],
        height_threshold_mm=5.0
    )

    if len(food_points) == 0:
        print("  ⚠️ 食品点群が空です（お椀が空？）")
        volume_ml = 0.0
        volume_result = {
            'volume_ml': 0.0,
            'volume_cm3': 0.0,
            'method': 'empty'
        }
    else:
        # ===== ステップ5: 絶対体積計算 =====
        print("\n【ステップ5】絶対体積計算")
        print("-" * 70)

        calculator = VolumeCalculator(voxel_size_mm=1.0)
        volume_result = calculator.calculate_volume_voxel(
            food_points,
            scale_factor=scale_factor
        )

        volume_ml = volume_result['volume_ml']

    # ===== 結果まとめ =====
    print("\n" + "=" * 70)
    print("食品体積推定完了")
    print("=" * 70)

    result = {
        'timestamp': datetime.now().isoformat(),
        'rgb_image': rgb_path,
        'depth_image': depth_path,
        'bowl_model': bowl_model_path,
        'bowl_real_diameter_mm': bowl_diameter_mm,
        'bowl_measured_diameter_mm': fitting_result['measured_diameter_mm'],
        'scale_factor': scale_factor,
        'scale_accuracy_percent': fitting_result['scale_accuracy_percent'],
        'icp_fitness': fitting_result['fitness'],
        'icp_rmse': fitting_result['rmse'],
        'num_bowl_points': len(bowl_points),
        'num_food_points': len(food_points),
        'food_volume_ml': volume_ml,
        'food_volume_cm3': volume_ml,
        'volume_calculation_method': volume_result.get('method', 'empty'),
        'camera_intrinsics': camera_intrinsics
    }

    print(f"\n【最終結果】")
    print(f"  食品体積: {volume_ml:.1f} ml ({volume_ml:.1f} cm³)")
    print(f"  スケール精度: ±{fitting_result['scale_accuracy_percent']:.2f}%")
    print(f"  お椀実寸: {bowl_diameter_mm:.1f} mm")
    print(f"  お椀測定: {fitting_result['measured_diameter_mm']:.1f} mm")
    print(f"  食品点群: {len(food_points):,} points")

    # 重量推定（オプション）
    if volume_ml > 0:
        # 仮定: ご飯の密度 ≈ 0.67 g/ml
        estimated_mass_g = volume_ml * 0.67
        result['estimated_mass_g'] = estimated_mass_g
        result['assumed_density_g_per_ml'] = 0.67
        print(f"  推定重量: {estimated_mass_g:.1f} g（密度0.67 g/ml仮定）")

    print("=" * 70)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Food Volume Estimation using SAM2.1 + ICP + Bowl 3D Model"
    )

    parser.add_argument(
        '--rgb',
        required=True,
        help='RGB画像パス'
    )
    parser.add_argument(
        '--depth',
        required=True,
        help='深度画像パス（Nutrition5k形式: 16-bit PNG, 10000 units/m）'
    )
    parser.add_argument(
        '--bowl-model',
        required=True,
        help='お椀の3Dモデルパス（.ply, .obj, .stl）'
    )
    parser.add_argument(
        '--bowl-diameter',
        type=float,
        required=True,
        help='お椀の実寸直径（mm）'
    )
    parser.add_argument(
        '--output',
        default='results/volume_estimation.json',
        help='出力JSONパス（デフォルト: results/volume_estimation.json）'
    )
    parser.add_argument(
        '--no-visualize',
        action='store_true',
        help='可視化を無効化'
    )

    args = parser.parse_args()

    # パイプライン実行
    try:
        result = estimate_food_volume_pipeline(
            rgb_path=args.rgb,
            depth_path=args.depth,
            bowl_model_path=args.bowl_model,
            bowl_diameter_mm=args.bowl_diameter,
            output_dir=str(Path(args.output).parent),
            visualize=not args.no_visualize
        )

        # 結果をJSON保存
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n✓ 結果保存: {args.output}")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
