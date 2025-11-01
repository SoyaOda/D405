# RealSense D405 Food Scanner
## Intel公式手法による高精度食材スキャンシステム

Intel RealSense D405カメラを使用した食材スキャンシステム。
**Intel公式のTare Calibration**と**推奨フィルターパイプライン**を採用し、Nutrition5kデータセット形式で出力します。

---

## 📋 特徴

### Intel公式技術の採用

✅ **Tare Calibration API**
- Intel公式の深度補正機能
- 1点のground truthで自動補正（slope + offset）
- カメラEEPROMに永続保存
- 全てのアプリで自動適用

✅ **D405最適設定**
- 解像度: 848x480（Intel推奨）
- Visual Preset: High Accuracy
- フレームレート: 60 FPS

✅ **Intel推奨フィルターパイプライン**
```
Depth → Decimation → Depth2Disparity → Spatial Filter
→ Temporal Filter → Disparity2Depth → Hole Filling
```

---

## 📁 プロジェクト構造

```
/Users/moei/program/D405/
├── scripts/                    # 実行可能スクリプト
│   ├── calibrate.py            # Intel Tare Calibration（実証済み）
│   ├── reset_calibration.py    # カメラのファクトリーリセット
│   └── scan.py                 # D405最適化スキャナー
├── data/                       # キャリブレーションデータ
│   └── (Tare calibrationはEEPROMに保存)
├── nutrition5k_data/           # スキャン結果
│   └── imagery/
│       └── realsense_overhead/
├── CALIBRATION_GUIDE.md        # キャリブレーションガイド（必読）
├── venv/                       # Python仮想環境
└── README.md                   # このファイル
```

---

## 🚀 使い方

### ステップ1: Tare Calibration（初回 & カメラ位置変更時）

Intel公式のTare Calibration APIを使用して深度精度を改善します。

**✅ 実証済み（macOS 15.6.1）:**

```bash
# 1. USBケーブルを抜き差し（10秒待つ）
# 2. 距離を測定（例: 374mm）
# 3. キャリブレーション実行
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 374
```

**引数:**
- `374`: カメラから基準面（トレイ底面）までの距離（mm単位）

**手順:**
1. **USBケーブルを抜き差し** → 10秒待つ → 再接続 → 5秒待つ
2. トレイをカメラの下に配置
3. 定規でカメラ～トレイ底面の距離を正確に測定
4. 上記コマンドを実行
5. 自動リトライ機能が動作（最大3回試行）
6. 補正データがカメラEEPROMに自動保存

**重要:**
- カメラとトレイを固定（三脚推奨）
- 平らな基準面を使用
- 照明を一定に保つ
- カメラ位置を変更したら必ず再キャリブレーション

**📚 詳しいガイド:**
- [CALIBRATION_GUIDE.md](CALIBRATION_GUIDE.md) - 頻繁にキャリブレーションする場合のベストプラクティス

**出力例:**
```
======================================================================
Intel RealSense D405 Tare Calibration（公式手法）
======================================================================
Ground Truth: 445mm (0.4450m)
精度設定:     high
スキャンタイプ: intrinsic
======================================================================

カメラ初期化中...
✓ Depth Scale: 0.0001 (m/unit)
✓ Visual Preset: High Accuracy
ウォームアップ中（30フレーム）...

======================================================================
Tare Calibration実行中...
======================================================================
※ この処理には30秒～1分程度かかります
※ カメラと基準面を動かさないでください

進捗: 100%...

✓ Tare Calibration完了（28.3秒）

【キャリブレーション品質】
  Health: (1.2, 0.8)

キャリブレーション結果をカメラに書き込み中...

======================================================================
✓ キャリブレーション完了
======================================================================
補正データがカメラのEEPROMに保存されました。
今後のスキャンで自動的に補正が適用されます。
======================================================================
```

---

### ステップ2: 食材スキャン

キャリブレーション後は、何度でもスキャンできます。

```bash
sudo /Users/moei/program/D405/venv/bin/python3 scripts/scan.py salmon_salad
```

**操作:**
- プレビュー画面が表示される（RGB + 深度カラーマップ）
- **'s' キー:** 高品質スキャン（20フレーム平均）
- **'c' キー:** クイックスキャン（1フレーム）
- **'q' キー:** 終了

**出力例:**
```
======================================================================
Intel RealSense D405 Food Scanner
======================================================================
カメラ初期化中...
✓ Depth Scale: 0.0001 (m/unit)
✓ Visual Preset: High Accuracy
✓ Intel推奨フィルターパイプライン初期化完了
ウォームアップ中...
✓ 準備完了
======================================================================

食材名: salmon_salad

操作:
  's' キー: 高品質スキャン（20フレーム平均）
  'c' キー: クイックスキャン（1フレーム）
  'q' キー: 終了

キャプチャ中（20フレーム平均）...
  5/20 フレーム...
  10/20 フレーム...
  15/20 フレーム...
  20/20 フレーム...
✓ キャプチャ完了
  解像度: 848x480
  深度範囲: 0 - 5230 units

✓ 保存完了:
  RGB:         rgb_salmon_salad_20251018_090532.png
  Depth Raw:   depth_raw_salmon_salad_20251018_090532.png
  Depth Color: depth_colorized_salmon_salad_20251018_090532.png
  Metadata:    metadata_salmon_salad_20251018_090532.json
```

---

## 📊 出力データ形式

各スキャンで以下のファイルが生成されます:

```
nutrition5k_data/imagery/realsense_overhead/
├── rgb_[食材名]_[タイムスタンプ].png              # RGB画像 (848x480)
├── depth_raw_[食材名]_[タイムスタンプ].png        # Raw深度 (16-bit PNG)
├── depth_colorized_[食材名]_[タイムスタンプ].png  # 深度可視化
└── metadata_[食材名]_[タイムスタンプ].json        # メタデータ
```

### メタデータ例:

```json
{
  "food_name": "salmon_salad",
  "timestamp": "20251018_090532",
  "resolution": {
    "width": 848,
    "height": 480
  },
  "depth_encoding": "16-bit PNG, 10000 units/meter",
  "depth_scale_factor": 10000,
  "camera_depth_scale": 0.0001,
  "depth_range_units": {
    "min": 0,
    "max": 5230
  },
  "calibration": "Intel Tare Calibration applied (stored in camera EEPROM)"
}
```

---

## 🔧 技術詳細

### Intel公式技術の採用

#### 1. Tare Calibration（深度補正）

**従来の方法（カスタム実装）との比較:**

| 項目 | カスタム実装 | Intel Tare Calibration |
|------|------------|------------------------|
| 測定回数 | 2点必要 | **1点のみ** |
| 補正計算 | アプリ側で実装 | **カメラ内部で自動** |
| 保存場所 | JSONファイル | **EEPROM（永続）** |
| 適用タイミング | スキャン時に手動 | **常に自動適用** |
| 信頼性 | 自前実装 | **Intel保証** |

**Intel公式API:**
```python
auto_calib_dev = device.as_auto_calibrated_device()
table, health = auto_calib_dev.run_tare_calibration(
    ground_truth_mm=445,
    json_content='{"accuracy": 1}',  # high
    timeout_ms=30000
)
auto_calib_dev.set_calibration_table(table)
auto_calib_dev.write_calibration()  # EEPROM永続保存
```

参考: [Intel RealSense Self-Calibration Documentation](https://github.com/IntelRealSense/librealsense/blob/master/wrappers/python/examples/depth_auto_calibration_example.py)

---

#### 2. D405最適設定

**解像度:** 848x480 @ 60fps（Intel推奨）
**Visual Preset:** High Accuracy (preset=3)
**Depth Scale:** 0.0001 m/unit（最小スケール、高精度）

```python
# D405最適設定
config.enable_stream(rs.stream.depth, 848, 480, rs.format.z16, 60)
config.enable_stream(rs.stream.color, 848, 480, rs.format.rgb8, 60)

# High Accuracy preset
depth_sensor.set_option(rs.option.visual_preset, 3)
```

---

#### 3. Intel推奨フィルターパイプライン

**公式推奨順序:**
```
Depth Frame
  ↓
Decimation Filter (optional)
  ↓
Depth to Disparity Transform
  ↓
Spatial Edge-Preserving Filter
  ↓
Temporal Filter (for static scenes)
  ↓
Disparity to Depth Transform
  ↓
Hole Filling Filter
```

**Spatial Filter設定（Intel推奨パラメータ）:**
```python
spatial = rs.spatial_filter()
spatial.set_option(rs.option.filter_magnitude, 2)
spatial.set_option(rs.option.filter_smooth_alpha, 0.5)  # 0.25-1.0
spatial.set_option(rs.option.filter_smooth_delta, 20)   # 1-50
```

**Temporal Filter設定:**
```python
temporal = rs.temporal_filter()
temporal.set_option(rs.option.filter_smooth_alpha, 0.4)
temporal.set_option(rs.option.filter_smooth_delta, 20)
```

**Hole Filling Filter:**
```python
hole_filling = rs.hole_filling_filter()
hole_filling.set_option(rs.option.holes_fill, 1)  # farest from around
```

参考: [Intel Post-Processing Filters](https://github.com/IntelRealSense/librealsense/blob/master/doc/post-processing-filters.md)

---

### D405仕様

- **測定範囲:** 7cm - 50cm（食材スキャンに最適）
- **精度:** 25cmで0.7%以下、20cmで±1.4%以内
- **最小検出:** 7cmで1mm未満（サブミリメートル精度）
- **ステレオベースライン:** 短距離用に最適化
- **プロジェクター:** なし（環境光使用、D435より低テクスチャに弱い）

---

## 🔄 再キャリブレーションが必要な場合

以下の場合はTare Calibrationを再実行してください:

1. **カメラ位置が変わった**（高さ・角度）
2. **トレイ位置が変わった**
3. **照明条件が大きく変わった**
4. **スキャン結果の精度が悪い**

```bash
# 再キャリブレーション
sudo /Users/moei/program/D405/venv/bin/python3 scripts/calibrate.py 445
```

**注意:** Tare CCalibrationはカメラEEPROMに保存されるため、
異なる環境で使用する場合は再キャリブレーションが必須です。

---

## ✅ Intel公式手法の利点

### 1. **シンプル**
- 1点測定だけで完了（2点不要）
- JSONファイル管理不要

### 2. **高精度**
- Intel公式アルゴリズム
- カメラ内部で最適化

### 3. **メンテナンスフリー**
- EEPROMに永続保存
- 再起動後も自動適用
- 全てのアプリで有効

### 4. **業界標準**
- Intel公式推奨
- 広く使用されている実証済み手法

---

## 📝 ワークフロー

```
初回セットアップ:
  カメラ設置 → Tare Calibration → スキャン → スキャン → ...
                      ↑                        ↑
                  1回だけ実行              何度でも可能
```

**Tare Calibrationは環境が変わらない限り、初回のみ実行すればOK**

---

## 🔗 参考資料

### Intel公式ドキュメント

- [RealSense Self-Calibration](https://github.com/IntelRealSense/librealsense/blob/master/wrappers/python/examples/depth_auto_calibration_example.py)
- [Post-Processing Filters](https://github.com/IntelRealSense/librealsense/blob/master/doc/post-processing-filters.md)
- [D400 Visual Presets](https://github.com/IntelRealSense/librealsense/wiki/D400-Series-Visual-Presets)
- [librealsense GitHub](https://github.com/IntelRealSense/librealsense)

### D405仕様

- [Intel RealSense D405 製品ページ](https://www.intelrealsense.com/depth-camera-d405/)
- [D405 技術仕様](https://www.intel.com/content/www/us/en/products/sku/229218/intel-realsense-depth-camera-d405/specifications.html)

---

## ⚙️ システム要件

- **OS:** macOS / Linux
- **Python:** 3.7+
- **pyrealsense2:** 2.50+
- **OpenCV:** 4.0+
- **カメラ:** Intel RealSense D405

---

## 📞 トラブルシューティング

### Q: Tare Calibrationが失敗する

**A:** 以下を確認してください:
- カメラとトレイが完全に固定されているか
- 基準面が平らか
- Ground truthが60-10000mmの範囲か
- 照明が十分か

### Q: スキャン結果の精度が悪い

**A:**
1. Tare Calibrationを再実行
2. カメラとトレイの距離を20-30cmに調整
3. 照明を改善（D405は環境光を使用）

### Q: 深度データに穴が多い

**A:**
- 食材の表面に低テクスチャ部分がある場合、D405は苦手
- Hole Fillingフィルターが有効化されているか確認
- より良い照明を追加

---

**Intel公式技術による高精度食材スキャンシステム** 🎯
