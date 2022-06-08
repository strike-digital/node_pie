from pathlib import Path
from bpy.utils import previews

icon_collections = {}
pcolls = []


# Add a button to the header
def register():
    global icon_collections

    # load icons
    path = Path(__file__).parents[1]
    pcoll = previews.new()
    # match all subdirectories named icons and load all pngs in them
    for file in list(path.glob("*/icons/*.png")):
        pcoll.load(file.name, str(file), "IMAGE")
    icon_collections["icons"] = pcoll
    pcolls.append(pcoll)


def unregister():

    global pcolls
    for pcoll in pcolls:
        try:
            previews.remove(pcoll)
        except KeyError:
            pass