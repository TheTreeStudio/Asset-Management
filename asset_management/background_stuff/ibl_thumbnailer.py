# -*- coding:utf-8 -*-

# Blender ASSET MANAGEMENT Add-on
# Copyright (C) 2018 Legigan Jeremy AKA Pistiwique and Pitiwazou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# <pep8 compliant>


import bpy
import sys
import os

argv = sys.argv
asset_path = ""
icon_path = ""
files = []
reso = 256
format = 'JPEG'

for arg in argv:
    if arg.startswith("asset:"):
        asset_path = arg[6:]
    if arg.startswith("icons:"):
        icon_path = arg[6:]
    if arg.startswith("files:"):
        files.extend(arg[6:].split(";"))
    if arg.startswith("reso:"):
        reso = int(arg[5:])
    if arg.startswith("format:"):
        format = arg[7:]

settings = bpy.context.scene.render.image_settings
settings.file_format = format
settings.color_mode = 'RGB'

for file in files:
    filename = os.path.splitext(file)[0]
    output = os.path.join(icon_path, f"{filename}.{format.lower()}")
    img = bpy.data.images.load(os.path.join(asset_path, file))
    coef = img.size[1] / reso
    img.scale(int(img.size[0] / coef), reso)
    img.save_render(output)
    print(f"{file} saved")

bpy.ops.wm.quit_blender()