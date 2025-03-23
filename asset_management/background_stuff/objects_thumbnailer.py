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

from mathutils import Vector


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
from asset_management.AmCore import AmObjects


camera = Thumbnailer.get_camera()
if camera is None:
    print(f"No camera found in {bpy.data.filepath}")
    bpy.ops.wm.quit_blender()


C = bpy.context
D = bpy.data


args = [engine, thumb_resolution, file_format, samples]
if engine == 'CYCLES':
    args.extend([device_type, scn_device])


def convert_particules(obj, imported):
    if obj.type not in ['MESH', 'TEXT', 'CURVE']:
        return

    particule_mod = [mod for mod in obj.modifiers if mod.type ==
                     'PARTICLE_SYSTEM']

    for mod in particule_mod:
        particles = mod.particle_system
        if particles.settings.render_type == 'PATH':
            C.view_layer.objects.active = obj
            bpy.ops.object.modifier_convert(modifier=mod.name)
            C.active_object.name = mod.name
            imported.append(C.active_object)


def get_min_z_coord():
    idx = [0, 3, 4, 7]
    coords = [(obj.matrix_world @ Vector(obj.bound_box[i][:]))[2] for obj in C.selected_objects for i in idx]
    threshold = 0.0001
    return min(coords)-threshold


def set_default_material(obj):
    obj.active_material = D.materials.get("object_material")


def is_view_camera():
    for area in C.screen.areas:
        if area.type != "VIEW_3D":
            continue
        return area.spaces[0].region_3d.view_perspective == "CAMERA"
    return


Thumbnailer.setup_render_setting(*args)


for file in files:
    filename = os.path.splitext(os.path.basename(file))[0]
    bpy.ops.object.select_all(action="DESELECT")
    imported, collections = AmObjects.import_asset(C, file)

    for obj in imported:
        convert_particules(obj, imported)

    for obj in imported:
        if not hasattr(obj.data, "materials"):
            continue
        if not obj.data.materials:
            set_default_material(obj)
        obj.select_set(True)

    D.objects["Ground"].location = (0, 0, get_min_z_coord())

    Thumbnailer.set_camera_framing(C, camera)

    C.scene.render.filepath = os.path.join(thumb_dir, f"{filename}")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.quit_blender()