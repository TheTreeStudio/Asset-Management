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

bl_info = {
    "name": "Asset Management",
    "description": "blender4.4兼容性修复（20250322）",
    "author": "Legigan Jeremy AKA Pistiwique, Stephen Leger and Cedric "
              "Lepiller aka Pitiwazou","某科学的大树"
    "version": (2, 7, 7),
    "blender": (2, 93, 0),
    "location": "View3D",
    "doc_url": "http://blscripts.com/asset_management_doc",
    "tracker_url": "https://discord.gg/ctQAdbY",
    "category": "Object"
    }


if "bpy" in locals():
    import importlib
    reloadable_modules = [
        "preferences",
        "properties",
        "AmLibraries",
        "AmIoIbls",
        "AmIoMaterials",
        "AmIoObjects",
        "AmIoScenes",
        "AmPresets",
        "AmLibrariesOps",
        "ui",
        "operators"
        ]
    for module in reloadable_modules:
        if module in locals():
            importlib.reload(locals()[module])


import bpy
import os
import shutil
import atexit

from bpy.app import handlers

from . import (
    preferences,
    properties,
    AmLibrariesOps,
    AmImportExport,
    ui,
    AmTools
    )

from .preferences.addon_updater import Updater
from .AmIcons import Icons
from .AmLibraries import LibrariesManager as LM
from .ressources.constants import AM_PRESET_PATH, AM_DATAS
from .AmUtils import AddonKeymaps, addon_prefs


@handlers.persistent
def libraries_loader(scene):
    Updater.load_json_file()
    # The handler is launched when creating a new scene or opening a .blend
    # but also after launching the register function when starting Blender (
    # the register function is also launched when activating the addon but not
    # the handler. This is why the libraries must also be loaded from the
    # register function).
    # When starting Blender, it is not necessary to load the libraries via the
    # handler because the register function takes care of this. We will
    # therefore check if the class has been initialized from the handler. If
    # not,  it means that we have just started Blender and that the register
    # function has done its job. So there is no need to load the libraries
    # from the handler.
    if LM.libraries.keys() and not LM._initialized:
        LM._initialized = True
    else:
        LM.libraries.load()

    if LM.libraries:
        LM.libraries.active = LM.libraries.sorted_libraries[0]
        LM.load_settings()


def save_settings():
    LM.save_settings()


def register_handlers():
    if os.path.exists(AM_PRESET_PATH):
        if not os.path.exists(AM_DATAS):
            shutil.move(AM_PRESET_PATH, AM_DATAS)

    if not os.path.exists(AM_DATAS):
        os.makedirs(AM_DATAS)

    if hasattr(bpy.context.window_manager, "asset_management"):
        Updater.async_check_update(
                check_update=addon_prefs().addon_pref.check_update)

    if libraries_loader in handlers.load_post:
        handlers.load_post.remove(libraries_loader)

    handlers.load_post.append(libraries_loader)

    if not LM.libraries.keys():
        LM.libraries.load()
        LM.load_settings()


def unregister_handlers():
    if libraries_loader in handlers.load_post:
        handlers.load_post.remove(libraries_loader)


def register():
    preferences.register()
    properties.register()
    AmLibrariesOps.register()
    AmImportExport.register()
    register_handlers()
    ui.register()
    AmTools.register()
    atexit.register(save_settings)

    AddonKeymaps.new_keymap('IBL Manipulate',
                            'asset_management.ibl_manipulate',
                            None, '3D View Generic', 'VIEW_3D', 'WINDOW',
                            'MIDDLEMOUSE', 'PRESS', True, True, False, 'NONE'
                            )

    AddonKeymaps.register_keymaps()


def unregister():
    AddonKeymaps.unregister_keymaps()

    AmTools.unregister()
    ui.unregister()
    unregister_handlers()
    AmLibrariesOps.unregister()
    AmImportExport.unregister()
    properties.unregister()
    preferences.unregister()
    Icons.clear_icons()
    LM.clear_preview_collections()