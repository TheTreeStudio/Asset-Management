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


import os

from .t3dn_bip import previews
from .ressources.constants import ICONS_PATH, MATERIAL_RENDER_SCENES


class AmIconCollection:

    def __init__(self):
        self._pcoll = previews.new(lazy_load=False)
        self._enum_items = []

        self._load_icons()

    @property
    def enum_items(self):
        return self._enum_items

    def get(self, key: str):
        return self._pcoll.get(key)

    def _load_icons(self):
        icons = [ico for ico in os.listdir(ICONS_PATH)]

        for ico_name in icons:
            if ico_name == 'default.bip':
                continue
            self._pcoll.load_safe(
                    ico_name[:-4], os.path.join(ICONS_PATH, ico_name), 'IMAGE')

        self._set_enum_items()

    def _set_enum_items(self):
        files = [file for file in os.listdir(MATERIAL_RENDER_SCENES)]
        self._enum_items.extend([
            (os.path.join(MATERIAL_RENDER_SCENES, file), file[:-6], "",
             self._pcoll.get(file[:-6]).icon_id, idx) for idx, file in
            enumerate(files)])

    def clear_icons(self):
        previews.remove(self._pcoll)


Icons = AmIconCollection()
