# RSPアイテム一括生成

`RSPアイテム一括生成.exe` を再ビルドするための最小ソース一式です。

## 含まれるファイル
- `RSPアイテム一括生成.py` (GUIエントリポイント)
- `複合itemdatからjson抽出.py` (item.dat復号後データ抽出)
- `rsp_tooltip_generator.py` (ツールチップ生成)
- `render_rsp_items.py` (HTML向けデータ整形)
- `アイテム表示用HTMLベース.html` (HTMLテンプレート)
- `RSPアイテム一括生成.spec` (PyInstaller設定)
- `EXE化手順.txt` (ビルド手順)

## ビルド
手順は `EXE化手順.txt` を参照してください。

## GitHub Actionsでビルド
このリポジトリには、Windows上でEXEを自動ビルドするワークフローが含まれています。

1. GitHubの `Actions` タブを開く
2. `Build RSP EXE` を選択
3. `Run workflow` を実行
4. 完了後、`Artifacts` から `RSPアイテム一括生成-exe` をダウンロード
