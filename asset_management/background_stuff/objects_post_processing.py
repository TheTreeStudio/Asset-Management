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
    if arg.startswith('data_type:'):
        data_type = arg[10:]
    if arg.startswith('package:'):
        package = arg[8:]
    if arg.startswith('path_remap:'):
        remap_type = arg[11:]

addon_dir = os.path.abspath(__file__.split(package)[0])
if addon_dir not in sys.path:
    sys.path.append(addon_dir)

from asset_management.AmCore import AmImage, ImageProcessing, AmObjects


def object_to_center_of_scene():
    objects = bpy.data.objects[:]

    root = AmObjects.get_root(objects)
    if root is None:
        root = AmObjects.parent_to_root_empty(bpy.context, objects)
    root.location = (0, 0, 0)
    if root.name == "AM_root":
        AmObjects.clear_root(bpy.context, root)


if data_type == 'SELECTION':
    for ob in bpy.data.objects:
        bpy.context.scene.collection.objects.link(ob)

elif data_type == 'COLLECTIONS':
    collections = {coll: {'parent': None } for coll in bpy.data.collections}

    for coll in collections.keys():
        for child in coll.children:
            collections[child]['parent'] = coll

    for coll in collections:
        if collections[coll]['parent'] is None:
            bpy.context.scene.collection.children.link(coll)

object_to_center_of_scene()

images = [AmImage(img) for img in bpy.data.images]

if images:
    ImageProcessing.remap_paths(remap_type, images)

bpy.ops.wm.save_mainfile(compress=True)

filepath = bpy.data.filepath
if os.path.exists(filepath + "1"):
    os.remove(filepath + "1")

bpy.ops.wm.quit_blender()
