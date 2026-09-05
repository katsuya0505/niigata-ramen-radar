# 新潟ラーメンレーダー v0.2

v0.1 の画面に、5つの公開Webサイトを巡回して `data/ramen.json` を更新する
Pythonコレクターを追加した版です。

## 監視する5サイト

1. にいがた速報
2. にいがた経済新聞
3. PR TIMES
4. Komachi Web
5. 025 | ゼロニィゴ

巡回URLは `sources.json` で管理します。

## Windowsで手動テスト

Python 3.11+ 推奨。

```bat
cd niigata-ramen-radar-v0.2
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python collector.py --dry-run
```

問題なければ：

```bat
python collector.py
```

`data/ramen.json` が更新されます。

## GitHub Actionsで自動更新

`.github/workflows/update-radar.yml` を同梱しています。
GitHubへリポジトリとしてアップロードすると、JST 3時・9時・15時・21時ごろに
自動巡回し、`data/ramen.json` に変化があればコミットします。

NetlifyをそのGitHubリポジトリと連携すれば、JSON更新 → GitHub commit →
Netlify自動デプロイ、まで無人化できます。

## 注意

- 記事本文や画像を保存・転載する作りではありません。
- 公開ページのタイトル、URL等を検知し、RADAR用の短い独自表示に変換します。
- robots.txt、利用規約、HTML構造変更、アクセス制限等により取得できないサイトが
  出ることがあります。
- 初期版なので店名抽出・重複判定はルールベースです。v0.3でAI補助を加える余地があります。
