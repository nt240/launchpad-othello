# Launchpad X Othello

Novation Launchpad X で遊ぶ、2人用のリバーシです。Launchpad の8×8パッドで石を置き、盤面と合法手を色で表示します。

## 必要なもの

- Python 3.12 以上
- Novation Launchpad X
- [uv](https://docs.astral.sh/uv/)

## セットアップ

Launchpad X を接続してから、依存パッケージをインストールします。

```powershell
uv sync
```

MIDI ポート名が環境と異なる場合は、`main.py` の `INPUT_PORT` と `OUTPUT_PORT` を利用可能なポート名に変更してください。ポート名は次のコマンドで確認できます。

```powershell
uv run python -c "import mido; print('Inputs:', mido.get_input_names()); print('Outputs:', mido.get_output_names())"
```

## 起動方法

```powershell
uv run python main.py
```

## 操作方法

- 緑色に点滅するパッドを押すと、その場所に石を置きます。
- プレイヤー1は青、プレイヤー2はオレンジです。
- 置けない場所を押すと、そのパッドが赤く点灯します。
- 勝負がつくと、石1枚につきパッド1個を使ったスコア表示に切り替わります。勝者の石の数だけ先に並び、その色が点滅します。
- 終局後、同じパッドを0.5秒以内に2回押すと新しいゲームを開始します。
- ゲーム中に終了するには `Ctrl+C` を押してください。

## Ruff

Ruff のルールとフォーマット設定は `pyproject.toml` にあります。Ruff をまだインストールしていない場合は、次のコマンドでインストールできます。

```powershell
uv tool install ruff
```

チェックとフォーマットは次のコマンドで実行します。

```powershell
ruff check .
ruff format .
```
