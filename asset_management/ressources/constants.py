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

from pathlib import Path

ADDON_PATH = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]

AM_DATAS = os.path.join(Path.home(), ".AssetManagement")

RESSOURCES_PATH = os.path.dirname(__file__)

ICONS_PATH = os.path.join(RESSOURCES_PATH, 'icons')

THUMBNAILERS_DIR = os.path.join(RESSOURCES_PATH, "thumbnailers")

AM_UI_SETTINGS = os.path.join(AM_DATAS, "ui_settings.json")

AM_PRESET_PATH = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets",
                "asset_management"
                )

NODE_ENVIRONMENT = os.path.join(RESSOURCES_PATH, "node_environment.blend")

SUPPORTED_FILES = ('.blend', '.exr', '.hdr')

SUPPORTED_ICONS = ('.jpg', '.jpeg', '.png', '.bip')

ASSET_TYPE = {'assets': 'MESH_MONKEY',
              'scenes': 'SCENE_DATA',
              'materials': 'MATERIAL_DATA',
              'hdri': 'IMAGE_BACKGROUND'
              }

ORDERED_TYPES = ('assets', 'scenes', 'materials', 'hdri')

WARNING_REMOVE_MESSAGE = {'HD': ("The active {} will be removed from "
                                 "your hard drive.",
                                 "All the content will be definitively lost.",
                                 "Please, enter \"YES\" to enable the validation."
                                 ),
                          'DB': ("The active library will be removed",
                                 "from the addon database."
                                 )
                          }

OLD_LIBRARIES_INSTRUCTIONS = "To add your old 2.79 libraries, select the " \
                             "file \"custom_filepath\" that you'll find by " \
                             "following the path: " \
                             "your_old_library/extra_files/custom_filepaths"

_BACKGROUND_STUFF = os.path.join(ADDON_PATH, 'background_stuff')

OBJECT_POST_PROCESS = os.path.join(_BACKGROUND_STUFF,
                                   'objects_post_processing.py')

OBJECT_THUMBNAILER = os.path.join(_BACKGROUND_STUFF,
                                     'objects_thumbnailer.py')

OBJECT_RENDER_SCENE = os.path.join(THUMBNAILERS_DIR,
                                   'object_files', 'object_render_scene.blend')

MATERIAL_POST_PROCESS = os.path.join(_BACKGROUND_STUFF,
                                     'materials_post_processing.py')

MATERIALS_THUMBNAILER = os.path.join(_BACKGROUND_STUFF,
                                     'materials_thumbnailer.py')

MATERIAL_RENDER_SCENES = os.path.join(THUMBNAILERS_DIR, "material_files")

SCENE_POST_PROCESS = os.path.join(_BACKGROUND_STUFF,
                                  'scenes_post_processing.py')

SETUP_EDIT_ASSET_SCENE = os.path.join(_BACKGROUND_STUFF,
                                     'setup_edit_asset_scene.py')

IBL_THUMBNAILER = os.path.join(_BACKGROUND_STUFF, 'ibl_thumbnailer.py')

RENAME_MATERIAL = os.path.join(_BACKGROUND_STUFF, 'rename_material.py')

RENAME_ASSET = os.path.join(_BACKGROUND_STUFF, 'rename_asset.py')
