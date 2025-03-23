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
import re

from mathutils import Vector

from .AmUtils import (AmName,
                      AmPath,
                      AmBackgroundProcessor,
                      minimum_blender_version,
                      addon_prefs)
from .ressources.constants import (SUPPORTED_ICONS,
                                   NODE_ENVIRONMENT,
                                   SUPPORTED_FILES,
                                   RENAME_MATERIAL,
                                   RENAME_ASSET,
                                   ICONS_PATH)

from .t3dn_bip import previews


ZERO = Vector()


class AmAsset:

    def __init__(self, parent, filename, from_root):
        self._parent = parent
        self._filename = filename
        self._name = os.path.splitext(self._filename)[0]
        self._from_root = from_root
        self._collections = None

    @property
    def collections(self):
        aType = self.parent_asset_type.name
        if aType != 'assets':
            print(f"Not supported for the asset type {aType}")
            return
        if self._collections is None:
            with bpy.data.libraries.load(self.path) as (data_from,
                                                            data_to):
                self._collections = [coll for coll in data_from.collections]

        return self._collections

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        ext = os.path.splitext(self._filename)[-1]
        self._filename = f"{new_name}{ext}"
        self._name = new_name

    @property
    def filename(self):
        return self._filename

    @property
    def parent(self):
        return self._parent

    @property
    def from_root(self):
        return self._from_root

    @property
    def id(self):
        """
        Return the asset identifier.
        His name if the asset have been registered at the root of the
        category or 'files/self._name if it have been registered in a 'file' folder.
        @return: String
        """
        return self._filename if self._from_root else os.path.join("files",
                                                               self._filename)
    @property
    def path(self):
        return os.path.join(self._parent.path, self.id)

    @property
    def dir_path(self):
        return os.path.dirname(self.path)

    @property
    def icon_dir(self):
        return self._parent.path if self._from_root else os.path.join(
                self._parent.path, "icons")

    @property
    def icon_name(self):
        thumb = [ico for ico in os.listdir(self.icon_dir) if ico.endswith(
                SUPPORTED_ICONS) and os.path.splitext(ico)[0] == self.name]

        bip_thumb = f"{self.name}.bip"
        if bip_thumb in thumb:
            return bip_thumb

        return thumb[0] if thumb else None

    @property
    def icon_path(self):
        icon_name = self.icon_name
        if icon_name is not None:
            return os.path.join(self.icon_dir, icon_name)
        return os.path.join(ICONS_PATH, 'default.bip')

    @property
    def icon_id(self):
        pcoll = self._parent.assets.pcoll
        icon = pcoll.get(self.id)
        if icon is not None:
            return icon.icon_id
        return self.load_icon()

    def load_icon(self):
        pcoll = self._parent.assets.pcoll
        icon = pcoll.load_safe(str(self.id), str(self.icon_path), 'IMAGE')
        return icon.icon_id

    @property
    def TEX_path(self):
        """
        Return the path of the TEX_ folder if exists
        @return: String, path
        """
        root, dirs, files = next(os.walk(self.dir_path))
        TEX_folder = f"TEX_{self.name}"
        if TEX_folder in dirs:
            return os.path.join(self.dir_path, TEX_folder)
        return None

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


class AmAssets(list):

    def __init__(self, parent):
        list.__init__(self)
        _icon_size = addon_prefs().addon_pref.icon_size

        self._parent = parent
        self._active = None
        self._active_index = 0
        self._enum_items = []
        self._pcoll = previews.new(max_size=(int(_icon_size),
                                             int(_icon_size)))
        self._asset_to_move = None

        self._load_files()

    def _load_files(self, from_root=True):
        path = self._parent.path if from_root else os.path.join(
                self._parent.path, "files")
        root, dirs, files = next(os.walk(path))
        for file in files:
            self.add(file, from_root)

        if "files" in dirs and "icons" in dirs:
            self._load_files(from_root=False)

        if self:
            self._active = self.sorted[self._active_index]

    @property
    def enum_items(self):
        self._enum_items.clear()
        assets = self.sorted

        if not assets:
            return [('NONE', "None", "")]

        self._enum_items.extend(
                [(asset.path, asset.name, asset.path, asset.icon_id,
                  idx) for idx, asset in enumerate(assets)])

        return self._enum_items

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, asset):
        if asset is not None and os.path.exists(asset.path):
            idx = self.sorted.index(asset)
            self._active = asset
            self._active_index = idx
        else:
            self._active = None
            self._active_index = 0

    @property
    def active_index(self):
        return self._active_index

    @property
    def pcoll(self):
        if self._pcoll is None:
            icon_size = addon_prefs().addon_pref.icon_size
            self._pcoll = previews.new(max_size=(int(icon_size),
                                                 int(icon_size)))
        return self._pcoll

    def update(self):
        self.clear()
        if self._pcoll is not None:
            previews.remove(self._pcoll)
        self._load_files()

    def add(self, filename, from_root):
        """
        Function to add a new asset in the library
        @param filename: String, the filename of the asset we want to add
        @param from_root: Bool, If this option is enabled, the created icon
        will not be placed in an 'icons' folder but will be at the same
        level as the asset file
        @return:
        """
        if os.path.splitext(filename)[-1].lower() in SUPPORTED_FILES:
            AmPath.get_export_dirs(self._parent.path, from_root)
            file = AmAsset(self._parent, filename, from_root)
            self.append(file)
            return file
        return None

    def remove_asset(self, asset, keep_icon=False):
        """
        Function to delete an asset and its related texture folder
        @param asset: Asset instance, instance of the asset we want to delete
        @param keep_icon: Bool, if this option is enabled, the icon
        associated with the asset will be deleted
        @return:
        """

        TEX_folder = asset.TEX_path
        if TEX_folder is not None:
            AmPath.remove_tree(TEX_folder)

        AmPath.remove_file(asset.path, output=True)
        self.remove(asset)

        default_icon = os.path.join(ICONS_PATH, "default.bip")
        if not keep_icon and asset.icon_path != default_icon:
            AmPath.remove_file(asset.icon_path, output=False)
            self._pcoll.delete_item(asset.id)

    def rename(self, asset, new_name):
        old_name = asset.name
        ext = os.path.splitext(asset.filename)[-1]
        TEX_folder = asset.TEX_path

        if TEX_folder is not None:
            os.rename(TEX_folder, os.path.join(asset.dir_path,
                                               f"TEX_{new_name}"))
        os.rename(asset.path, os.path.join(asset.dir_path, f"{new_name}{ext}"))
        icon_name = asset.icon_name
        if icon_name is not None:
            icon_ext = os.path.splitext(icon_name)[-1]
            os.rename(asset.icon_path,
                      os.path.join(asset.icon_dir, f"{new_name}{icon_ext}"))

        self._pcoll.delete_item(asset.id)
        asset.name = new_name
        asset.load_icon()

        if asset.parent_asset_type.name == 'materials':
            post_processing = AmBackgroundProcessor()
            for line in post_processing.run_process(
                    RENAME_MATERIAL,
                    asset.path,
                    True,
                    f"old_name:{old_name}",
                    f"new_name:{new_name}",
                    f"package:{__package__}",
                    f"TEX_folder:"
                    f"{TEX_folder if TEX_folder is not None else 'NONE'}"):
                print(line)

        elif asset.parent_asset_type.name == 'assets':
            post_processing = AmBackgroundProcessor()
            for line in post_processing.run_process(
                    RENAME_ASSET,
                    asset.path,
                    True,
                    f"old_name:{old_name}",
                    f"new_name:{new_name}",
                    f"package:{__package__}"):
                print(line)

        return asset

    def get_from_name(self, name):
        find = [asset for asset in self if asset.name == name]
        return find[0] if find else None

    @property
    def sorted(self):
        return sorted(self, key=lambda file: file.name.lower())


class AmImage:

    def __init__(self, image):
        self._img = image

    @property
    def image(self):
        return self._img

    @property
    def name(self):
        return self._img.name

    @property
    def filename(self):
        if AmPath.path_is_relative(self._img.filepath):
            return os.path.basename(AmPath.normalized_path(self._img.filepath))
        return os.path.basename(self._img.filepath)

    @property
    def filepath(self):
        return self._img.filepath

    @filepath.setter
    def filepath(self, path):
        self._img.filepath = path


class ImageProcessing:

    @staticmethod
    def _get_TEX_folder():
        blendfile = bpy.data.filepath
        blend_dir = os.path.dirname(blendfile)
        filename = os.path.basename(blendfile).split(".blend")[0]
        TEX_dirname = f"TEX_{filename}"
        TEX_dirpath = AmPath.get_folder(blend_dir, TEX_dirname)
        return TEX_dirname, TEX_dirpath

    @staticmethod
    def _remap_to_tex_folder(image, TEX_dirname, TEX_dirpath, copied_from):
        # When the same image is used several times, Blender increments
        # its name, but it is always the same image. We must therefore
        # retrieve the name of the image from its file path instead of
        # retrieving it via the "image.name" command so as not to remap
        # an erroneous path.
        img_name = image.filename
        path = AmPath.convert_path_to_absolute(image.filepath)
        if path is None:
            return

        TEX_filepath = os.path.join(TEX_dirpath, img_name)
        is_already_saved = os.path.exists(TEX_filepath)
        if not is_already_saved:
            # No need to copy the same image several times if it has
            # already been done
            copied_from.append(path)
            shutil.copy2(path, TEX_filepath)
            relpath = f"//{os.path.join(TEX_dirname, img_name)}"

        elif is_already_saved and path in copied_from:
            relpath = f"//{os.path.join(TEX_dirname, img_name)}"

        else:
            # Another case is also possible. The same image name but
            # from different folders. In this case, we will have to
            # compare the paths and if they are different, you will have
            # to increment the name of the image.
            existing_names = [
                file for file in os.listdir(TEX_dirpath) if
                file.endswith(SUPPORTED_ICONS)]
            new_name = AmName.get_valid_name(
                    img_name, existing_names)
            copied_from.append(path)
            TEX_filepath = os.path.join(TEX_dirpath, new_name)
            shutil.copy2(path, TEX_filepath)
            relpath = f"//{os.path.join(TEX_dirname, new_name)}"

        image.filepath = relpath

    @classmethod
    def remap_paths(cls, remap_type, am_images):
        if remap_type == 'PACK':
            bpy.ops.file.pack_all()
            return

        if remap_type in ('RELATIVE', 'ABSOLUTE'):
            remap_function = getattr(AmPath, f"convert_path_to_"
                                             f"{remap_type.lower()}")

            for image in am_images:
                remapped_path = remap_function(image.filepath)
                if remapped_path is not None:
                    image.filepath = remapped_path

        if remap_type == 'TEX_FOLDER':
            TEX_dirname, TEX_dirpath = cls._get_TEX_folder()
            copied_from = []

            for image in am_images:
                if image.image.packed_file:
                    image.image.unpack(method='WRITE_LOCAL')
                cls._remap_to_tex_folder(
                        image, TEX_dirname, TEX_dirpath, copied_from)

            textures_path = os.path.join(os.path.dirname(bpy.data.filepath),
                                         'textures')

            if os.path.exists(textures_path):
                AmPath.remove_tree(textures_path)

class AssetsCore:
    @staticmethod
    def load_library(filepath="", link=False, relative=False,
                     data_type='objects'):
        with bpy.data.libraries.load(
                filepath=filepath,
                link=link,
                relative=relative) as (data_from, data_to):
            setattr(data_to, data_type, getattr(data_from, data_type))

        return data_to

    @classmethod
    def link_data_to_scene(cls, data, collection):

        attr = {'Object': 'objects',
                'Collection': 'children'
                }

        identifier = data.bl_rna.identifier
        getattr(collection, attr[identifier]).link(data)

    @staticmethod
    def _remove(data):
        identifier = data.bl_rna.identifier
        getattr(bpy.data, f"{identifier.lower()}s").remove(data,
                                                           do_unlink=True)

    @classmethod
    def remove(cls, datas):
        if isinstance(datas, list):
            for data in datas:
                cls._remove(data)
        else:
            cls._remove(datas)

    @staticmethod
    def get_original_data(name, data_type):
        increment = AmName.get_increment(name)
        if increment:
            return getattr(bpy.data, data_type).get(name[:-len(increment)])


class AmCollections(AssetsCore):

    @staticmethod
    def create_collection(name):
        coll = bpy.data.collections.new(name)
        return coll

    @classmethod
    def get_collection(cls, context):
        return context.view_layer.active_layer_collection.collection

    @classmethod
    def get_layer_collection(cls, layer_coll, coll_name):
        """
        Function to find a layer collection by his name by iterating
        through the children of the layer collection passed in parameter
        :param layer_coll: layer collection
        :param coll_name: string, name of the collection to found
        :return: layer collection
        """
        if layer_coll.name == coll_name:
            return layer_coll

        for layer in layer_coll.children:
            coll = cls.get_layer_collection(layer, coll_name)
            if coll:
                return coll

    @staticmethod
    def _import_collections(data_to):
        imported_colls = {coll: {'is_instance': False,
                                 'parent': None
                                 } for coll in data_to.collections
                          }

        for coll, datas in imported_colls.items():
            for child in coll.children:
                imported_colls[child]['parent'] = coll
            for obj in coll.objects:
                if not AmObjects.is_instance_coll_object(obj):
                    continue
                inst_coll = obj.instance_collection
                imported_colls[inst_coll]['is_instance'] = True

        return imported_colls

    @classmethod
    def append_collections(cls, context, data_to):
        wm = context.window_manager
        if not bpy.app.background: # When we save an asset and the automatic
            # rendering starts, if the file contains collections, these will
            # be imported rather than the object data. But,
            # wm.asset_management is not accessible in the background. So we
            # have to make sure that it is accessible.
            io_objects = wm.asset_management.io_import.objects
        imported = set()
        imported_colls = cls._import_collections(data_to)
        colls_to_clean = []

        for coll in imported_colls:
            # exclusion of the instances collections that are not needed to be
            # visible in the outliner
            if imported_colls[coll]['is_instance']:
                continue

            imported.update(coll.objects)

            if not bpy.app.background and io_objects.use_existing_coll:
                original = cls.get_original_data(coll.name, 'collections')
                if original is not None:
                    for obj in coll.objects:
                        original.objects.link(obj)
                    colls_to_clean.append(coll)
                else:
                    if imported_colls[coll]['parent'] is None:
                        collection = cls.get_collection(context)
                        cls.link_data_to_scene(coll, collection)
            else:
                if imported_colls[coll]['parent'] is None:
                    collection = cls.get_collection(context)
                    cls.link_data_to_scene(coll, collection)

        if colls_to_clean:
            for coll in colls_to_clean:
                cls.remove(coll)
                del imported_colls[coll]

        return list(imported), imported_colls

    @classmethod
    def link_collections(cls, context, data_to):
        parent_coll = cls.get_collection(context)
        imported = []
        imported_colls = cls._import_collections(data_to)
        mains_collections = [coll for coll in imported_colls if imported_colls[
            coll]['parent'] is None]

        for coll in mains_collections:
            if imported_colls[coll]['is_instance']:
                continue
            inst_ob = AmObjects.create_instance_coll_object(coll.name, coll)
            parent_coll.objects.link(inst_ob)
            imported.append(inst_ob)

        return imported, None


class AmObjects(AssetsCore):

    @staticmethod
    def create_object(name, data):
        ob = bpy.data.objects.new(name, data)
        return ob

    @classmethod
    def create_empty(cls, name="AM_root", display_type='SPHERE', size=0.01,
                     location=Vector((0, 0, 0))):
        ob = cls.create_object(name, None)
        ob.empty_display_type = display_type
        ob.empty_display_size = size
        ob.location = location
        return ob

    @classmethod
    def create_instance_coll_object(cls, instance_name, collection):
        inst_ob = cls.create_empty(instance_name)
        inst_ob.instance_type = 'COLLECTION'
        inst_ob.instance_collection = collection
        return inst_ob

    @staticmethod
    def is_instance_coll_object(obj):
        return obj and obj.type == 'EMPTY' and obj.instance_collection

    @classmethod
    def remove_hierarchy(cls, ob):
        children = [ob]
        cls.get_children(ob, children)
        cls.remove(children)

    @classmethod
    def get_main_parent(cls, obj):
        if obj is not None and obj.parent:
            return cls.get_main_parent(obj.parent)

        return obj

    @classmethod
    def get_parents(cls, obj, datas):
        if obj is not None and obj.parent:
            if isinstance(datas, list):
                datas.append(obj.parent)
            elif isinstance(datas, set):
                datas.add(obj.parent)
            cls.get_parents(obj.parent, datas)

        return datas

    @classmethod
    def get_children(cls, obj, datas):
        if obj.children:
            if isinstance(datas, list):
                datas.extend(obj.children)
            elif isinstance(datas, set):
                datas.update(obj.children)
            for child in obj.children:
                cls.get_children(child, datas)

        return datas

    @classmethod
    def get_hierarchy(cls, obj, datas):
        parent = cls.get_main_parent(obj)
        if isinstance(datas, list):
            datas.append(parent)
        elif isinstance(datas, set):
            datas.add(parent)
        cls.get_children(parent, datas)

        return datas


    @classmethod
    def excluded_objects(cls, data_to):
        exclude = set()
        # In the case of a instance collection, it's not useful to link
        # objects other than empty to the collection.
        instances = [ob for ob in data_to.objects if
                     cls.is_instance_coll_object(ob)]

        # If we have collection instances, we must exclude the child objects
        # from those instances so as not to link them several time to the scene
        if instances:
            for inst_ob in instances:
                exclude.update(inst_ob.instance_collection.objects)

        # In case the object is of type ARMATURE, we don't need to link to
        # the scene the objects used as custom shape.
        armatures = [ob for ob in data_to.objects if ob.type == 'ARMATURE']
        if armatures:
            exclude.update([bone.custom_shape for ob in armatures for bone
                            in ob.pose.bones if bone.custom_shape])
        return exclude

    @staticmethod
    def get_object_visibility(ob):
        ob['asset_management']['hide_set'] = not ob.hide_viewport and not \
            ob.visible_get()

    @classmethod
    def set_object_custom_properties(cls, datas):
        if isinstance(next(iter(datas)), bpy.types.Object):
            for ob in datas:
                if not ob.get('asset_management'):
                    ob['asset_management'] = {}

                cls.get_object_visibility(ob)

    @staticmethod
    def set_object_properties(ob):
        if ob.get('asset_management'):
            ob.hide_set(state=ob['asset_management']['hide_set'])

    @classmethod
    def append_objects(cls, context, data_to):
        objects = []
        exclude = cls.excluded_objects(data_to)
        coll = AmCollections.get_collection(context)

        for obj in data_to.objects:
            if obj is None or obj in exclude:
                continue
            cls.link_data_to_scene(obj, coll)
            obj.select_set(state=True)
            objects.append(obj)
            cls.set_object_properties(obj)

        return objects, None

    @classmethod
    def link_object(cls, context, data_to):
        prefs = addon_prefs()

        imported = []
        exclude = cls.excluded_objects(data_to)
        parent_coll = AmCollections.get_collection(context)
        objects = [ob for ob in data_to.objects if ob is not None and ob
        not in exclude]

        # we need to know which is the main parent if there is one before
        # creating the collection instances because it removes the hierarchy
        root = cls.get_root(objects)
        if prefs.import_export.linked_to_coll:
            for obj in objects:
                coll = AmCollections.create_collection(obj.name)
                coll.objects.link(obj)
                inst_ob = cls.create_instance_coll_object(obj.name, coll)
                parent_coll.objects.link(inst_ob)
                # If the root exists, we replace the object with its collection
                # instance
                if obj == root:
                    root = inst_ob
                imported.append(inst_ob)
        else:
            for obj in objects:
                parent_coll.objects.link(obj)
                imported.append(obj)

        # if there was a root, we recreate the link to this parent
        if root is not None:
            for inst_ob in imported:
                if inst_ob == root:
                    continue
                inst_ob.parent = root

        return imported, None

    @staticmethod
    def select(context, to_select):
        for obj in context.scene.objects:
            if isinstance(to_select, list) or isinstance(to_select, tuple):
                obj.select_set(state=obj in to_select)
            else:
                obj.select_set(state=obj == to_select)

    @staticmethod
    def active(context, obj):
        context.view_layer.objects.active = obj

    @classmethod
    def clear_root(cls, context, root):
        children = root.children
        cls.select(context, children)
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        cls.active(context, children[0])
        cls.remove(root)

    @classmethod
    def parent_to_root_empty(cls, context, imported):
        root = cls.create_empty()
        coll = AmCollections.get_collection(context)
        cls.link_data_to_scene(root, coll)

        exclude = [obj for obj in imported if obj.parent or
                   (hasattr(obj, 'constraints') and
                    any([const for const in obj.constraints if const.type ==
                         'COPY_LOCATION']))]

        targets = [obj for obj in imported if obj not in exclude]

        for obj in targets:
            obj.parent = root

        return root

    @classmethod
    def get_root(cls, imported):
        if len(imported) == 1:
            return imported[0]

        parent = cls.get_main_parent(imported[0])

        if parent.children:
            children = []
            cls.get_children(parent, children)
            if len(children) + 1 == len(imported):
                return parent

        return None

    @staticmethod
    def is_plane(obj):
        tol = 1e-6
        return (all((tol > v.co.z > -tol for v in obj.data.vertices)) and
                not any((mod for mod in obj.modifiers if mod.type ==
                         'SOLIDIFY')))

    @classmethod
    def is_boolean_object(cls, obj):
        if not hasattr(obj, 'display_type'):
            return
        if obj.display_type not in {'WIRE', 'BOUNDS'}:
            return
        if cls.is_plane(obj):
            return
        return True

    @classmethod
    def set_boolean_object(cls, target, boolean):
        mod = target.modifiers.new("Boolean - DIFFERENCE", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        if minimum_blender_version(2, 91, 0):
            mod.solver = 'FAST'
        mod.object = boolean
        mod.show_expanded = False
        if boolean.parent:
            boolean.hide_viewport = True

    @classmethod
    def get_boolean_objects(cls, objects):
        return [ob for ob in objects if cls.is_boolean_object(ob)]

    @staticmethod
    def get_modifier_from_boolean_object(context, bool_obj):
        boolean = {}
        for obj in context.scene.objects:
            if not hasattr(obj, 'modifiers'):
                continue
            for mod in obj.modifiers:
                if mod.type != 'BOOLEAN':
                    continue
                if mod.object != bool_obj:
                    continue
                boolean[obj] = mod

        return boolean

    @staticmethod
    def get_weighted_normal(obj):
        weighted = [mod for mod in obj.modifiers if mod.type ==
                    'WEIGHTED_NORMAL']
        if weighted:
            return weighted[0]

        weighted = obj.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL')
        weighted.keep_sharp = True
        weighted.show_expanded = False
        return weighted

    @classmethod
    def setup_weighted_normal(cls, context, obj, root):
        obj.data.use_auto_smooth = True
        weighted = cls.get_weighted_normal(obj)
        cls.active(context, obj)
        idx = len(obj.modifiers)
        bpy.ops.object.modifier_move_to_index(modifier=weighted.name,
                                              index=idx - 1)
        cls.active(context, root)

    @classmethod
    def import_asset(cls, context, filepath=None, link=False,
                     relative=False, location=ZERO, data_type='objects'):
        data_to = cls.load_library(filepath, link, relative, data_type)

        if not getattr(data_to, data_type.lower()):
            return None, None

        if link:
            if data_type == 'objects':
                imported, collections = cls.link_object(context,
                                                        data_to)

            else:
                imported, collections = AmCollections.link_collections(
                        context,
                        data_to)

        else:
            if data_type == 'objects':
                imported, collections = cls.append_objects(context,
                                                           data_to)

            else:
                imported, collections = AmCollections.append_collections(
                        context,
                        data_to)

        root = cls.get_root(imported)
        if root is None:
            root = cls.parent_to_root_empty(context, imported)
        root.location = location
        cls.select(context, imported)
        cls.active(context, root)

        return imported, collections

    @staticmethod
    def copy_modifiers(src, dst):
        exclude = ('name', 'type', 'bl_rna', 'rna_type')

        for mod_from in src.modifiers:
            properties = [prop.identifier for prop in
                          mod_from.bl_rna.properties if prop.identifier not
                          in exclude]
            mod_to = dst.modifiers.new(mod_from.name, mod_from.type)
            for prop in properties:
                setattr(mod_to, prop, getattr(mod_from, prop))


class AmMaterials(AssetsCore):

    @staticmethod
    def create_material(name):
        mat = bpy.data.materials.new(name)
        return mat

    @staticmethod
    def add_material_slot(obj, material):
        obj.data.materials.append(material)
        return len(obj.data.materials) - 1

    @classmethod
    def assign_material(cls, obj, material, slot_idx=0):
        if obj.data.materials:
            obj.material_slots[slot_idx].material = material
        else:
            cls.add_material_slot(obj, material)

    @staticmethod
    def import_material(filepath=None, link=False, relative=False,
                        use_existing=True):

        mat_name = os.path.basename(filepath).split(".blend")[0]

        if use_existing:
            material = bpy.data.materials.get(mat_name)
            if material is not None:
                return material

        with bpy.data.libraries.load(
                filepath=filepath, link=link, relative=relative) as (
                data_from, data_to):
            setattr(data_to, 'materials', [mat for mat in
                                           data_from.materials if mat ==
                                           mat_name])

        if data_to.materials:
            return data_to.materials[0]

        return None

    @staticmethod
    def get_images(data, images=[]):
        """
        Gets the images used by the material passed in parameter
        @param data: blender material or node
        @return: List of AmImage object
        """
        for node in data.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image is not None:
                images.append(AmImage(node.image))
            elif node.type == 'GROUP':
                AmMaterials.get_images(node, images)
        return images


class AmEnvironment:

    @staticmethod
    def clean_node_tree(world):
        """ Clean the node editor """
        for node in world.node_tree.nodes:
            if node.name == "World Output":
                continue
            world.node_tree.nodes.remove(node)

    @classmethod
    def _new_world(cls, name):
        world = bpy.data.worlds.new(name)
        bpy.context.scene.world = world
        world.use_nodes = True
        cls.clean_node_tree(world)
        return world

    @classmethod
    def new_environment(cls, context, filepath):
        am_env_node = bpy.data.node_groups.get('AM_environment')
        if am_env_node is None:
            with bpy.data.libraries.load(filepath=NODE_ENVIRONMENT) as (
                    data_from, data_to):
                if data_from.node_groups:
                    data_to.node_groups = [
                        node_group for node_group in data_from.node_groups if
                        node_group == "AM_environment"]

            am_env_node = data_to.node_groups[0]

        # To keep the basic 'AM_environment' node intact, a copy is created
        # for each new environment.
        am_env_node = am_env_node.copy()

        if filepath:
            world_name = os.path.splitext(os.path.basename(filepath))[0]
        else:
            world_name = "AM_IBL_WORLD"

        world = cls._new_world(world_name)
        nodes = world.node_tree.nodes
        env_node = nodes.new("ShaderNodeGroup")
        env_node.name = am_env_node.name
        env_node.location = 0, 0
        env_node.node_tree = am_env_node

        if filepath:
            cls.setup_ibl(filepath, world)

        context.window_manager.asset_management.environment.am_worlds = world

    @staticmethod
    def _load_ibl(filepath):
        filename = os.path.basename(filepath)
        ibl = bpy.data.images.get(filename) or bpy.data.images.load(filepath)
        return ibl

    @classmethod
    def setup_ibl(cls, filepath, world):
        nodes = world.node_tree.nodes
        am_env_node = [node for node in nodes if node.name.startswith(
                'AM_environment')][0]
        env_node = am_env_node.node_tree.nodes.get('Environment')
        reflexion_node = am_env_node.node_tree.nodes.get('Reflexion')

        ibl = cls._load_ibl(filepath)

        if env_node is not None:
            env_node.image = ibl
        if reflexion_node is not None:
            reflexion_node.image = ibl

        output_node = nodes.get('World Output') or nodes.new(
                'ShaderNodeOutputWorld')
        output_node.location = 200, 0

        world.node_tree.links.new(am_env_node.outputs[0],
                                  output_node.inputs[0])


class AmTags(list):
    def __init__(self):
        list.__init__(self)

    @property
    def tags(self):
        return self

    @tags.setter
    def tags(self, tags):
        self.clear()
        if tags:
            pattern = r"[;:-]"
            output = re.sub(pattern, ", ", tags)

            pattern = r"^[\s,;:-]+|[\s,;:-]+$"
            output = re.sub(pattern, "", output)

            pattern = r"^\s+|\s+$"
            self.extend([re.sub(pattern, "", tag) for tag in output.split(",")])

    def clear_tags(self):
        self.clear()


class AmAssetFilter(AmTags):
    def __init__(self, id_):
        AmTags.__init__(self)
        self._id = id_
        self._assets = set()
        self._active = None
        self._active_index = 0
        self._enum_items = []

    def _get_assets(self, category):
        for cat in category.categories.values():
            for tag in self.tags:
                for am_asset in cat.assets:
                    if re.search(tag.lower(), am_asset.name.lower()):
                        self._assets.add(am_asset)

            self._get_assets(cat)

    def update_assets(self, am_libraries):
        if not self.tags:
            self.clear_search()
            return
        self._assets.clear()
        self._active_index = 0
        self._active = None

        for library in am_libraries:
            aType = library.asset_types.get(self._id)
            if aType is None:
                continue
            self._get_assets(aType)

        return self._assets

    @property
    def assets(self):
        return self._assets

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, asset):
        if asset is not None and os.path.exists(asset.path):
            idx = self.sorted.index(asset)
            self._active = asset
            self._active_index = idx
        else:
            self._active = None
            self._active_index = 0

    @property
    def active_index(self):
        return self._active_index

    @property
    def enum_items(self):
        self._enum_items.clear()
        assets = self.sorted

        if not assets:
            return [('NONE', "None", "")]

        self._enum_items.extend(
                [(asset.path, asset.name, asset.path, asset.icon_id,
                  idx) for idx, asset in enumerate(assets)])

        return self._enum_items

    @property
    def sorted(self):
        return sorted(self._assets, key=lambda asset: asset.name.lower())

    def clear_search(self):
        self._assets.clear()
        self.clear_tags()
        self._active_index = 0
        self.active = None


class _AmFilterSearchName:
    def __init__(self):
        self.assets = AmAssetFilter('assets')
        self.scenes = AmAssetFilter('scenes')
        self.materials = AmAssetFilter('materials')
        self.hdri = AmAssetFilter('hdri')


AmFilterSearchName = _AmFilterSearchName()
