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

for arg in sys.argv:
    if arg.startswith("old_name:"):
        old_name = arg[9:]
    if arg.startswith("new_name:"):
        new_name = arg[9:]
    if arg.startswith("package:"):
        package = arg[8:]
    if arg.startswith("TEX_folder:"):
        TEX_folder = arg[11:]

if not bpy.data.materials:
    print(f"ERROR: no material found in the Blendfile")
    bpy.ops.wm.quit_blender()

material = bpy.data.materials.get(old_name)
if material is None:
    material = bpy.data.materials[0]

if not bpy.context.scene.objects:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1,
                                         location=(0, 0, 0),
                                         scale=(1, 1, 1))

    ob = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(material)

print(f"{material.name} found")
material.name = new_name
print(f"Material renamed to {material.name}")

if TEX_folder != 'NONE':
    addon_dir = os.path.abspath(__file__.split(package)[0])
    if addon_dir not in sys.path:
        sys.path.append(addon_dir)

    from asset_management.AmCore import AmMaterials

    am_images = AmMaterials.get_images(material)
    for img in am_images:
        img.filepath = os.path.join(f"//TEX_{new_name}", img.filename)

    print("The TEX_ folder and the texture paths have been corrected.")

bpy.ops.wm.save_mainfile(compress=True)
filepath = bpy.data.filepath
if os.path.exists(filepath + "1"):
    os.remove(filepath + "1")


bpy.ops.wm.quit_blender()
