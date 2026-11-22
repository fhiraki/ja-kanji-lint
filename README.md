# ja-kanji-lint

[English](#english) | [日本語](#日本語)

## English

A command-line tool that finds Chinese kanji mixed into Japanese text. It scans whole documents and the comments in source code, and it is a single Python file with no dependencies.

- **For Japanese developers:** catch Chinese characters that LLMs sometimes mix into Japanese documents and code comments.
- **For localization teams:** check Japanese translations even if you do not read Japanese. Pairs such as `关`/`関` and `设`/`設` are easy to miss, and a Chinese character in a Japanese UI looks wrong to native readers.

Requires Python 3.11 or later. Supported on macOS, Linux, and Windows.

### Quick start

Copy `ja_kanji_lint.py` anywhere, then run it:

```bash
# Report only (the default; no files are changed)
python3 ja_kanji_lint.py path/to/project

# Preview the proposed fixes as a unified diff
python3 ja_kanji_lint.py path/to/project --diff

# Apply safe fixes and keep a <file>.bak-ja-kanji-lint backup
python3 ja_kanji_lint.py path/to/project --fix --backup

# Also fix known word typos and full-width/half-width variants
python3 ja_kanji_lint.py path/to/project --fix --fix-words --width --backup

# Machine-readable output
python3 ja_kanji_lint.py path/to/project --json

# Run the built-in tests
python3 ja_kanji_lint.py --selftest
```

### Checking Japanese translations

Add `--l10n` to scan translation files. It reads values and leaves keys alone.

```bash
python3 ja_kanji_lint.py locales/ja --l10n
```

Supported formats are `.po`, `.pot`, `.strings`, `.stringsdict`, `.xliff`, `.xlf`, `.properties`, `.arb`, `.resx`, `.ftl`, `.yml`, and `.yaml`. JSON is always scanned, and `--fix` does not change its keys. Directories named for a Chinese locale, such as `zh-Hans.lproj` or `zh_CN`, are skipped.

If you do not read Japanese, have a Japanese speaker confirm `ambiguous` findings. Many of them are correct Japanese.

### What it reports

| Kind (`--fail-on` name) | Examples | `--fix` |
|---|---|---|
| Fix candidate (`fix`) | `关→関` `质→質` `说→説` | Fixed |
| Needs review (`ambiguous`) | `发→発/髪` `國→国` `手机` | Report only |
| Chinese-only (`suspicious`) | `们` `这` `账` | Report only |
| Word typo (`word`) | `後程→後ほど` | Fixed with `--fix-words` |
| Repeated punctuation (`dup`) | `。。` `、、` `、。` | Fixed |
| Repeated particle (`particle`) | `のの` `をを` | Report only |
| Unbalanced brackets (`bracket`) | `「` without `」` (documents only) | Report only |
| Character width (`width`) | `ＡＢＣ１２３` `ｶﾀｶﾅ` | Reported and fixed with `--width` |
| Chinese comma (`punct`) | `，→、` | Reported and fixed with `--punct` |

### How it avoids false positives

A common tip is to save a file as Shift-JIS and treat garbled characters as non-Japanese. This tool does not rely on that, because real Japanese names such as `森鷗外` and `草彅剛` cannot be represented in plain Shift-JIS. Many characters used in Taiwan are also valid Japanese.

- **Chinese-only** means the character is in the mainland Chinese set (GB2312) and in neither the Japanese sets (JIS X 0208/0213) nor the Taiwanese set (Big5).
- **Auto-fix never touches** a character that Shift-JIS can represent, or one found in both the Japanese and Taiwanese sets. Old forms used in names, such as `國` `實` `澤`, and terms such as `骨粗鬆症` stay as written.
- **Common Japanese kanji** such as `机` `干` `据` are reported only inside Chinese words such as `手机` `干净` `数据`. Japanese words such as `机上` `若干` `据え置き` are not reported.
- **Characters shared by Japanese and Chinese**, such as `学` `区` `声`, are not reported.

### Options

| Option | Description |
|---|---|
| `--fix` | Apply fixes to files (without it, the tool only reports) |
| `--diff` | Show proposed fixes as a unified diff |
| `--backup` | With `--fix`, keep `<file>.bak-ja-kanji-lint` |
| `--fix-words` | With `--fix`, also apply word-level typo fixes |
| `--width` | Report and fix full-width alphanumerics and half-width kana |
| `--no-typos` | Turn off word, punctuation, particle, and bracket checks and their fixes |
| `--punct` | Also handle the Chinese comma (`，→、`) |
| `--l10n` | Scan the values in translation files |
| `--ignore-chars CHARS` | Never report or fix these characters, for example `--ignore-chars 澤廣櫻` |
| `--fail-on KINDS` | Exit 1 only for these comma-separated kinds, for example `fix,suspicious` |
| `--json` | Print JSON to stdout, with diffs and backup notices on stderr |
| `--include-strings` | Scan whole code lines, including string literals |
| `--all` | Treat other text files as documents (known binary types and backups are excluded) |
| `--ext .tex .org` | Scan more extensions as documents |
| `--exclude dir1 dir2` | Exclude more directory names |
| `--no-gitignore` | Also scan files ignored by Git |
| `--no-skip-zh` | Turn off the automatic skip for Chinese documents |
| `--words typos.json` | Load more word typos from JSON |
| `--encoding ENC` | Input encoding, also used when writing (UTF-16/32 keep their byte order and BOM) |
| `--selftest` | Run the built-in tests and exit |

Put paths before `--ext` and `--exclude`, because those options accept several values.

Exit codes are `0` for no findings, `1` for findings, and `2` for errors such as a missing path or an unreadable file. The code reflects the state before fixes, so a successful `--fix` still exits `1`.

### What gets scanned

- **Documents** (`.md`, `.txt`, `.html`, `.json`, `.csv`, and others): the whole file.
- **Source code** (`.py`, `.ts`, `.go`, `.sql`, `.sh`, and others): comments only. Block comments include `/* */`, Vue `<!-- -->`, Lua `--[[ ]]`, Haskell `{- -}`, and Ruby `=begin`/`=end`. Multi-line strings such as Python docstrings and JavaScript template literals are not treated as comments.
- **Reported but never auto-fixed:** URLs, Markdown link targets and code, HTML `href`/`src` values, and JSON keys.
- **Skipped by default:** directories such as `.git`, `node_modules`, `venv`, `build`, and `dist`.
- **Files ignored by Git are skipped** when you scan a directory in a Git repository, including nested repositories. Tracked files are still scanned, and so is any file or directory you pass directly. Use `--no-gitignore` to scan ignored files. If Git cannot run, the tool prints a warning and scans them.
- **Chinese documents are skipped** when the file name has a token such as `zh`, `zh-CN`, or `cn`, or when a document has no kana and 10 or more Chinese-related characters. Use `--no-skip-zh` to scan them.

### Using it in CI

```yaml
- name: Check for Chinese kanji
  run: python3 path/to/ja_kanji_lint.py . --fail-on fix,suspicious
```

`--fail-on` keeps report-only findings, such as old-form names like `澤田`, from failing the build. Use `--ignore-chars` to silence specific characters.

### Extending the tables

Add word typos with a JSON file:

```json
{
  "後程": "後ほど"
}
```

```bash
python3 ja_kanji_lint.py path/to/project --words typos.json --fix --fix-words
```

Character mappings live in `ja_kanji_lint.py`. `_MAP_SRC` holds auto-fixes, and `_REVIEW_SRC` holds report-only characters. Both are space-separated `wrong:right` pairs. Invalid pairs, and auto-fixes for characters that may be valid Japanese, raise an error at load time.

### Limitations

- A clean result does not prove that a text has no Chinese. Characters shared by both languages, and Taiwanese forms that are not in the tables, are not reported.
- The tool maps characters and does not translate words. For example, `软件` becomes `軟件`, not `ソフトウェア`.
- Comment detection is heuristic. A line with an odd number of quotes can make it treat string contents as a comment.
- Binary documents such as `.docx`, `.pdf`, and `.pptx` are not supported. Export them to text first.
- Always review `--diff` before running `--fix`.

### License

[MIT](LICENSE)

---

## 日本語

日本語テキストに混入した中国語の漢字を検出するコマンドラインツールです。ドキュメント全体と、ソースコードのコメントを走査します。依存ライブラリのない、Python の単一ファイルです。

- **日本語で開発する方に:** LLM が日本語のドキュメントやコードコメントに混ぜてしまう中国語の漢字を検出できます。
- **ローカライズに携わる方に:** 日本語が読めなくても、日本語訳を確認できます。`关`/`関` や `设`/`設` のような字は見分けにくく、日本語の UI に混ざると利用者には不自然に見えます。

Python 3.11 以上が必要です。macOS / Linux / Windows に対応しています。

### クイックスタート

`ja_kanji_lint.py` を任意の場所にコピーして実行します。

```bash
# 報告のみ(既定の動作。ファイルは変更しない)
python3 ja_kanji_lint.py path/to/project

# 修正案を unified diff で確認
python3 ja_kanji_lint.py path/to/project --diff

# 安全な修正を適用(バックアップ <file>.bak-ja-kanji-lint を作成)
python3 ja_kanji_lint.py path/to/project --fix --backup

# 誤字辞書・全角半角の表記ゆれもまとめて修正
python3 ja_kanji_lint.py path/to/project --fix --fix-words --width --backup

# JSON で出力
python3 ja_kanji_lint.py path/to/project --json

# 内部テストを実行
python3 ja_kanji_lint.py --selftest
```

### 日本語訳のチェック

`--l10n` を付けると翻訳ファイルを走査します。値だけを対象にし、キーは変更しません。

```bash
python3 ja_kanji_lint.py locales/ja --l10n
```

対応形式は `.po` `.pot` `.strings` `.stringsdict` `.xliff` `.xlf` `.properties` `.arb` `.resx` `.ftl` `.yml` `.yaml` です。JSON は常に走査され、`--fix` でもキーは変更されません。`zh-Hans.lproj` や `zh_CN` のように中国語ロケールを示すディレクトリは除外します。

日本語が読めない場合、`ambiguous`(要確認)の結果は日本語話者に確認してもらってください。正しい日本語であることも多くあります。

### 検出するもの

| 種別(`--fail-on` の名前) | 例 | `--fix` |
|---|---|---|
| 修正候補(`fix`) | `关→関` `质→質` `说→説` | 修正する |
| 要確認(`ambiguous`) | `发→発/髪` `國→国` `手机` | 報告のみ |
| 中華圏専用字(`suspicious`) | `们` `这` `账` | 報告のみ |
| 誤字候補(`word`) | `後程→後ほど` | `--fix-words` で修正 |
| 重複記号(`dup`) | `。。` `、、` `、。` | 修正する |
| 助詞重複(`particle`) | `のの` `をを` | 報告のみ |
| 括弧不一致(`bracket`) | `「` と `」` の個数不一致(ドキュメントのみ) | 報告のみ |
| 全角/半角(`width`) | `ＡＢＣ１２３` `ｶﾀｶﾅ` | `--width` で報告・修正 |
| 中国語の読点(`punct`) | `，→、` | `--punct` で報告・修正 |

### 誤検出を防ぐ仕組み

「Shift-JIS で保存して文字化けした字は日本語ではない」という見分け方がありますが、本ツールはこれに頼りません。`森鷗外` や `草彅剛` のように、標準の Shift-JIS で表せない実在の表記があるためです。台湾で使われる字にも、日本語として正しいものが多くあります。

- **中華圏専用字**は、中国本土の文字集合(GB2312)にあり、日本語(JIS X 0208/0213)にも台湾(Big5)にもない字に限定しています。
- **自動修正の対象外**は、Shift-JIS で表せる字と、日本語・台湾の両方の文字集合にある字です。人名に使われる `國` `實` `澤` などの旧字体や、`骨粗鬆症` のような用語は書き換えません。
- **日本語で日常的に使う字**(`机` `干` `据` など)は、`手机` `干净` `数据` のような中国語の語に含まれるときだけ報告します。`机上` `若干` `据え置き` のような日本語は報告しません。
- **日中共通の字**(`学` `区` `声` など)は検出しません。

### オプション

| オプション | 説明 |
|---|---|
| `--fix` | 修正をファイルに適用する(指定しなければ報告のみ) |
| `--diff` | 修正案を unified diff で表示する |
| `--backup` | `--fix` 時に `<file>.bak-ja-kanji-lint` を残す |
| `--fix-words` | `--fix` 時に誤字辞書の修正も適用する |
| `--width` | 全角英数字と半角カナを検出・修正する |
| `--no-typos` | 誤字・重複記号・助詞重複・括弧不一致の検出と修正を無効にする |
| `--punct` | 中国語の読点(`，→、`)も対象にする |
| `--l10n` | 翻訳ファイルの値を走査する |
| `--ignore-chars CHARS` | 指定した字を検出・修正しない(例: `--ignore-chars 澤廣櫻`) |
| `--fail-on KINDS` | 指定した種別(カンマ区切り)のときだけ終了コード 1 にする(例: `fix,suspicious`) |
| `--json` | JSON を標準出力に出す(diff とバックアップ通知は標準エラー出力) |
| `--include-strings` | コード行全体(文字列リテラルを含む)を走査する |
| `--all` | その他のテキストファイルも文書として走査する(既知のバイナリとバックアップは除外) |
| `--ext .tex .org` | 文書として走査する拡張子を追加する |
| `--exclude dir1 dir2` | 除外するディレクトリ名を追加する |
| `--no-gitignore` | Git の無視対象も走査する |
| `--no-skip-zh` | 中国語文書の自動除外を無効にする |
| `--words typos.json` | 追加の誤字辞書 JSON を読み込む |
| `--encoding ENC` | 入力エンコーディングを指定する(書き戻しにも使用。UTF-16/32 はバイト順と BOM を保持) |
| `--selftest` | 内部テストを実行して終了する |

`--ext` と `--exclude` は複数の値を受け取るため、パスはこれらより前に指定してください。

終了コードは `0`=検出なし、`1`=検出あり、`2`=エラー(存在しないパス、読み取れないファイルなど)です。修正前の状態を反映するため、`--fix` が成功しても `1` を返します。

### 走査の範囲

- **ドキュメント**(`.md` `.txt` `.html` `.json` `.csv` など): ファイル全体
- **ソースコード**(`.py` `.ts` `.go` `.sql` `.sh` など): コメントのみ。ブロックコメントは `/* */`、Vue の `<!-- -->`、Lua の `--[[ ]]`、Haskell の `{- -}`、Ruby の `=begin`/`=end` に対応しています。Python の docstring や JavaScript のテンプレートリテラルなどの複数行文字列は、コメントとして扱いません。
- **報告はするが自動修正しない部分:** URL、Markdown のリンク先とコード、HTML の `href`/`src`、JSON のキー
- **既定で除外:** `.git` `node_modules` `venv` `build` `dist` などのディレクトリ
- **Git の無視対象も除外:** Git リポジトリ内のディレクトリを走査するときは、`.gitignore` などで無視されたファイルを除外します(入れ子のリポジトリも含む)。追跡済みのファイルと、直接指定したファイルやディレクトリは走査します。無視対象も走査するには `--no-gitignore` を指定します。Git を実行できない場合は、警告を表示して走査します。
- **中国語文書の自動除外:** ファイル名に `zh` `zh-CN` `cn` などの区切りを含むものと、かなが1文字もなく中国語系の字が10件以上ある文書は除外します。走査するには `--no-skip-zh` を指定します。

### CI での利用

```yaml
- name: Check for Chinese kanji
  run: python3 path/to/ja_kanji_lint.py . --fail-on fix,suspicious
```

`--fail-on` を使うと、`澤田` のような旧字体の人名など、報告のみの結果でビルドが失敗しなくなります。特定の字を除外するには `--ignore-chars` を使います。

### 辞書の拡張

誤字は JSON ファイルで追加できます。

```json
{
  "後程": "後ほど"
}
```

```bash
python3 ja_kanji_lint.py path/to/project --words typos.json --fix --fix-words
```

文字の対応表は `ja_kanji_lint.py` 内にあります。`_MAP_SRC` が自動修正、`_REVIEW_SRC` が報告のみの字で、どちらも `誤字:正字` を空白で区切って並べます。不正な組や、日本語として正当な可能性がある字の自動修正は、読み込み時にエラーになります。

### 制限事項

- 検出なしの結果は、中国語が含まれないことの証明にはなりません。日中共通の字や、対応表にない台湾の字形は報告されません。
- 字の対応のみを扱い、単語は翻訳しません。たとえば `软件` は `ソフトウェア` ではなく `軟件` になります。
- コメント検出はヒューリスティクスです。引用符の個数が奇数の行では、文字列の中身をコメントとして扱うことがあります。
- `.docx` `.pdf` `.pptx` などのバイナリ文書には対応していません。テキストに書き出してからご利用ください。
- `--fix` の前に、必ず `--diff` で内容を確認してください。

### ライセンス

[MIT](LICENSE)
