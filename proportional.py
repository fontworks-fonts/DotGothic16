"""Derive DotGothic16 Proportional from the built DotGothic16 Regular.

DotGothic16 is duo-spaced: every half-width glyph is drawn inside a fixed
500-unit (8-dot) cell, so the narrow ones float in whitespace -- 'l' is 73
units of ink with 213 units of blank on each side. That is correct for a
16x16 bitmap grid, but it reads as very loose in running Latin text.

This module builds a second family, 'DotGothic16 Proportional', in which the
half-width Latin and punctuation glyphs are respaced from their own ink while
staying on the 62.5-unit dot grid:

    advance = (round(ink / PITCH) + TRACKING_COLS) * PITCH
    lsb     = (advance - ink) / 2                          # ink stays centred

TRACKING_COLS is the number of blank dot columns added to each glyph. At 1 a
full-cell glyph (ink 444) yields exactly 500 again, so the wide glyphs keep the
advances they were drawn with -- but the one-dot stems then touch, because
their ink is 73 units against a 62.5-unit column, so 'Ill' and 'little' close
up into a blob. The default of 2 buys those a second blank column and reads
correctly; it costs the wide glyphs one column, taking them to 562.5. No
outline is redrawn and no glyph leaves the dot grid either way.

Untouched: the 8720 full-width CJK glyphs, and the *.half forms reached through
'hwid', which must stay fixed-width. Digits are held to one common width so
figures still line up in columns, and connectors keep a zero side gap so runs
of them join up. As a side effect the existing 'pwid' feature, which maps the
*.half forms onto these glyphs, finally produces proportional widths.
"""
from collections import Counter

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

PITCH = 62.5            # one dot column, 1000/16
HALF = 500              # the half-width cell, 8 dot columns
TRACKING_COLS = 2       # blank dot columns added per glyph; see the note above

# Connectors have to stay flush to the cell edge so that runs of them join up
# (___, ---). A side gap would break the line into dashes.
CONNECTORS = {"underscore", "endash", "emdash", "horizontalbar", "overline",
              "macron", "bar", "brokenbar"}

DIGITS = ("zero", "one", "two", "three", "four", "five", "six",
          "seven", "eight", "nine")


def inkWidth(glyphSet, name):
    """Horizontal extent of the drawn outline, or None for a blank glyph."""
    pen = BoundsPen(glyphSet)
    glyphSet[name].draw(pen)
    if pen.bounds is None:
        return None
    xMin, _, xMax, _ = pen.bounds
    return xMin, xMax - xMin


def respace(font, trackingCols=TRACKING_COLS):
    """Set proportional advances on the half-width Latin and punctuation."""
    glyf, hmtx = font["glyf"], font["hmtx"]
    glyphSet = font.getGlyphSet()
    spaceCols = 3 + trackingCols        # the word gap grows with the tracking

    targets = [name for name in font.getGlyphOrder()
               if hmtx.metrics[name][0] == HALF
               and not name.endswith(".half")
               and name not in CONNECTORS]

    plan = {}
    for name in targets:
        ink = inkWidth(glyphSet, name)
        if ink is None:                 # space
            plan[name] = (int(round(spaceCols * PITCH)), 0, 0)
            continue
        xMin, width = ink
        advance = (round(width / PITCH) + trackingCols) * PITCH
        lsb = (advance - width) / 2
        plan[name] = (int(round(advance)), int(round(lsb)), int(round(lsb - xMin)))

    # Figures have to stay tabular. Use the modal width rather than the widest:
    # 'four' bleeds to the cell edge (ink 496 against the usual 444) and would
    # otherwise widen every digit by a column.
    digits = [name for name in DIGITS if name in plan]
    if digits:
        modal = Counter(plan[name][0] for name in digits).most_common(1)[0][0]
        widest = max(inkWidth(glyphSet, name)[1] for name in digits)
        needed = (-(-widest // PITCH) + trackingCols - 1) * PITCH   # ceil + tracking
        advance = int(round(max(modal, needed)))
        for name in digits:
            xMin, width = inkWidth(glyphSet, name)
            lsb = int(round((advance - width) / 2))
            plan[name] = (advance, lsb, int(round(lsb - xMin)))

    for name, (advance, lsb, shift) in plan.items():
        glyph = glyf[name]
        if shift:
            if glyph.isComposite():
                for component in glyph.components:
                    component.x += shift
            elif glyph.numberOfContours > 0:
                glyph.coordinates.translate((shift, 0))
        if glyph.numberOfContours != 0:
            glyph.recalcBounds(glyf)
        hmtx.metrics[name] = (advance, lsb)

    # The metadata says monospaced; this family is not, and apps act on it.
    font["post"].isFixedPitch = 0
    font["OS/2"].panose.bProportion = 0                 # Any, not 9 Monospaced
    font["OS/2"].recalcAvgCharWidth(font)
    advances = [hmtx.metrics[name][0] for name in font.getGlyphOrder()]
    font["hhea"].advanceWidthMax = max(advances)
    font["head"].xMin = min((glyf[name].xMin for name in font.getGlyphOrder()
                             if glyf[name].numberOfContours != 0), default=0)
    return plan


def rename(font, family="DotGothic16 Proportional",
           familyJP="ドットゴシック16 プロポーショナル"):
    """Move the font into its own family, keeping the Regular style."""
    postScriptName = family.replace(" ", "") + "-Regular"
    name = font["name"]
    version = name.getDebugName(5).replace("Version ", "")
    vendor = font["OS/2"].achVendID.strip()

    for nameID, value in ((1, family),
                          (3, version + ";" + vendor + ";" + postScriptName),
                          (4, family + " Regular"),
                          (6, postScriptName)):
        name.setName(value, nameID, 3, 1, 0x409)
    name.setName(familyJP, 1, 3, 1, 0x411)          # ja-JP, as in build.py


def make(sourcePath, destinationPath, trackingCols=TRACKING_COLS):
    font = TTFont(sourcePath)
    plan = respace(font, trackingCols)
    rename(font)
    font.save(destinationPath)
    return len(plan)
