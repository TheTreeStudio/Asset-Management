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
import pickle as pkl

from bpy.utils import register_class, unregister_class
from bpy.types import Operator
from bpy.props import (StringProperty,
                       BoolProperty)

from .AmLibraries import LibrariesManager as LM
from .AmUtils import AmJson, AmPath, AmName, wrap_text
from .ressources.constants import (ORDERED_TYPES,
                                   WARNING_REMOVE_MESSAGE,
                                   AM_DATAS,
                                   OLD_LIBRARIES_INSTRUCTIONS)


class OperatorsStatus:
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running() \
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running() \
               and LM.category_to_move is None


class CommonAssetsType:
    assets: BoolProperty(
            name="Add 'assets' type",
            default=True,
            description="Create automatically the type 'assets'"
            )

    scenes: BoolProperty(
            name="Add 'scenes' type",
            default=False,
            description="Create automatically the type 'scenes'"
            )

    materials: BoolProperty(
            name="Add 'materials' type",
            default=False,
            description="Create automatically the type 'materials'"
            )

    hdri: BoolProperty(
            name="Add 'environment' type",
            default=False,
            description="Create automatically the type 'environment'"
            )

    def draw_assets_type(self, layout, path):
        dirs = [dir_ for dir_ in os.listdir(path)]
        layout.label(text="Select default type to create:")
        row = layout.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        col = split.column()
        for type_ in ORDERED_TYPES:
            if type_ not in dirs:
                col.prop(self, type_, text=type_)


# -----------------------------------------------------------------------------
# Classes definition allowing to manage the libraries
# -----------------------------------------------------------------------------


def draw_output_message(self, context, text):
    for line in text.split("\n"):
        self.layout.label(text=line)


class ASSETM_OT_browser_directory(Operator):
    """Call a browser directory"""
    bl_idname = 'asset_management.browser_directory'
    bl_label = "Browser directory"
    bl_options = {'REGISTER'}

    _running = False

    @classmethod
    def set_status(cls):
        cls._running = not cls._running

    @classmethod
    def running(cls):
        return cls._running

    def modal(self, context, event):

        if not bpy.data.screens.get('temp'):
            self.set_status()
            context.area.tag_redraw()

            return {"FINISHED"}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        self.set_status()
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}


class ASSETM_OT_load_old_libraries(Operator, OperatorsStatus):
    """Allows to load old libraries from 2.79 version of AM"""
    bl_idname = 'asset_management.load_old_libraries'
    bl_label = "Load Blender 2.79 libraries"

    filepath: StringProperty(subtype="FILE_PATH")

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        for line in wrap_text(OLD_LIBRARIES_INSTRUCTIONS):
            box.label(text=line)

    def execute(self, context):
        src_datas = os.path.realpath(self.filepath)
        dst_datas = os.path.join(AM_DATAS, "libraries.json")
        if os.path.isfile(src_datas) and os.path.basename(src_datas) == \
                "custom_filepaths":

            with open(src_datas, 'rb') as pklf:
                file = pkl.Unpickler(pklf)
                library_dict = file.load()

                library_list = [
                    os.path.abspath(item[0]) for item in library_dict.values()
                    ]

            if os.path.exists(dst_datas):
                content = AmJson.load_json_file(dst_datas)
                for lib in content:
                    if lib in library_list:
                        continue
                    library_list.append(lib)

            if len(library_list):
                AmJson.save_as_json_file(dst_datas, library_list)
                LM.libraries.load()
        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.asset_management.browser_directory('INVOKE_DEFAULT')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ASSETM_OT_add_library(Operator, CommonAssetsType):
    """Add a new library or load an existing one in your database"""
    bl_idname = 'asset_management.add_library'
    bl_label = "Load/Create library"
    bl_options = {'REGISTER'}

    directory: StringProperty(
            name="Add library",
            default=""
            )

    def __init__(self):
        self.existing_libraries = None

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running()\
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running()

    def _already_exists(self, path):
        return any([os.path.abspath(path) == lib for lib in
                    self.existing_libraries])

    def _is_from_existing_library(self, path):
        return any(
                [lib+os.sep in path for lib in self.existing_libraries]
                )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        path = os.path.realpath(
                context.space_data.params.directory.decode("utf-8")
                )
        if self._already_exists(path):
            box.label(text="Library already registred in database",
                      icon='ERROR')
        elif self._is_from_existing_library(path):
            box.label(text="You can't add the selected", icon='ERROR')
            box.label(text="folder because it is part of a")
            box.label(text="library already registered in database")

        else:
            self.draw_assets_type(box, path)

    def modal(self, context, event):

        if not bpy.data.screens.get('temp'):
            self.set_status()
            context.area.tag_redraw()

            return {"FINISHED"}

        return {'PASS_THROUGH'}

    def execute(self, context):
        directory = os.path.realpath(self.directory)

        if self._already_exists(directory) or\
                self._is_from_existing_library(directory):
            print(f"\"{directory}\"  is already registered\n"
                  f"in database or is a part of an existing library"
                  )

            return {'FINISHED'}

        subfolders = AmPath.get_dirs(directory)
        for type_ in ORDERED_TYPES:
            if not getattr(self, type_) or type_ in subfolders:
                continue
            AmPath.get_folder(directory, type_)

        LM.libraries.add(directory)

        print(f"Library \"{directory}\" created")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.existing_libraries = LM.libraries.keys()
        bpy.ops.asset_management.browser_directory('INVOKE_DEFAULT')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ASSETM_OT_remove_library(Operator, OperatorsStatus):
    """Remove the active library"""
    bl_idname = 'asset_management.remove_library'
    bl_label = "Remove library"

    from_hard_drive: BoolProperty(
            name="from Hard Drive",
            default=False,
            description="If enabled, remove the library from the hard drive"
            )

    confirm: StringProperty(
            default=""
            )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        row = box.row(align=True)
        row.prop(self, 'from_hard_drive')

        text = "HD" if self.from_hard_drive else "DB"
        for i, line in enumerate(WARNING_REMOVE_MESSAGE[text]):
            if self.from_hard_drive and i == 0:
                box.label(text=line.format("library"))
            else:
                box.label(text=line)

        if self.from_hard_drive:
            box.separator()
            row = box.row(align=True)
            split = row.split(factor=0.2)
            split.separator()
            splited = split.split(factor=0.7)
            splited.prop(self, 'confirm', text="")

    def execute(self, context):
        active = LM.libraries.active
        LM.libraries.remove(active.path)

        if self.from_hard_drive and self.confirm == "YES":
            AmPath.remove_tree(active.path)
        context.area.tag_redraw()
        LM.libraries.save()

        return {'FINISHED'}

    def invoke(self, context, event):
        self.from_hard_drive = False
        self.confirm = ""

        context.window_manager.invoke_props_dialog(self, width=300)

        return {'RUNNING_MODAL'}


class ASSETM_OT_rename_library(Operator, OperatorsStatus):
    """Rename the active library"""
    bl_idname = 'asset_management.rename_library'
    bl_label = "Rename library"

    new_name: StringProperty(
            default=""
            )

    def __init__(self):
        self.new_name = ""
        self.src_path = LM.active_library.path
        self.path_root = os.path.dirname(self.src_path)
        self.dirs = next(os.walk(self.path_root))[1]

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Enter the new library name:")
        row = box.row(align=True)
        split = row.split(factor=0.2)
        split.separator()
        splited = split.split(factor=0.7)
        splited.prop(self, 'new_name', text="")
        if any([self.new_name == dir_ for dir_ in self.dirs]) and \
                self.new_name != os.path.basename(self.src_path):
            box.label(text="This name already exists.", icon='ERROR')
            box.label(text="If you validate it as it is, it will be "
                           "automatically incremented")

    def execute(self, context):
        if self.new_name == os.path.basename(self.src_path):
            return {'FINISHED'}

        try:
            LM.libraries.rename(self.src_path, self.new_name)
        except:
            self.report({'WARNING'}, f"{self.__class__.__name__} -"
                                     f" {self.src_path} is being used")
        context.area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=350)

        return {'RUNNING_MODAL'}


class ASSETM_OT_move_library(Operator, OperatorsStatus):
    """Move the active library in targeted location"""
    bl_idname = 'asset_management.move_library'
    bl_label = "Move library"

    directory: StringProperty(
            name="Add library",
            default=""
            )

    increment: BoolProperty(
            name="Increment the name",
            default=True,
            description="If enabled, the library name will incremented"
            )

    new_name: StringProperty(default="")

    def _is_from_existing_library(self, path):
        return any(
                [lib+os.sep in path or lib == path for lib in
                 self.existing_libraries]
                )

    def __init__(self):
        self.active = LM.libraries.active
        self.existing_libraries = LM.libraries.keys()

    def draw(self, context):
        layout = self.layout
        path = os.path.realpath(
                context.space_data.params.directory.decode("utf-8")
                )

        if self._is_from_existing_library(path):
            box = layout.box()
            box.label(text="You can't move the library", icon='ERROR')
            box.label(text="in a library already")
            box.label(text="registered in database")

    def execute(self, context):
        if os.path.realpath(self.directory) == os.path.dirname(
                self.active.path):
            return {'FINISHED'}

        LM.libraries.move(self.active, os.path.realpath(self.directory))

        return {'FINISHED'}

    def invoke(self, context, event):
        bpy.ops.asset_management.browser_directory('INVOKE_DEFAULT')
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# -----------------------------------------------------------------------------
# Classes definition allowing to manage the type of asset
# -----------------------------------------------------------------------------


class ASSETM_OT_add_asset_type(Operator, CommonAssetsType):
    """Add a new type of asset"""
    bl_idname = 'asset_management.add_asset_type'
    bl_label = "Add asset type"

    @classmethod
    def poll(cls, context):
        return len(LM.libraries.active.asset_types) < len(ORDERED_TYPES) \
               and not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running() \
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running()

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        self.draw_assets_type(box, LM.libraries.active.path)

    def execute(self, context):
        library = LM.libraries.active
        for type_ in ORDERED_TYPES:
            if not getattr(self, type_) or library.asset_types.get(type_):
                continue
            aType = library.asset_types.add(type_)
            aType.categories.active = aType

        context.area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        for type_ in ORDERED_TYPES:
            setattr(self, type_, False)

        context.window_manager.invoke_props_dialog(self, width=300)

        return {'RUNNING_MODAL'}


# -----------------------------------------------------------------------------
# Classes definition allowing to manage the categories
# -----------------------------------------------------------------------------


class ASSETM_OT_expand_category(Operator):
    """Toggle the sub categories visibility"""
    bl_idname = 'asset_management.expand_category'
    bl_label = "Expand"

    path: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running()\
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running()

    def execute(self, context):
        category = LM.get_category_from_path(self.path)
        if category is None:
            return {'FINISHED'}

        category.expanded = not category.expanded
        return {'FINISHED'}


class ASSETM_OT_collapse_all_categories(Operator):
    """Collapse all categories."""
    bl_idname = 'asset_management.collapse_all_categories'
    bl_label = "Collapse all"

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running()\
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running() \
               and LM.active_type.categories

    def _collapse_category(self, category):
        category.expanded = False

        for cat in category.categories.values():
            self._collapse_category(cat)

    def execute(self, context):
        for cat in LM.active_type.categories.values():
            self._collapse_category(cat)

        return {'FINISHED'}


class ASSETM_OT_show_active_category(Operator):
    """Expands the parent hierarchy of the active category"""
    bl_idname = 'asset_management.show_active_category'
    bl_label = "Show active category"

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running()\
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running() \
               and LM.active_type.categories

    def _expand_category(self, category):
        if hasattr(category.parent, "categories"):
            category.parent.expanded = True
            self._expand_category(category.parent)

    def execute(self, context):
        active_category = LM.active_category
        self._expand_category(active_category)

        return {'FINISHED'}


class ASSETM_OT_set_active_category(Operator):
    """Set the selected category as active"""
    bl_idname = 'asset_management.set_active_category'
    bl_label = "Active_category"

    path: StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return not bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running() \
               and not bpy.types.ASSET_MANAGEMENT_OT_new_category.running()

    def execute(self, context):
        category = LM.get_category_from_path(self.path)
        if category is not None:
            categories = LM.active_type.categories
            categories.active = category
            if hasattr(category, 'is_expandable') and category.is_expandable:
                category.expanded = True

            if len(LM.pinned_categories()) == 1 and LM.active_category == \
                    category:
                category.pinned = False

        return {'FINISHED'}


class ASSETM_OT_new_category(Operator):
    """Create a new category"""
    bl_idname = 'asset_management.new_category'
    bl_label = "Add category"
    bl_options = {'REGISTER'}

    _running = False

    @classmethod
    def poll(cls, context):
        return not cls._running and not \
            bpy.types.ASSET_MANAGEMENT_OT_browser_directory.running()

    @classmethod
    def running(cls):
        return cls._running

    @classmethod
    def set_status(cls, state=None):
        if state is None:
            cls._running = not cls._running
        else:
            cls._running = state

    def __init__(self):
        am = bpy.context.window_manager.asset_management
        am.category_name = "Untitled"

    def execute(self, context):
        if self._running:
            self.set_status()
        else:
            LM.libraries.active.asset_types.active.categories.active\
                .expanded = True
            self.set_status()
        return {'FINISHED'}


class ASSETM_OT_add_category(Operator):
    """Add the new category in your library"""
    bl_idname = 'asset_management.add_category'
    bl_label = "Add category"
    bl_options = {'REGISTER'}

    def execute(self, context):
        am = context.window_manager.asset_management
        name = am.category_name
        active_category = LM.active_category
        existing_names = AmPath.get_dirs(active_category.path)
        valid_name = AmName.get_valid_name(name, existing_names)
        LM.active_category.categories.add(valid_name)

        am.category_name = ""
        bpy.types.ASSET_MANAGEMENT_OT_new_category.set_status()

        return {'FINISHED'}


class ASSETM_OT_remove_category(Operator, OperatorsStatus):
    """Remove the active category"""
    bl_idname = 'asset_management.remove_category'
    bl_label = "Remove category"

    confirm: StringProperty(default="")

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        for i, line in enumerate(WARNING_REMOVE_MESSAGE["HD"]):
            if i == 0:
                box.label(text=line.format("category"))
            else:
                box.label(text=line)

        box.separator()
        row = box.row(align=True)
        split = row.split(factor=0.2)
        split.separator()
        splited = split.split(factor=0.7)
        splited.prop(self, 'confirm', text="")

    def execute(self, context):
        if self.confirm == "YES":
            category = LM.active_category
            parent = category.parent
            parent.categories.remove(category)

            AmPath.remove_tree(category.path)

            if parent.categories:
                cat = parent.categories.get(parent.categories.sorted[0])
                LM.active_category = cat
                if cat.preview is not None:
                    cat.set_active_asset_from_path(cat.preview.preview)

            else:
                LM.active_category = parent
            context.area.tag_redraw()

        return {'FINISHED'}

    def invoke(self, context, event):
        self.confirm = ""
        context.window_manager.invoke_props_dialog(self, width=320)

        return {'RUNNING_MODAL'}


class ASSETM_OT_move_category(Operator):
    """Move the active category"""
    bl_idname = 'asset_management.move_category'
    bl_label = "Move category"
    bl_options = {'REGISTER'}

    def execute(self, context):
        category = LM.category_to_move
        if category.path == LM.active_category.path or \
                LM.active_category.path == category.parent.path:
            LM.category_to_move = None
            return {'FINISHED'}

        category = LM.active_category
        LM.move_category(category)
        return {'FINISHED'}


class ASSETM_OT_rename_category(Operator, OperatorsStatus):
    """Rename the active category"""
    bl_idname = 'asset_management.rename_category'
    bl_label = "Rename category"
    bl_options = {'REGISTER'}

    new_name: StringProperty(
            default=""
            )

    def __init__(self):
        self.new_name = ""
        self.src_path = LM.active_category.path
        self.path_root = os.path.dirname(self.src_path)
        self.dirs = next(os.walk(self.path_root))[1]

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Enter the new category name:")
        row = box.row(align=True)
        split = row.split(factor=0.2)
        split.separator()
        splited = split.split(factor=0.7)
        splited.prop(self, 'new_name', text="")
        if any([self.new_name == dir_ for dir_ in self.dirs]) and \
                self.new_name != os.path.basename(self.src_path):
            box.label(text="This name already exists.", icon='ERROR')
            box.label(text="If you validate it as it is, it will be "
                           "automatically incremented")

    def execute(self, context):

        if self.new_name == os.path.basename(self.src_path):
            return {'FINISHED'}

        if self.new_name.lower() in ('files', 'icons'):
            self.report({'WARNING'}, f"{self.__class__.__name__} - "
                                     f"{self.new_name.lower()} is a reserved "
                                     f"name")
            return {'FINISHED'}

        try:
            category = LM.get_category_from_path(self.src_path)
            new_cat = LM.active_type.categories.rename(category,
                                                       self.new_name
                                                       )
            LM.active_type.categories.active = new_cat
            if new_cat.preview is not None:
                new_cat.set_active_asset_from_path(new_cat.preview.preview)
            context.area.tag_redraw()

        except:
            self.report({'WARNING'}, f"{self.__class__.__name__} -"
                                     f" {self.src_path} is being used")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=350)

        return {'RUNNING_MODAL'}


CLASSES = (ASSETM_OT_browser_directory,
           ASSETM_OT_load_old_libraries,
           ASSETM_OT_add_library,
           ASSETM_OT_remove_library,
           ASSETM_OT_rename_library,
           ASSETM_OT_move_library,
           ASSETM_OT_add_asset_type,
           ASSETM_OT_expand_category,
           ASSETM_OT_collapse_all_categories,
           ASSETM_OT_show_active_category,
           ASSETM_OT_set_active_category,
           ASSETM_OT_new_category,
           ASSETM_OT_add_category,
           ASSETM_OT_remove_category,
           ASSETM_OT_move_category,
           ASSETM_OT_rename_category)


def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in CLASSES:
        unregister_class(cls)
