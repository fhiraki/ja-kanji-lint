#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ja_kanji_lint.py — 日本語テキスト内の中国語系漢字(簡体字・繁体字)の検出・修正ツール
=================================================================================

ドキュメントファイル(.md, .txt, .html など)全体と、ソースコードのコメント行を
走査し、誤って使われている中国語系の漢字を検出します。

  - 「修正候補」    : 誤用がほぼ確実な中国語字(例: 关→関, 质→質, 说→説)。--fix で自動修正
  - 「誤字候補」    : 単語レベルの誤変換(例: 後程→後ほど)。--fix-words で適用
  - 「要確認」      : 複数の候補がある字(例: 发→発/髪)や人名に使われうる旧字体。報告のみ
  - 「中華圏専用字」: 日本語に存在しない字(例: 们, 这, 吗)。報告のみ
  - 「重複記号」    : 。。 、、 など。--fix で自動修正
  - 「全角/半角」   : 全角英数・半角カナ。--width で報告・修正

使い方:
  python3 ja_kanji_lint.py <パス...>                  # 検出して報告(既定: 修正しない)
  python3 ja_kanji_lint.py <パス...> --diff           # 修正案を unified diff で表示
  python3 ja_kanji_lint.py <パス...> --fix --backup   # 修正を適用(バックアップ付き)
  python3 ja_kanji_lint.py <パス...> --fix --fix-words --width  # 誤字・表記ゆれも修正
  python3 ja_kanji_lint.py <パス...> --l10n           # 翻訳ファイルの値も走査
  python3 ja_kanji_lint.py --selftest                 # 内部テストを実行

終了コード: 0=検出なし / 1=検出あり / 2=エラー
"""

import argparse
import codecs
import contextlib
import difflib
import functools
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import namedtuple

# ---------------------------------------------------------------------------
# 1. 文字対応表
# ---------------------------------------------------------------------------

# 誤用がほぼ確実な中国語字(簡体字・繁体字) → 日本語標準(新字体)。--fix で修正する。
# 日本語でも正当に使われる字はここに入れず、_REVIEW_SRC か AMBIGUOUS に置くこと。
_MAP_SRC = """
关:関 门:門 问:問 间:間 闷:悶 闲:閑 闻:聞 闹:鬧 闯:闖 开:開
质:質 图:図 团:団 园:園 圆:円 场:場 块:塊 坚:堅 产:産 严:厳
厅:庁 压:圧 县:県 库:庫 应:応 废:廃 庆:慶 边:辺 达:達 迁:遷
过:過 运:運 进:進 远:遠 违:違 连:連 迟:遅 选:選 递:逓 遗:遺
还:還 录:録 彻:徹 态:態 总:総 忆:憶 恳:懇 恶:悪 悬:懸 战:戦
户:戸 护:護 报:報 拥:擁 择:択 拟:擬 换:換 敌:敵 时:時 显:顕
术:術 东:東 枪:槍 桥:橋 检:検 标:標 树:樹 样:様 查:査 欢:歓
毕:畢 汉:漢 泽:沢 测:測 济:済 润:潤 满:満 渐:漸 灵:霊 烦:煩
热:熱 爱:愛 环:環 现:現 电:電 监:監 码:碼 稳:穏 穷:窮 竞:競
简:簡 类:類 紧:緊 红:紅 约:約 级:級 纪:紀 纯:純 纳:納 纵:縦
纷:紛 纸:紙 纽:紐 线:線 练:練 组:組 细:細 织:織 终:終 绍:紹
经:経 结:結 绘:絵 给:給 络:絡 绝:絶 统:統 继:継 绩:績 维:維
综:綜 绿:緑 缓:緩 编:編 缩:縮 罗:羅 罚:罰 罢:罷 义:義 习:習
联:連 节:節 荣:栄 药:薬 营:営 蓝:藍 虑:慮 补:補 规:規 视:視
觉:覚 览:覧 观:観 计:計 认:認 讨:討 让:譲 训:訓 议:議 讯:訊
记:記 论:論 讲:講 设:設 访:訪 证:証 评:評 识:識 诉:訴 词:詞
译:訳 试:試 诗:詩 话:話 询:詢 该:該 详:詳 语:語 误:誤 说:説
请:請 诸:諸 读:読 课:課 谁:誰 调:調 谈:談 谊:誼 谢:謝 谱:譜
财:財 责:責 败:敗 货:貨 购:購 贴:貼 贵:貴 买:買 费:費 贺:賀
资:資 赏:賞 赔:賠 赠:贈 趋:趨 跃:躍 车:車 轨:軌 转:転 轮:輪
软:軟 轻:軽 载:載 较:較 输:輸 铁:鉄 钱:銭 银:銀 锁:鎖 错:錯
键:鍵 长:長 闭:閉 队:隊 阶:階 阳:陽 阴:陰 际:際 陆:陸 险:険
隐:隠 雾:霧 页:頁 顶:頂 项:項 顺:順 顾:顧 顿:頓 预:預 领:領
题:題 风:風 飞:飛 饮:飲 饱:飽 饭:飯 馆:館 马:馬 驱:駆 验:験
鱼:魚 鸟:鳥 鸡:鶏 龙:龍 龟:亀 两:両 侦:偵 侧:側 俭:倹 债:債
倾:傾 偿:償 兰:蘭 兴:興 养:養 兽:獣 冈:岡 军:軍 农:農 减:減
凤:鳳 凯:凱 击:撃 则:則 刚:剛 创:創 删:刪 剂:剤 剧:劇 劝:勧
务:務 动:動 劳:労 勋:勲 协:協 单:単 卖:売 华:華 卫:衛 变:変
亚:亜 亲:親 亿:億 仓:倉 仪:儀 优:優 伟:偉 启:啓 员:員 响:響
哑:唖 备:備 头:頭 奋:奮 奖:奨 妇:婦 娱:娯 孙:孫 实:実 审:審
宫:宮 宾:賓 对:対 寻:尋 导:導 层:層 岁:歳 岛:島 币:幣 帅:帥
师:師 张:張 弹:弾 强:強 归:帰 扩:拡 扫:掃 扬:揚 执:執 苏:蘇
为:為 书:書 释:釈 钟:鐘 沟:溝 洁:潔 狮:獅 猎:猟 暂:暫 笔:筆
骗:騙 驻:駐 骑:騎 鲜:鮮 贰:弐 杂:雑 齐:斉 矿:鉱 疗:療 說:説
稅:税 歲:歳 絕:絶 鄉:郷 內:内 负:負 见:見 贝:貝 专:専 乐:楽
乌:烏 尝:嘗 剑:剣 阅:閲 戶:戸 樱:桜 姬:姫 濑:瀬 绫:綾 萨:薩
绢:絹 绳:縄 聪:聡 蚁:蟻 镇:鎮 鲸:鯨 鹤:鶴 处:処 别:別
"""

# 旧字体や台湾でも使う字など、日本語の人名・固有名詞・専門用語でも使われうる字(報告のみ)。
# 右側は置き換え候補の参考で、--fix では書き換えない。
_REVIEW_SRC = """
坏:壊 泪:涙 粮:糧 凉:涼 變:変 續:続 讀:読 賣:売 繪:絵 淺:浅
滯:滞 鐵:鉄 驛:駅 舍:舎 險:険 實:実 專:専 傳:伝 轉:転 輕:軽
圖:図 團:団 國:国 廢:廃 讓:譲 譯:訳 歸:帰 當:当 發:発 髮:髪
學:学 覺:覚 縣:県 嚴:厳 廳:庁 體:体 假:仮 價:価 兒:児 條:条
藝:芸 舉:挙 與:与 總:総 經:経 繼:継 缺:欠 臟:臓 處:処 從:従
惡:悪 應:応 懷:懐 擔:担 據:拠 擴:拡 擇:択 觸:触 註:注 醫:医
釋:釈 關:関 靜:静 顏:顔 顯:顕 麥:麦 點:点 畫:画 盡:尽 屬:属
峽:峡 恆:恒 勞:労 勵:励 勳:勲 單:単 圍:囲 壓:圧 壯:壮 榮:栄
樂:楽 權:権 歐:欧 沒:没 淨:浄 營:営 獨:独 譽:誉 灣:湾 橫:横
獸:獣 舊:旧 獻:献 隨:随 雜:雑 黨:党 齒:歯 禮:礼 靈:霊 豐:豊
寶:宝 聽:聴 驗:験 檢:検 兩:両 帶:帯 龜:亀 裡:裏 獵:猟
賴:頼 錢:銭 雙:双 濟:済 樓:楼 烟:煙 氣:気 瀨:瀬 筱:篠
遙:遥 适:適 愿:願 惊:驚 晚:晩 极:極 构:構 气:気 泛:汎 确:確
离:離 种:種 网:網 荐:薦 宁:寧 异:異 儿:児 溫:温 緣:縁 歷:歴
醬:醤 雞:鶏 錄:録 价:価 步:歩 戾:戻 壳:殻 广:広 梦:夢 决:決
况:況 盖:蓋 个:個 凭:憑 弃:棄 无:無
"""

# 複数の日本語字に解釈でき、文脈なしでは確定できない文字(報告のみ)
AMBIGUOUS = {
    "发": ["発", "髪"],   # 出发→出発 / 头发→頭髪
    "复": ["復", "複"],   # 恢复→回復 / 复杂→複雑
    "干": ["乾", "幹"],   # 干净→乾浄 / 干部→幹部
    "后": ["後"],         # 然后→然後 (※「后」は日本語でも「皇后」等で使用)
    "并": ["並", "併"],   # 并且→並びに/併せて
    "划": ["画", "劃"],   # 计划→計画
    "冲": ["衝", "沖"],
    "历": ["歴", "暦"],   # 历史→歴史 / 日历→日暦
    # 旧字体は人名(例: 西澤, 廣田, 櫻井, 圓谷, 邊)に意図的に使われるため自動修正しない
    "澤": ["沢"],
    "廣": ["広"],
    "櫻": ["桜"],
    "圓": ["円"],
    "邊": ["辺"],
    "涌": ["湧"],         # 「涌」は「湧」の旧字体
    # 現代の日本語として標準的に使われる字(中国語と符号点を共有する)。
    # 自動修正すると日本語側を壊すため報告のみ(候補はあくまで参考)。
    "几": ["幾"],         # 几帳面→きちょうめん
    "机": ["機"],         # 机(つくえ)は常用漢字。中国語の「机」=機とは限らない
    "据": ["拠"],         # 据える/据え置きは常用漢字
    "迹": ["跡"],         # 迹部 など固有名詞に使用
    "于": ["於"],         # 人名用漢字(于保 など)。中国語の前置詞「于」と同形
}

# 日本語で日常的に使う字は単独では報告せず、中国語の語に含まれるときだけ報告する。
_CHINESE_WORDS = {ch: words.split() for ch, words in {
    "机": "手机 飞机 司机 相机 耳机 主机 电机 计算机 打印机 发动机 虚拟机 洗衣机 "
          "录音机 机器 机会 机制 机构 机场 机械 机关 机密 机能 机动 机遇 机票 "
          "机型 机房 机组 机翻 危机 时机 动机 契机 转机 商机 有机 无机 死机 开机 "
          "关机 待机 登机 停机",
    "干": "干净 干活 干嘛 干吗 干什么 干掉 干脆 干扰 干预 干燥 干杯 干部 干事 "
          "干旱 干涉 树干 饼干",
    "据": "数据 根据 依据 证据 据说 据此 据悉 据称 占据 票据 收据 字据 论据 "
          "凭据 单据",
    "几": "几个 几乎 几何 几天 几年 几次 几种 几点 几分 几位 几十 几百 几千 "
          "好几 这几 那几 茶几",
    "于": "关于 对于 由于 属于 基于 等于 位于 至于 用于 终于 处于 在于 大于 "
          "小于 便于 易于 鉴于 于是 过于 敢于 善于 趋于 归于 源于",
    "迹": "痕迹 奇迹 足迹 轨迹 踪迹 笔迹 遗迹 事迹 迹象 血迹 古迹 手迹",
    "涌": "涌现 涌入 涌动 汹涌 喷涌",
    "裡": "這裡 那裡 哪裡 裡面 裡頭",
    "註": "註冊 註明 備註 註銷",
}.items()}

# 日本語の語に含まれるときは報告しない。「回数据え置き」の「数据」や
# 「若干部分」の「干部」のように、語の境界で中国語の語と重なる誤判定も防ぐ。
_JAPANESE_WORDS = {ch: words.split() for ch, words in {
    "干": "若干 干渉",
    "据": "据え 据わ 据付 据置",
    "几": "几帳 床几",
    "于": "于保",
    "迹": "垂迹 迹部",
    "后": "皇后 太后 王后 后妃 后宮 母后 天后 立后 后土",
    "并": "并河",
    "冲": "冲方",
}.items()}

# 日本語の常用では使われない中華圏専用の字(報告のみ・自動修正なし)
SUSPICIOUS = set(
    "们 这 吗 呢 吧 啊 哦 嗯 哇 哪 啦 咯 哟 喽 嘛 呀 咱 咋 啥 甭 "
    "您 你 它 她 懂 妈 爸 很 办 厂 么 呗 嘿".split()
)

# 中国語でよく誤入力される句読点(--punct 指定時のみ修正)
PUNCT = {"，": "、"}

# ---------------------------------------------------------------------------
# 1b. 誤字・脱字・表記ゆれの検出
# ---------------------------------------------------------------------------

# 単語レベルの誤変換辞書。報告は常時、--fix-words 指定時のみ --fix で適用する。
# プロジェクト固有の誤字は --words <JSON>({"誤": "正"} 形式)で追加できる。
# 注意: 助詞の取捨や文脈に依存する言い換えは対象外(誤修正防止のため最小限のみ)。
TYPO_WORDS = {
    "後程": "後ほど",   # 「のちほど」の誤変換
}

# 助詞(かな)の重複。人名・畳語と紛れるため報告のみ。
# ※ はは(母・笑い)/でで(〜でできる)/とと(とともに・こととし)は誤検出が多いため対象外。
# ※ 「ものの」を除外するため、直前が「も」ののの は対象外。
_PARTICLE_DUP_RE = re.compile(r"((?<!も)のの|がが|をを|にに|へへ)")

# 重複句読点は誤入力として自動修正(--fix 時に適用)
_DUP_PUNCT = [
    (re.compile(r"。。+"), "。"),
    (re.compile(r"、、+"), "、"),
    (re.compile(r"、。"), "。"),
]

# 半角カナ → 全角カナ(濁点・半濁点は直後の ﾞ/ﾟ と結合)
_HWKANA = {
    "｡": "。", "｢": "「", "｣": "」", "､": "、", "･": "・",
    "ｦ": "ヲ", "ｧ": "ァ", "ｨ": "ィ", "ｩ": "ゥ", "ｪ": "ェ", "ｫ": "ォ",
    "ｬ": "ャ", "ｭ": "ュ", "ｮ": "ョ", "ｯ": "ッ", "ｰ": "ー",
    "ｱ": "ア", "ｲ": "イ", "ｳ": "ウ", "ｴ": "エ", "ｵ": "オ",
    "ｶ": "カ", "ｷ": "キ", "ｸ": "ク", "ｹ": "ケ", "ｺ": "コ",
    "ｻ": "サ", "ｼ": "シ", "ｽ": "ス", "ｾ": "セ", "ｿ": "ソ", "ﾀ": "タ",
    "ﾁ": "チ", "ﾂ": "ツ", "ﾃ": "テ", "ﾄ": "ト",
    "ﾅ": "ナ", "ﾆ": "ニ", "ﾇ": "ヌ", "ﾈ": "ネ", "ﾉ": "ノ",
    "ﾊ": "ハ", "ﾋ": "ヒ", "ﾌ": "フ", "ﾍ": "ヘ", "ﾎ": "ホ",
    "ﾏ": "マ", "ﾐ": "ミ", "ﾑ": "ム", "ﾒ": "メ", "ﾓ": "モ",
    "ﾔ": "ヤ", "ﾕ": "ユ", "ﾖ": "ヨ",
    "ﾗ": "ラ", "ﾘ": "リ", "ﾙ": "ル", "ﾚ": "レ", "ﾛ": "ロ",
    "ﾜ": "ワ", "ﾝ": "ン", "ﾞ": "゛", "ﾟ": "゜",
}
_VOICED = {"ｶ": "ガ", "ｷ": "ギ", "ｸ": "グ", "ｹ": "ゲ", "ｺ": "ゴ",
           "ｻ": "ザ", "ｼ": "ジ", "ｽ": "ズ", "ｾ": "ゼ", "ｿ": "ゾ",
           "ﾁ": "ヂ", "ﾂ": "ヅ", "ﾃ": "デ", "ﾄ": "ド",
           "ﾊ": "バ", "ﾋ": "ビ", "ﾌ": "ブ", "ﾍ": "ベ", "ﾎ": "ボ",
           "ｳ": "ヴ", "ﾜ": "ヷ"}
_HANDAKU = {"ﾊ": "パ", "ﾋ": "ピ", "ﾌ": "プ", "ﾍ": "ペ", "ﾎ": "ポ"}

# ---------------------------------------------------------------------------


def _parse_pairs(source):
    """「誤字:正字」を空白区切りで並べた文字列を [(誤字, 正字)] に変換する。"""
    pairs = []
    for line in source.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for token in line.split():
            if token.count(":") != 1:
                raise ValueError("対応表の不正なトークン: %r" % token)
            src, dst = token.split(":")
            if len(src) != 1 or len(dst) != 1:
                raise ValueError("対応表のトークンが1文字でない: %r" % token)
            if src == dst:
                raise ValueError("対応表に同一文字ペア(無意味): %r" % token)
            pairs.append((src, dst))
    return pairs


def build_map():
    m = {}
    for src, dst in _parse_pairs(_MAP_SRC):
        if src in m and m[src] != dst:
            raise ValueError("mapping conflict for %r: %r vs %r"
                             % (src, m[src], dst))
        m[src] = dst
    return m


def _encodable(ch, encoding):
    try:
        ch.encode(encoding)
        return True
    except UnicodeEncodeError:
        return False


def _in_japanese_charset(ch):
    """JIS X 0208(cp932)または JIS X 0213 に収録された字か。"""
    return _encodable(ch, "cp932") or _encodable(ch, "euc_jis_2004")


def _in_taiwan_charset(ch):
    """台湾で使われる Big5 系の文字集合に収録された字か。"""
    return _encodable(ch, "big5") or _encodable(ch, "cp950")


MAP = build_map()
for _src, _dst in _parse_pairs(_REVIEW_SRC):
    AMBIGUOUS.setdefault(_src, [_dst])

# scan_text は MAP を先に判定するため、AMBIGUOUS / SUSPICIOUS と同じ文字が
# MAP にも入ると「要確認/専用字」側が黙って無効化される。ロード時に禁止する。
_OVERLAPS = set(MAP) & (set(AMBIGUOUS) | SUSPICIOUS)
if _OVERLAPS:
    raise ValueError("MAP と AMBIGUOUS/SUSPICIOUS の二重登録: %r"
                     % sorted(_OVERLAPS))

# 文脈判定の語は、対象の字を含み、その字が AMBIGUOUS にあること
for _table in (_CHINESE_WORDS, _JAPANESE_WORDS):
    for _ch, _words in _table.items():
        if _ch not in AMBIGUOUS or any(_ch not in w for w in _words):
            raise ValueError("文脈判定の語が不正です: %r" % _ch)

# Shift-JIS(cp932)で表せる字と、日本語・台湾の両方の文字集合にある字は、
# 日本語として正当な用法がありうる。自動修正すると本来の表記を壊すため、
# MAP への登録をロード時に禁止する。
_PROTECTED = sorted(c for c in MAP
                    if _encodable(c, "cp932")
                    or (_in_japanese_charset(c) and _in_taiwan_charset(c)))
if _PROTECTED:
    raise ValueError("日本語で使われうる字は _REVIEW_SRC に置くこと: %r"
                     % _PROTECTED)

# ---------------------------------------------------------------------------
# 2. ファイル分類とコメント抽出
# ---------------------------------------------------------------------------

DOC_EXTS = {
    ".md", ".markdown", ".txt", ".rst", ".adoc", ".html", ".htm",
    ".json", ".csv", ".tsv", ".tex", ".srt",
}

# --l10n 指定時に、キーを除いた「値」だけを走査する翻訳ファイル
LOCALE_EXTS = {
    ".po", ".pot", ".strings", ".stringsdict", ".xliff", ".xlf",
    ".properties", ".arb", ".resx", ".ftl", ".yml", ".yaml",
}

# 複数行文字列の区切りと、バックスラッシュエスケープの有無
MULTILINE_STRINGS = {
    ".py": (('"""', "'''"), True),
    ".js": (("`",), True), ".jsx": (("`",), True),
    ".ts": (("`",), True), ".tsx": (("`",), True),
    ".go": (("`",), False),
    ".java": (('"""',), True), ".swift": (('"""',), True),
    ".dart": (('"""', "'''"), True),
    ".kt": (('"""',), False), ".scala": (('"""',), False),
    ".cs": (('"""',), False),
    ".lua": (("[[", "[=[", "[==["), False),
}

# 開始と終了で記号が異なる複数行文字列
_STRING_CLOSERS = {"[[": "]]", "[=[": "]=]", "[==[": "]==]"}

# --all 指定時でも走査しない(バイナリと分かっている)拡張子
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".heic",
    ".tif", ".tiff", ".pdf", ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z",
    ".rar", ".tar", ".jar", ".war", ".class", ".so", ".dylib", ".a", ".o",
    ".obj", ".exe", ".dll", ".bin", ".pyc", ".pyo", ".woff", ".woff2",
    ".ttf", ".otf", ".eot", ".mp3", ".m4a", ".wav", ".ogg", ".flac",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".psd", ".ai", ".sketch",
    ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx", ".icns", ".sqlite",
    ".db", ".dmg", ".iso", ".wasm", ".xlsxm",
}

# ブロックコメントの定義。nested は入れ子可、line_start は行頭でのみ有効な記号。
BlockComment = namedtuple("BlockComment",
                          ["open", "close", "nested", "line_start"],
                          defaults=(False, False))

# 拡張子 → (行コメントマーカー群, ブロックコメント(1つ or 複数) or None)
EXT_LANG = {
    ".py": (["#"], None),
    ".rb": (["#"], BlockComment("=begin", "=end", line_start=True)),
    ".sh": (["#"], None), ".bash": (["#"], None), ".zsh": (["#"], None),
    ".yml": (["#"], None), ".yaml": (["#"], None), ".toml": (["#"], None),
    ".ini": (["#"], None), ".cfg": (["#"], None), ".conf": (["#"], None),
    ".r": (["#"], None), ".mk": (["#"], None),
    ".js": (["//"], ("/*", "*/")), ".jsx": (["//"], ("/*", "*/")),
    ".ts": (["//"], ("/*", "*/")), ".tsx": (["//"], ("/*", "*/")),
    ".go": (["//"], ("/*", "*/")), ".c": (["//"], ("/*", "*/")),
    ".h": (["//"], ("/*", "*/")), ".cpp": (["//"], ("/*", "*/")),
    ".cc": (["//"], ("/*", "*/")), ".hpp": (["//"], ("/*", "*/")),
    ".java": (["//"], ("/*", "*/")), ".kt": (["//"], ("/*", "*/")),
    ".swift": (["//"], ("/*", "*/")), ".rs": (["//"], ("/*", "*/")),
    ".php": (["//", "#"], ("/*", "*/")), ".dart": (["//"], ("/*", "*/")),
    ".cs": (["//"], ("/*", "*/")), ".scala": (["//"], ("/*", "*/")),
    ".m": (["//"], ("/*", "*/")), ".vue": (["//"], (("/*", "*/"), ("<!--", "-->"))),
    ".scss": (["//"], ("/*", "*/")), ".less": (["//"], ("/*", "*/")),
    ".proto": (["//"], ("/*", "*/")), ".graphql": (["//"], None),
    ".css": ([], ("/*", "*/")),
    ".sql": (["--"], ("/*", "*/")),
    ".lua": (["--"], (("--[[", "]]"), ("--[=[", "]=]"), ("--[==[", "]==]"))),
    ".hs": (["--"], BlockComment("{-", "-}", nested=True)),
    ".clj": ([";"], None), ".el": ([";"], None), ".lisp": ([";"], None),
    ".scm": ([";"], None),
    ".erl": (["%"], None), ".tex": (["%"], None),
}

DEFAULT_EXCLUDES = [
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", "dist", "build", "target", "vendor", ".idea", ".vscode",
    ".next", "coverage", ".build", "Pods", ".terraform", "__MACOSX",
]

MAX_SIZE = 10 * 1024 * 1024  # 10MB

# --backup が作成するファイルの接尾辞。元の内容を保持するため走査・修正しない
BACKUP_SUFFIX = ".bak-ja-kanji-lint"

# 意図的に中国語で書かれたファイルと推定できるファイル名パターン
# (README_zh.md, README.zh-CN.md, messages_zh_CN.properties など)
ZH_NAME_RE = re.compile(r"(?:^|[_\-.])(zh(?:[-_](?:cn|tw|hans|hant))?|cn)(?:[_\-.]|$)",
                        re.IGNORECASE)

# --l10n 時に中国語ロケールと判定するディレクトリ名(zh-Hans.lproj, zh_CN など)。
# 「cn」単独はプロジェクト名などと紛れるため、ディレクトリ名では判定しない。
ZH_DIR_RE = re.compile(r"(?:^|[_\-.])zh(?:[-_](?:cn|tw|hk|sg|hans|hant|r[a-z]{2}))?"
                       r"(?:[_\-.]|$)", re.IGNORECASE)

# --fix で書き換えない領域(検出結果としては報告する)
_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s<>\"'`)\]」』、。，]+")
_MD_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_MD_INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
_MD_LINK_RE = re.compile(r"\]\(([^)\s]+)")
_HTML_ATTR_RE = re.compile(r"\b(?:href|src)\s*=\s*(\"[^\"]*\"|'[^']*')",
                           re.IGNORECASE)
_JSON_KEY_RE = re.compile(r"\"(?:[^\"\\]|\\.)*\"(?=\s*:)")

# 翻訳ファイルのキー部分
_L10N_TAGS = {".xliff": "target", ".xlf": "target", ".resx": "value",
              ".stringsdict": "string"}
_STRINGS_KEY_RE = re.compile(r"\s*(?:\"(?:[^\"\\]|\\.)*\"|[\w.\-]+)\s*=\s*")
_PROPERTIES_SEP_RE = re.compile(r"(?<!\\)[=:]")
_FTL_KEY_RE = re.compile(r"-?[\w-]+\s*=\s*")
_FTL_ATTR_RE = re.compile(r"\s*\.[\w-]+\s*=\s*")
_YAML_KEY_RE = re.compile(r"\s*(?:-\s+)*(?:\"(?:[^\"\\]|\\.)*\"|'[^']*'|"
                          r"[^\s#:'\"][^:#]*?)\s*:(?=\s|$)")


class SkipFile(Exception):
    """対象外としてスキップすべきファイル。"""


def _quotes_unbalanced(line):
    """行内の引用符の個数が奇数(=対応が崩れている)か。"""
    return line.count("'") % 2 == 1 or line.count('"') % 2 == 1


def _find_marker_quoted(line, marker, start):
    """文字列リテラル(引用符)の外側にある marker を探す。"""
    q = None
    i = start
    n = len(line)
    while i < n:
        c = line[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in ('"', "'"):
            q = c
            i += 1
            continue
        if line.startswith(marker, i):
            # 「https://...」のスキーム部分をコメント開始と誤認しない
            if marker == "//" and i > 0 and line[i - 1] == ":":
                i += 2
                continue
            return i
        i += 1
    return -1


def _find_marker_plain(line, marker, start):
    """引用符を考慮せず marker を探す(URL スキームのガードのみ適用)。"""
    i = start
    n = len(line)
    while i < n:
        if line.startswith(marker, i):
            if marker == "//" and i > 0 and line[i - 1] == ":":
                i += 2
                continue
            return i
        i += 1
    return -1


def find_marker(line, marker, start):
    """marker の位置を返す。無ければ -1。

    引用符を考慮した検索で見つからない場合、行内の引用符の個数が奇数
    (例: 英文の it's のようなアポストロフィで文字列判定が崩れている行)
    ならば単純検索にフォールバックし、コメント検出の取りこぼしを防ぐ。
    """
    j = _find_marker_quoted(line, marker, start)
    if j == -1 and _quotes_unbalanced(line):
        j = _find_marker_plain(line, marker, start)
    return j


def _block_comments(block):
    """EXT_LANG のブロックコメント指定を BlockComment のタプルにそろえる。"""
    if not block:
        return ()
    if isinstance(block, BlockComment):
        return (block,)
    if isinstance(block[0], str):
        return (BlockComment(*block),)
    return tuple(b if isinstance(b, BlockComment) else BlockComment(*b)
                 for b in block)


def _matches_line_start(line, marker):
    """行頭の marker か(=begin のように後ろが空白か行末のものに限る)。"""
    return (line.startswith(marker)
            and (len(line) == len(marker) or line[len(marker)].isspace()))


def _find_block_open(line, blocks, start):
    """start 以降で最初のブロックコメント開始の (位置, BlockComment) を返す。"""
    best, opened = -1, None
    for b in blocks:
        if b.line_start:
            j = 0 if start == 0 and _matches_line_start(line, b.open) else -1
        else:
            j = find_marker(line, b.open, start)
        if j != -1 and (best == -1 or j < best):
            best, opened = j, b
    return best, opened


def _find_block_end(line, start, block, depth):
    """ブロックコメントの終了直後の位置と深さを返す。行内で閉じなければ -1。"""
    if block.line_start:
        if _matches_line_start(line, block.close):
            return len(line), 0
        return -1, depth
    if not block.nested:
        e = line.find(block.close, start)
        return (e + len(block.close), 0) if e != -1 else (-1, depth)
    i = start
    while i < len(line):
        if line.startswith(block.close, i):
            depth -= 1
            i += len(block.close)
            if depth == 0:
                return i, 0
        elif line.startswith(block.open, i):
            depth += 1
            i += len(block.open)
        else:
            i += 1
    return -1, depth


def iter_comment_spans(bodies, lang):
    """各行(改行除去済み)ごとのコメント領域 (行index, start, end) を列挙する。"""
    line_markers, block = lang
    blocks = _block_comments(block)
    active = None
    depth = 0
    for i, line in enumerate(bodies):
        n = len(line)
        if n == 0:
            continue
        spans = []
        pos = 0
        if active:
            e, depth = _find_block_end(line, 0, active, depth)
            if e == -1:
                spans.append((0, n))
                pos = n
            else:
                spans.append((0, e))
                pos = e
                active = None
        while pos < n:
            lm = None
            for m in line_markers:
                j = find_marker(line, m, pos)
                if j != -1 and (lm is None or j < lm):
                    lm = j
            bs, opened = _find_block_open(line, blocks, pos)
            if lm is None and bs == -1:
                break
            # Lua の --[[ は行コメント -- と同じ位置で始まるためブロックを優先する
            if bs != -1 and (lm is None or bs <= lm):
                e, depth = _find_block_end(line, bs + len(opened.open),
                                           opened, 1)
                if e == -1:
                    spans.append((bs, n))
                    active = opened
                    break
                spans.append((bs, e))
                pos = e
            else:
                spans.append((lm, n))
                break
        for s, e in spans:
            yield i, s, e


def mask_multiline_strings(bodies, lang, spec):
    """複数行文字列を空白に置き換えた行を返す(桁位置は維持する)。

    行単位の引用符判定では、複数行文字列の中の # や // をコメントと誤認して
    実行時の文字列を書き換えてしまうため、コメント抽出の前に取り除く。
    """
    delims, escapes = spec
    line_markers, block = lang
    blocks = [b for b in _block_comments(block) if not b.line_start]
    out = []
    in_str = None
    active = None
    depth = 0
    for line in bodies:
        chars = list(line)
        n = len(line)
        i = 0
        quote = None
        while i < n:
            if in_str:
                if escapes and line[i] == "\\":
                    chars[i] = " "
                    if i + 1 < n:
                        chars[i + 1] = " "
                    i += 2
                elif line.startswith(in_str, i):
                    for k in range(i, i + len(in_str)):
                        chars[k] = " "
                    i += len(in_str)
                    in_str = None
                else:
                    chars[i] = " "
                    i += 1
                continue
            if active:
                e, depth = _find_block_end(line, i, active, depth)
                if e == -1:
                    break
                i = e
                active = None
                continue
            if quote:
                if line[i] == "\\":
                    i += 2
                    continue
                if line[i] == quote:
                    quote = None
                i += 1
                continue
            opener = next((d for d in delims if line.startswith(d, i)), None)
            if opener:
                for k in range(i, i + len(opener)):
                    chars[k] = " "
                in_str = _STRING_CLOSERS.get(opener, opener)
                i += len(opener)
                continue
            # Lua の --[[ を行コメントと誤認しないよう、ブロックを先に判定する
            opened = next((b for b in blocks if line.startswith(b.open, i)),
                          None)
            if opened:
                active = opened
                depth = 1
                i += len(opened.open)
                continue
            if any(line.startswith(m, i)
                   and not (m == "//" and i > 0 and line[i - 1] == ":")
                   for m in line_markers):
                break
            if line[i] in "\"'":
                quote = line[i]
            i += 1
        out.append("".join(chars))
    return out


def protected_spans(bodies, ext):
    """--fix で書き換えない領域を {行index: [(start, end)]} で返す。

    URL・リンク先・Markdown のコード・JSON のキーは、書き換えるとリンクや
    プログラムの動作を壊すため、検出のみ行い修正しない。
    """
    is_md = ext in (".md", ".markdown")
    has_html = is_md or ext in (".html", ".htm")
    is_json = ext in (".json", ".arb")
    out = {}
    fence = None
    for i, b in enumerate(bodies):
        ranges = [m.span() for m in _URL_RE.finditer(b)]
        if is_md:
            m = _MD_FENCE_RE.match(b)
            if fence:
                ranges.append((0, len(b)))
                if (m and m.group(1)[0] == fence[0]
                        and len(m.group(1)) >= len(fence)
                        and not m.group(2).strip()):
                    fence = None
                out[i] = ranges
                continue
            if m and not (m.group(1)[0] == "`" and "`" in m.group(2)):
                fence = m.group(1)
                ranges.append((0, len(b)))
                out[i] = ranges
                continue
            ranges += [x.span() for x in _MD_INLINE_CODE_RE.finditer(b)]
            ranges += [x.span(1) for x in _MD_LINK_RE.finditer(b)]
        if has_html:
            ranges += [x.span(1) for x in _HTML_ATTR_RE.finditer(b)]
        if is_json:
            ranges += [x.span() for x in _JSON_KEY_RE.finditer(b)]
        if ranges:
            out[i] = ranges
    return out


def subtract_ranges(spans, ranges):
    """spans から ranges と重なる部分を取り除いた [(start, end)] を返す。"""
    out = []
    ordered = sorted(ranges)
    for s, e in spans:
        cur = s
        for rs, rend in ordered:
            if rend <= cur or rs >= e:
                continue
            if rs > cur:
                out.append((cur, rs))
            cur = max(cur, rend)
        if cur < e:
            out.append((cur, e))
    return out


def _xml_value_spans(bodies, tag):
    open_re = re.compile(r"<%s(?:\s[^>]*?)?(?<!/)>" % tag)
    close = "</%s>" % tag
    spans = {}
    inside = False
    for i, b in enumerate(bodies):
        pos = 0
        while pos <= len(b):
            if inside:
                e = b.find(close, pos)
                end = len(b) if e == -1 else e
                if end > pos:
                    spans.setdefault(i, []).append((pos, end))
                if e == -1:
                    break
                inside = False
                pos = e + len(close)
            else:
                m = open_re.search(b, pos)
                if not m:
                    break
                inside = True
                pos = m.end()
    return spans


def locale_value_spans(bodies, ext):
    """翻訳ファイルの「値」の領域を {行index: [(start, end)]} で返す。"""
    if ext in _L10N_TAGS:
        return _xml_value_spans(bodies, _L10N_TAGS[ext])
    spans = {}

    def add(i, start):
        if start < len(bodies[i]):
            spans[i] = [(start, len(bodies[i]))]

    active = False   # .po の msgstr 継続行 / .properties の継続行
    for i, b in enumerate(bodies):
        st = b.lstrip()
        indent = len(b) - len(st)
        if not st:
            active = False
        elif ext in (".po", ".pot"):
            if st.startswith("msgstr"):
                active = True
                if '"' in b:
                    add(i, b.index('"'))
            elif st.startswith('"') and active:
                add(i, indent)
            else:
                active = False
        elif ext == ".properties":
            if active:
                add(i, indent)
            elif st[0] not in "#!":
                m = _PROPERTIES_SEP_RE.search(b)
                if m:
                    add(i, m.end())
            active = st[0] not in "#!" and b.endswith("\\")
        elif ext == ".strings":
            m = _STRINGS_KEY_RE.match(b)
            if m:
                add(i, m.end())
        elif ext == ".arb":
            keys = [x.span() for x in _JSON_KEY_RE.finditer(b)]
            values = subtract_ranges([(0, len(b))], keys)
            if values:
                spans[i] = values
        elif ext == ".ftl":
            if st.startswith("#"):
                continue
            if indent:
                m = _FTL_ATTR_RE.match(b)
                add(i, m.end() if m else indent)
            else:
                m = _FTL_KEY_RE.match(b)
                if m:
                    add(i, m.end())
        else:   # .yml / .yaml(コメント行と継続行は行全体を対象にする)
            m = _YAML_KEY_RE.match(b)
            add(i, m.end() if m else indent)
    return spans


# ---------------------------------------------------------------------------
# 3. スキャン本体
# ---------------------------------------------------------------------------

class Finding(object):
    def __init__(self, line_no, col, kind, src, dst, context):
        self.line_no = line_no      # 1始まり
        self.col = col              # 1始まり(行内の文字位置)
        self.kind = kind            # fix / ambiguous / suspicious / punct
        self.src = src
        self.dst = dst              # str か list か None
        self.context = context

    def to_dict(self):
        return {"line": self.line_no, "col": self.col, "kind": self.kind,
                "src": self.src, "dst": self.dst, "context": self.context}


# 走査結果1ファイル分。fatal は終了コード(2=エラー)に影響するエラーかどうか。
# (意図的な中国語文書の除外 SkipFile は fatal ではない)
Result = namedtuple("Result",
                    ["path", "findings", "old", "new", "err", "enc", "fatal"])


@functools.lru_cache(maxsize=None)
def is_simplified_only(ch):
    """中国本土の簡体字にしかない字か。

    GB2312 に収録され、日本語(JIS X 0208/0213)にも台湾(Big5)にも無い字だけを
    対象にする。Shift-JIS で表せないことだけを根拠にすると、森鷗外の「鷗」や
    草彅剛の「彅」のような実在の表記を誤検出する。台湾で使う字も日本語と共通する
    ものが多いため、簡体字であるという積極的な根拠がある字に限定する。
    """
    return (_encodable(ch, "gb2312")
            and not _in_japanese_charset(ch)
            and not _in_taiwan_charset(ch))


def _word_at(text, idx, words):
    """text[idx] の字を含む形で words のいずれかが出現しているか。"""
    ch = text[idx]
    for word in words:
        offset = word.find(ch)
        while offset != -1:
            if idx >= offset and text.startswith(word, idx - offset):
                return True
            offset = word.find(ch, offset + 1)
    return False


def is_ambiguous_use(text, idx):
    """AMBIGUOUS の字を、この文脈で「要確認」として報告すべきか。"""
    ch = text[idx]
    if _word_at(text, idx, _JAPANESE_WORDS.get(ch, ())):
        return False
    words = _CHINESE_WORDS.get(ch)
    return words is None or _word_at(text, idx, words)


def scan_text(text, fix_punct=False):
    """1テキスト断片中の検出結果 [(位置, 種別, 原字, 候補)] を返す。"""
    out = []
    for idx, ch in enumerate(text):
        if ch in MAP:
            out.append((idx, "fix", ch, MAP[ch]))
        elif ch in AMBIGUOUS:
            if is_ambiguous_use(text, idx):
                out.append((idx, "ambiguous", ch, AMBIGUOUS[ch]))
        elif ch in SUSPICIOUS or ("一" <= ch <= "鿿"
                                  and is_simplified_only(ch)):
            out.append((idx, "suspicious", ch, None))
        elif fix_punct and ch in PUNCT:
            out.append((idx, "punct", ch, PUNCT[ch]))
    return out


def fix_region(text, args):
    """確実な修正を適用する(文字マップ/句読点/重複記号/誤字辞書/全角半角)。"""
    t = text
    ignore = getattr(args, "ignore_chars", None) or ()
    if args.fix_words and not args.no_typos:
        # --no-typos では語の検出を行わないため、無報告の書き換えもしない
        for w in sorted(TYPO_WORDS, key=len, reverse=True):
            t = t.replace(w, TYPO_WORDS[w])
    res = []
    for ch in t:
        if ch in ignore:
            res.append(ch)
        elif ch in MAP:
            res.append(MAP[ch])
        elif args.punct and ch in PUNCT:
            res.append(PUNCT[ch])
        else:
            res.append(ch)
    t = "".join(res)
    if not args.no_typos:
        # --no-typos は検出だけでなく修正も無効化する(無報告の書き換え防止)
        for pattern, rep in _DUP_PUNCT:
            t = pattern.sub(rep, t)
    if args.width:
        t = normalize_width(t)
    return t


def apply_spans(body, spans, args):
    """行内のコメント領域 (s, e) に fix_region を適用した行を返す。

    修正が文字数を変える(重複句読点の除去・半角カナの濁点結合・語置換)と、
    後続スパンのオフセットがずれて無関係な位置の文字が壊れる。そのため
    後方のスパンから順に適用する。
    """
    fixed = body
    for s, e in reversed(spans):
        fixed = fixed[:s] + fix_region(fixed[s:e], args) + fixed[e:]
    return fixed


def normalize_width(text):
    """全角英数字→半角、半角カナ→全角カナ(濁点結合込み)。"""
    res = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _HWKANA:
            if i + 1 < n:
                nxt = text[i + 1]
                if nxt == "ﾞ" and ch in _VOICED:
                    res.append(_VOICED[ch])
                    i += 2
                    continue
                if nxt == "ﾟ" and ch in _HANDAKU:
                    res.append(_HANDAKU[ch])
                    i += 2
                    continue
            res.append(_HWKANA[ch])
            i += 1
            continue
        o = ord(ch)
        if (0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF3A
                or 0xFF41 <= o <= 0xFF5A):
            res.append(chr(o - 0xFEE0))
        else:
            res.append(ch)
        i += 1
    return "".join(res)


def scan_words(text):
    """誤字辞書に一致する語の [(位置, 種別, 語, 候補)] を返す。"""
    out = []
    for w, r in TYPO_WORDS.items():
        start = 0
        while True:
            i = text.find(w, start)
            if i == -1:
                break
            out.append((i, "word", w, r))
            start = i + len(w)
    out.sort()
    return out


def scan_dup_particles(text):
    return [(mt.start(), "particle", mt.group(0), None)
            for mt in _PARTICLE_DUP_RE.finditer(text)]


def scan_dup_punct(text):
    """重複句読点の報告(修正自体は fix_region が行う)。"""
    out = []
    for pattern, rep in _DUP_PUNCT:
        for mt in pattern.finditer(text):
            out.append((mt.start(), "dup", mt.group(0), rep))
    out.sort()
    return out


def scan_width(text):
    """全角英数字・半角カナの報告(修正は normalize_width が行う)。

    濁点・半濁点は直前のカナと結合した1件として報告し、修正結果
    (例: ｶﾞ→ガ)と候補が食い違わないようにする。
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in _HWKANA and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "ﾞ" and ch in _VOICED:
                out.append((i, "width", ch + nxt, _VOICED[ch]))
                i += 2
                continue
            if nxt == "ﾟ" and ch in _HANDAKU:
                out.append((i, "width", ch + nxt, _HANDAKU[ch]))
                i += 2
                continue
        o = ord(ch)
        if (0xFF10 <= o <= 0xFF19 or 0xFF21 <= o <= 0xFF3A
                or 0xFF41 <= o <= 0xFF5A):
            out.append((i, "width", ch, chr(o - 0xFEE0)))
        elif ch in _HWKANA:
            out.append((i, "width", ch, _HWKANA[ch]))
        i += 1
    return out


def context_of(line, col0, width=26):
    """検出位置の前後を略して表示する。col0 は 0始まり。"""
    s = max(0, col0 - 8)
    e = min(len(line), col0 + width)
    frag = line[s:e]
    if s > 0:
        frag = "…" + frag
    if e < len(line):
        frag = frag + "…"
    return frag.replace("\t", " ")


def wide_encoding(raw, encoding):
    """UTF-16/32 指定時に (バイト順付きコーデック, BOM) を返す。他は None。

    書き戻しでバイト順と BOM の有無が変わらないよう、読み込み時に確定する。
    """
    name = codecs.lookup(encoding).name
    boms = {"utf-16": (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE),
            "utf-32": (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)}
    if name in boms:
        le, be = boms[name]
        if raw.startswith(le):
            return name + "-le", le
        if raw.startswith(be):
            return name + "-be", be
        return name + ("-le" if sys.byteorder == "little" else "-be"), b""
    if name[:-3] in boms and name[-3:] in ("-le", "-be"):
        bom = boms[name[:-3]][0 if name.endswith("-le") else 1]
        return name, bom if raw.startswith(bom) else b""
    return None


def encode_text(text, encoding):
    """テキストを書き戻し用のバイト列にする(wide_encoding の結果にも対応)。"""
    if isinstance(encoding, tuple):
        codec, bom = encoding
        return bom + text.encode(codec)
    return text.encode(encoding)


class FileScanner(object):
    def __init__(self, args):
        self.args = args

    def read(self, path):
        """(テキスト, 書き戻し用エンコーディング) を返す。

        BOM 付き UTF-8 の場合は utf-8-sig で読み書きし、BOM を保持する。
        UTF-16/32 はバイト順と BOM の有無を保持する。
        """
        with open(path, "rb") as f:
            raw = f.read(MAX_SIZE + 1)
        if len(raw) > MAX_SIZE:
            raise IOError("ファイルが大きすぎます (>10MB)")
        if not raw.startswith(codecs.BOM_UTF8):
            wide = wide_encoding(raw, self.args.encoding)
            if wide:
                # UTF-16/32 は正常なテキストにも NUL バイトが含まれるため、
                # デコード後の文字で判定する
                text = raw[len(wide[1]):].decode(wide[0])
                if "\x00" in text:
                    raise IOError("バイナリファイルの可能性")
                return text, wide
        if b"\x00" in raw:
            raise IOError("バイナリファイルの可能性")
        if raw.startswith(b"\xef\xbb\xbf"):
            enc = "utf-8-sig"
        else:
            enc = self.args.encoding
        return raw.decode(enc), enc

    def classify(self, path):
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if self.args.l10n and ext in LOCALE_EXTS:
            return "locale", ext
        if ext in DOC_EXTS:
            return "doc", None
        lang = EXT_LANG.get(ext)
        if lang:
            return "code", lang
        if os.path.basename(path) in ("Makefile", "makefile", "Rakefile",
                                      "Gemfile", "Vagrantfile"):
            return "code", (["#"], None)
        return None, None

    def _check_intentional_chinese(self, path, text, kind):
        """意図的な中国語文書(翻訳ファイル等)を対象外にする。"""
        if self.args.no_skip_zh:
            return
        if ZH_NAME_RE.search(os.path.basename(path)):
            raise SkipFile("ファイル名が中国語(zh/cn)を示すため除外")
        if self.args.l10n:
            parents = os.path.normpath(os.path.dirname(path)).split(os.sep)
            if any(ZH_DIR_RE.search(p) for p in parents[-3:]):
                raise SkipFile("ディレクトリ名が中国語ロケール(zh)を示すため除外")
        if kind in ("doc", "locale"):
            kana =sum(1 for ch in text if "\u3041" <= ch <= "\u30ff")
            hits = sum(1 for ch in text
                       if ch in MAP or ch in AMBIGUOUS or ch in SUSPICIOUS)
            if kana == 0 and hits >= 10:
                raise SkipFile("かなを含まず中国語系文字が多いため、"
                               "中国語文書と推定して除外")

    def scan(self, path, kind, lang):
        """戻り値: (findings, original_lines, fixed_lines, write_encoding)"""
        text, enc = self.read(path)
        self._check_intentional_chinese(path, text, kind)
        lines = text.splitlines(keepends=True)
        bodies = [ln.rstrip("\r\n") for ln in lines]
        ext = os.path.splitext(path)[1].lower()
        protected = protected_spans(bodies, ext)
        ignore = self.args.ignore_chars
        # コメント領域はファイル全体を通じて一度に計算(ブロック継続のため)
        spans_by_line = {}
        if kind == "locale":
            spans_by_line = locale_value_spans(bodies, ext)
        elif kind == "doc":
            for i, b in enumerate(bodies):
                spans_by_line[i] = [(0, len(b))] if b else []
        elif not self.args.include_strings:
            spec = MULTILINE_STRINGS.get(ext)
            masked = (mask_multiline_strings(bodies, lang, spec) if spec
                      else bodies)
            for i, s, e in iter_comment_spans(masked, lang):
                spans_by_line.setdefault(i, []).append((s, e))
        else:
            for i, b in enumerate(bodies):
                spans_by_line[i] = [(0, len(b))] if b else []

        findings = []
        fixed_lines = []
        for i, raw in enumerate(lines):
            body = bodies[i]
            eol = raw[len(body):]
            fixed = body
            spans = spans_by_line.get(i, [])
            for s, e in spans:
                seg = body[s:e]
                for col0, fkind, src, dst in scan_text(seg, self.args.punct):
                    if src in ignore:
                        continue
                    findings.append(Finding(
                        i + 1, s + col0 + 1, fkind, src, dst,
                        context_of(body, s + col0)))
                extra = []
                if not self.args.no_typos:
                    extra += (scan_words(seg) + scan_dup_punct(seg)
                              + scan_dup_particles(seg))
                # --width の検出は --no-typos の対象外(修正側と対にするため)
                if self.args.width:
                    extra += scan_width(seg)
                for col0, fkind, src, dst in extra:
                    findings.append(Finding(
                        i + 1, s + col0 + 1, fkind, src, dst,
                        context_of(body, s + col0)))
            if self.args.fix or self.args.diff:
                fix_spans = subtract_ranges(spans, protected.get(i, []))
                fixed = apply_spans(body, fix_spans, self.args)
            fixed_lines.append(fixed + eol)

        # ドキュメント全体で括弧の対応を確認(コードでは誤検出が多いため対象外)
        if kind == "doc" and not self.args.no_typos:
            for opener, closer, label in (("「", "」", "かぎ括弧"),
                                          ("『", "』", "二重かぎ括弧"),
                                          ("（", "）", "全角丸括弧"),
                                          ("【", "】", "隅付き括弧")):
                no = text.count(opener)
                nc = text.count(closer)
                if no != nc:
                    findings.append(Finding(
                        0, 0, "bracket", label, None,
                        "%s: %d個 / %s: %d個" % (opener, no, closer, nc)))
        return findings, lines, fixed_lines, enc


# ---------------------------------------------------------------------------
# 4. 出力・修正処理
# ---------------------------------------------------------------------------

KIND_LABEL = {
    "fix": "修正候補",
    "word": "誤字候補",
    "ambiguous": "要確認",
    "suspicious": "中華圏専用字",
    "dup": "重複記号",
    "particle": "助詞重複?",
    "bracket": "括弧不一致",
    "width": "全角/半角",
    "punct": "句読点",
}


def print_report(results):
    total = sum(len(r.findings) for r in results)
    shown = 0
    truncated = False
    for r in results:
        if r.err:
            print("スキップ: %s (%s)" % (r.path, r.err))
            continue
        if not r.findings or truncated:
            continue
        print("=== %s (%d件)" % (r.path, len(r.findings)))
        for f in r.findings:
            if shown >= 400:
                print("  … (表示は400件で打ち切り。--json を利用してください)")
                truncated = True
                break
            if f.dst is None:
                sug = ("(削除/書き直しを検討)" if f.kind == "suspicious"
                       else "(自動修正なし・内容を確認)")
            elif isinstance(f.dst, list):
                sug = "/".join(f.dst)
            else:
                sug = f.dst
            print("  %5d:%-4d %-8s %s → %s   「%s」" % (
                f.line_no, f.col, KIND_LABEL[f.kind], f.src, sug, f.context))
            shown += 1
    print("-" * 60)
    print("合計: %d件" % total)


def print_diff(path, old_lines, new_lines, stream=None):
    stream = stream or sys.stdout
    diff = difflib.unified_diff(old_lines, new_lines,
                                fromfile="a/" + path, tofile="b/" + path)
    stream.writelines(diff)


def apply_fix(path, fixed_lines, do_backup, encoding, stream=None):
    """ファイルを修正後の内容で書き戻す。エンコーディング(BOM 含む)を保持する。

    書き込みは同一ディレクトリの一時ファイル経由で行い、書き込み失敗時
    にファイルが空になったり断片化しないようにする。シンボリックリンクの
    場合は従来どおり実体ファイルを書き換える。
    """
    stream = stream or sys.stdout
    # バックアップや一時ファイルを作る前に符号化し、失敗時は何も変更しない
    data = encode_text("".join(fixed_lines), encoding)
    if do_backup:
        bak = path + BACKUP_SUFFIX
        shutil.copy2(path, bak)
        print("backup: %s -> %s" % (path, bak), file=stream)
    target = os.path.realpath(path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target) or ".",
                               prefix=".ja-kanji-lint-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        shutil.copymode(target, tmp)   # 元ファイルの権限を引き継ぐ
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _git_env():
    """親プロセスの GIT_DIR などに影響されない環境変数を返す(Git フック内の実行対策)。"""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _path_key(path):
    """パス比較用のキー。macOS では Git が NFC、OS が NFD の名前を返すことがある。"""
    return unicodedata.normalize("NFC",
                                 os.path.normcase(os.path.abspath(path)))


def _inside_git_repo(directory):
    cur = os.path.abspath(directory)
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return True
        parent = os.path.dirname(cur)
        if parent == cur:
            return False
        cur = parent


def git_ignored_paths(directory):
    """directory 配下で Git が無視するパスのキー集合を返す。Git 管理外なら空集合。

    走査対象のリポジトリは信頼できるとは限らない。core.fsmonitor はリポジトリの
    設定から任意のコマンドを実行できるため、必ず無効化して呼び出す。
    """
    cmd = ["git", "-c", "core.fsmonitor=false", "-C", directory, "ls-files",
           "-z", "--others", "--ignored", "--exclude-standard", "--directory"]
    try:
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                              capture_output=True, env=_git_env(), timeout=60)
    except (OSError, subprocess.SubprocessError):
        proc = None
    if proc is None or proc.returncode != 0:
        if _inside_git_repo(directory):
            print("警告: Git を実行できないため .gitignore を適用できません: %s"
                  % directory, file=sys.stderr)
        return set()
    return {_path_key(os.path.join(directory, os.fsdecode(p)))
            for p in proc.stdout.split(b"\0") if p}


def iter_files(paths, extra_excludes, missing, tool_path=None,
               use_gitignore=True):
    """走査対象ファイルを列挙する。存在しないパスは missing に追記する。

    ディレクトリ走査ではツール本体と Git の無視対象を除外する。プロジェクト直下に
    置かれた場合でも、同じディレクトリの他のファイルは走査する。直接指定された
    ファイルやディレクトリは、無視対象でも走査する。
    """
    excludes = set(DEFAULT_EXCLUDES) | set(extra_excludes or [])
    tool = os.path.realpath(tool_path or __file__)
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        if not os.path.isdir(p):
            missing.append(p)
            print("警告: 存在しないパス: %s" % p, file=sys.stderr)
            continue
        ignored = git_ignored_paths(p) if use_gitignore else set()
        for root, dirs, files in os.walk(p):
            # 入れ子のリポジトリ(サブモジュールなど)には、その .gitignore も適用する
            if use_gitignore and root != p \
                    and (".git" in dirs or ".git" in files):
                ignored |= git_ignored_paths(root)
            dirs[:] = sorted(
                d for d in dirs if d not in excludes
                and not (ignored and _path_key(os.path.join(root, d)) in ignored))
            for name in sorted(files):
                full = os.path.join(root, name)
                if ignored and _path_key(full) in ignored:
                    continue
                if name == os.path.basename(tool) \
                        and os.path.realpath(full) == tool:
                    continue
                yield full


# ---------------------------------------------------------------------------
# 5. selftest
# ---------------------------------------------------------------------------

def _selftest_gitignore():
    """.gitignore 関連のテスト。Git が使えない環境では省略する。"""
    if not shutil.which("git"):
        print("SKIP: git が無いため .gitignore のテストを省略")
        return True
    ok = True

    def check(label, got, expected):
        nonlocal ok
        if got != expected:
            ok = False
            print("FAIL: %s: %r" % (label, got))

    with tempfile.TemporaryDirectory() as d:
        def git(*cmd, cwd=d):
            return subprocess.run(["git", "-C", cwd, *cmd],
                                  stdin=subprocess.DEVNULL, capture_output=True,
                                  env=_git_env()).returncode

        def write(rel, text="关门\n"):
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as h:
                h.write(text)
            return p

        def names(paths, **kwargs):
            return sorted(os.path.relpath(x, d).replace(os.sep, "/")
                          for x in iter_files(paths, [], [], **kwargs))

        if git("init", "-q") != 0:
            print("SKIP: git init に失敗したため .gitignore のテストを省略")
            return True
        for rel in ("src/keep.md", "generated/sub/a.md", "ignored.md",
                    "tracked.md", "nested/keep.md", "nested/gen/a.md",
                    unicodedata.normalize("NFD", "ガイド.ignored.md")):
            write(rel)
        write(".gitignore", "generated/\nignored.md\ntracked.md\n*.ignored.md\n")
        git("add", "-f", "tracked.md")
        git("init", "-q", cwd=os.path.join(d, "nested"))
        write("nested/.gitignore", "gen/\n")

        # 無視対象を除外する。追跡済みファイルは無視パターンに一致しても残す
        check(".gitignore の適用", names([d]),
              [".gitignore", "nested/.gitignore", "nested/keep.md",
               "src/keep.md", "tracked.md"])
        everything = set(names([d], use_gitignore=False))
        check("--no-gitignore 相当",
              {"generated/sub/a.md", "ignored.md", "nested/gen/a.md"}
              <= everything, True)
        # 直接指定されたパスは無視対象でも走査する
        check("無視ディレクトリの直接指定",
              names([os.path.join(d, "generated")]), ["generated/sub/a.md"])
        check("無視ファイルの直接指定",
              names([os.path.join(d, "ignored.md")]), ["ignored.md"])
        # 走査対象のリポジトリ設定にあるコマンドを実行しない
        if os.name == "posix":
            marker = os.path.join(d, "fsmonitor-ran")
            hook = write("hook.sh", "#!/bin/sh\n: > '%s'\n" % marker)
            os.chmod(hook, 0o755)
            git("config", "core.fsmonitor", hook)
            git_ignored_paths(d)
            check("core.fsmonitor を実行しない", os.path.exists(marker), False)
    return ok


def selftest():
    ok = True
    cases = [
        ("ソフトの関数を実行する", [], []),
        ("开发人员と关门时间", ["开", "员", "关", "门", "时", "间"], []),
        ("质量と品質、质的处理", ["质", "质", "处"], []),
        ("头发と発展の区别", ["头", "别"], []),   # 发は「要確認」、区は日中共通字で対象外
        ("这们东西很好", ["东"], ["这", "们", "很"]),
        ("設定値は温度です", [], []),
        ("简体字の字", ["简"], []),
    ]
    for text, expect_fix, expect_susp in cases:
        got = scan_text(text, False)
        fixes = [s for _i, k, s, _d in got if k == "fix"]
        susps = [s for _i, k, s, _d in got if k == "suspicious"]
        if fixes != expect_fix or susps != expect_susp:
            ok = False
            print("FAIL: %r -> fix=%r susp=%r (期待 fix=%r susp=%r)"
                  % (text, fixes, susps, expect_fix, expect_susp))

    # URL スキームをコメント誤認しない
    lang = (["//"], None)
    spans = list(iter_comment_spans(['url = "https://example.com/開発"'], lang))
    if spans:
        ok = False
        print("FAIL: URL scheme をコメント誤認: %r" % (spans,))

    # ブロックコメントの行跨ぎ
    bodies = ["/* 開発中の機能", "継続 */ code();"]
    spans = list(iter_comment_spans(bodies, (["//"], ("/*", "*/"))))
    if len(spans) != 2 or spans[0][0] != 0 or spans[1][0] != 1:
        ok = False
        print("FAIL: ブロックコメント: %r" % (spans,))

    # 文字列リテラル内の # をコメント誤認しない
    spans = list(iter_comment_spans(['color = "#FF0000"  # 顔色'], (["#"], None)))
    if spans != [(0, 19, 23)]:
        ok = False
        print("FAIL: # コメント位置: %r" % (spans,))

    # アポストロフィで引用符判定が崩れても // コメントを検出する
    spans = list(iter_comment_spans(["x = it's fine; // 開発メモ"],
                                    (["//"], None)))
    if len(spans) != 1 or spans[0][1] != 15:
        ok = False
        print("FAIL: アポストロフィ行: %r" % (spans,))

    # 旧字体(人名に使われうる字)は AMBIGUOUS で自動修正しない
    got = scan_text("西澤さん", False)
    if [k for _i, k, _s, _d in got] != ["ambiguous"]:
        ok = False
        print("FAIL: 旧字体の扱い: %r" % (got,))

    # 誤字辞書・重複記号・表記ゆれ
    got = scan_words("後程お送りします")
    if [(s, d) for _i, _k, s, d in got] != [("後程", "後ほど")]:
        ok = False
        print("FAIL: 誤字辞書: %r" % (got,))
    if len(scan_dup_punct("確認。。完了、、")) != 2:
        ok = False
        print("FAIL: 重複記号の検出")
    if len(scan_dup_particles("設定のの確認")) != 1:
        ok = False
        print("FAIL: 助詞重複の検出")
    if scan_dup_particles("終了したものの、動作は速い") != []:
        ok = False
        print("FAIL: 「ものの」の除外")

    a = argparse.Namespace(fix_words=False, punct=False, width=False,
                           no_typos=False)
    if fix_region("後程。。ＡＢＣ", a) != "後程。ＡＢＣ":
        ok = False
        print("FAIL: fix_region(辞書OFF)")
    a = argparse.Namespace(fix_words=True, punct=False, width=True,
                           no_typos=False)
    if fix_region("後程。。ＡＢＣｶﾞ", a) != "後ほど。ABCガ":
        ok = False
        print("FAIL: fix_region(辞書ON/widthON)")
    if fix_region("半角ｶﾀｶﾅ", a) != "半角カタカナ":
        ok = False
        print("FAIL: 半角カナ(ﾀ)")

    # --no-typos は重複句読点の修正も止める(報告なしの書き換え防止)
    a = argparse.Namespace(fix_words=False, punct=False, width=False,
                           no_typos=True)
    if fix_region("確認。。です", a) != "確認。。です":
        ok = False
        print("FAIL: fix_region(--no-typos で句読点を修正しない)")

    # 1行に複数のコメント領域があると、修正で後続のオフセットがずれないか
    a = argparse.Namespace(fix_words=False, punct=False, width=False,
                           no_typos=False)
    line = "a = 1; /* memo。。 */ b = 2; // 確認。。"
    spans = [(s, e) for _i, s, e
             in iter_comment_spans([line], (["//"], ("/*", "*/")))]
    got = apply_spans(line, spans, a)
    if got != "a = 1; /* memo。 */ b = 2; // 確認。":
        ok = False
        print("FAIL: 複数コメント領域の修正(オフセットずれ): %r" % got,)

    # 濁点・半濁点は結合して1件として報告し、修正結果と候補が一致する
    if scan_width("ｶﾞﾊﾟ") != [(0, "width", "ｶﾞ", "ガ"),
                              (2, "width", "ﾊﾟ", "パ")]:
        ok = False
        print("FAIL: scan_width(濁点結合): %r" % (scan_width("ｶﾞﾊﾟ"),))

    # 日本語として標準的な共有字は自動修正しない(几帳面・据え置き等)
    for word in ("机上の空論", "机の上", "勉強机", "若干", "若干部分", "若干杯",
                 "干渉", "機能干渉", "干す", "物干し", "梅干し", "据える",
                 "据え置き", "見据える", "回数据え置き", "几帳面", "床几", "皇后",
                 "太后", "迹部", "垂迹", "于保", "涌き水", "冲方丁", "并河",
                 "脳裡", "脚註", "註解", "奇蹟", "桧山"):
        got = scan_text(word, False)
        if got:
            ok = False
            print("FAIL: 正しい日本語を報告: %s %r" % (word, got))
    # 同じ字でも中国語の語や単独の用法は「要確認」として報告する
    for word, ch in (("手机", "机"), ("机器", "机"), ("数据", "据"),
                     ("根据", "据"), ("干净", "干"), ("几乎", "几"),
                     ("用于", "于"), ("痕迹", "迹"), ("時間后", "后"),
                     ("設定并保存", "并"), ("這裡", "裡"), ("註冊", "註")):
        if ch not in [s for _i, k, s, _d in scan_text(word, False)
                      if k == "ambiguous"]:
            ok = False
            print("FAIL: 中国語の用法を見逃した: %s" % word)
    # 「楼」は日本語の標準字。旧字体の「樓」は報告のみで自動修正しない
    if scan_text("楼閣", False) != [] or \
            [(k, d) for _i, k, _s, d in scan_text("樓閣", False)] \
            != [("ambiguous", ["楼"])]:
        ok = False
        print("FAIL: 楼/樓の扱い")

    # 簡体字にしかない字は検出する
    got = scan_text("账链获", False)
    if [k for _i, k, _s, _d in got] != ["suspicious"] * 3:
        ok = False
        print("FAIL: 簡体字のみの字: %r" % (got,))
    # 日本語や台湾でも使う字を「中華圏専用字」と誤判定しない
    got = scan_text("森鷗外草彅剛𠮷野家髙橋山﨑德濵栁𠮟塡剝頰俱吞搔瘦麴荔榨涉每"
                    "骨粗鬆症噓繫顚", False)
    if got != []:
        ok = False
        print("FAIL: 正当な字を誤検出: %r" % (got,))

    # 旧字体・人名・専門用語・台湾と共有する字は自動修正しない
    a = argparse.Namespace(fix_words=False, punct=False, width=False,
                           no_typos=False)
    for word in ("森鷗外", "草彅剛", "渡邊", "骨粗鬆症", "欠缺", "高坏", "桧山",
                 "泪橋", "國分", "實", "與謝野", "遙", "奇蹟", "脚註", "溫泉",
                 "晚", "日历", "广", "无"):
        if fix_region(word, a) != word:
            ok = False
            print("FAIL: 正当な語を書き換えた: %s -> %s"
                  % (word, fix_region(word, a)))
    if fix_region("驱动", a) != "駆動":
        ok = False
        print("FAIL: 驱 の修正先: %s" % fix_region("驱动", a))
    if [k for _i, k, _s, _d in scan_text("日历", False)] != ["ambiguous"]:
        ok = False
        print("FAIL: 历 は複数候補として報告する")

    # --no-typos 指定時は語の修正も行わない(無報告の書き換え防止)
    a = argparse.Namespace(fix_words=True, punct=False, width=False,
                           no_typos=True)
    if fix_region("後程", a) != "後程":
        ok = False
        print("FAIL: --no-typos で語を書き換えた")

    with tempfile.TemporaryDirectory() as d:
        def run(name, text, *flags):
            p = os.path.join(d, name)
            with open(p, "w", encoding="utf-8", newline="") as h:
                h.write(text)
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(list(flags) + [p])
            with open(p, encoding="utf-8", newline="") as h:
                return code, h.read()

        def check(label, got_text, expected):
            nonlocal ok
            if got_text != expected:
                ok = False
                print("FAIL: %s: %r" % (label, got_text))

        # ツールと同じディレクトリの他のファイルも走査する
        tool = os.path.join(d, "tool.py")
        doc = os.path.join(d, "a.md")
        for p in (tool, doc):
            with open(p, "w", encoding="utf-8") as h:
                h.write("关门\n")
        check("ツール配置ディレクトリの走査",
              list(iter_files([d], [], [], tool_path=tool)), [doc])
        os.unlink(tool)
        os.unlink(doc)

        # URL・リンク先・Markdown のコード・JSON のキーは書き換えない
        check("Markdown の保護", run(
            "b.md", "[x](https://example.com/关门) `关门` 关门\n```\n关门\n```\n",
            "--fix")[1],
            "[x](https://example.com/关门) `关门` 関門\n```\n关门\n```\n")
        check("JSON キーの保護", run("c.json", '{"关门": "关门"}\n', "--fix")[1],
              '{"关门": "関門"}\n')

        # 複数行文字列の中身はコメントとして扱わない
        check("Python の複数行文字列", run(
            "d.py", 'S = """\n# 关门\n"""\n# 关门\n', "--fix")[1],
            'S = """\n# 关门\n"""\n# 関門\n')
        check("テンプレートリテラル", run(
            "e.ts", "const s = `\n// 关门\n`; // 关门\n", "--fix")[1],
            "const s = `\n// 关门\n`; // 関門\n")

        # --l10n は翻訳ファイルの値だけを走査・修正する
        for name, text, expected in (
                ("f.po", 'msgid "关门"\nmsgstr "关门"\n',
                 'msgid "关门"\nmsgstr "関門"\n'),
                ("g.properties", "关门=关门\n", "关门=関門\n"),
                ("h.yml", "关门: 关门\n", "关门: 関門\n"),
                ("i.strings", '"关门" = "关门";\n', '"关门" = "関門";\n'),
                ("j.xliff", "<source>关门</source><target>关门</target>\n",
                 "<source>关门</source><target>関門</target>\n"),
                ("k.arb", '{"关门": "关门"}\n', '{"关门": "関門"}\n'),
                ("l.resx", '<data name="关门"><value>关门</value></data>\n',
                 '<data name="关门"><value>関門</value></data>\n'),
                ("m.ftl", "关门 = 关门\n", "关门 = 関門\n")):
            check("--l10n %s" % name, run(name, text, "--l10n", "--fix")[1],
                  expected)
        check("--l10n なしの .po", run("n.po", 'msgstr "关门"\n')[0], 0)

        # CI で正当な日本語を許容できる
        check("既定の終了コード", run("o.md", "國の上\n")[0], 1)
        check("--fail-on", run("p.md", "國の上\n", "--fail-on", "fix")[0], 0)
        check("--ignore-chars", run("q.md", "國の上\n", "--ignore-chars", "國")[0],
              0)
        check("--ignore-chars の修正除外", run(
            "r.md", "关门\n", "--ignore-chars", "关", "--fix")[1], "关門\n")

        # --words の空キーは検索が終わらなくなるため拒否する
        words = os.path.join(d, "words.json")
        with open(words, "w", encoding="utf-8") as h:
            h.write('{"": "x"}')
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["--words", words, words])
            check("--words の空キー", "受理された", "拒否")
        except SystemExit as ex:
            check("--words の空キー", ex.code, 2)
        os.unlink(words)

        # UTF-16/32 はバイト順・BOM の有無・改行を保持して修正する
        wide = os.path.join(d, "wide.md")
        for enc, bom, codec in (("utf-16", codecs.BOM_UTF16_LE, "utf-16-le"),
                                ("utf-16", codecs.BOM_UTF16_BE, "utf-16-be"),
                                ("utf-16-le", b"", "utf-16-le"),
                                ("utf-16-be", codecs.BOM_UTF16_BE, "utf-16-be"),
                                ("utf-32", codecs.BOM_UTF32_BE, "utf-32-be")):
            with open(wide, "wb") as h:
                h.write(bom + "关门\r\n".encode(codec))
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--encoding", enc, "--fix", wide])
            with open(wide, "rb") as h:
                check("%s の書き戻し" % enc, (code, h.read()),
                      (1, bom + "関門\r\n".encode(codec)))
        with open(wide, "wb") as h:
            h.write("a\x00b".encode("utf-16"))
        with contextlib.redirect_stdout(io.StringIO()):
            check("UTF-16 のバイナリ判定",
                  main(["--encoding", "utf-16", wide]), 2)
        os.unlink(wide)

        # 実際のフォルダ名 __MACOSX を除外する
        mac = os.path.join(d, "mac", "__MACOSX")
        os.makedirs(mac)
        with open(os.path.join(mac, "a.md"), "w", encoding="utf-8") as h:
            h.write("关门\n")
        check("__MACOSX の除外",
              list(iter_files([os.path.join(d, "mac")], [], [])), [])

        # Vue / Lua / Haskell / Ruby のブロックコメント
        for name, text, expected in (
                ("s.vue", "<p>关门</p><!-- 关门 -->\n",
                 "<p>关门</p><!-- 関門 -->\n"),
                ("t.vue", "<!--\n关门\n-->\n<p>关门</p>\n",
                 "<!--\n関門\n-->\n<p>关门</p>\n"),
                ("u.lua", "x = 1 --[[ 关门 ]] y = '关门'\n",
                 "x = 1 --[[ 関門 ]] y = '关门'\n"),
                ("v.lua", "--[==[\n关门 ]] 关门\n]==]\nz = '关门'\n",
                 "--[==[\n関門 ]] 関門\n]==]\nz = '关门'\n"),
                ("w.lua", "s = [[\n-- 关门\n]]\n-- 关门\n",
                 "s = [[\n-- 关门\n]]\n-- 関門\n"),
                ("y.hs", "{- 关门 {- 关门 -} 关门 -} f = \"关门\"\n",
                 "{- 関門 {- 関門 -} 関門 -} f = \"关门\"\n"),
                ("z.hs", "{- a {- b\n关门 -} 关门\n-} g = 关门\n",
                 "{- a {- b\n関門 -} 関門\n-} g = 关门\n"),
                ("a.rb", "=begin\n关门\n=end\nputs '关门'\n",
                 "=begin\n関門\n=end\nputs '关门'\n"),
                ("b.rb", "x =begin\n关门\n=beginning\n关门\n",
                 "x =begin\n关门\n=beginning\n关门\n")):
            check("コメント %s" % name, run(name, text, "--fix")[1], expected)

        # 既存のバックアップは --all --fix でも書き換えない(元の内容を失わないため)
        bak = os.path.join(d, "x.md" + BACKUP_SUFFIX)
        with open(bak, "w", encoding="utf-8") as f:
            f.write("关门です\n")
        with contextlib.redirect_stdout(io.StringIO()):
            main(["--all", "--fix", d])
        with open(bak, encoding="utf-8") as f:
            if f.read() != "关门です\n":
                ok = False
                print("FAIL: バックアップが書き換えられた")

    ok = _selftest_gitignore() and ok

    print("selftest: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# 6. main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="中国語系漢字(簡体字・繁体字)の誤用を検出・修正します")
    ap.add_argument("paths", nargs="*", help="走査対象のファイル/ディレクトリ")
    ap.add_argument("--fix", action="store_true", help="修正をファイルに適用する")
    ap.add_argument("--diff", action="store_true",
                    help="修正案を unified diff で表示")
    ap.add_argument("--backup", action="store_true",
                    help="--fix 時に <file>.bak-ja-kanji-lint を残す")
    ap.add_argument("--json", action="store_true",
                    help="JSON で出力する(通知・diff は stderr に出す)")
    ap.add_argument("--punct", action="store_true",
                    help="中国語句読点(，→、)も対象にする")
    ap.add_argument("--fix-words", action="store_true",
                    help="誤字辞書(単語レベル)の修正も --fix で適用する")
    ap.add_argument("--width", action="store_true",
                    help="全角英数字・半角カナの検出/修正も行う")
    ap.add_argument("--no-typos", action="store_true",
                    help="誤字・重複記号・括弧不一致などの検出を無効化する"
                         "(中国語系漢字の検出のみ行う)")
    ap.add_argument("--words", metavar="JSON", default=None,
                    help="追加の誤字辞書 JSON({\"誤\": \"正\"} 形式)を読み込む")
    ap.add_argument("--include-strings", action="store_true",
                    help="コメントだけでなくコード行全体(文字列リテラル等)を走査")
    ap.add_argument("--all", action="store_true",
                    help="既知拡張子以外のテキストファイルも文書として走査")
    ap.add_argument("--no-skip-zh", action="store_true",
                    help="中国語文書の自動除外(ファイル名/かな判定)を無効化する")
    ap.add_argument("--ext", nargs="*", default=[],
                    help="追加で走査する拡張子 (例: --ext .tex .org)")
    ap.add_argument("--exclude", nargs="*", default=[],
                    help="除外するディレクトリ名を追加")
    ap.add_argument("--encoding", default="utf-8", help="入力エンコーディング"
                    "(書き戻しにも同じものを使う)")
    ap.add_argument("--l10n", action="store_true",
                    help="翻訳ファイル(.po .strings .xliff .properties .arb "
                         ".resx .ftl .yml など)の値を走査する")
    ap.add_argument("--ignore-chars", metavar="CHARS", default="",
                    help="検出・修正しない文字を並べて指定する"
                         "(例: --ignore-chars 澤廣櫻)")
    ap.add_argument("--fail-on", metavar="KINDS", default=None,
                    help="終了コード 1 にする種別をカンマ区切りで指定する"
                         "(例: fix,suspicious。既定は全種別)")
    ap.add_argument("--no-gitignore", action="store_true",
                    help="Git の無視対象(.gitignore など)も走査する")
    ap.add_argument("--selftest", action="store_true",
                    help="内部テストを実行して終了")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.paths:
        ap.error("走査対象のパスを指定してください")
    args.ignore_chars = set(args.ignore_chars)
    fail_kinds = set(KIND_LABEL)
    if args.fail_on is not None:
        fail_kinds = {k.strip() for k in args.fail_on.split(",") if k.strip()}
        unknown = sorted(fail_kinds - set(KIND_LABEL))
        if unknown or not fail_kinds:
            ap.error("--fail-on の種別が不正です: %s(指定可能: %s)"
                     % (",".join(unknown), ",".join(sorted(KIND_LABEL))))
    try:
        codecs.lookup(args.encoding)
    except LookupError:
        ap.error("不明なエンコーディング: %s" % args.encoding)

    for e in args.ext or []:
        e = e if e.startswith(".") else "." + e
        DOC_EXTS.add(e.lower())

    if args.words:
        with open(args.words, encoding="utf-8") as f:
            extra = json.load(f)
        if not isinstance(extra, dict):
            ap.error("--words は {\"誤字\": \"正字\"} 形式の JSON を指定してください")
        if any(not str(k) for k in extra):
            ap.error("--words に空のキーは指定できません")
        TYPO_WORDS.update({str(k): str(v) for k, v in extra.items()})

    scanner = FileScanner(args)
    results = []
    missing_paths = []
    for path in iter_files(args.paths, args.exclude, missing_paths,
                           use_gitignore=not args.no_gitignore):
        if path.endswith(BACKUP_SUFFIX):
            continue  # --all / --ext / パス直接指定でもバックアップは書き換えない
        try:
            kind, lang = scanner.classify(path)
            if kind is None:
                if not args.all:
                    continue
                if os.path.splitext(path)[1].lower() in BINARY_EXTS:
                    continue  # --all でもバイナリ拡張子は除外
                kind, lang = "doc", None
            findings, old, new, enc = scanner.scan(path, kind, lang)
            if not (args.fix or args.diff):
                # diff/fix に使わない行全体は保持しない(大規模ツリーで
                # メモリが積み上がるのを防ぐ)
                old = new = None
            results.append(Result(path, findings, old, new, None, enc, False))
        except SkipFile as ex:
            results.append(Result(path, [], None, None, str(ex), None, False))
        except (IOError, UnicodeDecodeError, LookupError) as ex:
            results.append(Result(path, [], None, None, str(ex), None, True))

    # 終了コード: 2=エラー(存在しないパス・読み取り不能ファイル) >
    #           1=検出あり > 0=検出なし。出力形式(--json 等)には依存しない。
    if missing_paths or any(r.fatal for r in results):
        exit_code = 2
    else:
        exit_code = 1 if any(f.kind in fail_kinds
                             for r in results for f in r.findings) else 0

    if args.json:
        data = {"files": [], "summary": {"files": 0}}
        for r in results:
            entry = {"path": r.path,
                     "findings": [f.to_dict() for f in r.findings]}
            if r.err:
                entry["error"] = r.err
            data["files"].append(entry)
            data["summary"]["files"] += 1
            for f in r.findings:
                data["summary"][f.kind] = data["summary"].get(f.kind, 0) + 1
        if missing_paths:
            data["missing_paths"] = missing_paths
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_report(results)

    # --diff / --fix の実処理。--json 時は stdout を JSON 専用に保つため
    # diff や backup 通知を stderr に出す。
    stream = sys.stderr if args.json else sys.stdout
    for r in results:
        if not r.old or r.old == r.new:
            continue
        if args.diff:
            print_diff(r.path, r.old, r.new, stream)
        if args.fix:
            apply_fix(r.path, r.new, args.backup, r.enc, stream)

    return exit_code


if __name__ == "__main__":
    # cp932 などの出力先でも、表示できない字で処理全体を中断しない
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(errors="backslashreplace")
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as ex:  # 整形されていない例外はここで拾って exit 2
        print("エラー: %s" % ex, file=sys.stderr)
        sys.exit(2)
