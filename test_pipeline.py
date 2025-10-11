#!/usr/bin/env python3
"""
RealSense D405 パイプライン動作確認スクリプト
使い方: sudo python3 test_pipeline.py
"""

import pyrealsense2 as rs
import numpy as np

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

print('パイプラインを開始中...')
pipeline.start(config)
print('✓ パイプライン開始成功!')

for i in range(5):
    frames = pipeline.wait_for_frames()
    depth = frames.get_depth_frame()
    color = frames.get_color_frame()
    if depth and color:
        print(f'フレーム {i+1}: 深度={depth.get_width()}x{depth.get_height()}, カラー={color.get_width()}x{color.get_height()}')

pipeline.stop()
print('✓ テスト完了!')
