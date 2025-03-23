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
import bmesh
import os
import shutil

from math import radians, floor, ceil
from mathutils import Matrix, Vector
from bpy_extras import view3d_utils

from bpy.props import (StringProperty,
                       FloatVectorProperty,
                       CollectionProperty,
                       EnumProperty)
from bpy.utils import register_class, unregister_class
from bpy.types import Operator, PropertyGroup
from bpy_extras.io_utils import ImportHelper

from .AmIoProps import IoCommonProps

from .AmLibraries import LibrariesManager as LM
from .AmCore import AmObjects, AmMaterials, AmEnvironment
from .AmUtils import (AmName,
                      AmPath,
                      AmBackgroundProcessor,
                      Thumbnailer,
                      addon_prefs,
                      Console)
from .SL_Api import SL_Raycast, SL_Snap, Z_AXIS, ZERO, ALL_AXIS
from .ressources.constants import (OBJECT_POST_PROCESS,
                                   OBJECT_THUMBNAILER,
                                   OBJECT_RENDER_SCENE,
                                   MATERIAL_POST_PROCESS,
                                   MATERIALS_THUMBNAILER,
                                   SCENE_POST_PROCESS,
                                   IBL_THUMBNAILER)


class AmExportHelper:

    def __init__(self):
        self._category = LM.active_category
        self._existing_files = [asset.name for asset in self.category.assets]

    @property
    def category(self):
        return self._category

    @property
    def to_root(self):
        return addon_prefs().import_export.save_to_root

    @property
    def existing_files(self):
        return self._existing_files

    @property
    def asset_dir(self):
        asset_dir, icon_dir = AmPath.get_export_dirs(self.category.path,
                                                     self.to_root)
        return asset_dir

    @staticmethod
    def get_asset_properties(asset_type):
        am = bpy.context.window_manager.asset_management
        return getattr(am.io_export, asset_type)

    @staticmethod
    def get_objects_to_save(context, io_objects):
        datablock = set()

        selection = context.selected_objects
        if context.object not in selection:
            selection.append(context.object)

        for ob in selection:
            if io_objects.include_complete_hierarchy:
                AmObjects.get_hierarchy(ob, datablock)

            else:
                datablock.add(ob)
                if io_objects.include_parents:
                    AmObjects.get_parents(ob, datablock)
                if io_objects.include_children:
                    AmObjects.get_children(ob, datablock)

        return datablock

    @staticmethod
    def get_collections_to_save(io_objects):
        return {bpy.data.collections.get(coll.name) for coll in
                io_objects.UL_collections if
                coll.to_export}

    @classmethod
    def get_data_to_save(cls, context, type_from):
        io_objects = cls.get_asset_properties('objects')

        if type_from == 'SELECTION':
            return cls.get_objects_to_save(context, io_objects)
        else: # from 'COLLECTION'
            return cls.get_collections_to_save(io_objects)

    @classmethod
    def get_objects_from(cls, context, type_from):
        io_objects = cls.get_asset_properties('objects')
        if type_from == 'SELECTION':
            return cls.get_objects_to_save(context, io_objects)

        else: # from 'COLLECTION'
            collections = cls.get_collections_to_save(io_objects)
            return [ob for coll in collections for ob in coll.objects]

    @staticmethod
    def run_background_processing(filepath_processor, file, *args):
        post_processing = AmBackgroundProcessor()

        Console.output.append("#-------   POSTPROCESSING   -------#")

        for line in post_processing.run_process(
                filepath_processor,
                file.path,
                True,
                f"package:{__package__}",
                f"path_remap:{addon_prefs().import_export.textures_backup}",
                *args):

            Console.output.append(line)
            print(line)


class ASSETM_OT_import_assets(Operator, IoCommonProps, AmObjects):
    """ Append/Link the active asset.
    SHIFT+click to display the file browser
    CTRL+click to change the import behavior"""
    bl_idname = 'asset_management.import_assets'
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}

    location: FloatVectorProperty(name="Location",
                                  default=(0.0, 0.0, 0.0),
                                  description="Location where to import or "
                                              "link the asset")

    object_as: EnumProperty(
            name="Import object as",
            items=(
                ('OBJECTS', 'Objects', "Import objects", 'OBJECT_DATAMODE', 0),
                ('COLLECTIONS', 'Collections', "Import collections",
                 'OUTLINER_COLLECTION', 1)),
            default='OBJECTS'
            )

    @classmethod
    def poll(cls, context):
        # if LM.pinned_categories():
        #     return True
        # category = LM.active_category
        # return hasattr(category, 'assets') and category.assets and \
        #        context.mode != 'EDIT_MESH'
        category = LM.active_category
        return context.mode != 'EDIT_MESH' and \
               category.preview.preview != "NONE"

    def exit(self, context):
        if self._ob.name == "AM_root":
            self.clear_root(context, self._ob)

        if self._raycast is not None:
            self._raycast.exit()

        context.window.cursor_modal_restore()
        context.area.tag_redraw()
        context.space_data.overlay.show_relationship_lines = \
            self._relationship_lines
        return {'FINISHED'}

    def on_cursor(self, context, event):
        coords = SL_Raycast.event_pixel_coord(event)
        return view3d_utils.region_2d_to_location_3d(
                context.region,
                context.space_data.region_3d,
                coords,
                Z_AXIS
                )

    def on_asset(self, context, coords):
        return view3d_utils.location_3d_to_region_2d(
                context.region,
                context.space_data.region_3d,
                coords
                )

    def _import_asset(self, context):
        # wm = context.window_manager
        # io_import = wm.asset_management.io_import
        asset = LM.get_asset_from_path(self.filepath)
        data_type = 'objects'
        if asset.collections:
            data_type = self.object_as.lower()

        self._imported, collections = self.import_asset(
                context,
                filepath=self.filepath,
                link=self.link,
                data_type=data_type
                )

        if self._imported is not None:
            # self.imported can return None in case the Blendfile does not
            # have the desired data type, such as collections for example.
            self._ob = context.active_object
            self._tM = self._ob.matrix_world.copy()
            self._ob.location = self.location
            self._collections = collections

    def _get_transforms(self):
        rM = Matrix.Rotation(self._rot_z, 4, Z_AXIS)
        sM = Matrix([[self._scale, 0, 0, 0],
                     [0, self._scale, 0, 0],
                     [0, 0, self._scale, 0],
                     [0, 0, 0, 1]])

        return rM, sM

    def _set_transforms(self):
        if self._hit is not None:
            rM, sM = self._get_transforms()
            self._ob.matrix_world = SL_Snap._matrix_from_normal(
                    self._pos + self._normal * 2 * self._cast_threshold,
                    self._normal) @ rM @ sM @ self._tM
        else:
            rM, sM = self._get_transforms()
            self._ob.matrix_world = SL_Snap._matrix_from_normal(
                    self._ob.location, Z_AXIS) @ rM @ sM @ self._tM

    def _translate(self, context, event):
        cast = self._raycast.cast(context.evaluated_depsgraph_get(), event)
        if cast is not None:
            self._hit, self._pos, self._normal, face_index, self._target_ob, \
            matrix_world = cast
            self._set_transforms()
        else:
            if self._hit:
                trans, rot, scale = self._tM.decompose()
                self._ob.rotation_euler = rot.to_euler()
                self._hit = None
        self._ob.location = self.on_cursor(context, event)

    def _rotate(self, context, event):
        delta = radians(event.mouse_region_x - self._mouse_x)
        if event.ctrl:
            increment = radians(45)
            if delta > self._rot_z + increment:
                self._rot_z = (floor(self._init_rot / increment) * increment) \
                              + (floor(delta / increment) * increment)
            elif delta < self._rot_z - increment:
                self._rot_z = (ceil(self._init_rot / increment) * increment) \
                              + (ceil(delta / increment) * increment)
        else:
            self._rot_z = self._init_rot + delta

        if self._hit is not None:
            self._set_transforms()
        else:
            rM, sM = self._get_transforms()
            self._ob.matrix_world = SL_Snap._matrix_from_normal(
                    self._ob.location, Z_AXIS) @ rM @ sM @ self._tM

    def _resize(self, context, event):
        delta = (event.mouse_region_x - self._mouse_x) * 0.01
        self._scale = self._init_scale + delta
        if self._hit is not None:
            self._set_transforms()
        else:
            self._ob.scale = ALL_AXIS * self._scale

    def paste_asset(self, context):
        if self._hit is not None:
            self._ob.location = self._pos

            booleans = self.get_boolean_objects(self._imported)

            if booleans:
                for obj in booleans:
                    self.set_boolean_object(self._target_ob, obj)
                self.setup_weighted_normal(context,
                                           self._target_ob,
                                           self._ob)

    def _get_linked_data_from_type(self, data_type):
        return [data for data in getattr(bpy.data, data_type) if
                data.library and data.library.filepath == self.filepath]

    def _is_free_of_linked_asset(self, context, data_type):
        linked = self._get_linked_data_from_type(data_type)
        if linked:
            scene_object = list(context.scene.objects)
            filename = os.path.basename(self.filepath)
            library = bpy.data.libraries.get(filename)
            inst_coll = [ob for ob in scene_object if
                         self.is_instance_coll_object(ob)]

            if data_type == 'collections':
                if any([ob for ob in inst_coll if ob.instance_collection in
                                                  linked]):
                    return False

            elif data_type == 'objects':
                if any([inst in scene_object for inst in inst_coll for
                        ob in inst.instance_collection.objects if ob in
                                                                  linked]):
                    return False

                if any([ob in scene_object for ob in linked]):
                    return False

            bpy.data.libraries.remove(library, do_unlink=True)
        return True

    def execute(self, context):
        if not os.path.exists(self.filepath):
            return self.path_report(self)

        self._import_asset(context)

        if self._imported is None:
            return self.object_report(self)

        return self.exit(context)

    def modal(self, context, event):
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} \
                or event.type in self.num_keys:
            return {'PASS_THROUGH'}

        if event.type in {'G', 'R', 'S'}:
            self._init_rot = self._rot_z
            self._init_scale = self._scale

            if event.type == 'G' and event.value == 'PRESS' and \
                    self._action != 'G':
                region = context.region
                coords_3d = self._ob.location
                coords_2d = self.on_asset(context, coords_3d)
                context.window.cursor_warp(coords_2d[0] + region.x + 1,
                                           coords_2d[1] + region.y + 0.5)

            if event.type in {'R', 'S'} and event.value == 'PRESS' and \
                    event.type != self._action:
                self._mouse_x = event.mouse_region_x

            self._action = event.type

        if event.type == 'MOUSEMOVE':
            getattr(self, self._action_dict[self._action])(context, event)

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.paste_asset(context)

            filename = os.path.basename(self.filepath)
            if any([ob.library.name == filename for ob in
                    context.scene.objects if ob.library]):
                self.exit(context)
                return {'FINISHED'}

            if self.prefs.import_export.object_import == 'DRAG':
                return self.exit(context)

            if self._ob.name == "AM_root":
                self.clear_root(context, self._ob)

            self._import_asset(context)
            self._raycast.start(context, self._imported)
            self._set_transforms()

            self._action = 'G'
            self._init_rot = self._rot_z
            self._init_scale = self._scale

        elif event.type in {'ESC', 'RIGHTMOUSE'}:
            self.paste_asset(context)
            self.exit(context)
            self.remove(self._imported)
            if self._collections is not None:
                for coll in self._collections:
                    if coll.objects:
                        continue
                    self.remove(coll)

            return {'FINISHED'}

        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # 初始化原 __init__ 中的变量
        self._imported = None
        self._collections = None
        self._ob = None
        self._tM = None
        self._init_rot = 0
        self._rot_z = 0
        self._init_scale = 0
        self._scale = 1
        self._raycast = SL_Raycast()
        self._cast_threshold = self._raycast._cast_threshold
        self._hit = None
        self._pos = ZERO
        self._normal = None
        self._target_ob = None
        self._action = 'G'
        self._action_dict = {'G': "_translate", 'R': "_rotate", 'S': "_resize"}
        self._mouse_x = ZERO
        self._io_import = context.window_manager.asset_management.io_import.objects
        self._relationship_lines = context.space_data.overlay.show_relationship_lines
        
        if not os.path.exists(self.filepath):
            return self.path_report(self)

        if context.space_data.type == 'VIEW_3D':
            self.prefs = addon_prefs()

            if event.shift:
                wm = context.window_manager
                io_import = wm.asset_management.io_import
                if context.object is not None and context.object.mode != \
                        "OBJECT":
                    bpy.ops.object.mode_set(mode="OBJECT")

                import_type = io_import.import_type.lower()
                getattr(bpy.ops.wm, import_type)('INVOKE_DEFAULT',
                                                 filepath=self.filepath)

                return {"FINISHED"}

            if not self._is_free_of_linked_asset(context, 'collections') \
                    or not self._is_free_of_linked_asset(context,
                                                         'objects'):
                return self.linked_asset_report(self)


            to_cursor_3D = (
                    not event.ctrl and
                    self.prefs.import_export.object_import == 'ON_CURSOR') or \
                    (event.ctrl and self.prefs.import_export.object_import
                     != 'ON_CURSOR')

            self.location = context.scene.cursor.location if to_cursor_3D \
                else self.on_cursor(context, event)

            self._import_asset(context)
            if self._imported is None:
                return self.object_report(self)

            if to_cursor_3D:
                return self.exit(context)

            self._action = 'G'
            self._rot_z = radians(self._ob.rotation_euler[2])
            self._raycast.start(context, self._imported)
            context.window.cursor_set("CROSSHAIR")

            self.num_keys = [f"NUMPAD_{num}" for num in range(10)]

            context.space_data.overlay.show_relationship_lines = False
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


class ASSETM_OT_import_assets_edit(Operator, IoCommonProps, AmObjects):
    """ Import/Link the active asset on the selected faces"""
    bl_idname = 'asset_management.import_assets_edit'
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}

    object_as: EnumProperty(
            name="Import object as",
            items=(
                ('OBJECTS', 'Objects', "Import objects", 'OBJECT_DATAMODE', 0),
                ('COLLECTIONS', 'Collections', "Import collections",
                 'OUTLINER_COLLECTION', 1)),
            default='OBJECTS'
            )

    @classmethod
    def poll(cls, context):
        # category = LM.active_category
        # return ((hasattr(category, 'assets') and category.assets) or
        #         LM.pinned_categories()) and context.mode == 'EDIT_MESH'
        category = LM.active_category
        return context.mode == 'EDIT_MESH' and \
               category.preview.preview != "NONE"


    def execute(self, context):
        act_obj = context.active_object
        me = act_obj.data
        bm = bmesh.from_edit_mesh(me)
        tM = act_obj.matrix_world

        if not self.link:
            linked = [ob for ob in bpy.data.objects if
                      ob.library and ob.library.filepath == self.filepath]

            if linked:
                scene_object = list(context.scene.objects)
                filename = os.path.basename(self.filepath)
                library = bpy.data.libraries.get(filename)
                inst_coll = [ob for ob in bpy.data.objects if
                             self.is_instance_coll_object(ob)]

                if any([inst in scene_object for inst in inst_coll for ob in
                        inst.instance_collection.objects if ob in linked]):
                    return self.linked_asset_report(self)

                if any([ob in scene_object for ob in linked]):
                    return self.linked_asset_report(self)

                bpy.data.libraries.remove(library, do_unlink=True)

        data_type = 'objects'
        asset = LM.get_asset_from_path(self.filepath)
        if asset.collections:
            data_type = self.object_as.lower()

        for face in bm.faces:
            if face.select:
                imported, collections = self.import_asset(
                        context,
                        filepath=self.filepath,
                        link=self.link,
                        data_type=data_type
                        )

                if imported is None:
                    return self.object_report(self)

                loc = tM @ Vector(face.calc_center_median())
                quat = face.normal.to_track_quat('Z',
                                                 'Y')
                quat.rotate(tM)
                ob = context.active_object
                ob.matrix_world @= quat.to_matrix().to_4x4()
                ob.location = loc

                if ob.name == "AM_root":
                    self.clear_root(context, ob)

                booleans = self.get_boolean_objects(imported)

                if booleans:
                    for obj in booleans:
                        self.set_boolean_object(act_obj, obj)
                    self.setup_weighted_normal(context,
                                               act_obj,
                                               act_obj)
                    self.select(context, act_obj)

        return {'FINISHED'}


class ASSETM_OT_replace_asset(Operator, IoCommonProps, AmObjects):
    bl_idname = 'asset_management.replace_asset'
    bl_label = "Replace asset"
    bl_options = {'REGISTER', 'UNDO'}

    object_as: EnumProperty(
            name="Import object as",
            items=(
                ('OBJECTS', 'Objects', "Import objects", 'OBJECT_DATAMODE', 0),
                ('COLLECTIONS', 'Collections', "Import collections",
                 'OUTLINER_COLLECTION', 1)),
            default='OBJECTS'
            )

    @classmethod
    def poll(cls, context):
        # category = LM.active_category
        # return hasattr(category, 'assets') and category.assets and \
        #        context.mode != 'EDIT_MESH' and context.selected_objects
        category = LM.active_category
        return context.mode != 'EDIT_MESH' and \
               context.selected_objects and \
               category.preview.preview != "NONE"


    def _remove_booleans(self, context, src):
        src_hierarchy = [src]
        self.get_children(src, src_hierarchy)
        boolean_targets = set()
        for obj in src_hierarchy:
            booleans_dict = self.get_modifier_from_boolean_object(context, obj)
            for ob, mod in booleans_dict.items():
                if ob not in src_hierarchy:
                    boolean_targets.add(ob)
                ob.modifiers.remove(mod)

        return boolean_targets

    def execute(self, context):
        am = context.window_manager.asset_management
        io_objects = am.io_import.objects
        to_replace = {self.get_main_parent(ob) for ob in
                      context.selected_objects}
        to_select = []

        active = self.get_main_parent(context.active_object)

        data_type = 'objects'
        asset = LM.get_asset_from_path(self.filepath)
        if asset.collections:
            data_type = self.object_as.lower()

        for src in list(to_replace)[::-1]:
            imported, collections = self.import_asset(
                    context,
                    filepath=self.filepath,
                    link=self.link,
                    data_type=data_type)

            if imported is not None:
                boolean_targets = self._remove_booleans(context, src)

                ob = context.active_object
                tM = src.matrix_world
                if io_objects.copy_scale:
                    ob.matrix_world = tM
                else:
                    loc, rot, scale = tM.decompose()
                    ob.location = loc
                    ob.rotation_euler = rot.to_euler()

                if ob.name == "AM_root":
                    to_select.extend(ob.children)
                    if src == active:
                        active = ob.children[0]
                    self.clear_root(context, ob)

                else:
                    to_select.append(ob)
                    if src == active:
                        active = ob

                self.remove_hierarchy(src)

                booleans = self.get_boolean_objects(imported)

                if booleans:
                    for target in boolean_targets:
                        for obj in booleans:
                            self.set_boolean_object(target, obj)
                        self.setup_weighted_normal(context,
                                                   target,
                                                   obj)

        self.select(context, to_select)
        if active is not None:
            self.active(context, active)

        return {'FINISHED'}


class ASSETM_OT_save_asset(Operator, AmExportHelper):
    ''' Save the selected objects into your library '''
    bl_idname = 'asset_management.save_asset'
    bl_label = "Confirm"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        io_objects = cls.get_asset_properties('objects')
        return context.mode == 'OBJECT' and (
            io_objects.objects_from == 'COLLECTIONS' or
            (io_objects.objects_from == 'SELECTION' and context.object is not
             None))

    def _is_renderable(self, io_objects):
        return (io_objects.thumbnailer in {'BLENDER_EEVEE', 'CYCLES', 'OGL'}
                and (not io_objects.replace or (io_objects.replace and not
                io_objects.use_existing_thumb)))

    def execute(self, context):
        # 初始化父类的属性（替代 __init__ 中的逻辑）
        self._category = LM.active_category
        self._existing_files = [asset.name for asset in self.category.assets]

        io_objects = self.get_asset_properties('objects')
        filename = io_objects.filename
        Console.clear_output()

        content = self.get_data_to_save(context, io_objects.objects_from)

        if content:
            # Delete the file if it already exists and the "replace" option
            # is enabled
            if filename in self.existing_files and io_objects.replace:
                previous_asset = self.category.assets.get_from_name(filename)
                self.category.assets.remove_asset(
                        previous_asset,
                        keep_icon=io_objects.use_existing_thumb)
            else:
                filename = AmName.get_valid_name(filename, self.existing_files)

            asset = self.category.assets.add(f"{filename}.blend", self.to_root)

            if io_objects.objects_from == 'SELECTION':
                AmObjects.set_object_custom_properties(content)

            bpy.data.libraries.write(filepath=asset.path,
                                     datablocks=content,
                                     path_remap='ABSOLUTE',
                                     fake_user=False,
                                     compress=True)

            self.run_background_processing(
                    OBJECT_POST_PROCESS, asset,
                    f"data_type:{io_objects.objects_from}")

            thumbnailer = Thumbnailer()
            if self._is_renderable(io_objects):
                if io_objects.thumbnailer in {'BLENDER_EEVEE', 'CYCLES'}:
                    thumbnailer.run_background_render(
                            script_path=OBJECT_THUMBNAILER,
                            blendfile=OBJECT_RENDER_SCENE,
                            data_paths=[asset.path],
                            thumb_dir=asset.icon_dir,
                            engine=io_objects.thumbnailer)
                else: # OpenGl render
                    thumbnailer.run_opengl_render(context, asset)

            if io_objects.thumbnailer == 'THUMB':
                output = thumbnailer.save_rendered_image(io_objects, asset)
                if output is not None:
                    self.report({'ERROR_INVALID_INPUT'}, output)

            self.category.assets.active = asset
            asset.load_icon()

        io_objects.display_panel = False

        return {'FINISHED'}


class CommonIoMaterial(IoCommonProps):
    use_existing_material = True


class ASSETM_OT_import_materials(Operator, CommonIoMaterial, AmMaterials):
    """ Import/Link the material.
    CTRL+click to change the import behavior"""
    bl_idname = 'asset_management.import_materials'
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}

    _handler = None

    @classmethod
    def poll(cls, context):
        # if LM.pinned_categories():
        #     return True
        # category = LM.active_category
        # return context.mode == 'OBJECT' and \
        #        ((hasattr(category, 'assets') and category.assets) or
        #         category.preview.preview != "NONE")
        category = LM.active_category
        return context.mode == 'OBJECT' and category.preview.preview != "NONE"

    def exit(self, context, exit='FINISHED'):
        if self._raycast is not None:
            self._raycast.exit()

        if self._modifiers:
            self._restore_modifiers()

        context.window.cursor_modal_restore()
        context.window.cursor_set('DEFAULT')
        context.area.tag_redraw()
        return {exit}

    def _import_material(self):
        imported = self.import_material(
                filepath=self.filepath,
                link=self.link,
                relative=False,
                use_existing=self.use_existing_material
                )
        return imported

    def _update_highlighted_object(self, context):
        if self._highlighted != self._ob:
            self._highlighted = self._ob
            AmObjects.select(context, self._ob)

    def _show_viewport_off(self):
        modifiers = {'SUBSURF', 'SOLIDIFY', 'BOOLEAN'}
        for mod in self._ob.modifiers:
            if mod.type in modifiers and mod.show_viewport:
                mod.show_viewport = False
                self._modifiers.append(mod)

    def _restore_modifiers(self):
        for mod in self._modifiers:
            mod.show_viewport = True

    @property
    def _can_apply_material(self):
        is_array = any([mod for mod in self._ob.modifiers if mod.type ==
                        'ARRAY'])
        return not is_array or self._face_idx <= len(self._ob.data.polygons)

    def _get_ui(self, context):
        for region in context.area.regions:
            if region.type == 'UI':
                return region

    def _over_n_panel(self, context, event):
        ui_panel = self._get_ui(context)
        mouse_x = event.mouse_region_x
        return mouse_x > (context.area.width-ui_panel.width)

    def modal(self, context, event):
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            return self.exit(context)

        if event.type == 'MOUSEMOVE':
            self._cast = self._raycast.cast(context, event)

            if self._cast is not None:
                previous_ob = self._ob
                _, _, _, self._face_idx, self._ob, _ = self._cast
                self._update_highlighted_object(context)

                if previous_ob != self._ob:
                    self._restore_modifiers()
                    self._modifiers.clear()

                if not self._modifiers:
                    self._show_viewport_off()

            else:
                self._restore_modifiers()
                self._ob = None
                self._modifiers.clear()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._cast is None:
                return self.exit(context)

            if self._ob.hide_select and not event.shift:
                self.report(
                        {'INFO'}, f"Object not selectable, Hold SHIFT to "
                                  f"force the application of the material")
            else:
                self._material = self._import_material()
                # If self._material return None, that mean the
                # material doesn't exists in the blendfile.
                if self._material is None:
                    mat_name = os.path.basename(self.filepath).split(
                            ".blend")[0]
                    self.report({'WARNING'}, f"{self.__class__.__name__} -"
                                             f" {mat_name} not found in the "
                                             f"blendfile.")

                    return self.exit(context, exit='CANCELLED')

                if len(self._ob.data.materials) <= 1:
                    self.assign_material(self._ob, self._material)

                else:
                    if self._can_apply_material:
                        slot_idx = self._ob.data.polygons[
                            self._face_idx].material_index
                        self.assign_material(self._ob, self._material, slot_idx)
                    else:
                        self.report(
                                {'WARNING'}, f"For object with array modifier, "
                                             f"hit the original object")

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        # 初始化原 __init__ 中的变量
        self._material = None
        self._highlighted = None
        self._strucked = {}
        self._raycast = SL_Raycast()
        self._hit = None
        self._ob = None
        self._face_idx = None
        self._modifiers = []
        self._cast = None
        
        if not os.path.exists(self.filepath):
            return self.path_report(self)

        if context.space_data.type == 'VIEW_3D':
            prefs = addon_prefs()

            if (not event.ctrl and prefs.import_export.material_import == \
                    'ACTIVE') or \
                    (event.ctrl and prefs.import_export.material_import ==
                     'PICKER'):
                objects = [ob for ob in context.selected_objects if hasattr(
                        ob.data, 'materials')]
                if not objects:
                    return {'FINISHED'}

                material = self._import_material()
                if material is not None:
                    for obj in objects:
                        self.assign_material(obj,
                                             material,
                                             obj.active_material_index)
                return {'FINISHED'}

            wm = context.window_manager
            io_materials = wm.asset_management.io_import.materials
            self.use_existing_material = io_materials.use_existing_material
            self._raycast.start(context,
                                [ob for ob in context.scene.objects if
                                 ob.display_type == 'WIRE'])

            context.window.cursor_modal_set('PAINT_BRUSH')
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


class ASSETM_OT_import_materials_edit(Operator, CommonIoMaterial, AmMaterials):
    """ Import/Link the material on selected faces"""
    bl_idname = 'asset_management.import_materials_edit'
    bl_label = "Import"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # if LM.pinned_categories():
        #     return True
        # category = LM.active_category
        # return hasattr(category, 'assets') and category.assets and \
        #        context.mode == 'EDIT_MESH' and category.preview.preview != \
        #        "NONE"
        category = LM.active_category
        return context.mode == 'EDIT_MESH' and \
               category.preview.preview != "NONE"

    def _import_material(self):
        imported = self.import_material(
                filepath=self.filepath,
                link=self.link,
                relative=False,
                use_existing=self.use_existing_material
                )
        return imported

    def execute(self, context):
        if not os.path.exists(self.filepath):
            return self.path_report(self)

        wm = context.window_manager
        io_materials = wm.asset_management.io_import.materials
        use_existing_material = io_materials.use_existing_material

        report = []
        for ob in context.selected_objects:
            me = ob.data
            bm = bmesh.from_edit_mesh(me)
            if not bm.faces:
                report.append(f"{ob.name} has no faces.")
                continue

            material = self._import_material()
            faces = [f for f in bm.faces if f.select]

            if not faces:
                slot_idx = ob.active_material_index
                self.assign_material(ob, material, slot_idx)
            else:
                if not ob.data.materials:
                    base_mat = self.create_material("Material")
                    self.assign_material(ob, base_mat, 0)

                if use_existing_material and \
                        ob.data.materials.get(material.name):
                    slot_idx = ob.data.materials.find(material.name)
                else:
                    slot_idx = self.add_material_slot(ob, material)

                for f in faces:
                    f.material_index = slot_idx

                bmesh.update_edit_mesh(me)

        if report:
            self.report({'WARNING'}, f"{self.__class__.__name__}"
                                     f" - Some objects has no faces.")
            for input in report:
                print(input)

        return {'FINISHED'}


class ASSETM_OT_save_material(Operator, AmExportHelper):
    ''' Save the selected materials into your library '''
    bl_idname = 'asset_management.save_material'
    bl_label = "Confirm"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        am = bpy.context.window_manager.asset_management
        io_materials = am.io_export.materials
        return any([ul_mat.to_export for ul_mat in io_materials.UL_materials])

    def execute(self, context):
        bpy.context.window.cursor_set('WAIT')
        # 初始化父类的关键属性
        self._category = LM.active_category
        self._existing_files = [asset.name for asset in self.category.assets]        

        io_materials = self.get_asset_properties('materials')
        saved_materials = {}

        for ul_mat in io_materials.UL_materials:
            if not ul_mat.to_export:
                continue

            to_render = 1
            # Delete the file if it already exists and the "replace" option
            # is enabled
            if ul_mat.name in self.existing_files and ul_mat.replace:
                asset = self.category.assets.get_from_name(ul_mat.name)
                self.category.assets.remove_asset(
                        asset,
                        keep_icon=ul_mat.use_existing_thumb)
                mat_name = ul_mat.name
                to_render = not ul_mat.use_existing_thumb
            else:
                mat_name = AmName.get_valid_name(ul_mat.name, self.existing_files)

            am_mat = self.category.assets.add(f"{mat_name}.blend", self.to_root)
            material = bpy.data.materials.get(ul_mat.name)
            bpy.data.libraries.write(filepath=am_mat.path,
                                     datablocks={material},
                                     path_remap='ABSOLUTE',
                                     fake_user=False,
                                     compress=True)

            if not os.path.exists(am_mat.path):
                continue

            self.existing_files.append(am_mat.name)
            saved_materials[am_mat] = to_render

            self.run_background_processing(MATERIAL_POST_PROCESS, am_mat,
                                           f"scn_mat:{material.name}")

        if saved_materials:
            thumbnailer = Thumbnailer()
            if io_materials.thumbnailer in {'BLENDER_EEVEE', 'CYCLES'}:
                data_paths = [am_mat.path for am_mat, to_render in
                              saved_materials.items() if to_render]
                thumbnailer.run_background_render(
                        script_path=MATERIALS_THUMBNAILER,
                        blendfile=io_materials.material_preview,
                        data_paths=data_paths,
                        thumb_dir=am_mat.icon_dir,
                        engine=io_materials.thumbnailer)

            if io_materials.thumbnailer == 'THUMB':
                file = list(saved_materials.keys())[0]
                output = thumbnailer.save_rendered_image(io_materials, file)
                if output is not None:
                    self.report({'ERROR_INVALID_INPUT'}, output)

            self.category.assets.active = list(saved_materials.keys())[-1]

        for mat in saved_materials:
            mat.load_icon()

        bpy.context.window.cursor_set('DEFAULT')
        io_materials.display_panel = False
        return {'FINISHED'}


class ASSETM_OT_open_scene(Operator):
    """ Open blendfile of the active asset"""
    bl_idname = 'asset_management.open_scene'
    bl_label = "Open Blendfile"
    bl_options = {'REGISTER'}

    filepath: StringProperty()

    @classmethod
    def poll(cls, context):
        # category = LM.active_category
        # return hasattr(category, 'assets') and category.assets
        category = LM.active_category
        return category.preview.preview != "NONE"

    def execute(self, context):
        prefs = addon_prefs().import_export

        if os.path.exists(self.filepath):
            bpy.ops.wm.open_mainfile(filepath=self.filepath,
                                     load_ui=prefs.load_ui)

        else:
            self.report({'ERROR'}, f"{self.__class__.__name__} - "
                                   f" {self.filepath} is not a valid path")

        return {'FINISHED'}


class ASSETM_OT_save_scene(Operator, AmExportHelper):
    ''' Save the current scene into your library '''
    bl_idname = 'asset_management.save_scene'
    bl_label = "Confirm"
    bl_options = {'REGISTER'}

    def execute(self, context):
        # 初始化父类的关键属性
        self._category = LM.active_category
        self._existing_files = [asset.name for asset in self.category.assets]  
        
        io_scenes = self.get_asset_properties('scenes')
        filename = AmName.get_valid_name(io_scenes.filename,
                                         self.existing_files)
        # Delete the file if it already exists and the "replace" option
        # is enabled
        if filename in self.existing_files and io_scenes.replace:
            asset = self.category.assets.get_from_name(filename)
            self.category.assets.remove_asset(
                    asset,
                    keep_icon=io_scenes.use_existing_thumb)
        else:
            filename = AmName.get_valid_name(filename, self.existing_files)

        am_asset = self.category.assets.add(f"{filename}.blend", self.to_root)

        thumbnailer = Thumbnailer()

        if io_scenes.thumbnailer == 'OGL':
            thumbnailer.run_opengl_render(context, am_asset)
        else:
            output = thumbnailer.save_rendered_image(io_scenes, am_asset)
            if output is not None:
                self.report({'ERROR_INVALID_INPUT'}, output)

        bpy.ops.wm.save_as_mainfile(filepath=am_asset.path,
                                    compress=True,
                                    relative_remap=False,
                                    copy=True)

        self.run_background_processing(SCENE_POST_PROCESS, am_asset)

        self.category.assets.active = am_asset
        am_asset.load_icon()

        io_scenes.display_panel = False

        return {'FINISHED'}


class IblCollection(PropertyGroup):

    name: StringProperty()


class ASSETM_OT_save_ibl(Operator, ImportHelper):
    ''' Save the IBLs selected from the file browser to your library '''
    bl_idname = 'asset_management.save_ibl'
    bl_label = "Add IBL"
    bl_options = {'REGISTER'}

    filter_glob: StringProperty(
            default="*.hdr;*.exr"
            )

    filepath: StringProperty(name="File path",
                             subtype='FILE_PATH',
                             maxlen=1024)

    files: CollectionProperty(type=IblCollection)

    @classmethod
    def poll(cls, context):
        return hasattr(LM.active_category, 'assets')

    def draw(self, layout):
        addon_pref = addon_prefs()
        layout = self.layout
        box = layout.box()
        row_title = box.row()
        row_title.alignment = 'CENTER'
        row_title.label(text="IBL OPTIONS")
        box.separator()
        box.label(text="Save IBL:", icon='FILE_FOLDER')
        row = box.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        split.prop(addon_pref.import_export, 'save_to_root')
        box.label(text="Thumbnail resolution:", icon='IMAGE_PLANE')
        row = box.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        split.prop(addon_pref.import_export, 'thumb_resolution', text="")

    def execute(self, context):
        
        files = [file.name for file in self.files if file.name != ""]

        if not files:
            self.report({'INFO'}, "No files selected")
            return {'FINISHED'}

        existing = [f.filename for f in LM.active_category.assets]

        category = LM.active_category
        addon_pref = addon_prefs()
        to_root = addon_pref.import_export.save_to_root

        path_from = os.path.dirname(self.filepath)
        asset_path, icon_path = AmPath.get_export_dirs(category.path,
                                                       to_root)

        imported = []
        not_saved = []

        for file in files:
            if file in existing:
                not_saved.append(file)
                continue

            src = os.path.join(path_from, file)
            dst = os.path.join(asset_path, file)
            shutil.copy2(src, dst)
            imported.append(category.assets.add(file, to_root))

        if imported:
            bpy.context.window.cursor_set('WAIT')

            thumbnailer = AmBackgroundProcessor()

            for line in thumbnailer.run_process(
                    IBL_THUMBNAILER,
                    None,
                    True,
                    f"asset:{asset_path}",
                    f"icons:{icon_path}",
                    f"files:{';'.join(files)}",
                    f"reso:{addon_pref.import_export.thumb_resolution}",
                    f"format:{addon_pref.import_export.thumb_format}"):
                print(line)

            for asset in sorted(imported, key=lambda file: file.name.lower()):
                asset.load_icon()
            if asset is not None:
                category.assets.active = asset
            bpy.context.window.cursor_set('DEFAULT')

            context.area.tag_redraw()

        if not_saved:
            self.report({'INFO'}, "Some files already exists")
            print("Some files already exists:")
            for file in not_saved:
                print(f"\t{file}")

        return {'FINISHED'}


class ASSETM_OT_setup_environment(Operator, AmEnvironment):
    """ Create a new environment """
    bl_idname = 'asset_management.setup_environment'
    bl_label = "Setup environment"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty()

    @classmethod
    def poll(cls, context):
        # if LM.pinned_categories():
        #     return True
        # category = LM.active_category
        # return hasattr(category, 'assets') and category.assets
        category = LM.active_category
        return category.preview.preview != "NONE"


    def execute(self, context):
        if os.path.exists(self.filepath):
            world = context.scene.world
            if world is None:
                self.new_environment(context, self.filepath)
            else:
                nodes = world.node_tree.nodes
                env_node = [node for node in nodes if node.name.startswith(
                        'AM_environment')]
                if env_node:
                    self.setup_ibl(self.filepath, world)
                    filename = os.path.splitext(os.path.basename(self.filepath))[0]
                    world.name = filename
                else:
                    self.new_environment(context, self.filepath)
        else:
            self.report({'ERROR'}, f"{self.__class__.__name__} - "
                                   f" {self.filepath} is not a valid path")
        return {'FINISHED'}


CLASSES = (ASSETM_OT_import_assets,
           ASSETM_OT_import_assets_edit,
           ASSETM_OT_replace_asset,
           ASSETM_OT_save_asset,
           ASSETM_OT_import_materials,
           ASSETM_OT_import_materials_edit,
           ASSETM_OT_save_material,
           ASSETM_OT_open_scene,
           ASSETM_OT_save_scene,
           IblCollection,
           ASSETM_OT_save_ibl,
           ASSETM_OT_setup_environment
           )


def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in CLASSES:
        unregister_class(cls)
