from fontTools.ttLib.ttFont import newTable
from fontmake import __main__
from fontTools.ttLib import TTFont, newTable
import shutil, subprocess, glob
from pathlib import Path

print ("[DotGothic16] Generating TTFs")
__main__.main(("-g","sources/DotGothic16.glyphs", "-o","ttf",))

for font in Path("master_ttf").glob("*.ttf"):
    modifiedFont = TTFont(font)
    print ("["+str(font).split("/")[1][:-4]+"] Adding stub DSIG")
    modifiedFont["DSIG"] = newTable("DSIG")     #need that stub dsig
    modifiedFont["DSIG"].ulVersion = 1
    modifiedFont["DSIG"].usFlag = 0
    modifiedFont["DSIG"].usNumSigs = 0
    modifiedFont["DSIG"].signatureRecords = []

    print ("["+str(font).split("/")[1][:-4]+"] Making other changes")
    modifiedFont["name"].addMultilingualName({'ja':'ドットゴシック16'}, modifiedFont, nameID = 1, windows=True, mac=False)
    modifiedFont["name"].addMultilingualName({'ja':'Regular'}, modifiedFont, nameID = 2, windows=True, mac=False)
    modifiedFont["head"].flags |= 1 << 3        #sets flag to always round PPEM to integer

    modifiedFont.save("fonts/ttf/"+str(font).split("/")[1])

shutil.rmtree("instance_ufo")
shutil.rmtree("master_ufo")
shutil.rmtree("master_ttf")

for font in Path("fonts/ttf/").glob("*.ttf"):
    print ("["+str(font).split("/")[2][:-4]+"] Autohinting")
    fontName = str(font)
    hintedName = fontName[:-4]+"-hinted.ttf"
    subprocess.check_call(
        [
            "ttfautohint",
            "--stem-width",
            "nsn",
            fontName,
            hintedName,
        ]
    )

    shutil.move(hintedName, fontName)
