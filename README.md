# NIIGATA RAMEN RADAR v0.7.2

地図表示の安定化版です。

- 緯度経度が取得できた店舗：OpenStreetMapに店舗位置を表示
- 緯度経度が未取得：区のエリア地図を必ず表示し、「店舗位置未確認」と明示
- MANNISH / マルシチは既知住所をジオコーディング候補として追加
- MANNISHは公開されている同一建物（イオン新潟青山店）の座標を利用
- app.js / styles.css にバージョン文字列を付け、ブラウザキャッシュで旧版が残る問題を回避

既存履歴を残す場合、data/ramen.json はアップロード不要です。collector.py / app.js / index.html / styles.css を更新し、GitHub Actions を1回実行してください。
