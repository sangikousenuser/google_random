# Google乱数ツールの出現頻度調査

Google検索の乱数生成ツールを **1〜41** に設定し、生成ボタンをクリックして表示値を記録します。別の乱数生成器による代用はしません。

## GitHub Actionsで実行

1. このリポジトリの変更をGitHubの `main` にコミット・pushします。
2. GitHubの **Actions → Google random sampling → Run workflow** を開きます。
3. 最初は `samples: 20` で実行し、Googleのツールを操作できることを確認します。
4. 成功したら `samples: 10000`、`delay_ms: 1200` で実行します。数時間かかります。
5. 完了した実行画面の **Artifacts → google-random-results** をダウンロードします。

`summary.txt` に集計とカイ二乗検定、`distribution.png` に出現回数のグラフ、`frequencies.csv` に数値ごとの回数・割合、`samples.csv` に全観測値が入ります。実行条件と完了件数は `metadata.json` に記録します。

Googleによる自動操作の制限・CAPTCHA・画面構成の変更で失敗する可能性があります。失敗時は `failure.png` と `failure.html` で確認してください。制限を回避する処理はありません。途中までのデータは `PARTIAL` として集計します。**10,000件完了しない限り、10,000回の調査結果ではありません。**

## 手元のPCで実行する場合

Python 3.12で以下を実行します。GitHub Actionsが拒否される場合も、通常のPCから動作するか確認できます。

```sh
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windowsでは上の行の代わりに .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python collect.py --samples 20 --headed
python collect.py --samples 10000 --headed
python analyze.py results/samples.csv --expected 10000
```

生成後に最低1.2秒待ち、結果表示のCSSアニメーション終了を待ってから読み取ります。実行前に範囲を1〜1と41〜41にして生成結果を確認します。この確認は調査件数に含みません。連続して同じ値が出ても、それぞれ1件として記録します。各実行は `results/` の同名ファイルを上書きするため、必要な結果は先に別の場所へ保存してください。

均等なら10,000回で各数値は平均約243.90回です。多少のばらつきは自然に発生します。カイ二乗検定は出現頻度を検査するもので、乱数の独立性や将来の予測可能性まで保証するものではありません。

## 現時点の検証状況

集計処理は人工の検証用データで確認しています。クラウド環境ではGoogleへの接続が拒否されており、Googleの画面要素・クリック後の待ち時間・実測収集は未検証です。まず20回の試行で画面操作と結果の取得を確認してください。
