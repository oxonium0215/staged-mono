#!/bin/env python3

import configparser
import glob
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from fontTools import merge, ttLib, ttx
from ttfautohint import options, ttfautohint

# iniファイルを読み込む
settings = configparser.ConfigParser()
settings.read("build.ini", encoding="utf-8")

FONT_NAME = settings.get("DEFAULT", "FONT_NAME").replace(" ", "")
FONTFORGE_PREFIX = settings.get("DEFAULT", "FONTFORGE_PREFIX")
FONTTOOLS_PREFIX = settings.get("DEFAULT", "FONTTOOLS_PREFIX")
SOURCE_FONTS_DIR = os.environ.get("SOURCE_FONTS_DIR") or settings.get("DEFAULT", "SOURCE_FONTS_DIR")
BUILD_FONTS_DIR = os.environ.get("BUILD_FONTS_DIR") or settings.get("DEFAULT", "BUILD_FONTS_DIR")
HALF_WIDTH_STR = settings.get("DEFAULT", "HALF_WIDTH_STR")
HALF_WIDTH_12 = int(settings.get("DEFAULT", "HALF_WIDTH_12"))
HALF_WIDTH_35 = int(settings.get("DEFAULT", "HALF_WIDTH_35"))
FULL_WIDTH_35 = int(settings.get("DEFAULT", "FULL_WIDTH_35"))
EM_ASCENT = int(settings.get("DEFAULT", "EM_ASCENT"))
EM_DESCENT = int(settings.get("DEFAULT", "EM_DESCENT"))
OS2_ASCENT = int(settings.get("DEFAULT", "OS2_ASCENT"))
OS2_DESCENT = int(settings.get("DEFAULT", "OS2_DESCENT"))
OS2_LINEGAP = int(settings.get("DEFAULT", "OS2_LINEGAP"))


def main():
    # 第一引数を取得
    # 特定のバリエーションのみを処理するための指定
    specific_variant = None
    line_height = None

    for arg in sys.argv[1:]:
        if arg.startswith("--line-height="):
            line_height = float(arg.split("=")[1])
        else:
            specific_variant = arg

    edit_fonts(specific_variant, line_height)


def edit_fonts(specific_variant: str, line_height: float = None):
    """フォントを編集する"""

    global OS2_ASCENT, OS2_DESCENT, OS2_LINEGAP
    if line_height is not None:
        # HackGen互換: 行高さを Typo/Win 両方で調整
        # line_height=1.12 → Typo=1.08 EM, Win=1.12 EM (HackGenと同等)
        total = round(1000 * line_height)
        OS2_LINEGAP = max(0, total - 1000 - 40)  # Typo用: 約4%少なく
        OS2_ASCENT = 880 + (total - 1000) // 2   # Win用: 上下に分配
        OS2_DESCENT = 120 + (total - 1000) - (total - 1000) // 2

    if specific_variant is None:
        specific_variant = ""

    # ファイルをパターンで指定
    file_pattern = f"{FONTFORGE_PREFIX}{FONT_NAME}{specific_variant}*-eng.ttf"
    filenames = glob.glob(f"{BUILD_FONTS_DIR}/{file_pattern}")
    # ファイルが見つからない場合はエラー
    if len(filenames) == 0:
        print(f"Error: {file_pattern} not found")
        return
    paths = [Path(f) for f in filenames]
    for path in paths:
        print(f"edit {str(path)}")
        style = path.stem.split("-")[1]
        variant = path.stem.split("-")[0].replace(f"{FONTFORGE_PREFIX}{FONT_NAME}", "")
        add_hinting(str(path), str(path).replace(".ttf", "-hinted.ttf"))
        merge_fonts(style, variant)
        fix_font_tables(style, variant)

    # 一時ファイルを削除
    # スタイル部分以降はワイルドカードで指定
    for filename in glob.glob(
        f"{BUILD_FONTS_DIR}/{FONTTOOLS_PREFIX}{FONT_NAME}{specific_variant}*"
    ):
        os.remove(filename)
    for filename in glob.glob(
        f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME}{specific_variant}*"
    ):
        os.remove(filename)


def add_hinting(input_font_path, output_font_path):
    """フォントにヒンティングを付与（罫線・ブロック要素は除外）"""
    # 罫線・ブロック要素（U+2500-U+259F）をヒンティング対象から除外するため事前に退避
    original_font = ttLib.TTFont(input_font_path)
    original_glyf = original_font.get("glyf")
    cmap = original_font.getBestCmap()

    saved_glyphs = {}
    if original_glyf:
        for code in range(0x2500, 0x259F + 1):
            if code in cmap:
                glyph_name = cmap[code]
                if glyph_name in original_glyf:
                    saved_glyphs[glyph_name] = original_glyf[glyph_name]
    original_font.close()

    args = [
        "-l",
        "6",
        "-r",
        "45",
        "-D",
        "latn",
        "-f",
        "none",
        "-S",
        "-W",
        "-X",
        "13-",
        "-I",
        input_font_path,
        output_font_path,
    ]
    options_ = options.parse_args(args)
    print("exec hinting", options_)
    ttfautohint(**options_)

    # 退避したグリフを未ヒンティングの状態で復元
    if saved_glyphs:
        hinted_font = ttLib.TTFont(output_font_path)
        hinted_glyf = hinted_font.get("glyf")
        if hinted_glyf:
            for glyph_name, glyph_data in saved_glyphs.items():
                if glyph_name in hinted_glyf:
                    hinted_glyf[glyph_name] = glyph_data
            hinted_font.save(output_font_path)
            print(f"Restored {len(saved_glyphs)} box drawing glyphs (unhinted)")
        hinted_font.close()


def merge_fonts(style, variant):
    """フォントを結合する"""
    eng_font_path = f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME}{variant}-{style}-eng-hinted.ttf"
    jp_font_path = (
        f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME}{variant}-{style}-jp.ttf"
    )

    # vhea, vmtxテーブルを削除
    jp_font_object = ttLib.TTFont(jp_font_path)
    if "vhea" in jp_font_object:
        del jp_font_object["vhea"]
    if "vmtx" in jp_font_object:
        del jp_font_object["vmtx"]
    jp_font_object.save(jp_font_path)
    # フォントを結合
    merger = merge.Merger()
    merged_font = merger.merge([eng_font_path, jp_font_path])
    merged_font.save(
        f"{BUILD_FONTS_DIR}/{FONTTOOLS_PREFIX}{FONT_NAME}{variant}-{style}_merged.ttf"
    )


def fix_font_tables(style, variant):
    """フォントテーブルを編集する"""

    input_font_name = f"{FONTTOOLS_PREFIX}{FONT_NAME}{variant}-{style}_merged.ttf"
    output_name_base = f"{FONTTOOLS_PREFIX}{FONT_NAME}{variant}-{style}"
    completed_name_base = f"{FONT_NAME}{variant}-{style}"

    # OS/2, post, hhea, cmap, head テーブルのttxファイルを出力
    xml = dump_ttx(input_font_name, output_name_base)
    # head テーブルを編集
    fix_head_table(xml, style)
    # OS/2 テーブルを編集
    fix_os2_table(xml, style, flag_hw=HALF_WIDTH_STR in variant)
    # hhea テーブルを編集
    fix_hhea_table(xml, style)
    # post テーブルを編集
    fix_post_table(xml)
    # cmap テーブルを編集
    fix_cmap_table(xml, style, variant)

    # ttxファイルを上書き保存
    xml.write(
        f"{BUILD_FONTS_DIR}/{output_name_base}.ttx",
        encoding="utf-8",
        xml_declaration=True,
    )

    # ttxファイルをttfファイルに適用
    ttx.main(
        [
            "-o",
            f"{BUILD_FONTS_DIR}/{output_name_base}_os2_post.ttf",
            "-m",
            f"{BUILD_FONTS_DIR}/{input_font_name}",
            f"{BUILD_FONTS_DIR}/{output_name_base}.ttx",
        ]
    )

    # ファイル名を変更
    os.rename(
        f"{BUILD_FONTS_DIR}/{output_name_base}_os2_post.ttf",
        f"{BUILD_FONTS_DIR}/{completed_name_base}.ttf",
    )


def dump_ttx(input_name_base, output_name_base) -> ET:
    """OS/2, post, hhea, cmap, head テーブルのみのttxファイルを出力"""
    ttx.main(
        [
            "-t",
            "OS/2",
            "-t",
            "post",
            "-t",
            "hhea",
            "-t",
            "cmap",
            "-t",
            "head",
            "-f",
            "-o",
            f"{BUILD_FONTS_DIR}/{output_name_base}.ttx",
            f"{BUILD_FONTS_DIR}/{input_name_base}",
        ]
    )

    return ET.parse(f"{BUILD_FONTS_DIR}/{output_name_base}.ttx")


def fix_head_table(xml: ET, style: str):
    """head テーブルを編集する"""
    mac_style = 0
    if "Bold" in style:
        mac_style |= 0x01
    if "Italic" in style:
        mac_style |= 0x02
    
    mac_style_bin = format(mac_style, "016b")
    mac_style_bin = f"{mac_style_bin[:8]} {mac_style_bin[8:]}"
    xml.find("head/macStyle").set("value", mac_style_bin)


def fix_os2_table(xml: ET, style: str, flag_hw: bool = False):
    """OS/2 テーブルを編集する"""
    # Version を 4 に固定 (USE_TYPO_METRICS のため)
    xml.find("OS_2/version").set("value", "4")

    # xAvgCharWidthを編集
    if flag_hw:
        x_avg_char_width = HALF_WIDTH_12
    else:
        x_avg_char_width = HALF_WIDTH_35
    xml.find("OS_2/xAvgCharWidth").set("value", str(x_avg_char_width))

    # Typo メトリクス = EM サイズ (HackGen互換)
    xml.find("OS_2/sTypoAscender").set("value", str(EM_ASCENT))
    xml.find("OS_2/sTypoDescender").set("value", str(-EM_DESCENT))
    xml.find("OS_2/sTypoLineGap").set("value", str(OS2_LINEGAP))

    # HackGen互換: WinメトリクスはLineGapとは独立して設定
    # Typo方式(1.08 EM)とWin方式(1.12 EM)の差を4%に縮小し、アプリ間の一貫性を確保
    xml.find("OS_2/usWinAscent").set("value", str(OS2_ASCENT))
    xml.find("OS_2/usWinDescent").set("value", str(OS2_DESCENT))

    # fsSelection (Bit 7 USE_TYPO_METRICS は無効化: HackGen互換)
    fs_selection = None
    if style == "Regular":
        fs_selection = "00000000 01000000"
    elif style == "Italic":
        fs_selection = "00000000 00000001"
    elif style == "Bold":
        fs_selection = "00000000 00100000"
    elif style == "BoldItalic":
        fs_selection = "00000000 00100001"

    if fs_selection is not None:
        xml.find("OS_2/fsSelection").set("value", fs_selection)

    # panose
    if style == "Regular" or style == "Italic":
        bWeight = 5
    else:
        bWeight = 8
    
    panose = {
        "bFamilyType": 2,
        "bSerifStyle": 11,
        "bWeight": bWeight,
        "bProportion": 9,
        "bContrast": 2,
        "bStrokeVariation": 2,
        "bArmStyle": 3,
        "bLetterForm": 2,
        "bMidline": 2,
        "bXHeight": 7,
    }

    for key, value in panose.items():
        xml.find(f"OS_2/panose/{key}").set("value", str(value))


def fix_hhea_table(xml: ET, style: str):
    """hhea テーブルを編集する"""
    xml.find("hhea/ascent").set("value", str(OS2_ASCENT))
    xml.find("hhea/descent").set("value", str(-OS2_DESCENT))
    xml.find("hhea/lineGap").set("value", "0")  # HackGen互換

    # Italic 調整
    if "Italic" in style:
        # Rise は EM (1000)
        # Run は Rise * tan(9 deg) = 1000 * 0.15838 = 158
        xml.find("hhea/caretSlopeRise").set("value", "1000")
        xml.find("hhea/caretSlopeRun").set("value", "158")
    else:
        xml.find("hhea/caretSlopeRise").set("value", "1")
        xml.find("hhea/caretSlopeRun").set("value", "0")


def fix_post_table(xml: ET):
    """post テーブルを編集する"""
    xml.find("post/isFixedPitch").set("value", "1")
    
    xml.find("post/underlinePosition").set("value", "-100")


def fix_cmap_table(xml: ET, style: str, variant: str):
    """異体字シーケンス (cmap_format_14) をマージ後フォントに復元する。"""
    source_xml = dump_ttx(
        f"{FONTFORGE_PREFIX}{FONT_NAME}{variant}-{style}-jp.ttf",
        f"{FONTFORGE_PREFIX}{FONT_NAME}{variant}-{style}-jp",
    )
    source_cmap_format_14 = source_xml.find("cmap/cmap_format_14")
    if source_cmap_format_14 is not None:
        target_cmap = xml.find("cmap")
        # 既存の cmap_format_14 があれば削除
        existing_format_14 = target_cmap.find("cmap_format_14")
        if existing_format_14 is not None:
            target_cmap.remove(existing_format_14)
        target_cmap.append(source_cmap_format_14)
    else:
        print(f"Warning: cmap_format_14 not found in {FONTFORGE_PREFIX}{FONT_NAME}{variant}-{style}-jp.ttf")


if __name__ == "__main__":
    main()
