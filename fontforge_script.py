#!fontforge --lang=py -script

import configparser
import math
import os
import shutil
import sys
import uuid

import fontforge
import psMat

# 設定読み込み
settings = configparser.ConfigParser()
settings.read("build.ini", encoding="utf-8")

VERSION = settings.get("DEFAULT", "VERSION")
FONT_NAME = settings.get("DEFAULT", "FONT_NAME")
JP_FONT = settings.get("DEFAULT", "JP_FONT")
ENG_FONT = settings.get("DEFAULT", "ENG_FONT")
SOURCE_FONTS_DIR = os.environ.get("SOURCE_FONTS_DIR") or settings.get("DEFAULT", "SOURCE_FONTS_DIR")
BUILD_FONTS_DIR = os.environ.get("BUILD_FONTS_DIR") or settings.get("DEFAULT", "BUILD_FONTS_DIR")
VENDER_NAME = settings.get("DEFAULT", "VENDER_NAME")
FONTFORGE_PREFIX = settings.get("DEFAULT", "FONTFORGE_PREFIX")
IDEOGRAPHIC_SPACE = settings.get("DEFAULT", "IDEOGRAPHIC_SPACE")
HALF_WIDTH_STR = settings.get("DEFAULT", "HALF_WIDTH_STR")
FULL_WIDTH_35_STR = settings.get("DEFAULT", "FULL_WIDTH_35_STR")
INVISIBLE_ZENKAKU_SPACE_STR = settings.get("DEFAULT", "INVISIBLE_ZENKAKU_SPACE_STR")
JPDOC_STR = settings.get("DEFAULT", "JPDOC_STR")
NERD_FONTS_STR = settings.get("DEFAULT", "NERD_FONTS_STR")
EM_ASCENT = int(settings.get("DEFAULT", "EM_ASCENT"))
EM_DESCENT = int(settings.get("DEFAULT", "EM_DESCENT"))
OS2_ASCENT = int(settings.get("DEFAULT", "OS2_ASCENT"))
OS2_DESCENT = int(settings.get("DEFAULT", "OS2_DESCENT"))
OS2_LINEGAP = int(settings.get("DEFAULT", "OS2_LINEGAP"))
HALF_WIDTH_12 = int(settings.get("DEFAULT", "HALF_WIDTH_12"))
HALF_WIDTH_35 = int(settings.get("DEFAULT", "HALF_WIDTH_35"))
FULL_WIDTH_35 = int(settings.get("DEFAULT", "FULL_WIDTH_35"))

COPYRIGHT = """[Commit Mono]
Copyright (c) Eigil Nikolajsen https://github.com/eigilnikolajsen/commit-mono

[BIZ UDGothic]
Copyright 2022 The BIZ UDGothic Project Authors https://github.com/googlefonts/morisawa-biz-ud-gothic

[Pending Mono]
Copyright 2022 Yuko Otawara
"""  # noqa: E501

options = {}
nerd_font = None
REG_WEIGHT = 400
BOLD_WEIGHT = 700


def main():
    get_options()
    if options.get("unknown-option"):
        usage()
        return

    # buildディレクトリ作成
    if os.path.exists(BUILD_FONTS_DIR) and not options.get("do-not-delete-build-dir"):
        shutil.rmtree(BUILD_FONTS_DIR)
        os.mkdir(BUILD_FONTS_DIR)
    if not os.path.exists(BUILD_FONTS_DIR):
        os.mkdir(BUILD_FONTS_DIR)

    generate_font("Regular", f"{REG_WEIGHT}-Regular", "Regular")
    generate_font("Bold", f"{BOLD_WEIGHT}-Regular", "Bold")
    generate_font("Regular", f"{REG_WEIGHT}-Italic", "Italic", italic=True)
    generate_font("Bold", f"{BOLD_WEIGHT}-Italic", "BoldItalic", italic=True)


def get_options():
    """オプション取得"""

    global options, REG_WEIGHT, BOLD_WEIGHT, OS2_ASCENT, OS2_DESCENT, OS2_LINEGAP

    # オプションなしの場合は何もしない
    args = sys.argv[1:]
    if len(args) == 0:
        return

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--do-not-delete-build-dir":
            options["do-not-delete-build-dir"] = True
        elif arg == "--invisible-zenkaku-space":
            options["invisible-zenkaku-space"] = True
        elif arg == "--half-width":
            options["half-width"] = True
        elif arg == "--jpdoc":
            options["jpdoc"] = True
        elif arg == "--nerd-font":
            options["nerd-font"] = True
        elif arg == "--regular-weight":
            if i + 1 < len(args):
                val = args[i + 1]
                if val and val.isdigit():
                    REG_WEIGHT = int(val)
                i += 1
        elif arg == "--bold-weight":
            if i + 1 < len(args):
                val = args[i + 1]
                if val and val.isdigit():
                    BOLD_WEIGHT = int(val)
                i += 1
        elif arg == "--line-height":
            if i + 1 < len(args):
                val = args[i + 1]
                try:
                    lh = float(val)
                    # HackGen互換: Typo/Win両方で調整
                    total = round(1000 * lh)
                    OS2_LINEGAP = max(0, total - 1000 - 40)  # Typo用: 約4%少なく
                    OS2_ASCENT = 880 + (total - 1000) // 2   # Win用: 上下に分配
                    OS2_DESCENT = 120 + (total - 1000) - (total - 1000) // 2
                except ValueError:
                    pass
                i += 1
        else:
            options["unknown-option"] = True
            return
        i += 1


def usage():
    print(
        f"Usage: {sys.argv[0]} "
        "[--invisible-zenkaku-space] [--half-width] [--jpdoc] [--nerd-font] [--regular-weight N] [--bold-weight N] [--line-height N]"
    )


def generate_font(jp_style, eng_style, merged_style, italic=False):
    print(f"=== Generate {merged_style} ===")

    jp_font, eng_font = open_fonts(jp_style, eng_style)

    # jpdoc: 罫線・ブロック要素を除き、日本語記号を削除
    if options.get("jpdoc"):
        remove_jpdoc_symbols(eng_font)

    # 罫線調整は常にeng_fontに適用
    adjust_box_drawing_symbols(eng_font)

    delete_duplicate_glyphs(jp_font, eng_font)
    em_1000(jp_font)
    adjust_some_glyph(jp_font)

    if italic:
        transform_italic_glyphs(jp_font)

    width_600_or_1000(jp_font)

    # 1:2幅に変換
    if options.get("half-width"):
        transform_half_width(jp_font, eng_font)

    # GSUB削除 (全角文字行でリガチャ解除対策)
    remove_lookups(jp_font)

    if not options.get("invisible-zenkaku-space"):
        visualize_zenkaku_space(jp_font)

    if options.get("nerd-font"):
        add_nerd_font_glyphs(jp_font, eng_font)

    # バリアント名生成
    variant = HALF_WIDTH_STR if options.get("half-width") else FULL_WIDTH_35_STR
    variant += INVISIBLE_ZENKAKU_SPACE_STR if options.get("invisible-zenkaku-space") else ""
    variant += JPDOC_STR if options.get("jpdoc") else ""
    variant += NERD_FONTS_STR if options.get("nerd-font") else ""

    edit_meta_data(eng_font, merged_style, variant)
    edit_meta_data(jp_font, merged_style, variant)

    # 保存
    generate_filename_part = f"{BUILD_FONTS_DIR}/{FONTFORGE_PREFIX}{FONT_NAME.replace(' ', '')}{variant}-{merged_style}"
    eng_font.generate(f"{generate_filename_part}-eng.ttf")
    jp_font.generate(f"{generate_filename_part}-jp.ttf")

    jp_font.close()
    eng_font.close()


def open_fonts(jp_style: str, eng_style: str):
    """フォントを開く"""
    jp_font = fontforge.open(
        f"{SOURCE_FONTS_DIR}/{JP_FONT.replace('{style}', jp_style)}"
    )
    eng_font = fontforge.open(
        f"{SOURCE_FONTS_DIR}/{ENG_FONT.replace('{style}', eng_style)}"
    )

    jp_font = altuni_to_entity(jp_font)
    jp_font.unlinkReferences()
    eng_font.unlinkReferences()
    return jp_font, eng_font


def altuni_to_entity(jp_font):
    """透過参照を実体グリフに変換"""
    for glyph in jp_font.glyphs():
        if glyph.altuni is not None:
            # (unicode-value, variation-selector, reserved-field)
            altunis = glyph.altuni

            before_altuni = ""
            for altuni in altunis:
                if altuni[1] == -1 and before_altuni != ",".join(map(str, altuni)):
                    glyph.altuni = None
                    copy_target_unicode = altuni[0]
                    try:
                        copy_target_glyph = jp_font.createChar(
                            copy_target_unicode,
                            f"uni{hex(copy_target_unicode).replace('0x', '').upper()}copy",
                        )
                    except (TypeError, ValueError, KeyError):
                        copy_target_glyph = jp_font[copy_target_unicode]
                    copy_target_glyph.clear()
                    copy_target_glyph.width = glyph.width
                    jp_font.selection.select(glyph.glyphname)
                    jp_font.copy()
                    jp_font.selection.select(copy_target_glyph.glyphname)
                    jp_font.paste()
                before_altuni = ",".join(map(str, altuni))
    # エンコーディング整理のため開き直す
    font_path = f"{BUILD_FONTS_DIR}/{jp_font.fullname}_{uuid.uuid4()}.ttf"
    jp_font.generate(font_path)
    jp_font.close()
    reopen_jp_font = fontforge.open(font_path)
    os.remove(font_path)
    return reopen_jp_font


def adjust_some_glyph(jp_font):
    """グリフ形状調整"""
    full_width = jp_font[0x3042].width
    adjust_length = round(full_width / 6)
    for glyph_name in [0xFF08, 0xFF3B, 0xFF5B]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate(-adjust_length, 0))
        glyph.width = full_width
    for glyph_name in [0xFF09, 0xFF3D, 0xFF5D]:
        glyph = jp_font[glyph_name]
        glyph.transform(psMat.translate(adjust_length, 0))
        glyph.width = full_width


def em_1000(font):
    """フォントのEMを1000に変換"""
    font.em = EM_ASCENT + EM_DESCENT


def delete_duplicate_glyphs(jp_font, eng_font):
    """jp_fontとeng_fontのグリフを比較し、重複するグリフを削除する"""

    eng_font.selection.none()
    jp_font.selection.none()

    for glyph in jp_font.glyphs("encoding"):
        try:
            if glyph.isWorthOutputting() and glyph.unicode > 0:
                eng_font.selection.select(("more", "unicode"), glyph.unicode)
        except ValueError:
            continue
    for glyph in eng_font.selection.byGlyphs:
        jp_font.selection.select(("more", "unicode"), glyph.unicode)
    for glyph in jp_font.selection.byGlyphs:
        glyph.clear()

    # 罫線・ブロック要素（U+2500-259F）はeng_font側を優先
    jp_font.selection.none()
    jp_font.selection.select(("ranges",), 0x2500, 0x259F)
    for glyph in jp_font.selection.byGlyphs:
        glyph.clear()

    jp_font.selection.none()
    eng_font.selection.none()


def remove_lookups(font):
    """ルックアップ削除"""
    for lookup in list(font.gsub_lookups) + list(font.gpos_lookups):
        font.removeLookup(lookup)


def transform_italic_glyphs(font):
    """斜体変換"""
    ITALIC_SLOPE = 9
    font.italicangle = -ITALIC_SLOPE
    for glyph in font.glyphs():
        glyph.transform(psMat.skew(ITALIC_SLOPE * math.pi / 180))


def remove_jpdoc_symbols(eng_font):
    """日本語記号を削除"""
    limit_top = OS2_ASCENT
    limit_bottom = -OS2_DESCENT

    ranges = [
        (0x00A7, 0x00A7), (0x00B1, 0x00B1), (0x00B6, 0x00B6), (0x00F7, 0x00F7), (0x00D7, 0x00D7),
        (0x21D2, 0x21D2), (0x21D4, 0x21D4), (0x25A0, 0x25A1), (0x25B2, 0x25B3), (0x25BC, 0x25BD),
        (0x25C6, 0x25C7), (0x25CB, 0x25CB), (0x25CE, 0x25CF), (0x25E5, 0x25E5), (0x25EF, 0x25EF),
        (0x221A, 0x221A), (0x221E, 0x221E), (0x2010, 0x2010), (0x2018, 0x201A), (0x201C, 0x201E),
        (0x2020, 0x2021), (0x2026, 0x2026), (0x2030, 0x2030), (0x2190, 0x2193), (0x2200, 0x2200),
        (0x2202, 0x2203), (0x2208, 0x2208), (0x220B, 0x220B), (0x2211, 0x2211), (0x2225, 0x2225),
        (0x2227, 0x222C), (0x2260, 0x2261), (0x2282, 0x2283), (0x2286, 0x2287),
    ]
    
    count = 0
    for glyph in eng_font.glyphs():
        u = glyph.unicode
        name = glyph.glyphname
        bbox = glyph.boundingBox()
        
        should_remove = False
        # 罫線・ブロック要素は境界チェック対象外
        is_box_drawing = (u != -1 and 0x2500 <= u <= 0x259F)
        if not is_box_drawing and (bbox[3] > limit_top or bbox[1] < limit_bottom):
            should_remove = True
        
        if not should_remove and u != -1:
            for start, end in ranges:
                if start <= u <= end:
                    should_remove = True
                    break
        
        # U+25A0以降の幾何学記号のみ削除（罫線は残す）
        if not should_remove and name.startswith("uni25") and len(name) == 7:
            try:
                code = int(name[3:], 16)
                if code >= 0x25A0:
                    should_remove = True
            except ValueError:
                pass
            
        if should_remove:
            glyph.clear()
            glyph.unicode = -1
            glyph.glyphname = f"deleted_symbol_{count}"
            count += 1


def adjust_box_drawing_symbols(font):
    """罫線を行間に延伸"""
    font.selection.none()
    font.selection.select(("ranges",), 0x2500, 0x259F)

    # 延長の目標座標 (Win/hhea高さに一致)
    TARGET_TOP = OS2_ASCENT
    TARGET_BOTTOM = -OS2_DESCENT
    # 延長対象判定の閾値 (EM境界より少し内側)
    THRESHOLD_TOP = EM_ASCENT - 100  # 780
    THRESHOLD_BOTTOM = -EM_DESCENT + 100  # -20
    THRESHOLD_X_LEFT = 200
    THRESHOLD_X_RIGHT_MARGIN = 200

    for glyph in font.selection.byGlyphs:
        width = glyph.width
        layer_name = "Foreground"
        if layer_name not in glyph.layers:
            layer_name = glyph.activeLayer

        foreground = glyph.layers[layer_name]
        modified = False

        for contour in foreground:
            for point in contour:
                # 上端: 閾値を超えたら目標座標に設定
                if point.y > THRESHOLD_TOP:
                    point.y = TARGET_TOP
                    modified = True
                # 下端: 閾値を下回ったら目標座標に設定
                elif point.y < THRESHOLD_BOTTOM:
                    point.y = TARGET_BOTTOM
                    modified = True

                if point.x < THRESHOLD_X_LEFT:
                    point.x = 0
                    modified = True
                elif point.x > width - THRESHOLD_X_RIGHT_MARGIN:
                    point.x = width
                    modified = True
        
        if modified:
            glyph.layers[layer_name] = foreground

    font.selection.none()


def width_600_or_1000(jp_font):
    """幅を600または1000に統一"""
    half_width = HALF_WIDTH_35
    full_width = FULL_WIDTH_35
    for glyph in jp_font.glyphs():
        if 0 < glyph.width <= half_width + 20:
            glyph.transform(psMat.translate((half_width - glyph.width) / 2, 0))
            glyph.width = half_width
        elif half_width < glyph.width < full_width:
            glyph.transform(psMat.translate((full_width - glyph.width) / 2, 0))
            glyph.width = full_width


def transform_half_width(jp_font, eng_font):
    """幅を1:2比に変換"""
    before_width_eng = eng_font[0x0030].width
    after_width_eng = HALF_WIDTH_12
    x_scale = 540 / before_width_eng
    for glyph in eng_font.glyphs():
        if glyph.width > 0:
            after_width_eng_multiply = after_width_eng * round(glyph.width / HALF_WIDTH_35)
            glyph.transform(psMat.scale(x_scale, 1))
            glyph.transform(
                psMat.translate((after_width_eng_multiply - glyph.width) / 2, 0)
            )
            glyph.width = after_width_eng_multiply

    for glyph in jp_font.glyphs():
        if glyph.width == HALF_WIDTH_35:
            glyph.transform(psMat.translate((after_width_eng - glyph.width) / 2, 0))
            glyph.width = after_width_eng
        elif glyph.width == FULL_WIDTH_35:
            glyph.transform(psMat.translate((after_width_eng * 2 - glyph.width) / 2, 0))
            glyph.width = after_width_eng * 2


def visualize_zenkaku_space(jp_font):
    """全角スペース可視化"""
    glyph = jp_font[0x3000]
    width_to = glyph.width
    glyph.clear()
    jp_font.mergeFonts(fontforge.open(f"{SOURCE_FONTS_DIR}/{IDEOGRAPHIC_SPACE}"))
    jp_font.selection.select("U+3000")
    for glyph in jp_font.selection.byGlyphs:
        width_from = glyph.width
        glyph.transform(psMat.translate((width_to - width_from) / 2, 0))
        glyph.width = width_to
    jp_font.selection.none()


def add_nerd_font_glyphs(jp_font, eng_font):
    """ネードフォントグリフ追加"""
    global nerd_font
    if nerd_font is None:
        nerd_font = fontforge.open(
            f"{SOURCE_FONTS_DIR}/nerd-fonts/SymbolsNerdFont-Regular.ttf"
        )
        nerd_font.em = EM_ASCENT + EM_DESCENT
        glyph_names = set()
        for nerd_glyph in nerd_font.glyphs():
            # グリフ名重複対策
            if nerd_glyph.glyphname in glyph_names:
                nerd_glyph.glyphname = f"{nerd_glyph.glyphname}-{nerd_glyph.encoding}"
            glyph_names.add(nerd_glyph.glyphname)
            half_width = eng_font[0x0030].width
            if 0xE0B0 <= nerd_glyph.unicode <= 0xE0D4:
                # 右付きグリフの位置調整
                original_width = nerd_glyph.width
                if nerd_glyph.unicode == 0xE0B2:
                    nerd_glyph.transform(psMat.translate(-353, 0))
                elif nerd_glyph.unicode == 0xE0B6:
                    nerd_glyph.transform(psMat.translate(-414, 0))
                elif nerd_glyph.unicode == 0xE0C5:
                    nerd_glyph.transform(psMat.translate(-137, 0))
                elif nerd_glyph.unicode == 0xE0C7:
                    nerd_glyph.transform(psMat.translate(-214, 0))
                elif nerd_glyph.unicode == 0xE0D4:
                    nerd_glyph.transform(psMat.translate(-314, 0))
                nerd_glyph.width = original_width
                if nerd_glyph.width < half_width:
                    nerd_glyph.transform(
                        psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                    )
                elif nerd_glyph.width > half_width:
                    nerd_glyph.transform(psMat.scale(half_width / nerd_glyph.width, 1))
                # 行高さに合わせてスケーリング (Win/hhea高さ / EM)
                line_height_scale = (OS2_ASCENT + OS2_DESCENT) / (EM_ASCENT + EM_DESCENT)
                nerd_glyph.transform(psMat.scale(1, line_height_scale))
                # 上下中央揃え調整
                vertical_shift = (OS2_DESCENT - EM_DESCENT) - (OS2_ASCENT - EM_ASCENT)
                nerd_glyph.transform(psMat.translate(0, vertical_shift / 2))
            elif nerd_glyph.width < HALF_WIDTH_35:
                nerd_glyph.transform(
                    psMat.translate((half_width - nerd_glyph.width) / 2, 0)
                )
            nerd_glyph.width = half_width
    # 既存グリフ削除後マージ
    for nerd_glyph in nerd_font.glyphs():
        if nerd_glyph.unicode != -1:
            try:
                jp_font[nerd_glyph.unicode].clear()
            except (TypeError, KeyError):
                pass
            try:
                eng_font[nerd_glyph.unicode].clear()
            except (TypeError, KeyError):
                pass
    jp_font.mergeFonts(nerd_font)


def edit_meta_data(font, weight: str, variant: str):
    """メタデータ編集"""
    font.ascent = EM_ASCENT
    font.descent = EM_DESCENT

    font.version = VERSION
    try:
        v_parts = VERSION.split('.')
        if len(v_parts) >= 2:
            font.fontRevision = float(f"{v_parts[0]}.{''.join(v_parts[1:])}")
        else:
            font.fontRevision = float(VERSION)
    except Exception:
        pass

    font.os2_typoascent = EM_ASCENT
    font.os2_typodescent = -EM_DESCENT
    font.os2_typolinegap = OS2_LINEGAP
    font.os2_winascent = OS2_ASCENT
    font.os2_windescent = OS2_DESCENT

    font.hhea_ascent = OS2_ASCENT
    font.hhea_descent = -OS2_DESCENT
    font.hhea_linegap = 0

    font.sfnt_names = (
        (
            "English (US)",
            "License",
            """This Font Software is licensed under the SIL Open Font License,
Version 1.1. This license is available with a FAQ
at: http://scripts.sil.org/OFL""",
        ),
        ("English (US)", "License URL", "http://scripts.sil.org/OFL"),
        ("English (US)", "Version", VERSION),
    )
    font.familyname = f"{FONT_NAME} {variant}".strip()
    font.fontname = f"{FONT_NAME.replace(' ', '')}{variant}-{weight}"
    font.fullname = f"{FONT_NAME} {variant}".strip() + f" {weight}"
    font.os2_vendor = VENDER_NAME
    font.copyright = COPYRIGHT

    # macstyle settings
    mac_style = 0
    if "Bold" in weight:
        mac_style |= 0x01
    if "Italic" in weight:
        mac_style |= 0x02
    font.macstyle = mac_style

    # HackGen settings
    font.os2_width = 5  # Medium
    font.os2_fstype = 0  # Installable Embedding
    font.os2_family_class = 2057  # SS Typewriter Gothic
    
    if "Bold" in weight:
        font.os2_weight = BOLD_WEIGHT
    else:
        font.os2_weight = REG_WEIGHT


if __name__ == "__main__":
    main()