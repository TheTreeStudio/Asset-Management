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
    if arg.startswith('scn_mat:'):
        scn_mat = arg[8:]
    if arg.startswith('package:'):
        package = arg[8:]
    if arg.startswith('path_remap:'):
        remap_type = arg[11:]


# To be able to import other modules from the addon, we need to make sure
# that the "addons" folder where the AM is located is in the PATH. If this
# is not the case (which can happen if the 'script_directory' property in
# the preferences has been set to point to another 'addons' folder and the
# AM has been placed in this folder), we need to add this folder to the PATH
# 'manually'.
addon_dir = os.path.abspath(__file__.split(package)[0])
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from asset_management.AmCore import AmMaterials, ImageProcessing


material = bpy.data.materials.get(scn_mat)

if material is not None:
    filepath = bpy.data.filepath

    # If the material already exists, the blendfile name is incremented.
    # So we have to rename the material in the file
    filename = os.path.basename(filepath).split(".blend")[0]

    if filename != material.name:
        material.name = filename

    bpy.ops.mesh.primitive_uv_sphere_add(radius=1,
                                         location=(0, 0, 0),
                                         scale=(1, 1, 1))

    ob = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(material)

    am_images = AmMaterials.get_images(material)
    if am_images:
        ImageProcessing.remap_paths(remap_type, am_images)

    bpy.ops.wm.save_mainfile(compress=True)
    if os.path.exists(filepath + "1"):
        os.remove(filepath + "1")

    bpy.ops.wm.quit_blender()

else:
    print(f"ERROR: material {material} not found")
    bpy.ops.wm.quit_blender()
