# NIIGATA RAMEN RADAR v0.7.10

## Safari / iPhone アイコン互換性改善
- ルート直下に `apple-touch-icon.png` を追加
- `apple-touch-icon-precomposed.png` も追加
- ルート直下に `favicon-32x32.png` / `favicon-16x16.png` を追加
- `shortcut icon` を明示
- アイコン参照をルート絶対パス化
- v0.7.10 のキャッシュバスターを付与

Safariはお気に入りアイコンを強くキャッシュするため、デプロイ後は古いお気に入りを削除し、Safariを完全に閉じて開き直してから再登録すると反映されやすくなります。

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


## v0.7.7
- NEARBY RADARを最新の新店・閉店・リニューアル等の更新情報より下へ移動
- iPhone向け位置情報設定ガイド（Safari / Chrome）を追加
- 位置情報取得タイムアウトを10秒から20秒へ延長
- SCAN FAILED時の案内を具体化

## v0.7.8 — BOOKMARK / HOME SCREEN ICON
- RAMEN RADAR専用アイコンを追加（黒背景＋赤いレーダー＋ラーメン鉢）。
- Safari / Chromeのタブ・ブックマーク用 favicon を追加。
- iPhone「ホーム画面に追加」用 `apple-touch-icon`（180x180）を追加。
- Android / Chrome / PWA向け 192x192・512x512 アイコンを追加。
- `manifest.webmanifest` を追加し、ホーム画面表示名を `RAMEN RADAR` に設定。
- iPhoneのホーム画面起動時にアプリ風表示になるためのWeb Appメタ情報を追加。
- テーマ色をRAMEN RADARのダークUIに合わせて設定。

### GitHubへ更新するファイル
`index.html`, `manifest.webmanifest`, `favicon.ico`, `favicon.png`, `icons/` フォルダを追加・上書きしてください。
既存の `app.js`, `styles.css`, `collector.py`, `data/ramen.json` の中身は変更不要です（index.html側のキャッシュバージョンのみ0.7.8に更新済み）。

### iPhoneで確認
Safariでサイトを開き、共有ボタン → 「ホーム画面に追加」。追加画面とホーム画面にRAMEN RADARの専用アイコンが表示されます。
以前すでにホーム画面へ追加している場合は、一度古いアイコンを削除してから再追加すると新しいアイコンが反映されやすくなります。


## v0.7.9 — Green RAMEN RADAR icon
- ブックマーク／ホーム画面用アイコンを、緑基調のRAMEN RADAR正式アイコンへ変更。
- ナルトをレーダー化し、発見を表すハートときらめきを追加。
- NIIGATA表記をアイコンから外し、他地域にも展開できる共通ブランド仕様に変更。
- favicon / Apple Touch Icon / Android・PWA 192px・512px / favicon.ico を一括更新。
- ブラウザテーマカラーもグリーンへ変更。
- data/ramen.json と collector.py は変更不要。
