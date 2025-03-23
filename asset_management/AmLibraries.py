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
import shutil
from pathlib import Path

from .AmUtils import *
from .AmCore import AmAssets, AmAsset

from .ressources.constants import (ASSET_TYPE,
                                   AM_DATAS,
                                   ORDERED_TYPES,
                                   AM_UI_SETTINGS)
from .t3dn_bip import previews

class Library:

    def __init__(self, path):
        self._path = path

        self.asset_types = AssetTypeCollection(self)

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def path(self):
        return self._path


class AssetType:

    def __init__(self, name, parent):
        self._parent_library = parent
        self._name = name

        self.categories = CategoryCollection(self)
        self._active_category = None

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent_library

    @property
    def path(self):
        return os.path.join(self._parent_library.path, self._name)

    @property
    def active_category(self):
        return self._active_category

    @active_category.setter
    def active_category(self, category):
        previous_category = self.active_category

        am = bpy.context.window_manager.asset_management
        am_previews = am.previews
        if previous_category is not None and \
                hasattr(previous_category, 'pinned') and \
                not previous_category.pinned and \
                am_previews.get(previous_category.path):
            am_previews.remove(am_previews.find(previous_category.path))

        if category == self:
            active_preview = am_previews.get(f"{self._name}_filtered_preview")
            if active_preview is None:
                active_preview = am_previews.add()
                active_preview.name = f"{self._name}_filtered_preview"
        else:
            active_preview = am_previews.add()
            active_preview.name = category.path

        self._active_category = category

    @property
    def preview(self):
        am = bpy.context.window_manager.asset_management
        preview = am.previews.get(f"{self._name}_filtered_preview")
        if preview is None:
            preview = am.previews.add()
            preview.name = f"{self._name}_filtered_preview"
        return preview


class CategoriesCore(dict):

    def __init__(self, parent):
        dict.__init__(self)
        # The parent can be either an AssetType or a Category object
        self._parent = parent

    def _new(self, name):
        category = Category(name, self._parent)
        self[category.path] = category
        return category

    def _convert_blend_to_file(self, name):
        src = os.path.join(os.path.join(self._parent.path, name,
                                        'blends'))
        dst = os.path.join(os.path.join(self._parent.path, name,
                                        'files'))
        os.rename(src, dst)

    def add(self, name):
        """
        Add a new category
        :param name: String, name of the category
        :return: Object, created category
        """
        if os.path.exists(os.path.join(self._parent.path, name)):
            dirs = next(os.walk(os.path.join(self._parent.path, name)))[1]
            if "blends" in dirs:
                self._convert_blend_to_file(name)

        if name in ('files', 'blends', 'icons', 'favorites') or \
                name.startswith("TEX_"):
            return

        path = AmPath.get_folder(self._parent.path, name)
        category = self._new(name)

        dirs = next(os.walk(path))[1]
        for dir_ in dirs:
            category.categories.add(dir_)

        return category

    def remove(self, category):
        if category.categories:
            sub_categories = list(category.categories.values())
            for cat in sub_categories:
                category.categories.remove(cat)
        pcoll = category.assets.pcoll
        if pcoll is not None:
            previews.remove(pcoll)
        del self[category.path]
        del category

    @property
    def sorted(self):
        return AmPath.sort_path_by_name(self.keys())


class Category:
    def __init__(self, name, parent):
        self._name = name
        self._parent = parent
        self._categories = CategoriesCore(self)
        self.expanded = False
        self._pinned = False
        self._assets = AmAssets(self)

    @property
    def preview(self):
        am = bpy.context.window_manager.asset_management
        return am.previews.get(self.path)

    @property
    def active_asset(self):
        return self._assets.active

    def set_active_asset_from_path(self, path):
        asset = LibrariesManager.get_asset_from_path(self, path)
        self._assets.active = asset

    @property
    def name(self):
        return self._name

    @property
    def parent(self):
        return self._parent

    @property
    def path(self):
        return os.path.join(self._parent.path, self.name)

    @property
    def categories(self):
        return self._categories

    @property
    def pinned(self):
        return self._pinned

    @pinned.setter
    def pinned(self, status):
        if self._assets:
            am = bpy.context.window_manager.asset_management
            active_category = self.parent_asset_type.active_category
            pinned_count = len(LibrariesManager.pinned_categories())
            if active_category == self and \
                    active_category.pinned and \
                    pinned_count > 1:
                return

            self._pinned = status
            am_previews = am.previews
            if not status and \
                    active_category != self and \
                    am_previews.get(self.path):
                am_previews.remove(am_previews.find(self.path))
                if pinned_count == 2:
                    active_category.pinned = False
            if status and not am_previews.get(self.path):
                preview = am_previews.add()
                preview.name = self.path

    @property
    def is_expandable(self):
        return self._categories

    @property
    def assets(self):
        return self._assets

    @property
    def parent_asset_type(self):
        """
        Returns the AssetType object class of the asset
        @return: AssetType Object
        """
        category = self._parent
        while category.__class__.__name__ != 'AssetType':
            category = category.parent

        return category

    @property
    def parent_library(self):
        """
        Returns the Library object class of the asset
        @return: Library Object
        """
        return self.parent_asset_type.parent


class LibraryCollection(dict):

    def __init__(self):
        dict.__init__(self)
        self._active = None
        self._active_index = 0
        self._enum_items = []
        self.unvalid_libraries = []

    def _new(self, path):
        """
        Create a new instance of Library
        :param path: str, library path
        :return: instance of the created library
        """
        if not os.path.exists(path):
            self.unvalid_libraries.append(path)
            return
        else:
            new_lib = Library(path)
            self[path] = new_lib
            return self[path]

    def add(self, path):
        """
        Add a new library in the database
        :param path: String, library path
        """
        library = self._new(path)
        if library is not None:
            library.asset_types.load()
            self.active = library.path
            self.save()
            return library

    def remove(self, path):
        """
        Remove the library from the database
        :param path: String, path of the library to remove
        """
        library = self.get(path)
        if library is not None:
            for type_ in library.asset_types.values():
                for category in type_.categories.values():
                    pcoll = category.assets.pcoll
                    if pcoll is None:
                        continue
                    previews.remove(pcoll)
            library.asset_types.clear_types()
            del self[path]

            if self.keys():
                self.active = self.sorted_libraries[0]

    def rename(self, path, new_name):
        new_path = AmName.rename(path, new_name)
        self.add(new_path)
        self.remove(path)
        self.active = new_path
        return new_path

    def load(self):
        """
        Load the libraries from the database
        """
        self.clear()
        path = os.path.join(AM_DATAS, "libraries.json")
        if not os.path.exists(path):
            return

        libraries = AmJson.load_json_file(path)

        for lib_path in libraries:
            library = self._new(lib_path)
            if library is not None:
                library.asset_types.load()

        if self.keys():
            self.active = self.sorted_libraries[0]
            print("Asset Management libraries loaded")
            if self.unvalid_libraries:
                print("Some library paths are not valid:")
                for lib in self.unvalid_libraries:
                    print(f"\t{lib}")
                self.save()

        else:
            print("No valid library to load")

    def save(self):
        """
        Save the libraries in the database
        """
        # libraries = list(self.keys()) + self.unvalid_libraries
        libraries = list(self.keys())
        AmJson.save_as_json_file(
                os.path.join(AM_DATAS, "libraries.json"),
                libraries
                )

    @property
    def active(self):
        """
        Return the active library
        :return: Object, instance of the library
        """
        return self._active

    @active.setter
    def active(self, path):
        """
        Set the active library
        :param path:
        """
        if self.get(path):
            libraries = self.sorted_libraries
            idx = libraries.index(path)
            self._active_index = idx
            self._active = self[path]

    @property
    def active_index(self):
        return self._active_index

    @property
    def sorted_libraries(self):
        return AmPath.sort_path_by_name(self.keys())

    @property
    def enum_items(self):
        return self._enum_items

    def set_enum_items(self):
        self._enum_items.clear()
        if not self.keys():
            self._enum_items.extend([('NONE', "No valid libraries", "")])
        else:
            libraries = self.sorted_libraries
            self._enum_items.extend([
                (path, os.path.basename(path), "", 'FILE_FOLDER', i)
                for i, path in enumerate(libraries)
                ])

    def move(self, library, dst):
        """
        Move the selected  library to the targeted folder
        :param library: Object, library instance to be moved
        :param dst: String, folder path where to move the library
        """
        dirs = next(os.walk(dst))[1]
        valid_name = AmName.get_valid_name(library.name, dirs)
        full_path = os.path.join(dst, valid_name)
        shutil.move(self.active.path, full_path)
        self.remove(self.active.path)
        self.add(full_path)
        self.save()
        return full_path


class AssetTypeCollection(dict):

    def __init__(self, parent):
        dict.__init__(self)
        self._parent = parent
        self._active = None

    def _new(self, aType_id):
        new_type = AssetType(aType_id, self._parent)
        self[aType_id] = new_type
        return self[aType_id]

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, aType_id):
        if self.get(aType_id):
            self._active_index = self.sorted_types.index(aType_id)
            self._active = self[aType_id]

    def add(self, aType_id):
        AmPath.get_folder(self._parent.path, aType_id)
        aType = self._new(aType_id)
        aType.categories.load()
        return aType

    def load(self):
        self.clear()
        try:
            dirs = next(os.walk(self._parent.path))[1]
            for aType in ASSET_TYPE:
                if aType not in dirs:
                    continue
                aType = self._new(aType)
                aType.categories.load()

            if self.keys():
                self.active = self.sorted_types[0]
                for aType in self.values():
                    if not aType.categories:
                        # if no categories registred, we set the asset type as
                        # the active category
                        aType.categories.active = aType
                        continue
                    categories = aType.categories
                    sorted_ = categories.sorted
                    categories.active = categories.get(sorted_[0])
        except PermissionError:
            print(f"{self._parent.path}:\n\tYou don't seem to have the "
                  f"necessary rights on this folder.")
        except:
            print(f"{self._parent.path}:\n\tAn error undefined has occurred")

    def update(self):
        existing_types = os.listdir(self._parent.path)
        for type_ in existing_types:
            if not self.get(type_):
                aType = self.add(type_)
                aType.categories.active = aType

    @property
    def sorted_types(self):
        return [type_ for type_ in self.keys() if type_ in ORDERED_TYPES]

    @property
    def sorted_types(self):
        return [type_ for type_ in ORDERED_TYPES if self.get(type_)]

    def clear_types(self):
        for aType in self.values():
            del aType

        self.clear()


class CategoryCollection(CategoriesCore):

    @property
    def active(self):
        return self._parent.active_category

    @active.setter
    def active(self, category):
        self._parent.active_category = category

    def load(self):
        self.clear()

        categories = next(os.walk(self._parent.path))[1]
        for category in categories:
            self.add(category)

    @staticmethod
    def rename(category, new_name):
        parent = category.parent
        new_path = AmName.rename(category.path, new_name)
        valid_name = os.path.basename(new_path)
        new_cat = parent.categories.add(valid_name)
        parent.categories.remove(category)
        return new_cat

    def _get_expanded_categories(self, category, expanded_categories):
        if hasattr(category, 'expanded') and category.expanded:
            expanded_categories.append(category.path)
        for cat in category.categories.values():
            self._get_expanded_categories(cat,
                                          expanded_categories)

    def update(self):
        def _restore(category, pinned, expanded):
            category.pinned = category.path in pinned
            category.expanded = category.path in expanded
            if category.categories:
                for sub_category in category.categories.values():
                    _restore(sub_category, pinned, expanded)

        pinned_categories = [cat.path for
                             cat in LibrariesManager.pinned_categories()]
        expanded_categories = []
        for cat in self.values():
            self._get_expanded_categories(cat, expanded_categories)

        self.load()

        for category in self.values():
            _restore(category, pinned_categories, expanded_categories)


class AmLibrariesManager:

    def __init__(self):
        self._initialized = False
        self._libraries = LibraryCollection()
        self._category_to_move = None
        self._asset_to_move = None
        self._asset_to_edit = None
        self._back_to_previous = ""

    @property
    def libraries(self):
        return self._libraries

    @property
    def active_library(self):
        if self._libraries:
            return self._libraries.active
        return None

    @active_library.setter
    def active_library(self, library_path):
        if self._libraries.get(library_path):
            self._libraries.active = library_path

    @property
    def active_type(self):
        library = self.active_library
        if library is not None and library.asset_types:
            return library.asset_types.active
        return None

    @active_type.setter
    def active_type(self, aType_id):
        library = self.active_library
        if library is not None and library.asset_types and \
                library.asset_types.get(aType_id):
            library.asset_types.active = aType_id

    @property
    def active_category(self):
        aType = self.active_type
        if aType is not None:
            return aType.categories.active
        return None

    @active_category.setter
    def active_category(self, category):
        aType = self.active_type
        if aType is not None:
            aType.categories.active = category

    def get_library_from_path(self, path):
        library = [library for library in self.libraries.values() if
                   path.startswith(f"{library.path}{os.sep}")]

        return library[0] if library else None

    def get_asset_type_from_path(self, path, library=None):
        if library is None:
            library = self.get_library_from_path(path)

        if library is not None:
            a_type = Path(path.split(library.path)[-1]).parts[1]
            return library.asset_types.get(a_type)

        return

    def get_category_from_path(self, path, aType=None):
        if path in [f"{type_}_filtered_preview" for type_ in
                    ASSET_TYPE.keys()]:
            return self.active_type
        if aType is None:
            aType = self.get_asset_type_from_path(path)
        if aType.path == path:
            return aType

        if aType is not None:
            categories = path.split(aType.path + os.sep)[-1].split(os.sep)
            category = aType
            for category_name in categories:
                path = os.path.join(category.path, category_name)
                tmp_category = category.categories.get(path)
                if tmp_category is None:
                    break
                category = tmp_category

            return category

        return

    def get_asset_from_path(self, path, category=None):
        """
        Return the Object of the asset sought
        @param category: Object, the category in which to look the asset
        @param path: String, the path of the asset
        @return: Object
        """
        if category is None:
            cat_path = os.path.dirname(path)
            category = self.get_category_from_path(cat_path)

        if category is not None:
            asset = [asset for asset in category.assets if asset.path == path]
            return asset[0] if asset else None

        return


    def pinned_categories(self, category=None, pinned=None):
        if category is None:
            if pinned is None:
                pinned = []
            for cat in self.active_type.categories.values():
                self.pinned_categories(cat, pinned)
        else:
            if category.pinned:
                pinned.append(category)

            for cat in category.categories.values():
                self.pinned_categories(cat, pinned)

        return pinned

    def expand_hierarchy_visibility(self, category):
        if hasattr(category.parent, 'expanded'):
            category.parent.expanded = True
            self.expand_hierarchy_visibility(category.parent)

    def _get_categories(self, category, datas):
        """Function call """
        if category.categories:
            for path, sub_category in category.categories.items():
                if sub_category.pinned or \
                        (sub_category.active_asset is not None and
                        sub_category.assets.active_index):
                    datas[path] = {
                        'pinned': sub_category.pinned,
                        'asset_index': sub_category.assets.active_index}
                self._get_categories(sub_category, datas)

    @property
    def category_to_move(self):
        return self._category_to_move

    @category_to_move.setter
    def category_to_move(self, category):
        if category is None:
            self._category_to_move = None
        elif isinstance(category, Category):
                self._category_to_move = category

    def move_category(self, to_category, category=None):
        """
        Moves the selected  category into the targeted one
        :param to_category: Object, Category instance where to move
        :param category: Object, Category instance to move
        """
        if category is None:
            category = self._category_to_move
        library = to_category.parent_library if isinstance(
                to_category, Category) else to_category.parent
        aType = category.parent_asset_type
        asset_type_coll = to_category.parent_library.asset_types if isinstance(
                to_category, Category) else to_category.parent.asset_types
        to_aType = to_category.parent_asset_type if isinstance(
                to_category, Category) else to_category
        # if the asset type doesn't exists in the targeted library,
        # we have to create it.
        if not asset_type_coll.get(aType.name):
            asset_type_coll.add(aType.name)
            asset_type_coll.active = aType.name
            asset_type_coll.active.categories.active = self.active_type

        dirs = next(os.walk(to_category.path))[1]
        valid_name = AmName.get_valid_name(category.name, dirs)
        dst = os.path.join(to_category.path, valid_name)
        shutil.move(category.path, dst)
        category.parent.categories.remove(category)
        moved_category = to_category.categories.add(valid_name)
        to_aType.categories.active = moved_category
        moved_category.parent.expanded = True
        moved_category.set_active_asset_from_path(
                moved_category.preview.preview)

        if library != category.parent_library:
            parent = category.parent
            if parent.categories:
                cat = parent.categories.get(parent.categories.sorted[0])
                aType.categories.active = cat
            else:
                aType.categories.active = parent

        self.category_to_move = None

    @property
    def asset_to_move(self):
        return self._asset_to_move

    @asset_to_move.setter
    def asset_to_move(self, asset):
        if asset is None:
            self._asset_to_move = None
        elif isinstance(asset, AmAsset):
            self._asset_to_move = asset

    def move_asset(self, to_category, asset=None):
        """
        Moves the asset in the targeted category
        :param to_category: Category where to move
        :param asset: Object, Category instance to be moved
        """
        if asset is None:
            asset = self._asset_to_move

        # if the asset's name already exists in the targeted category,
        # we have to increment it
        existing = [asset.name for asset in to_category.assets]
        asset_name = AmName.get_valid_name(self.asset_to_move.name, existing)

        filename = f"{asset_name}{os.path.splitext(asset.filename)[-1]}"
        icon_filename = f"{asset_name}{os.path.splitext(asset.icon_name)[-1]}"
        dst_asset_dir, dst_icon_dir = AmPath.get_export_dirs(
                to_category.path, asset.from_root)

        shutil.move(asset.path, os.path.join(dst_asset_dir, filename))
        shutil.move(asset.icon_path, os.path.join(dst_icon_dir, icon_filename))
        if asset.TEX_path is not None:
            TEX_folder = f"TEX_{asset.name}"
            shutil.move(asset.TEX_path, os.path.join(dst_asset_dir,
                                                     TEX_folder))

        moved_asset = to_category.assets.add(filename,
                                             from_root=asset.from_root)
        if to_category.assets.pcoll is not None:
            moved_asset.load_icon()
        to_category.assets.active = moved_asset

        # By moving the asset, the old category no longer has an active
        # asset, so one must be defined
        assets = asset.parent.assets
        assets.remove_asset(asset, keep_icon=False)
        assets.active = assets.sorted[0] if assets else None

        self.asset_to_move = None

    @property
    def asset_to_edit(self):
        return self._asset_to_edit

    def set_asset_to_edit(self, asset, path=""):
        if asset is None:
            self._asset_to_edit = None
            self._back_to_previous = ""
        else:
            self._asset_to_edit = asset
            self._back_to_previous = path


    def save_settings(self):
        if self.active_library is not None:
            datas = {'active_library': self.active_library.path}
            for lib_path, library in self.libraries.items():
                aTypes = library.asset_types
                datas[lib_path] = {'active_type': aTypes.active.name,
                                   'assets_type': {}
                                   }

                data_types = datas[lib_path]['assets_type']
                for id, atype in aTypes.items():
                    data_types[id] = {
                        'active_category': atype.active_category.path,
                        'categories': {}
                        }
                    data_categories = data_types[id]['categories']
                    self._get_categories(atype, data_categories)

            AmJson.save_as_json_file(AM_UI_SETTINGS, datas)

    def load_settings(self):
        datas = AmJson.load_json_file(AM_UI_SETTINGS)
        if datas is not None:
            for lib_path, am_library in self.libraries.items():
                library = datas.get(lib_path)

                if library is None:
                    print(f"Error with library: {lib_path}\nThe path is not "
                          f"valid")
                    continue

                aTypes = am_library.asset_types

                # setup the active type
                if library.get('active_type') and \
                        aTypes.get(library['active_type']):
                    aTypes.active = library['active_type']

                for id, aType in aTypes.items():
                    data_type = library['assets_type'].get(id)
                    if data_type is None:
                        continue

                    # setup the active category
                    if data_type.get('active_category'):
                        active_category = self.get_category_from_path(
                                data_type['active_category'], aType)
                        if active_category is not None:
                            aType.active_category = active_category
                            self.expand_hierarchy_visibility(active_category)

                    data_categories = data_type['categories']
                    for path, values in data_categories.items():
                        if not os.path.exists(path):
                            continue
                        amCategory = self.get_category_from_path(path, aType)
                        amCategory.pinned = values['pinned']
                        # min function because an asset may have been
                        # deleted manually which could make the saved index
                        # erroneous in case there are less assets
                        amCategory.assets.active = amCategory.assets.sorted[
                            min(values['asset_index'],
                                len(amCategory.assets)-1)]

    def _clear_preview_collections(self, category):
        if category.assets.pcoll is not None:
            previews.remove(category.assets.pcoll)
        if category.categories:
            for cat in category.categories.values():
                self._clear_preview_collections(cat)

    def clear_preview_collections(self):
        for lib in self.libraries.values():
            for _type in lib.asset_types.values():
                for cat in _type.categories.values():
                    self._clear_preview_collections(cat)


LibrariesManager = AmLibrariesManager()
