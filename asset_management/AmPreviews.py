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

from bpy.utils import register_class, unregister_class
from bpy.types import PropertyGroup
from bpy.props import EnumProperty

from .AmLibraries import LibrariesManager as LM
from .AmUtils import addon_prefs, minimum_blender_version
from .AmCore import AmFilterSearchName


def get_preview_index(self):
    if self.name.endswith("_filtered_preview"):
        name = self.name.split("_filtered_preview")[0]
        filter = getattr(AmFilterSearchName, name)
        if filter is None:
            return 0
        return filter.active_index

    category = LM.get_category_from_path(self.name)
    if hasattr(category, 'assets'):
        return category.assets.active_index
    return 0


def set_preview_index(self, value):
    if self.name.endswith("_filtered_preview"):
        name = self.name.split("_filtered_preview")[0]
        filter = getattr(AmFilterSearchName, name)
        if filter is not None and filter.assets:
            filter.active = filter.sorted[value]
    else:
        category = LM.get_category_from_path(self.name)
        category.assets.active = category.assets.sorted[value]


def preview_enum_items(self, context):
    if self.name.endswith("_filtered_preview"):
        name = self.name.split("_filtered_preview")[0]
        filter = getattr(AmFilterSearchName, name)
        if filter is None:
            return [('NONE', "None", "")]
        return filter.enum_items

    category = LM.get_category_from_path(self.name)
    if hasattr(category, 'assets'):
        return category.assets.enum_items
    return [('NONE', "None", "")]


def _get_operator(self, context, asset_type, filepath, link):

    operators = {
        'assets': ("import_assets", {"filepath":filepath,
                                     "link":link,
                                     "object_as":self.object_as}),
        'assets_edit': ("import_assets_edit", {"filepath":filepath,
                                               "link":link,
                                               "object_as":self.object_as}),
        'replace': ("replace_asset", {"filepath":filepath,
                                      "link":link}),
        'materials': ("import_materials", {"filepath":filepath,
                                           "link":link}),
        'materials_edit': ("import_materials_edit", {"filepath":filepath,
                                                     "link":link}),
        'scenes': ("open_scene", {"filepath":filepath}),
        'hdri': ("setup_environment", {"filepath":filepath}),
        }

    edit = "_edit" if context.mode == 'EDIT_MESH' and  asset_type in (
        'assets', 'materials') else ""
    return operators[f"{asset_type}{edit}"]


def _override(context):
    override = None
    window = context.window
    screen = window.screen
    for area in screen.areas:
        if area.type != 'VIEW_3D':
            continue
        for region in area.regions:
            if region.type == 'WINDOW':
                override = {'window': window,
                            'screen': screen,
                            'area': area,
                            'region': region}
                break

    return override


def import_from_enum_preview(self, context):
    am = context.window_manager.asset_management
    prefs = addon_prefs()
    filepath = self.preview

    if not prefs.import_export.lock_import and filepath != 'NONE':
        asset_type = LM.active_type.name
        io_import = am.io_import
        io_objects = io_import.objects
        filepath = self.preview
        link = io_import.import_type == 'LINK'

        if asset_type == 'assets' and io_objects.replace:
            asset_type = 'replace'

        operator, args = _get_operator(self, context, asset_type, filepath,
                                       link)

        if getattr(
                bpy.types, f"ASSET_MANAGEMENT_OT_{operator}").poll(context):

            if asset_type in ('assets', 'materials'):
                override = _override(context)
                if override is not None:
                    if minimum_blender_version(4,0,0):
                        with context.temp_override(**override):
                            getattr(bpy.ops.asset_management, operator)(
                                    'INVOKE_DEFAULT',
                                    **args)
                    else:
                        getattr(bpy.ops.asset_management, operator)(
                                override,
                                'INVOKE_DEFAULT',
                                **args)
            else:
                getattr(bpy.ops.asset_management, operator)(**args)


class AssetManagementPreviews(PropertyGroup):
    preview: EnumProperty(name="Asset Preview",
                          items=preview_enum_items,
                          get=get_preview_index,
                          set=set_preview_index,
                          update=import_from_enum_preview
                          )

    object_as: EnumProperty(
            name="Import object as",
            items=(
                ('OBJECTS', 'Objects', "Import objects", 'OBJECT_DATAMODE', 0),
                ('COLLECTIONS', 'Collections', "Import collections",
                 'OUTLINER_COLLECTION', 1)),
            default='OBJECTS'
            )


CLASSES = [AssetManagementPreviews]

def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        unregister_class(cls)
