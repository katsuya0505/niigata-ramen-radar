# NIIGATA RAMEN RADAR v0.7.2

地図表示の安定化版です。

- 緯度経度が取得できた店舗：OpenStreetMapに店舗位置を表示
- 緯度経度が未取得：区のエリア地図を必ず表示し、「店舗位置未確認」と明示
- MANNISH / マルシチは既知住所をジオコーディング候補として追加
- MANNISHは公開されている同一建物（イオン新潟青山店）の座標を利用
- app.js / styles.css にバージョン文字列を付け、ブラウザキャッシュで旧版が残る問題を回避

既存履歴を残す場合、data/ramen.json はアップロード不要です。collector.py / app.js / index.html / styles.css を更新し、GitHub Actions を1回実行してください。


## v0.7.3
- カード内地図を「座標取得待ち」方式から廃止。
- 既存のMAPリンクと同じ検索対象をGoogle Maps埋め込みで即時表示。
- 緯度・経度の事前取得やOpenStreetMapのジオコーディング待ちは不要。
- `data/ramen.json` は既存履歴保護のため上書き不要。
- GitHubへは `app.js`, `styles.css`, `index.html` を上書きすればよい。collector.pyの変更は不要。

## v0.7.4
- トップを「今日のラーメン情報」要約に変更
- 新店・開店予定 / 閉店 / 移転・リニューアル / 限定を店名＋地域で即確認
- 各項目の「詳しく見る」から下部の該当フィルターへジャンプ
- 今日 / 7日間 / 30日間の切替に合わせてトップ要約も自動更新

## v0.7.5
- 新店 / OPENING SOON を検知後60分だけ `WARNING / NEW RAMEN SHOP DETECTED` を表示
- 警報中はヘッダーを `NEW SIGNAL` モードに変更
- 5分ごとに `data/ramen.json` を再確認（ページを開いたままでも新着を反映）
- フッターに `POWERED BY CivITech` を追加
- 既存の今日 / 7日 / 30日サマリー、Google Maps、履歴表示は維持


## v0.7.6 — NEARBY RADAR
- 「近くのラーメンを探す」を追加。
- ブラウザの位置情報許可後、現在地を中心にGoogle Mapsのラーメン検索をサイト内に表示。
- Google Mapsで大きく開くリンクも現在地に追随。
- 位置情報はブラウザ内で表示に使うだけで、RAMEN RADAR側には保存しません。
- HTTPS（Netlify）上で動作します。
