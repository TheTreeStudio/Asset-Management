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
import os
import sys


for arg in sys.argv:
    if arg.startswith('package:'):
        package = arg[8:]
    if arg.startswith("engine:"):
        engine = arg[7:]
    if arg.startswith("thumb_reso:"):
        thumb_resolution = int(arg[11:])
    if arg.startswith("file_format:"):
        file_format = arg[12:]
    if arg.startswith("device_type:"):
        device_type = arg[12:]
    if arg.startswith("scn_device:"):
        scn_device = arg[11:]
    if arg.startswith("samples:"):
        samples = int(arg[8:])
    if arg.startswith("thumb_dir:"):
        thumb_dir = arg[10:]
    if arg.startswith("files:"):
        files = arg[6:].split("|")

addon_dir = os.path.abspath(__file__.split(package)[0])
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from asset_management.AmUtils import Thumbnailer

C = bpy.context
D = bpy.data
SCN = C.scene
render = SCN.render

args = [engine, thumb_resolution, file_format, samples]
if engine == 'CYCLES':
    args.extend([device_type, scn_device])

Thumbnailer.setup_render_setting(*args)

ob = C.active_object

for file in files:
    mat_name = os.path.splitext(os.path.basename(file))[0]
    with D.libraries.load(filepath=file) as (data_from, data_to):
        data_to.materials = data_from.materials

    mat = D.materials.get(mat_name)
    if mat is not None:
        if len(ob.data.materials):
            ob.active_material = mat
        else:
            ob.data.materials.append(mat)

    render.filepath = os.path.join(thumb_dir, f"{mat_name}")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.quit_blender()
