# Staged Mono

Staged Mono は、欧文フォント [Commit Mono](https://commitmono.com/) と日本語フォント [BIZ UDゴシック](https://github.com/googlefonts/morisawa-biz-ud-gothic) を合成した、プログラミング向けの等幅フォントです。  
本フォントは [yuru7/pending-mono](https://github.com/yuru7/pending-mono) をベースに開発されています。

![image](https://github.com/yuru7/pending-mono/assets/13458509/ff434f2b-6f22-4cf6-893f-d1e2de7e154e)

[✒ **ダウンロード（Releases）**](https://github.com/oxonium0215/staged-mono/releases)  
※ Assets 内の zip ファイルをダウンロードしてご利用いただけます。

---

## 主な特徴

- 隣接する文字に応じて自然な字間を保つ Smart Kerning を搭載。字体のシンプルさに重点を置いた [Commit Mono](https://commitmono.com/) 由来の英数字
- ユニバーサルデザインを掲げ、読みやすさを追求したモリサワ製 [BIZ UDゴシック](https://github.com/googlefonts/morisawa-biz-ud-gothic) 由来の日本語文字
  - BIZ UDゴシックと同等の異体字シーケンス（IVS）に対応
- 用途に合わせて選べる文字幅比率
  - 標準版: 半角3:全角5（英数字にゆとりのあるモダンなプログラミング比率）
  - 半角版: 半角1:全角2（従来のターミナルや固定幅環境に馴染む比率）
- ソースコードへの混入トラブルを防ぐ全角スペースの可視化（非表示版あり）
- 開発環境やターミナルでのアイコン表示に対応した Nerd Fonts 同梱版を用意

---

## 改善点と独自機能

Pending Mono に対し、以下の改善や機能拡張を加えています。

### 1. アプリケーション間での行の高さの差を縮小
- 各フォントテーブル（`OS/2`, `hhea`, `head`）の垂直メトリクスを統一
- VS Code、Windows Terminal、Neovim、nvy など、異なるアプリケーション間で行の高さの差を 4% 以内に縮小

### 2. GitHub Actions によるカスタムビルド
GitHub Actions から、好みの設定で自分専用のフォントをビルドしてダウンロードできます。

- Commit Mono のフィーチャー設定
  - `<=` や `>=`、矢印などのリガチャ
  - スマートカーニング
  - `a` や `g`、`0` などの代替グリフ
- ウェイトの指定（Regular / Bold を 200〜700 の範囲で細かく指定可能）
- 行の高さの倍率指定
- Nerd Fonts、日本語記号、半角比率、全角スペース可視化の切り替え

### 3. 罫線・大型記号の描画最適化
- ターミナル等で罫線や大型括弧、Powerline 記号が途切れたり歪んだりしないよう、ヒンティング対象からの除外とメトリクスの統一を実施

---

## フォント名の命名規則

配布されるフォントファイルは以下の規則で命名されています。

| 識別子 | 内容 |
| :--- | :--- |
| なし | 半角3:全角5 比率 |
| `HW` | 半角1:全角2 比率 |
| `NF` | Nerd Fonts アイコン同梱 |
| `JPDOC` | 一部記号に日本語フォント由来のグリフを使用 |
| `IS` | 全角スペース非表示 |

---

## ローカルでのビルド方法

### 必要な環境
- FontForge: `20230101`
- Python: `>= 3.8`
- ttfautohint

### Docker を利用する場合
```bash
docker build -t staged-mono-builder .
docker run --rm -v "$(pwd):/work" staged-mono-builder
```

### Linux / macOS
```bash
chmod +x build_variants.sh
./build_variants.sh
```

### Windows
```powershell
pip install -r requirements.txt
& "C:\Program Files (x86)\FontForgeBuilds\bin\ffpython.exe" .\fontforge_script.py && python fonttools_script.py
```

---

## ライセンス

SIL Open Font License, Version 1.1 が適用され、個人・商用問わず利用可能です。

- Commit Mono: SIL Open Font License, Version 1.1
- BIZ UDゴシック: SIL Open Font License, Version 1.1

詳細は `source_fonts` ディレクトリに含まれる各 LICENSE ファイルを参照してください。
