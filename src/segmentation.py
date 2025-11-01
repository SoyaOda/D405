#!/usr/bin/env python3
"""
SAM2.1-based Segmentation Module

SAM2.1（Segment Anything Model 2.1）を使用したお椀と食品のセグメンテーション。

参考:
- https://github.com/facebookresearch/sam2
- SAM2.1リリース: 2024年9月
"""

import numpy as np
import cv2
import torch
from typing import Optional, Tuple, List
from pathlib import Path


class SAM2Segmentor:
    """
    SAM2.1を使用したセグメンテーションクラス

    お椀や食品の自動セグメンテーションを実行
    """

    def __init__(
        self,
        model_type: str = "sam2.1_hiera_large",
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Args:
            model_type: モデルタイプ
                - sam2.1_hiera_tiny
                - sam2.1_hiera_small
                - sam2.1_hiera_base_plus
                - sam2.1_hiera_large (default)
            device: 実行デバイス ('cuda' or 'cpu')
        """
        self.device = device
        self.model_type = model_type
        self.predictor = None

        print(f"SAM2.1 Segmentor初期化中...")
        print(f"  モデル: {model_type}")
        print(f"  デバイス: {device}")

        self._load_model()

    def _load_model(self):
        """SAM2.1モデルをロード"""
        try:
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor

            # Hugging Faceから事前学習済みモデルをロード
            print(f"  Hugging Faceから{self.model_type}をロード中...")
            # モデル名変換: sam2.1_hiera_tiny -> facebook/sam2.1-hiera-tiny
            model_id = f"facebook/{self.model_type.replace('_', '-')}"
            print(f"  モデルID: {model_id}")
            print(f"  デバイス: {self.device}")
            self.predictor = SAM2ImagePredictor.from_pretrained(
                model_id,
                device=self.device
            )

            print("✓ SAM2.1ロード完了")

        except ImportError as e:
            print(f"エラー: SAM2がインストールされていません")
            print(f"インストール方法:")
            print(f"  git clone https://github.com/facebookresearch/sam2.git")
            print(f"  cd sam2 && pip install -e .")
            raise
        except Exception as e:
            print(f"エラー: SAM2.1のロードに失敗: {e}")
            raise

    def segment_bowl_automatic(
        self,
        rgb_image: np.ndarray,
        num_points: int = 10
    ) -> Optional[np.ndarray]:
        """
        自動グリッドポイントでお椀をセグメント

        Args:
            rgb_image: RGB画像 (H, W, 3)
            num_points: グリッドポイント数

        Returns:
            mask: お椀のマスク (H, W) bool配列、失敗時None
        """
        print(f"\nお椀の自動セグメンテーション...")

        # 画像をセット
        with torch.inference_mode():
            self.predictor.set_image(rgb_image)

        # 画像中央付近にグリッドポイントを生成
        h, w = rgb_image.shape[:2]
        grid_points = self._generate_center_grid(h, w, num_points)

        # マルチポイントプロンプトでセグメント
        masks, scores, logits = self.predict_with_points(
            point_coords=grid_points,
            point_labels=np.ones(len(grid_points))  # すべて前景ポイント
        )

        if masks is None or len(masks) == 0:
            print("  ⚠️ セグメンテーション失敗")
            return None

        # 最もスコアが高いマスクを選択
        best_idx = np.argmax(scores)
        mask = masks[best_idx]

        print(f"  ✓ お椀検出成功（スコア: {scores[best_idx]:.3f}）")
        print(f"    マスク面積: {mask.sum()} pixels ({mask.sum()/(h*w)*100:.1f}%)")

        return mask

    def segment_bowl_with_bbox(
        self,
        rgb_image: np.ndarray,
        bbox: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        """
        バウンディングボックスプロンプトでお椀をセグメント

        Args:
            rgb_image: RGB画像 (H, W, 3)
            bbox: (x1, y1, x2, y2) バウンディングボックス

        Returns:
            mask: お椀のマスク (H, W) bool配列、失敗時None
        """
        print(f"\nお椀のセグメンテーション（BBoxプロンプト）...")
        print(f"  BBox: {bbox}")

        # 画像をセット
        with torch.inference_mode():
            self.predictor.set_image(rgb_image)

        # BBoxプロンプトでセグメント
        masks, scores, logits = self.predict_with_box(bbox)

        if masks is None or len(masks) == 0:
            print("  ⚠️ セグメンテーション失敗")
            return None

        # 最もスコアが高いマスクを選択
        best_idx = np.argmax(scores)
        mask = masks[best_idx]

        h, w = mask.shape
        print(f"  ✓ お椀検出成功（スコア: {scores[best_idx]:.3f}）")
        print(f"    マスク面積: {mask.sum()} pixels ({mask.sum()/(h*w)*100:.1f}%)")

        return mask

    def predict_with_points(
        self,
        point_coords: np.ndarray,
        point_labels: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """
        ポイントプロンプトで予測

        Args:
            point_coords: ポイント座標 (N, 2) [[x, y], ...]
            point_labels: ポイントラベル (N,) [1=前景, 0=背景]

        Returns:
            masks: マスク (M, H, W)
            scores: スコア (M,)
            logits: ロジット (M, H, W)
        """
        try:
            with torch.inference_mode():
                masks, scores, logits = self.predictor.predict(
                    point_coords=point_coords,
                    point_labels=point_labels,
                    multimask_output=True
                )
            return masks, scores, logits
        except Exception as e:
            print(f"  エラー: 予測失敗: {e}")
            return None, None, None

    def predict_with_box(
        self,
        bbox: Tuple[int, int, int, int]
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """
        バウンディングボックスプロンプトで予測

        Args:
            bbox: (x1, y1, x2, y2)

        Returns:
            masks: マスク (M, H, W)
            scores: スコア (M,)
            logits: ロジット (M, H, W)
        """
        try:
            with torch.inference_mode():
                masks, scores, logits = self.predictor.predict(
                    box=np.array(bbox),
                    multimask_output=True
                )
            return masks, scores, logits
        except Exception as e:
            print(f"  エラー: 予測失敗: {e}")
            return None, None, None

    def _generate_center_grid(
        self,
        height: int,
        width: int,
        num_points: int
    ) -> np.ndarray:
        """
        画像中央付近にグリッドポイントを生成

        Args:
            height: 画像高さ
            width: 画像幅
            num_points: ポイント数

        Returns:
            points: (N, 2) [[x, y], ...]
        """
        # 画像中央60%の領域
        cx, cy = width // 2, height // 2
        margin_x, margin_y = int(width * 0.3), int(height * 0.3)

        # グリッドサイズ計算
        grid_size = int(np.sqrt(num_points))

        # グリッド生成
        x_coords = np.linspace(cx - margin_x, cx + margin_x, grid_size)
        y_coords = np.linspace(cy - margin_y, cy + margin_y, grid_size)

        xx, yy = np.meshgrid(x_coords, y_coords)
        points = np.stack([xx.ravel(), yy.ravel()], axis=1)

        return points.astype(np.float32)

    def visualize_mask(
        self,
        rgb_image: np.ndarray,
        mask: np.ndarray,
        alpha: float = 0.5,
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        マスクを画像に重畳表示

        Args:
            rgb_image: RGB画像 (H, W, 3)
            mask: マスク (H, W) bool配列
            alpha: 透明度
            color: マスク色 (R, G, B)

        Returns:
            overlay: マスク重畳画像
        """
        overlay = rgb_image.copy()
        # マスクをbool型に変換
        mask_bool = mask.astype(bool)
        overlay[mask_bool] = (
            overlay[mask_bool] * (1 - alpha) +
            np.array(color) * alpha
        ).astype(np.uint8)

        # 輪郭を描画
        contours, _ = cv2.findContours(
            mask_bool.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(overlay, contours, -1, color, 2)

        return overlay


def segment_bowl_simple(
    rgb_image_path: str,
    output_mask_path: Optional[str] = None,
    visualize: bool = True
) -> Optional[np.ndarray]:
    """
    シンプルなお椀セグメンテーション関数

    Args:
        rgb_image_path: RGB画像のパス
        output_mask_path: マスク保存先（Noneなら保存しない）
        visualize: 可視化するか

    Returns:
        mask: お椀のマスク、失敗時None
    """
    # 画像読み込み
    rgb_image = cv2.imread(rgb_image_path)
    if rgb_image is None:
        print(f"エラー: 画像読み込み失敗: {rgb_image_path}")
        return None

    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2RGB)

    # セグメンテーション
    segmentor = SAM2Segmentor()
    mask = segmentor.segment_bowl_automatic(rgb_image)

    if mask is None:
        return None

    # マスク保存
    if output_mask_path:
        cv2.imwrite(output_mask_path, (mask * 255).astype(np.uint8))
        print(f"✓ マスク保存: {output_mask_path}")

    # 可視化
    if visualize:
        overlay = segmentor.visualize_mask(rgb_image, mask)
        overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)

        vis_path = str(Path(rgb_image_path).parent /
                       f"bowl_segmented_{Path(rgb_image_path).stem}.png")
        cv2.imwrite(vis_path, overlay_bgr)
        print(f"✓ 可視化保存: {vis_path}")

    return mask


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使い方: python3 src/segmentation.py <rgb_image_path>")
        sys.exit(1)

    rgb_path = sys.argv[1]
    mask = segment_bowl_simple(rgb_path, visualize=True)

    if mask is not None:
        print(f"\n✓ セグメンテーション成功")
        print(f"  マスクサイズ: {mask.shape}")
        print(f"  マスク面積: {mask.sum()} pixels")
