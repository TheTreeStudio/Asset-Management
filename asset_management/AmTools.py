# -*- coding:utf-8 -*-

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
import time

from bpy.types import Operator
from bpy.props import (IntProperty, FloatProperty, StringProperty)
from bpy.utils import register_class, unregister_class

from .AmUtils import (AmName, Thumbnailer, AmBackgroundProcessor,
                      addon_prefs, Console)
from .AmLibraries import LibrariesManager as LM
from .AmCore import AmEnvironment, AmFilterSearchName
from .AmImportExport import AmExportHelper
from .t3dn_bip.ops import InstallPillow
from .ressources.constants import SETUP_EDIT_ASSET_SCENE


class ASSETM_OT_cancel(Operator):
    """Cancel"""
    bl_idname = 'asset_management.cancel'
    bl_label = "Cancel"
    bl_options = {'REGISTER'}

    def execute(self, context):
        am = context.window_manager.asset_management
        LM.category_to_move = LM.asset_to_move = None
        bpy.types.ASSET_MANAGEMENT_OT_new_category.set_status(state=False)
        am.edit_asset = False
        if LM.asset_to_edit is not None:
            if os.path.exists(LM._back_to_previous):
                bpy.ops.wm.open_mainfile(filepath=LM._back_to_previous)
            LM.set_asset_to_edit(None)
        return {'FINISHED'}


class ASSETM_OT_saving_asset(Operator):
    """Generic class to save or cancel the saving of an asset"""

    asset_type: StringProperty()

    def execute(self, context):
        am = context.window_manager.asset_management
        if self.asset_type == 'assets':
            self.asset_type = 'objects'
        if hasattr(am.io_export, self.asset_type):
            data = getattr(am.io_export, self.asset_type)
            data.display_panel = not data.display_panel
            if not data.display_panel:
                data.reset_values()
            else:
                am.io_export.objects.filename = context.object.name if \
                    context.object is not None else "Untitled"
        return {'FINISHED'}


class ASSETM_OT_save_new_asset(ASSETM_OT_saving_asset):
    """Save a new asset in your library"""
    bl_idname = 'asset_management.save_new_asset'
    bl_label = "New"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return LM.active_category != LM.active_type


class ASSETM_OT_asset_cancel(ASSETM_OT_saving_asset):
    """Cancel"""
    bl_idname = 'asset_management.asset_cancel'
    bl_label = "Cancel"
    bl_options = {'REGISTER'}


class ASSETM_OT_remove_asset(Operator):
    """Remove the active asset from your library"""
    bl_idname = 'asset_management.remove_asset'
    bl_label = "Delete"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return hasattr(LM.active_category, 'assets') and \
               len(LM.active_category.assets) >= 1

    def draw(self, context):
        layout = self.layout
        asset_name = LM.active_category.assets.active.name
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="---- REMOVE ASSET ----")
        layout.separator()
        layout.label(text=f"{asset_name}",
                     icon="ERROR"
                     )
        layout.label(text="will be remove from your library",
                     icon="BLANK1"
                     )

    def execute(self, context):
        category = LM.active_category
        category.assets.remove_asset(category.assets.active)

        assets = category.assets
        assets.active = assets.sorted[0] if assets else None
        context.area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=300)
        return {'RUNNING_MODAL'}


class ASSETM_OT_rename_asset(Operator):
    """Rename the active asset"""
    bl_idname = 'asset_management.rename_asset'
    bl_label = "Rename asset"
    bl_options = {'REGISTER'}

    name: StringProperty()

    @classmethod
    def poll(cls, context):
        return hasattr(LM.active_category, 'assets') and \
               LM.active_category.assets

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.alignment = "CENTER"
        row.label(text="---- RENAME ASSET ----")
        layout.separator()
        layout.label(text="New name:")
        row = layout.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        split.prop(self, 'name', text="")

    def execute(self, context):
        if not self.name or len(self.name) == self.name.count(" "):
            return {'FINISHED'}
        category = LM.active_category
        existing_name = [file.name for file in category.assets]
        valid_name = AmName.get_valid_name(self.name, existing_name)
        renamed_asset = category.assets.rename(category.assets.active,
                                               valid_name)
        category.assets.active = renamed_asset
        context.area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        category = LM.active_category
        self.name = category.assets.active.name
        context.window_manager.invoke_props_dialog(self, width=300)
        return {'RUNNING_MODAL'}


class ASSETM_OT_move_asset(Operator):
    """Move the active asset in the selected category"""
    bl_idname = 'asset_management.move_asset'
    bl_label = "Move asset"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return LM.active_category.path != LM.active_type.path and \
               LM.asset_to_move is not None and LM.active_category.path != \
               LM.asset_to_move.parent.path

    def execute(self, context):
        if LM.asset_to_move.parent.path == LM.active_category.path:
            LM.asset_to_move = None
            return {'FINISHED'}

        category = LM.active_category
        LM.move_asset(category)
        return {'FINISHED'}


class ASSETM_OT_edit_asset(Operator):
    """ Opens the active asset file for editing """
    bl_idname = 'asset_management.edit_asset'
    bl_label = "Edit asset"
    bl_options = {'REGISTER'}


    def execute(self, context):
        asset = LM.active_category.assets.active
        # we store the last modification date in order to test, once the
        # modification is done, if the file has been saved again.
        current_backup = time.ctime(os.path.getmtime(asset.path))

        post_processing = AmBackgroundProcessor()

        for line in post_processing.run_process(
                SETUP_EDIT_ASSET_SCENE,
                asset.path,
                background=False):
            print(line)
            if "Blender quit" in line:
                to_reload = any([coll for coll in bpy.data.collections if
                                 coll.library is not None and
                                 coll.library.filepath == asset.path])
                if not to_reload:
                    to_reload = any([ob for ob in context.scene.objects if
                                     ob.library is not None and
                                     ob.library.filepath == asset.path])
                if to_reload:
                    last_backup = time.ctime(os.path.getmtime(asset.path))
                    # if a date/time difference is found, it means that the
                    # file has been saved and that we can update the
                    # concerned library in the current scene
                    if current_backup != last_backup:
                        library = bpy.data.libraries.get(asset.filename)
                        library.reload()
                        self.report(
                                {'INFO'},
                                f"The library '{asset.filename}' has been "
                                f"reloaded")

        return {'FINISHED'}


class ASSETM_OT_save_asset_changes(Operator):
    """Saving changes of the asset and back to previous"""
    bl_idname = 'asset_management.save_asset_changes'
    bl_label = "Save"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.save_mainfile()

        if os.path.exists(f"{bpy.data.filepath}1"):
            os.remove(f"{bpy.data.filepath}1")

        bpy.ops.wm.quit_blender()
        return {'FINISHED'}


class ASSETM_OT_change_asset(Operator):
    """  """
    bl_idname = 'asset_management.change_asset'
    bl_label = "Change Asset"
    bl_options = {'REGISTER'}

    index: IntProperty(default=0)

    category_path: StringProperty(default="")

    def execute(self, context):
        category = LM.get_category_from_path(self.category_path)

        if category.__class__.__name__ == "AssetType":
            category = getattr(AmFilterSearchName, category.name)

        # have to change when GPU UI will be on place
        if category is None or not hasattr(category, 'assets') or not \
                category.assets:
            return {'FINISHED'}

        max_index = len(category.assets) - 1

        if category.__class__.__name__ != "Category":
            assets = category.sorted
            data_blocks = category
        else:
            assets = category.assets.sorted
            data_blocks = category.assets

        idx = data_blocks.active_index + self.index

        if idx > max_index:
            data_blocks.active = assets[0]
        elif idx < 0:
            data_blocks.active = assets[-1]
        else:
            data_blocks.active = assets[idx]

        return {'FINISHED'}


class ASSETM_OT_create_collection(Operator):
    """Create a new collection and set it as active by default"""
    bl_idname = 'asset_management.create_collection'
    bl_label = "Create Collection"
    bl_options = {'REGISTER', 'UNDO'}

    new_collection: StringProperty(default="Collection")

    def execute(self, context):
        am = context.window_manager.asset_management
        io_objects = am.io_import.objects
        parent_coll = context.view_layer.active_layer_collection

        collection = bpy.data.collections.new(self.new_collection)
        parent_coll.collection.children.link(collection)
        io_objects.collection = collection
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.label(text="New collection name:")
        row = layout.row(align=True)
        split = row.split(factor=0.2)
        split.separator()
        split.prop(self, 'new_collection', text="")

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=300)
        return {'RUNNING_MODAL'}


class ASSETM_OT_toggle_pinned_category(Operator):
    """Change the status of the category pin"""
    bl_idname = 'asset_management.toggle_pinned_category'
    bl_label = "Toggle pinned category"
    bl_options = {'REGISTER'}

    category_path: StringProperty(default="")

    def execute(self, context):
        if self.category_path:
            category = LM.get_category_from_path(self.category_path)
            category.pinned = not category.pinned
        return {'FINISHED'}


class ASSETM_OT_ibl_manupilate(Operator):
    """Displays options"""
    bl_idname = 'asset_management.ibl_manipulate'
    bl_label = "IBL manupulate"
    bl_options = {'REGISTER', "BLOCKING", "GRAB_CURSOR"}

    mouse_pos_x: IntProperty()
    shading_rotation: FloatProperty()
    end_position = 0
    tmp_pos_x = 0

    @staticmethod
    def get_node_from_type(nodes, nType):
        for node in nodes:
            if node.type == nType:
                return node

        return None

    def get_mapping_node(self, world):
        nodes = world.node_tree.nodes
        mapping_node = self.get_node_from_type(nodes, "MAPPING")
        if not mapping_node:
            group_node = self.get_node_from_type(nodes, "GROUP")
            if group_node:
                mapping_node = self.get_node_from_type(
                        group_node.node_tree.nodes, "MAPPING"
                        )

        return mapping_node

    @staticmethod
    def get_shading_type(shading):
        if shading.type != "WIREFRAME" or\
                (shading.type == "SOLID" and shading.light == "STUDIO") or\
                shading.type in {"MATERIAL", "RENDERED"}:
            return shading.type
        return

    def set_shading_rotation(self, mapping_node):
        self.shading_rotation = mapping_node.inputs[2].default_value[2]

    @staticmethod
    def set_z_axis(mapping_node, value):
        mapping_node.inputs[2].default_value[2] = value

    def modal(self, context, event):
        if event.type == "MOUSEMOVE":
            offset = (event.mouse_x - self.mouse_pos_x) / 300
            if self.shading_type == "RENDERED":
                self.set_z_axis(self.mapping_node,
                                self.shading_rotation - offset)

            elif self.shading_type in {"MATERIAL", "SOLID"}:
                if self.shading_type == "MATERIAL" and \
                        self.shading.use_scene_world:
                    self.set_z_axis(
                            self.mapping_node, self.shading_rotation - offset
                            )
                else:
                    self.shading.studiolight_rotate_z = \
                        self.shading_rotation - offset

                    if round(self.shading.studiolight_rotate_z, 4) == -3.1416:
                        self.end_position = -3.1416
                    if round(self.shading.studiolight_rotate_z, 4) == 3.1416:
                        self.end_position = 3.1416

                    if self.end_position:
                        if not self.tmp_pos_x:
                            self.tmp_pos_x = event.mouse_x
                        if self.end_position == -3.1416 and \
                                event.mouse_x > self.tmp_pos_x:
                            self.shading.studiolight_rotate_z = \
                                self.shading_rotation = 3.14159
                            self.end_position = self.tmp_pos_x = 0
                            self.mouse_pos_x = event.mouse_x

                        elif self.end_position == 3.1416 and \
                                event.mouse_x < self.tmp_pos_x:
                            self.shading.studiolight_rotate_z = \
                                self.shading_rotation = -3.14159
                            self.end_position = self.tmp_pos_x = 0
                            self.mouse_pos_x = event.mouse_x

        if event.type == "ESC":
            if self.shading_type == "RENDERER":
                self.set_z_axis(
                        self.mapping_node, self.shading_rotation
                        )

            elif self.shading_type in {"MATERIAL", "SOLID"}:
                if self.shading_type == "MATERIAL" and \
                        self.shading.use_scene_world:
                    self.set_z_axis(
                            self.mapping_node, self.shading_rotation
                            )
                else:
                    self.shading.studiolight_rotate_z = self.shading_rotation

            return {"FINISHED"}

        if event.type == self.event_key and event.value == "RELEASE":
            return {"FINISHED"}

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        self.shading = context.space_data.shading
        self.shading_type = self.get_shading_type(self.shading)
        if self.shading_type:
            if self.shading_type == "RENDERED":
                if not hasattr(context.scene.world, "node_tree"):
                    self.report({'WARNING'}, "No environment")
                    return {'CANCELLED'}

                world = context.scene.world
                self.mapping_node = self.get_mapping_node(world)
                if not self.mapping_node:
                    self.report({'WARNING'}, "Mapping node not found")
                    return {'CANCELLED'}

                self.set_shading_rotation(self.mapping_node)

            elif self.shading_type in {"MATERIAL", "SOLID"}:
                if self.shading_type == "SOLID":
                    self.shading.use_world_space_lighting = True
                if self.shading_type == "MATERIAL" and \
                        self.shading.use_scene_world:
                    if not hasattr(context.scene.world, "node_tree"):
                        self.report({'WARNING'}, "No environment")
                        return {'CANCELLED'}

                    world = context.scene.world
                    self.mapping_node = self.get_mapping_node(world)
                    if not self.mapping_node:
                        self.report({'WARNING'}, "Mapping node not found")
                        return {'CANCELLED'}
                    self.set_shading_rotation(self.mapping_node)
                else:
                    self.shading_rotation = self.shading.studiolight_rotate_z

            self.event_key = context.window_manager.keyconfigs.user.keymaps[
                "3D View Generic"].keymap_items[
                "asset_management.ibl_manipulate"].type
            self.mouse_pos_x = event.mouse_x
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        self.report({'WARNING'}, "Invalid shading type")
        return {"CANCELLED"}


class ASSETM_OT_add_environment(Operator, AmEnvironment):
    """Create a new world environment"""
    bl_idname = 'asset_management.add_environment'
    bl_label = "Add world environment"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty()

    @classmethod
    def poll(cls, context):
        # if LM.pinned_categories() and LM.active_type.name == 'hdri':
        #     return True
        # category = LM.active_category
        # return LM.active_type.name == 'hdri' and \
        #        hasattr(category, 'assets') and category.assets
        category = LM.active_category
        return LM.active_type.name == 'hdri' and \
               category.preview.preview != "NONE"

    def execute(self, context):
        if os.path.exists(self.filepath):
            self.new_environment(context, self.filepath)
        else:
            self.report({'ERROR'}, f"{self.__class__.__name__} - "
                                   f" {self.filepath} is not a valid path")
        return {'FINISHED'}


class ASSETM_OT_remove_environment(Operator):
    """Remove the active AM environment from the datas"""
    bl_idname = 'asset_management.remove_environment'
    bl_label = "Remove Environment"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        am = context.window_manager.asset_management
        env = am.environment
        return env.am_worlds

    def execute(self, context):
        am = context.window_manager.asset_management
        env = am.environment
        bpy.data.worlds.remove(env.am_worlds, do_unlink=True)
        worlds = [world for world in bpy.data.worlds for node in
                  world.node_tree.nodes if node.name.startswith(
                    'AM_environment')]
        if worlds:
            env.am_worlds = worlds[0]
        else:
            env.am_worlds = None
        return {'FINISHED'}


class ASSETM_OT_restore_hotkey(Operator):
    bl_idname = "asset_management.restore_hotkey"
    bl_label = "Restore hotkeys"
    bl_options = {'REGISTER', 'INTERNAL'}

    km_name: StringProperty()

    def execute(self, context):
        context.preferences.active_section = 'KEYMAP'
        wm = context.window_manager
        kc = wm.keyconfigs.addon
        km = kc.keymaps.get(self.km_name)
        if km:
            km.restore_to_default()
            context.preferences.is_dirty = True
        context.preferences.active_section = 'ADDONS'
        return {'FINISHED'}


class ShadingOverlayStatus:
    overlay = True

    @classmethod
    def set_overlay(cls, status):
        cls._overlay = status


class UpdateSelectionAndRestore():

    def __init__(self, context, parent=True, children=True):
        self._ctx = context
        self._sel = context.selected_objects[:]
        self._parent = parent
        self._children = children

    def __enter__(self):
        am = bpy.context.window_manager.asset_management
        io_objects = am.io_export.objects
        for obj in AmExportHelper.get_objects_from(self._ctx,
                                                   io_objects.objects_from):
            obj.select_set(state=True)

        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        for obj in self._ctx.scene.objects:
            obj.select_set(state=obj in self._sel)

        return False


class ASSETM_OT_setup_opengl_camera(Operator, Thumbnailer):
    """Setup the camera for the openGl render"""
    bl_idname = "asset_management.setup_opengl_camera"
    bl_label = "Setup camera"
    bl_options = {'REGISTER', 'UNDO'}

    lock_camera = True

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and context.selected_objects

    def execute(self, context):
        # we have store the overlay status to restore it later because
        # when rendering, it will be automatically set to False
        ShadingOverlayStatus.set_overlay(context.space_data.overlay.show_overlays)
        camera = self.get_camera("opengl_cam")
        if camera is None:
            camera = self.add_camera(context, 'opengl_cam')
        with UpdateSelectionAndRestore(context):
            self.set_camera_framing(context, camera)

        context.space_data.lock_camera = True

        return {'FINISHED'}


class ASSETM_OT_remove_opengl_camera(Operator):
    """Remove the camera 'opengl_cam'"""
    bl_idname = "asset_management.remove_opengl_camera"
    bl_label = "Remove camera"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.objects.get("opengl_cam") is not None

    def execute(self, context):
        bpy.data.objects.remove(bpy.data.objects.get("opengl_cam"),
                                    do_unlink=True)

        context.space_data.overlay.show_overlays = ShadingOverlayStatus.overlay
        return {'FINISHED'}


class ASSETM_OT_auto_target_selection(Operator):
    """If enabled, target automatically the selected objects
    Also take into account the options 'Parents' and 'Childrens'"""
    bl_idname = "asset_management.auto_target"
    bl_label = "Auto target"
    bl_options = {'REGISTER', 'UNDO'}

    _running = False
    _targets = []

    @classmethod
    def poll(cls, context):
        return context.scene.objects.get("opengl_cam") is not None

    @classmethod
    def set_status(cls):
        cls._running = not cls._running

    def selection_changed(self, context):
        targets = AmExportHelper.get_objects_from(
                context, self.io_objects.objects_from)
        return (len(context.selected_objects) != len(self._targets) or not
        all([obj in self._targets for obj in targets]))

    def restore(self, context):
        self.set_status()

    def modal(self, context, event):
        if not self._running:
            return {'FINISHED'}
        if context.selected_objects and self.selection_changed(context):
            bpy.ops.asset_management.setup_opengl_camera()
            self._targets = AmExportHelper.get_objects_from(
                context, self.io_objects.objects_from)
        if context.scene.objects.get("opengl_cam") is None:
            self.restore(context)
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if self._running:
            self.set_status()
            return {'FINISHED'}
        am = context.window_manager.asset_management
        self.io_objects = am.io_export.objects
        self.set_status()
        self._targets = AmExportHelper.get_objects_from(
                context, self.io_objects.objects_from)
        bpy.ops.asset_management.setup_opengl_camera()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class ASSETM_OT_install_pillow(Operator, InstallPillow):
    bl_idname = 'asset_management.install_pillow'


class ASSETM_OT_render_logs(Operator):
    """Save the render logs in a file to share it easily"""
    bl_idname = "asset_management.print_render_logs"
    bl_label = "Print render logs"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prefs = addon_prefs().addon_pref
        dir_path = prefs.file_debug_path
        filepath = os.path.join(dir_path, 'AssetManagement_render_logs')
        with open(filepath, "w") as file:
            file.write("\n".join(Console.output))

        self.report({'INFO'}, f"The logs has been saved to {filepath}")
        return {'FINISHED'}


class ASSETM_OT_update_asset_type(Operator):
    """Update asset types (useful when you work with several blender
    sessions to make an asset type created in another session appear in the
    current one)"""
    bl_idname = "asset_management.update_asset_type"
    bl_label = "Update asset types"
    bl_options = {'REGISTER'}

    def execute(self, context):
        LM.active_library.asset_types.update()
        return {'FINISHED'}


class ASSETM_OT_update_categories(Operator):
    """Update categories (useful when you work with several blender sessions
    to update the display of categories modified from another session)"""
    bl_idname = "asset_management.update_categories"
    bl_label = "Update categories"
    bl_options = {'REGISTER'}

    def execute(self, context):
        LM.active_type.categories.update()
        return {'FINISHED'}


class ASSETM_OT_search_by_name(Operator):
    """Search for matching assets from the given names"""
    bl_idname = "asset_management.search_by_name"
    bl_label = "Search asset"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        am = context.window_manager.asset_management
        return  not am.filter_search

    def draw(self, context):
        am = context.window_manager.asset_management
        layout = self.layout
        layout.prop(am, 'filter_search', icon='VIEWZOOM')

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)


class ASSETM_OT_clear_filter_search(Operator):
    """Clear the filter search for active asset type"""
    bl_idname = "asset_management.clear_filter_search"
    bl_label = "Clear filter"
    bl_options = {'REGISTER'}

    asset_type: StringProperty(default="")

    def execute(self, context):
        if not self.asset_type:
            self.asset_type = LM.active_type.name

        filter = getattr(AmFilterSearchName, self.asset_type)
        filter.clear_search()

        self.asset_type = ""

        pinned_categories = LM.pinned_categories()
        if len(pinned_categories) == 1 and LM.active_category == \
                pinned_categories[0]:
            pinned_categories[0].pinned = False

        return {'FINISHED'}


CLASSES = (ASSETM_OT_cancel,
           ASSETM_OT_save_new_asset,
           ASSETM_OT_asset_cancel,
           ASSETM_OT_remove_asset,
           ASSETM_OT_rename_asset,
           ASSETM_OT_move_asset,
           ASSETM_OT_edit_asset,
           ASSETM_OT_save_asset_changes,
           ASSETM_OT_change_asset,
           ASSETM_OT_create_collection,
           ASSETM_OT_toggle_pinned_category,
           ASSETM_OT_ibl_manupilate,
           ASSETM_OT_add_environment,
           ASSETM_OT_remove_environment,
           ASSETM_OT_restore_hotkey,
           ASSETM_OT_setup_opengl_camera,
           ASSETM_OT_remove_opengl_camera,
           ASSETM_OT_auto_target_selection,
           ASSETM_OT_install_pillow,
           ASSETM_OT_render_logs,
           ASSETM_OT_update_asset_type,
           ASSETM_OT_update_categories,
           ASSETM_OT_search_by_name,
           ASSETM_OT_clear_filter_search)


def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in CLASSES:
        unregister_class(cls)
