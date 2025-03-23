# -*- coding:utf-8 -*-

# Blender asset_management_2_8 Add-on
# Copyright (C) 2018 Legigan Jeremy AKA Pistiwique
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

from bpy.utils import register_class, unregister_class
from bpy.types import Panel, Operator, Menu, UIList

from .preferences.addon_updater import Updater
from .AmLibraries import LibrariesManager as LM
from .AmUtils import addon_prefs
from .ressources.constants import ASSET_TYPE
from .AmCore import AmFilterSearchName


DEBUG = False


class ASSETM_OT_debug(Operator):
    bl_idname = "asset_management.debug"
    bl_label = "DEBUG"
    bl_options = {'REGISTER'}

    def execute(self, context):
        from .AmUtils import Console

        filepath = "C:/Users/pisti/Desktop/AssetManagement_logs"

        with open(filepath, "w") as file:
            file.write("\n".join(Console.output))
        return {'FINISHED'}


class ASSETM_MT_library_options(Menu):
    """Display the library options"""
    bl_label = "Library Options"

    def draw(self, context):
        layout = self.layout
        if not LM.libraries:
            layout.operator('asset_management.load_old_libraries',
                            icon='RECOVER_LAST')
        layout.operator('asset_management.add_library',
                        icon='ADD')
        if LM.libraries:
            layout.operator('asset_management.remove_library',
                            icon='PANEL_CLOSE')
            layout.operator('asset_management.rename_library',
                            icon='TEXT')
            layout.operator('asset_management.move_library',
                            icon='VIEW_PAN')
            layout.separator()
            layout.operator('asset_management.add_asset_type', icon='ADD')

            existing_types = os.listdir(LM.active_library.path)
            if any(type_ for type_ in existing_types if not
            LM.active_library.asset_types.get(type_)):
                layout.operator('asset_management.update_asset_type',
                                text="Refresh asset types",
                                icon='FILE_REFRESH')


class ASSETM_MT_category_options(Menu):
    """ Display the category options """
    bl_label = "Category Options"

    def draw(self, context):
        layout = self.layout
        layout.operator('asset_management.new_category', icon='ADD')
        aType = LM.libraries.active.asset_types.active
        if aType.categories.active != aType:
            wm = context.window_manager
            am = wm.asset_management
            layout.operator('asset_management.remove_category',
                            icon='PANEL_CLOSE')
            layout.operator('asset_management.rename_category',
                            icon='TEXT')
            row = layout.row()
            row.active = not am.move_category
            row.prop(am, 'move_category', text="Move category",
                     icon='VIEW_PAN', toggle=False)
        else:
            layout.operator('asset_management.update_categories',
                            text="Refresh categories",
                            icon='FILE_REFRESH')


class ASSETM_PT_category_browser(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AM"
    bl_label = "Category Browser"
    bl_parent_id = "ASSETM_PT_asset_management_panel"

    @classmethod
    def poll(cls, context):
        am = context.window_manager.asset_management
        return bpy.app.version >= (2, 93, 0) and LM.libraries and not any(
                getattr(am.io_export, asset_type).display_panel for
                asset_type in ('objects', 'materials', 'scenes')) and \
               LM.asset_to_edit is None

    def _category_browser(self, context, layout, category, margin_count):
        active_category = LM.active_category
        am = context.window_manager.asset_management

        if active_category == category and \
                bpy.types.ASSET_MANAGEMENT_OT_new_category.running():

            row_name = layout.row(align=True)
            row_name.alignment = 'LEFT'
            for _ in range(margin_count + 1):
                row_name.label(text="", icon='BLANK1')
            row_name.prop(am, 'category_name', text="")
            row_name.operator('asset_management.add_category',
                              text="",
                              icon='FILE_TICK')
            row_name.operator('asset_management.cancel', text="", icon='X')

        subcategories = sorted(category.categories.values(), key=lambda cat:
        cat.name.lower())

        if category.__class__.__name__ == "AssetType" or (
                category.is_expandable and category.expanded):
            for subcategory in subcategories:
                row = layout.row(align=True)
                row.alignment = 'LEFT'
                for _ in range(margin_count):
                    row.label(text="", icon='BLANK1')

                if hasattr(subcategory, 'is_expandable') and \
                        subcategory.is_expandable:
                    icon = 'TRIA_RIGHT' if not subcategory.expanded else \
                        'TRIA_DOWN'
                    row.operator('asset_management.expand_category',
                                 text="",
                                 icon=icon,
                                 emboss=False).path = subcategory.path
                else:
                    row.label(text="", icon='BLANK1')

                row.operator('asset_management.set_active_category',
                             text=subcategory.name,
                             icon='FILEBROWSER',
                             emboss=active_category == subcategory).path = \
                    subcategory.path

                if active_category == subcategory:
                    row.menu('ASSETM_MT_category_options',
                             text="",
                             icon='THREE_DOTS'
                             )

                if subcategory.assets:
                    if LM.active_category == subcategory:
                        row.label(icon='BLANK1')
                    else:
                        icon = 'PINNED' if subcategory.pinned else 'UNPINNED'
                        row.operator('asset_management.toggle_pinned_category',
                                     text="",
                                     icon=icon,
                                     emboss=False).category_path=subcategory.path

                self._category_browser(context,
                                       layout,
                                       subcategory,
                                       margin_count + 1)

    def _categories_layout(self, context, layout):
        col = layout.column()
        aType = LM.active_type
        row = col.row(align=True)
        row.alignment = 'LEFT'
        row.operator('asset_management.set_active_category',
                     text=aType.name,
                     icon='FILEBROWSER',
                     emboss=aType.active_category == aType).path = aType.path

        if aType.categories.active == aType:
            row.menu('ASSETM_MT_category_options',
                     text="",
                     icon='THREE_DOTS')
        else:
            row.label(text="", icon='BLANK1')

        row.operator('asset_management.show_active_category',
                     text="",
                     icon='DOCUMENTS',
                     emboss=False)

        row.operator('asset_management.collapse_all_categories',
                     text="",
                     icon='COLLAPSEMENU',
                     emboss=False)

        row.operator('asset_management.search_by_name',
                     text="",
                     icon='VIEWZOOM',
                     emboss=False)

        self._category_browser(context, col, aType, 1)

    def _categories_layout_poll(self, to_move):
        return  to_move is None or \
                (to_move and LM.active_library.asset_types.get(
                        to_move.parent_asset_type.name))

    def draw(self, context):
        library = LM.active_library
        layout = self.layout

        if library and library.asset_types:
            cat_to_move = LM.category_to_move
            asset_to_move = LM.asset_to_move
            if self._categories_layout_poll(cat_to_move) and \
                self._categories_layout_poll(asset_to_move):
                self._categories_layout(context, layout)

            if cat_to_move is not None:
                layout.separator(factor=2)
                row = layout.row(align=True)
                row.operator('asset_management.move_category', text="Move",
                             icon='VIEW_PAN')
                row.operator('asset_management.cancel', text="Cancel",
                             icon='X')

            if asset_to_move is not None:
                layout.separator(factor=2)
                row = layout.row(align=True)
                row.operator('asset_management.move_asset', text="Move",
                             icon='VIEW_PAN')
                row.operator('asset_management.cancel', text="Cancel",
                             icon='X')


def draw_tool_template(context, layout):
    """Function displaying the tools at the right side of the preview"""

    if LM.active_category != LM.active_type:
        if LM.active_type.name != 'hdri':
            layout.operator('asset_management.save_new_asset',
                            text="",
                            icon='FILE_TICK').asset_type = LM.active_type.name
        else:
            layout.operator('asset_management.save_ibl',
                            text="",
                            icon='FILE_TICK')

        layout.operator('asset_management.remove_asset',
                        text="",
                        icon='TRASH')

        layout.menu('ASSETM_MT_edit_asset',
                    text="",
                    icon='OUTLINER_DATA_GP_LAYER')

    layout.popover(panel='ASSETM_PT_options',
                   text="",
                   icon='PREFERENCES')


def _draw_import_button(context, layout, category, io_import, asset_type):
    """Function displaying the import button according the asset type"""
    io_objects = io_import.objects
    filepath = getattr(category.preview, 'preview')
    if filepath == 'NONE':
        filepath = ""
    if asset_type in ('assets', 'materials'):
        import_type = io_import.import_type.capitalize()

        if asset_type == 'assets' and io_objects.replace:
            op = layout.operator('asset_management.replace_asset',
                                 text="Replace object")
        else:
            operator = 'asset_management.import_{}{}'.format(
                    asset_type, "_edit" if context.mode == 'EDIT_MESH'
                    else "")
            op = layout.operator(operator,
                                 text=f"{import_type} {asset_type[:-1]}")

        op.filepath = filepath
        op.link = io_import.import_type == 'LINK'
        if asset_type == 'assets':
            op.object_as = category.preview.object_as

    if asset_type == 'scenes':
        layout.operator('asset_management.open_scene',
                        text="Open Blendfile").filepath=filepath

    if asset_type == 'hdri':
        layout.operator('asset_management.setup_environment').filepath\
            =filepath


def draw_preview_template_actions(context, layout, category):
    am = context.window_manager.asset_management
    io_import = am.io_import
    asset_type = LM.active_type.name
    path = category.path

    row = layout.row(align=True)
    row.scale_y = 1.2
    left = row.operator('asset_management.change_asset', text="",
                 icon='TRIA_LEFT')
    left.index = -1
    left.category_path = path

    _draw_import_button(context, row, category, io_import, asset_type)

    # if asset_type == 'assets' and \
    #         category != LM.active_type and \
    #         category.assets.active is not None and \
    #         category.assets.active.collections:
    #     row.prop(category.preview, 'object_as', text="", expand=True)
    if asset_type == 'assets':
        if category == LM.active_type:
            datablock = getattr(AmFilterSearchName, asset_type)
        else:
            datablock = category.assets

        if datablock.active is not None and datablock.active.collections:
            row.prop(category.preview, 'object_as', text="", expand=True)

    right = row.operator('asset_management.change_asset', text="",
                 icon='TRIA_RIGHT')
    right.index = 1
    right.category_path = path


def draw_template_preview(context, layout, category):
    prefs = addon_prefs()
    row = layout.row(align=True)
    col_preview = row.column()
    col_tool = row.column(align=True)
    col_preview.template_icon_view(
            category.preview,
            'preview',
            show_labels=prefs.interface.show_labels,
            scale=prefs.interface.preview_size,
            scale_popup=prefs.interface.popup_icon_size
            )
    draw_preview_template_actions(context, col_preview, category)
    if category == LM.active_category:
        draw_tool_template(context, col_tool)
    else:
        col_tool.label(icon='BLANK1')
    col_preview.separator()


def draw_template_pinned_categories(context, layout, pinned_categories):
    """Function displaying the previews of the pinned categories"""
    box = layout.box()
    row_template = box.row(align=True)
    pinned_col = row_template.column()
    flow = pinned_col.grid_flow(
            row_major=True, # Fill row by row, instead of column by column
            columns=0,
            even_columns=True, # All columns will have the same width
            even_rows=True, # All rows will have the same height
            align=False) # Align buttons to each other

    for cat in pinned_categories:
        col_template = flow.column()
        row_header = col_template.row(align=True)
        if hasattr(cat, 'pinned') and cat != LM.active_category:
            icon = 'PINNED' if cat.pinned else 'UNPINNED'
            row_header.operator('asset_management.toggle_pinned_category',
                         text="",
                         icon=icon,
                         emboss=False).category_path = cat.path

        if cat == LM.active_type:
            am = context.window_manager.asset_management
            row_header.prop(am, 'filter_search', text="", icon='VIEWZOOM')
            row_header.operator('asset_management.clear_filter_search',
                         text="",
                         icon='X')
        else:
            row_header.operator('asset_management.set_active_category',
                         text=cat.name,
                         emboss=cat == LM.active_category).path = cat.path
        row_header.label(icon='BLANK1')

        draw_template_preview(context, col_template, cat)


class ASSETM_PT_asset_management_panel(Panel):
    bl_label = "Asset Management"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AM"

    def _update_template(self, layout):
        if Updater.update_available:
            row = layout.row(align=True)
            row.operator('asset_management.open_preferences', text="",
                         icon='PREFERENCES')
            row.label(text="New update available")

    @property
    def poll_template_preview(self):
        library = LM.active_library
        return (library and library.asset_types and
                LM.category_to_move is None
                and LM.asset_to_move is None)

    def draw(self, context):
        prefs_interface = addon_prefs().interface
        layout = self.layout
        if bpy.app.version < (2, 93, 0):
            layout.label(text="This version of the addon", icon='ERROR')
            layout.label(text="only works with Blender 2.93+")
        else:
            am = context.window_manager.asset_management

            self._update_template(layout)
            if DEBUG:
                layout.operator('asset_management.debug')

            if am.edit_asset:
                row = layout.row()
                row.alignment = 'CENTER'
                row.label(text="----------- EDIT ASSET -----------")
                layout.separator()
                asset = LM.get_asset_from_path(bpy.data.filepath)
                layout.template_icon(icon_value=asset.icon_id,
                                     scale=prefs_interface.preview_size)
                layout.separator()
                row = layout.row(align=True)
                row.operator('asset_management.save_asset_changes')
                row.operator('wm.quit_blender', text="Cancel")

            else:
                export =\
                    [asset_type for asset_type in ('objects', 'materials', 'scenes')
                    if getattr(am.io_export, asset_type).display_panel]
                if export:
                    getattr(am.io_export, export[0]).draw(layout)

                else:
                    row_libraries = layout.row(align=True)
                    row_libraries.active = \
                        not bpy.types.ASSET_MANAGEMENT_OT_new_category.running()
                    row_libraries.scale_y = 1.1
                    row_libraries.prop(am, 'libraries', text="")
                    row_libraries.menu('ASSETM_MT_library_options', text="",
                                       icon='PREFERENCES')

                    if self.poll_template_preview:
                        am = context.window_manager.asset_management
                        row = layout.row(align=True)
                        if prefs_interface.asset_types_labels:
                            left_col = row.column(align=True)
                            left_col.scale_y = 1.2
                            right_col = row.column(align=True)
                            right_col.scale_y = 1.2

                            for i, aType in enumerate(
                                    LM.active_library.asset_types):
                                if i % 2 == 0:
                                    left_col.prop(am.asset_types,
                                                  aType,
                                                  icon=ASSET_TYPE[aType])
                                else:
                                    right_col.prop(am.asset_types,
                                                   aType,
                                                   icon=ASSET_TYPE[aType])

                        else:
                            row.alignment = 'CENTER'
                            row.scale_x = 1.2
                            for aType in LM.active_library.asset_types:
                                row.prop(am.asset_types, aType, icon=ASSET_TYPE[
                                    aType], icon_only=True)

                        io_import = am.io_import

                        col = layout.column(align=True)
                        col.separator()
                        if LM.active_type.name in ('assets', 'materials'):
                            layout.separator()
                            row = col.row(align=True)
                            row.scale_y = 1.2
                            row.prop(io_import,
                                     'import_type',
                                     text=" ",
                                     expand=True)
                        else:
                            row = layout.row()
                            row.label(text="", icon='BLANK1')

                        category = LM.active_category
                        pinned_categories = LM.pinned_categories()
                        if pinned_categories or am.filter_search:
                            if hasattr(category, 'assets') and \
                                    category.assets and \
                                    not category.pinned:
                                category.pinned = True
                                pinned_categories.insert(0, category)

                            if am.filter_search:
                                pinned_categories.insert(0, LM.active_type)

                            draw_template_pinned_categories(context,
                                                            col,
                                                            pinned_categories
                                                            )

                        else:
                            draw_template_preview(context, col, category)

                    if LM.asset_to_move:
                        layout.template_icon(LM.asset_to_move.icon_id, scale=5)
                        layout.label(text="Select the category to move the asset:")
                        layout.label(text=LM.asset_to_move.name)


class ASSETM_PT_environment_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AM"
    bl_label = "Am Environment"
    bl_parent_id = "ASSETM_PT_asset_management_panel"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return bpy.app.version >= (2, 93, 0) and LM.active_category is not None

    def draw(self, context):
        AM = context.window_manager.asset_management
        # preview = AM.previews.active
        preview = LM.active_category.preview.preview
        environment = AM.environment
        layout = self.layout

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator('asset_management.add_environment', text="Add world",
                     icon='ADD').filepath = preview if preview != 'NONE' \
            else ""
        row.operator('asset_management.remove_environment', text="Remove",
                     icon='X')
        col.prop(environment, 'am_worlds', text="")

        col_2 = layout.column(align=True)
        world = environment.am_worlds
        if world is not None:
            world_nodes = world.node_tree.nodes
            am_env_node = [node for node in world_nodes if node.name.startswith(
                    'AM_environment')]

            if am_env_node:
                env_node = am_env_node[0]
                nodes = env_node.node_tree.nodes
                # IMAGE
                box = col_2.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text="IMAGE")
                row = box.row(align=True)
                row.label(text="Rotation:")
                sub_col = row.column()
                sub_col.prop(nodes["Mapping"].inputs[2], "default_value",
                             text="")
                row = box.row(align=True)
                row.label(text="Projection:")
                row.prop(environment, "ibl_projection", text="")
                row = box.row(align=True)
                row.label(text="Blur:")
                row.prop(env_node.inputs[9], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Background visibility:")
                row.prop(environment, "background_visibility", text="")
                row = box.row(align=True)
                row.label(text="Background color:")
                row.prop(env_node.inputs[10], "default_value", text="")

                box = col_2.box()
                row = box.row(align=True)
                row.label(text="Gamma:")
                row.prop(env_node.inputs[0], "default_value", text="")

                # LIGHT
                box = col_2.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text="LIGHT")
                row = box.row(align=True)
                row.label(text="Strength:")
                row.prop(env_node.inputs[1], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Saturation:")
                row.prop(env_node.inputs[2], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Hue:")
                row.prop(env_node.inputs[3], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Mix Hue:")
                row.prop(env_node.inputs[4], "default_value", text="")

                # GLOSSY
                box = col_2.box()
                row = box.row()
                row.alignment = 'CENTER'
                row.label(text="GLOSSY")
                row = box.row(align=True)
                row.label(text="Strength:")
                row.prop(env_node.inputs[5], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Saturation:")
                row.prop(env_node.inputs[6], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Hue:")
                row.prop(env_node.inputs[7], "default_value", text="")
                row = box.row(align=True)
                row.label(text="Mix Hue:")
                row.prop(env_node.inputs[8], "default_value", text="")

            else:
                box = col_2.box()
                box.label(text="AM environment node not found")


class ASSETM_PT_options(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_label = "Options"

    def draw(self, context):
        am = context.window_manager.asset_management
        prefs = addon_prefs()
        data_type = LM.active_type.name
        io_import = am.io_import
        io_objects = io_import.objects
        io_materials = io_import.materials

        layout = self.layout
        layout.label(text="Options")

        if data_type == 'assets':
            layout.prop(io_objects, 'replace')
            layout.prop(io_objects, 'copy_scale')
            layout.prop(io_objects, 'use_existing_coll')

        if data_type == 'materials':
            layout.prop(io_materials, 'use_existing_material')

        layout.prop(prefs.import_export, 'lock_import')
        if data_type == 'assets':
            layout.label(text="Import behaviour:")
            layout.prop(prefs.import_export, 'object_import', text="")

        if data_type == 'materials':
            layout.label(text="Import behaviour:")
            layout.prop(prefs.import_export, 'material_import', text="")

        if data_type == 'scenes':
            layout.prop(prefs.import_export, 'load_ui')


class ASSETM_MT_edit_asset(Menu):
    """Edit asset menu"""
    bl_label = "Edit"

    def draw(self, context):
        am = context.window_manager.asset_management
        layout = self.layout
        layout.operator('asset_management.rename_asset', icon='TEXT')
        col = layout.column()
        col.active = hasattr(LM.active_category, 'assets') and \
                     len(LM.active_category.assets) != 0
        move_row = col.row()
        move_row.active = LM.asset_to_move is None
        move_row.prop(am, 'move_asset', icon='VIEW_PAN', toggle=False)
        if LM.active_type.name != 'hdri':
            edit_row = col.row()
            edit_row.active = LM.asset_to_edit is None
            edit_row.operator('asset_management.edit_asset',
                              icon='LOOP_BACK')


class ASSETM_UL_export_materials(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname):
        mat = item.material

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if mat:
                col = layout.column()
                row = col.row(align=True)
                row.prop(mat, 'name', text="", emboss=False,
                         icon_value=layout.icon(mat))
                row.prop(item, 'to_export', text="")
                if hasattr(LM.active_category, "assets"):
                    existing_files = [mat.name for mat in
                                  LM.active_category.assets]
                    if item.name in existing_files and item.to_export:
                        row2 = col.row(align=True)
                        split = row2.split(factor=0.05)
                        split.separator()
                        col2 = split.column()
                        col2.label(text=f"{item.name} already exists",
                                   icon='ERROR')
                        col2.prop(item, 'replace')
                        row = col2.row()
                        row.active = item.replace
                        row.prop(item, 'use_existing_thumb')


class ASSETM_UL_export_collections(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname):
        coll = item.collection

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if coll:
                col = layout.column()
                row = col.row(align=True)
                row.prop(coll, 'name', text="", emboss=False)
                row.prop(item, 'to_export', text="")


CLASSES = (ASSETM_UL_export_materials,
           ASSETM_PT_asset_management_panel,
           ASSETM_PT_options,
           ASSETM_PT_category_browser,
           ASSETM_PT_environment_panel,
           ASSETM_MT_edit_asset,
           ASSETM_MT_library_options,
           ASSETM_MT_category_options,
           ASSETM_UL_export_collections,
           ASSETM_OT_debug)


def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in CLASSES:
        unregister_class(cls)
