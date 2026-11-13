# 毎朝の自動更新（無料構成）

Windowsのタスクスケジューラで毎日06:20（日本時間）に実行します。PCが起動してサインイン中である必要があります。スリープ中は起動する設定ですが、電源が切れている場合は実行できません。OllamaまたはCOEIROINKが停止していれば、インストール済みアプリをバックグラウンドで起動します。

## セットアップ

1. Ollamaとローカルモデル `qwen3:4b` をインストールします。モデルは約2.5GBで、PC内で処理します。
2. PowerShellでリポジトリのフォルダーを開き、次を実行します。

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-daily-task.ps1
   ```

3. タスク `Palmin Radio Daily` が登録されます。APIキーは不要です。

## 実行内容と制限

- Bing Newsの公開RSSから話題候補と記事元URLを取得し、ローカルAIが `NEWS_POLICY.md` と `CASTERS.md` に沿って選択・台本化します。モデルの処理はPC内で行い、OpenAI APIは呼び出しません。
- RSSの候補数、台本形式、話者、出典リンク、COEIROINKを確認します。条件を満たさない日や音声生成に失敗した日は公開しません。
- 既存の日付の回や未コミット変更がある場合も、上書き・公開を止めます。
- 音声生成後にエピソードをコミットし、`tools/publish.sh` でPagesへ公開します。
- Qwen3 4BはChatGPTのGPTモデルより小さく、要約・台本の品質や選ぶ話題に差が出ることがあります。出典ページを確認できない場合は公開を止めます。

ログは `%LOCALAPPDATA%\PalminRadio\logs\YYYY-MM-DD` に保存します。失敗時はその日のログと、タスクスケジューラの「Palmin Radio Daily」の履歴を確認してください。

必要な実行ファイルは、Python 3.13、Ollamaと `qwen3:4b`、Git Bash、COEIROINK、MP3エンコーダー付きFFmpegです。現在のFFmpegの場所は `C:\Program Files (x86)\Steam\steamapps\common\Lethal Company\BoomboxController\other\ffmpeg.exe` です。場所が変わった場合は `tools/daily-run.ps1` を更新してください。
