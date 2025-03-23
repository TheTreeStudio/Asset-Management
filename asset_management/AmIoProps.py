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
from bpy.types import PropertyGroup, Operator
from bpy.props import (PointerProperty,
                       StringProperty,
                       BoolProperty,
                       EnumProperty,
                       CollectionProperty,
                       IntProperty)
from bpy_extras.io_utils import ImportHelper

from .AmIcons import Icons
from .AmUtils import addon_prefs, AmPath
from .AmLibraries import LibrariesManager as LM


# -----------------------------------------------------------------------------
# Classes and functions to manage the backup of assets
# -----------------------------------------------------------------------------

class IoCommonProps:
    filepath: StringProperty(name="Filepath",
                             default="",
                             description="Filepath of the asset to append or link"
                             )

    link: BoolProperty(name="Link",
                       default=False,
                       description="If enabled, links the asset instead of "
                                   "appending it."
                       )

    @staticmethod
    def path_report(parent):
        parent.report({'ERROR'}, f"{parent.__class__.__name__} - Invalid "
                                 f"filepath: \"{parent.filepath}\"")
        return {'CANCELLED'}

    @staticmethod
    def linked_asset_report(parent):
        parent.report({'INFO'}, f"{parent.__class__.__name__} - "
                                   f"Asset already linked in the scene. Not "
                                   f"possible to append it")
        return {'CANCELLED'}

    @staticmethod
    def object_report(parent):
        parent.report({'WARNING'}, f"{parent.__class__.__name__} - "
                                   f"There's no {parent.data_type.lower()} "
                                   f"in this blendfile")
        return {'CANCELLED'}


class IoImportObjects(PropertyGroup):

    use_existing_coll: BoolProperty(
            name="Use existing collection",
            default=True,
            description="Uses the collection of the same name if it already "
                        "exists."
            )

    replace: BoolProperty(
            name="Replace asset",
            default=False,
            description="Replace each selected object by the active asset. "
                        "Only parents will be replaced in a hierarchy."
            )

    copy_scale: BoolProperty(
            name="Copy scale",
            default=False,
            description="Copy the scale of the object to be replaced"
            )


class IoImportMaterials(PropertyGroup):
    use_existing_material: BoolProperty(
            name="Use existing material",
            default=True,
            description="Uses the material of the same name if it already "
                        "exists."
            )


# -----------------------------------------------------------------------------
# Classes and functions to manage the export of assets
# -----------------------------------------------------------------------------

class ASSETM_OT_select_image_file(Operator, ImportHelper):
    ''' Open the filebrowser to select an image '''
    bl_idname = 'asset_management.select_image_file'
    bl_label = "Image file select"
    bl_options = {'INTERNAL'}

    filter_glob: StringProperty(default='*.jpeg;*.jpg;*.png',
                                 options={'HIDDEN'})

    def execute(self, context):
        am = context.window_manager.asset_management
        asset_type = LM.active_type.name
        if asset_type == 'assets':
            asset_type = 'objects'
        io_export = getattr(am.io_export, asset_type)
        img_path = AmPath.convert_path_to_absolute(self.filepath) or ""

        io_export.image_from_computer = img_path
        context.area.tag_redraw()
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}


def thumbnailer_enum_items(self, context):
    if LM.active_type.name == 'assets':
        return [('BLENDER_EEVEE', "Eevee", "Eevee render"),
                ('CYCLES', "Cycles", "Cycles render"),
                ('OGL', "OpenGl", "OpengL render"),
                ('THUMB', "Thumb", "Existing thumbnail")
                ]

    elif LM.active_type.name == 'materials':
        am = context.window_manager.asset_management
        io_materials = am.io_export.materials
        if len([ul_mat for ul_mat in io_materials.UL_materials if
                ul_mat.to_export]) > 1:
            return [('BLENDER_EEVEE', "Eevee", "Eevee render"),
                    ('CYCLES', "Cycles", "Cycles render")
                    ]

        return [('BLENDER_EEVEE', "Eevee", "Eevee render"),
                ('CYCLES', "Cycles", "Cycles render"),
                ('THUMB', "Thumb", "Existing thumbnail")
                ]

    else:
        return [('OGL', "OpenGl", "OpengL render"),
                ('THUMB', "Thumb", "Existing thumbnail")
                ]


class CommonIoExportProps(PropertyGroup):
    display_panel: BoolProperty(
            name="Display panel",
            default=False)

    thumbnailer: EnumProperty(
            name="Thumbnailer",
            items=thumbnailer_enum_items,
            description="Render engine using to creating the thumbnail")

    thumbnail_source: EnumProperty(
            name="Thumbnail source",
            items=(("RENDERED", "Rendered", "Thumb from rendered image"),
                   ("FROM_COMPUTER", "From computer",
                    "Thumb selected on the computer")),
            default="RENDERED"
            )

    rendered_image: StringProperty(
            name="Rendered image",
            default="Render Result"
            )

    image_from_computer: StringProperty(
            name="Thumb path",
            default=""
            )

    def _row_split(self, layout, factor=0.1):
        row = layout.row(align=True)
        split = row.split(factor=factor)
        split.separator()
        return split

    def draw_options_template(self, layout, operator, asset_type):
        pref = addon_prefs()

        layout.label(text="Texture path remapping:")
        split = self._row_split(layout)
        split.prop(pref.import_export, 'textures_backup', text="")

        layout.label(text="Thumbnailer:")
        split = self._row_split(layout)
        row_2 = split.row(align=True)
        col = row_2.column()
        sub_row = col.row(align=True)
        sub_row.prop(self, 'thumbnailer', text=" ", expand=True)
        if self.thumbnailer in {'BLENDER_EEVEE', 'CYCLES'} and \
                LM.active_type.name == 'materials':
            layout.label(text="Preview type:")
            split = self._row_split(layout)
            split.template_icon_view(self, 'material_preview')

        elif self.thumbnailer == 'OGL':
            self.draw_opengl_options(col)

        elif self.thumbnailer == 'THUMB':
            self.draw_thumb_options(layout)

        layout.separator()
        layout.prop(pref.import_export, 'save_to_root')
        layout.separator()

        row = layout.row(align=True)
        row.operator(f'asset_management.{operator}', icon='ADD')
        row.operator(f'asset_management.asset_cancel',
                     icon='X').asset_type = asset_type

    def draw_thumb_options(self, layout):
        layout.label(text="Thumbnail source:")
        split = self._row_split(layout)
        src_row = split.row(align=True)
        src_row.prop(self, 'thumbnail_source', expand=True)
        split_2 = self._row_split(layout)
        if self.thumbnail_source == 'RENDERED':
            split_2.prop_search(self, 'rendered_image', bpy.data, 'images',
                              text="", icon='IMAGE_DATA')
        else:
            row = split_2.row(align=True)
            row.prop(self, 'image_from_computer', text="", icon='IMAGE_DATA')
            row.operator('asset_management.select_image_file', text="",
                         icon='FILEBROWSER')

    def draw_opengl_options(self, layout):
        camera_row = layout.row(align=True)
        camera_row.operator('asset_management.setup_opengl_camera',
                            icon='CAMERA_DATA')
        icon = 'CON_CAMERASOLVER' if \
            bpy.types.ASSET_MANAGEMENT_OT_auto_target._running else \
            'RADIOBUT_OFF'
        camera_row.operator('asset_management.auto_target', text="",
                            icon=icon)
        camera_row.operator('asset_management.remove_opengl_camera',
                            text="", icon='X')


#---------- OBJECTS ----------#

class AmSceneCollections(PropertyGroup):
    collection: PointerProperty(type=bpy.types.Collection)
    to_export: BoolProperty(default=False)


def get_UL_collections(self):
    return set(bpy.data.collections)


def get_updated_collections(self):
    update = set(coll.name for coll in
                 self.UL_collections).symmetric_difference(coll.name for
                                                           coll in
                                                         self.collections)
    if update:
        update_UL_collections(self, list(update))
    return False


def update_UL_collections(self, value):
    if value:
        for coll_name in value:
            coll = bpy.data.collections.get(coll_name)
            if coll is None:
                self.UL_collections.remove(self.UL_collections.find(coll_name))
                self.active_collection_index = 0
            elif coll not in self.collections:
                self.UL_collections.remove(self.UL_collections.find(coll_name))
            else:
                UL_coll = self.UL_collections.add()
                UL_coll.collection = coll
                UL_coll.name = coll_name


class IoExportObjects(CommonIoExportProps):

    objects_from: EnumProperty(
            name="Objects from",
            items=(('SELECTION', "Selection",
                    'Save the objects depending from the selected '
                    'scene options', 'RESTRICT_SELECT_OFF', 0),
                   ('COLLECTIONS', "Collections",
                    'Save all the objects presents in the selected '
                    'collections', 'OUTLINER_COLLECTION', 1)),
            default='SELECTION')

    UL_collections: CollectionProperty(type=AmSceneCollections)

    active_collection_index: IntProperty(default=0)

    collections = property(get_UL_collections)

    collections_watcher: BoolProperty(
            get=get_updated_collections,
            set=update_UL_collections
            )

    include_complete_hierarchy: BoolProperty(
            name="Include complete hierarchy",
            default=True,
            description="Automatically include the complete hierarchy")

    include_parents: BoolProperty(
            name="Include parents",
            default=True,
            description="Automatically include the chain of parents"
            )

    include_children: BoolProperty(
            name="Include children",
            default=True,
            description="Automatically include the chain of children"
            )

    filename: StringProperty(
            name="Filename",
            default="Untitled",
            description="Name of the file asset")

    replace: BoolProperty(
            name="Replace existing",
            default=False,
            description="Use this option to replace the existing file "
                        "otherwise, the file will be incremented")

    use_existing_thumb: BoolProperty(
            name="Use existing Thumb",
            default=False,
            description="If you replace the file, use this option to use the"
                        "existing icon instead of regenerating it")

    def reset_values(self):
        self.filename = "Untitled"
        self.replace = self.use_existing_thumb = False
        self.rendered_image = "Render Result"
        self.image_from_computer = ""

    def draw(self, layout):
        category = LM.active_category
        col = layout.column()

        if self.collections_watcher:
            col.prop(self, "collections_watcher", toggle=True,
                     icon='FILE_REFRESH')

        col.label(text="Save objects from:")
        row = col.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        split.prop(self, 'objects_from', text="")
        if self.objects_from == 'COLLECTIONS':
            col.template_list(
                    "ASSETM_UL_export_collections",
                    "",
                    self,
                    "UL_collections",
                    self,
                    "active_collection_index")
        else:
            col.prop(self, 'include_complete_hierarchy')
            sub_col = col.column()
            sub_col.active = not self.include_complete_hierarchy
            sub_col.prop(self, 'include_parents')
            sub_col.prop(self, 'include_children')

        col.label(text="Filename:")
        row = col.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        sub_col = split.column()
        sub_col.prop(self, 'filename', text="")
        existing_files = [asset.name for asset in category.assets]
        if self.filename in existing_files:
            sub_col.label(text=f"{self.filename} already exists",
                       icon='ERROR')
            sub_col.prop(self, 'replace')
            row = sub_col.row()
            row.active = self.replace
            row.prop(self, 'use_existing_thumb')

        self.draw_options_template(col, 'save_asset', 'objects')


#---------- MATERIALS ----------#

def get_updated_materials(self):
    update = set(mat.name for mat in
                 self.UL_materials).symmetric_difference(mat.name for mat in
                                                         self.materials)
    if update:
        update_UL_materials(self, list(update))
    return False


def update_UL_materials(self, value):
    if value:
        for mat_name in value:
            material = bpy.data.materials.get(mat_name)
            if material is None:
                self.UL_materials.remove(self.UL_materials.find(mat_name))
                self.active_material_index = 0
            elif material not in self.materials:
                self.UL_materials.remove(self.UL_materials.find(mat_name))
            else:
                UL_mat = self.UL_materials.add()
                UL_mat.material = material
                UL_mat.name = mat_name


def get_UL_materials(self):
    if self.materials_from == 'ACTIVE' and bpy.context.object is not None:
        ob = bpy.context.active_object
        return set(slot.material for slot in ob.material_slots if
                   slot.material)

    elif self.materials_from == 'SELECTION' and bpy.context.object is not None:
        return set(slot.material for ob in bpy.context.selected_objects for
                   slot in ob.material_slots if slot.material)

    elif self.materials_from == 'DATA_MATERIALS':
        return set(mat for mat in bpy.data.materials if mat.name != 'Dots Stroke')

    else:
        return set()


def update_Ul_materials(self, context):
    self.UL_materials.clear()
    self.active_material_index = 0


def update_thumbnailer(self, context):
    if self.to_export:
        am = context.window_manager.asset_management
        io_materials = am.io_export.materials
        if len([ul_mat for ul_mat in io_materials.UL_materials if
                ul_mat.to_export]) > 1 and io_materials.thumbnailer not in {
            'BLENDER_EEVEE', 'CYCLES'}:
            io_materials.thumbnailer = 'BLENDER_EEVEE'


class AmSceneMaterials(PropertyGroup):
    material: PointerProperty(type=bpy.types.Material)

    to_export: BoolProperty(
            default=False,
            update=update_thumbnailer)

    replace: BoolProperty(
            name="Replace existing",
            default=False,
            description="Use this option to replace the existing file "
                        "otherwise, the file will be incremented")

    use_existing_thumb: BoolProperty(
            name="Use existing Thumb",
            default=False,
            description="If you replace the file, use this option to use the "
                        "existing icon instead of regenerating it")


def material_previews(self, context):
    return Icons.enum_items


class IoExportMaterials(CommonIoExportProps):

    materials_from: EnumProperty(
            name="Materials from",
            items=(('ACTIVE', "Active object",
                    'Displays the materials of the active object'),
                   ('SELECTION', "Selected objects",
                    'Displays the materials of the selected objects'),
                   ('DATA_MATERIALS', "Data materials",
                    'Displays all materials')),
            default='DATA_MATERIALS',
            update=update_Ul_materials)

    UL_materials: CollectionProperty(type=AmSceneMaterials)

    active_material_index: IntProperty(default=0)

    materials_watcher: BoolProperty(
            get=get_updated_materials,
            set=update_UL_materials
            )

    materials = property(get_UL_materials)

    material_preview: EnumProperty(
            name="Material previews",
            items=material_previews
            )

    def reset_values(self):
        self.rendered_image = "Render Result"
        self.image_from_computer = ""
        for material in self.UL_materials:
            material.to_export = False

    def draw(self, layout):
        col = layout.column()
        if self.materials_watcher:
            col.prop(self, "materials_watcher", toggle=True,
                     icon='FILE_REFRESH')

        col.label(text="Save materials from:")
        row = col.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        split.prop(self, 'materials_from', text="")
        col.template_list(
                "ASSETM_UL_export_materials",
                "",
                self,
                "UL_materials",
                self,
                "active_material_index")

        self.draw_options_template(col, 'save_material', 'materials')


#---------- SCENES ----------#

class IoExportScenes(CommonIoExportProps):
    filename: StringProperty(
            name="Filename",
            default="Untitled",
            description="Name of the file asset")

    replace: BoolProperty(
            name="Replace existing",
            default=False,
            description="Use this option to replace the existing file "
                        "otherwise, the file will be incremented")

    use_existing_thumb: BoolProperty(
            name="Use existing Thumb",
            default=False,
            description="If you replace the file, use this option to use the"
                        "existing icon instead of regenerating it")

    def reset_values(self):
        self.filename = "Untitled"
        self.rendered_image = "Render Result"
        self.image_from_computer = ""

    def draw(self, layout):
        category = LM.active_category
        col = layout.column()

        col.label(text="Filename:")
        row = col.row(align=True)
        split = row.split(factor=0.1)
        split.separator()
        sub_col = split.column()
        sub_col.prop(self, 'filename', text="")
        existing_files = [asset.name for asset in category.assets]
        if self.filename in existing_files:
            sub_col.label(text=f"{self.filename} already exists",
                          icon='ERROR')
            sub_col.prop(self, 'replace')
            row = sub_col.row()
            row.active = self.replace
            row.prop(self, 'use_existing_thumb')

        self.draw_options_template(col, 'save_scene', 'scenes')


class AmIoImport(PropertyGroup):
    objects: PointerProperty(type=IoImportObjects)

    materials: PointerProperty(type=IoImportMaterials)

    import_type: EnumProperty(
            name="Import type",
            items=(('APPEND', "Append", "", 'APPEND_BLEND', 0),
                   ('LINK', "Link", "", 'LINKED', 1)),
            default='APPEND',
            description="Define the type of import"
            )


class AmIoExport(PropertyGroup):
    objects: PointerProperty(type=IoExportObjects)

    materials: PointerProperty(type=IoExportMaterials)

    scenes: PointerProperty(type=IoExportScenes)


CLASSES = (ASSETM_OT_select_image_file,
           IoImportObjects,
           IoImportMaterials,
           IoExportScenes,
           AmSceneCollections,
           AmSceneMaterials,
           IoExportObjects,
           IoExportMaterials,
           AmIoImport,
           AmIoExport)


def register():
    for cls in CLASSES:
        register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        unregister_class(cls)
