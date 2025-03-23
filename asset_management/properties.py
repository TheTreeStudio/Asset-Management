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
from bpy.props import (PointerProperty,
                       EnumProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty)

from . import AmIoProps
from . import AmPreviews
from .AmLibraries import LibrariesManager as LM
from .AmCore import AmFilterSearchName


def update_projection(self, context):
    world = context.scene.world
    nodes = world.node_tree.nodes
    am_env_node = [node for node in nodes if node.name.startswith(
            'AM_environment')]
    if am_env_node:
        env_node = am_env_node[0].node_tree.nodes.get("Environment")
        reflexion_node = am_env_node[0].node_tree.nodes.get("Reflexion")
        env_node.projection = reflexion_node.projection = self.ibl_projection


def update_background_visibility(self, context):
    if self.background_visibility != 'TRANSPARENT':
        world = context.scene.world
        nodes = world.node_tree.nodes
        am_env_node = [node for node in nodes if node.name.startswith(
                'AM_environment')]
        if am_env_node:
            IBL_tool = am_env_node[0].node_tree.nodes.get("IBL_Tool")
            IBL_tool.node_tree.nodes["toggle_visibility"].inputs[
                0].default_value = self.background_visibility == 'IBL'

    context.scene.render.film_transparent = self.background_visibility \
                                                == 'TRANSPARENT'


def update_active_world(self, context):
    if self.am_worlds is None:
        world = bpy.data.worlds.get('World')
        context.scene.world = world
    else:
        context.scene.world = self.am_worlds


def environment_poll(self, am_worlds):
    valid_worlds = [world for world in bpy.data.worlds for node in
                    world.node_tree.nodes if
                    node.name.startswith('AM_environment')]

    return am_worlds in valid_worlds


class AssetManagementEnvironment(PropertyGroup):

    ibl_projection: EnumProperty(
            name="Projection",
            items=(("EQUIRECTANGULAR", "Equirectangular",
                    "Equirectangulare or latitude-longitude projection"),
                   ("MIRROR_BALL", "Mirror Ball", "Projection of an "
                                                  "orthographic photo of a "
                                                  "mirror ball")
                   ),
            default="EQUIRECTANGULAR",
            description="Projection of the input image",
            update=update_projection
            )

    background_visibility: EnumProperty(
            name="Visibility",
            items=(('IBL', "IBL", ""),
                   ('TRANSPARENT', "Transparent", ""),
                   ('BACKGROUND', "Background", "")),
            default='IBL',
            description="Set the background visibility of the ibl",
            update=update_background_visibility
            )

    am_worlds: PointerProperty(
            name="Am Worlds",
            type=bpy.types.World,
            update=update_active_world,
            poll=environment_poll
            )


def libraries_enum_items(self, context):
    LM.libraries.set_enum_items()
    return LM.libraries.enum_items


def get_active_library(self):
    return LM.libraries.active_index


def set_active_library(self, value):
    if LM.libraries and not bpy.types.ASSET_MANAGEMENT_OT_new_category\
            .running():
        LM.active_library = LM.libraries.sorted_libraries[value]

        if LM.category_to_move is not None and \
            LM.active_library.asset_types.get(
                    LM.category_to_move.parent_asset_type.name):
            index = LM.active_library.asset_types.sorted_types.index(
                    LM.category_to_move.parent_asset_type.name)
            LM.active_type = \
                LM.active_library.asset_types.sorted_types[index]


def get_active_type(attr):
    def get(self):
        return attr == LM.active_type.name
    return get


def set_active_type(attr):
    def set(self, value):
        if value and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running():
            LM.active_type = attr
        return None
    return set


def asset_type_enum_items(self, context):
    library = LM.libraries[self.libraries]
    library.asset_types.set_enum_items()
    return library.asset_types.enum_items


def get_category_status(self):
    return LM.category_to_move is not None


def set_category_status(self, value):
    if value and LM.category_to_move is None:
        LM.category_to_move = LM.active_category


def get_asset_status(self):
    return LM.asset_to_move is not None


def set_asset_status(self, value):
    if value and LM.asset_to_move is None:
        LM.asset_to_move = LM.active_category.assets.active


class AssetTypesItems(PropertyGroup):
    assets: BoolProperty(
            name='Assets',
            default=True,
            get=get_active_type("assets"),
            set=set_active_type("assets")
            )

    materials: BoolProperty(
            name='Materials',
            default=False,
            get=get_active_type("materials"),
            set=set_active_type("materials")
            )

    scenes: BoolProperty(
            name='Scenes',
            default=False,
            get=get_active_type("scenes"),
            set=set_active_type("scenes")
            )

    hdri: BoolProperty(
            name='IBL',
            default=False,
            get=get_active_type("hdri"),
            set=set_active_type("hdri")
            )


def get_tags(self):
    aType = LM.active_type.name
    filter = getattr(AmFilterSearchName, aType)
    return ", ".join(filter.tags)


def set_tags(self, tags):
    aType = LM.active_type.name
    filter = getattr(AmFilterSearchName, aType)
    return setattr(filter, "tags", tags)


def update_search(self, context):
    aType = LM.active_type.name
    filter = getattr(AmFilterSearchName, aType)
    filter.update_assets(LM.libraries.values())

    pinned_categories = LM.pinned_categories()
    if len(pinned_categories) == 1 and LM.active_category == \
            pinned_categories[0]:
        pinned_categories[0].pinned = False
        
    context.area.tag_redraw()


class AssetManagementProperties(PropertyGroup):

    libraries: EnumProperty(
            name="Libraries",
            items=libraries_enum_items,
            get=get_active_library,
            set=set_active_library,
            description="List of the valid libraries",
            )

    asset_types: PointerProperty(type=AssetTypesItems)

    category_name: StringProperty(
            name="Category name",
            default="",
            description="Name of the new category"
            )

    previews: CollectionProperty(type=AmPreviews.AssetManagementPreviews)

    filter_search: StringProperty(
            name="Search filter",
            default="",
            description="Filter by name. Support ',' separator for multiple "
                        "filters",
            get=get_tags,
            set=set_tags,
            update=update_search
            )

    io_import: PointerProperty(type=AmIoProps.AmIoImport)

    io_export: PointerProperty(type=AmIoProps.AmIoExport)

    environment: PointerProperty(type=AssetManagementEnvironment)

    move_category: BoolProperty(
            name="Move category",
            default=False,
            get=get_category_status,
            set=set_category_status)

    move_asset: BoolProperty(
            name="Move asset",
            default=False,
            get=get_asset_status,
            set=set_asset_status)

    edit_asset: BoolProperty(
            name="Edit asset",
            default=False)


CLASSES = [
    AssetTypesItems,
    AssetManagementEnvironment,
    AssetManagementProperties
    ]


def register():
    AmIoProps.register()
    AmPreviews.register()

    for cls in CLASSES:
        register_class(cls)

    bpy.types.WindowManager.asset_management = PointerProperty(
            name="Asset Management Properties",
            description="",
            type=AssetManagementProperties
            )


def unregister():
    del bpy.types.WindowManager.asset_management

    for cls in CLASSES:
        unregister_class(cls)

    AmPreviews.unregister()
    AmIoProps.unregister()
