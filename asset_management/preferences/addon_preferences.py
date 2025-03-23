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
import sys

from bpy.types import AddonPreferences, Operator, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    PointerProperty,
    FloatProperty,
    IntProperty,
    StringProperty
    )

from .addon_updater import Updater

from .. import bl_info
from ..AmIcons import Icons
from ..AmUtils import AddonKeymaps, addon_prefs, wrap_text
from ..AmLibraries import LibrariesManager as LM
from..t3dn_bip import previews


_CREDITS = {
    "Wazou": (
        ("Because we don't change a winning team ;). Check out his addon "
         "collection, i'm sure you'll find what you need."),
        [("SpeedFlow", "https://pitiwazou.gumroad.com/l/speedflow"),
         ("SpeedSculpt", "https://gumroad.com/l/SpeedSculpt"),
         ("SpeedRetopo", "https://gumroad.com/l/speedretopo"),
         ("Easyref", "https://gumroad.com/l/easyref"),
         ("RMB Pie Menu", "https://gumroad.com/l/wazou_rmb_pie_menu_v2"),
         ("Wazou's Pie Menu", "https://gumroad.com/l/wazou_pie_menus")]),
    "Stephen Leger": (
        ("Thanks to him for his precious help. Don't hesitate to check his "
         "addons which are worth their weight in gold."),
        [("Archipack", "https://gumroad.com/l/ZRMyP"),
         ("CAD Transform", "https://blender-archipack.gumroad.com/l/nQVcS")]),
    "Ben Bellavia": (
        ("Creator of the Zantique sphere, recovered from Blend Swap."),
        [("Zantique sphere", "https://www.blendswap.com/blends/view/86037")])
    }

_SIZE_ICONS_INFO = """Loading icons with a resolution of 256x256 will allow 
you to display sharper icons but, depending of the number of thumbnails to 
be displayed, may cause a slight latency in the icon popup when moving the 
mouse."""

class ASSETM_OT_open_preferences(Operator):
    """ Open the addon preferences """
    bl_idname = 'asset_management.open_preferences'
    bl_label = "Open preferences"
    bl_options = {'REGISTER'}

    def execute(self, context):
        addon_pref = addon_prefs()
        context.preferences.active_section = "ADDONS"
        addon_name = bl_info["name"]
        module_name = __package__.split(".")[0]
        context.window_manager.addon_search = addon_name
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        bpy.ops.preferences.addon_expand(module=module_name)
        addon_pref.layout_preferences = 'OPTIONS'
        addon_pref.addon_pref.draw_layout = True
        return {'FINISHED'}


class Templates:

    @staticmethod
    def box_template(layout, data, attr, text):
        box = layout.box()
        header = box.row(align=True)
        icon = 'TRIA_DOWN' if getattr(data, attr) else 'TRIA_RIGHT'
        header.prop(data, attr, text="", icon=icon, emboss=False)
        header.label(text=text)
        return box


class ASSETM_OT_check_for_update(Operator):
    """ Checks if a new update exists even if the 'Automatic check for update'
    option is disabled """
    bl_idname = 'asset_management.check_for_update'
    bl_label = "Check for update manually"
    bl_options = {'REGISTER'}

    def execute(self, context):
        Updater.async_check_update(manual=True)
        return {'FINISHED'}


def check_for_update(self, context):
    if self.check_update:
        Updater.async_check_update(check_update=True)


def _update_icons_loading(self, context):
    def update(category):
        pcoll = category.assets.pcoll
        if pcoll is not None:
            previews.remove(pcoll)
            category.assets._pcoll = None
        for cat in category.categories.values():
            update(cat)

    for library in LM.libraries.values():
        for type_ in library.asset_types.values():
            for category in type_.categories.values():
                update(category)


class AssetManagementAddonPreferences(PropertyGroup, Templates):

    draw_layout: BoolProperty(
            name="Addon",
            default=False,
            description="Displays addon preferences"
            )

    icon_size: EnumProperty(
            name="icon size",
            items=(('128', "128x128", ""),
                   ('256', "256x256", "")),
            default='128',
            description="Maximum size which icons will be loaded",
            update=_update_icons_loading
            )

    check_update: BoolProperty(
            name="Automatic check for update",
            default=True,
            description="Checks if a more recent update exists.",
            update=check_for_update
            )

    pillow: BoolProperty(
            name="Ask for Pillow module installation",
            default=True
            )

    file_debug_path: StringProperty(
            name="Location",
            default="",
            subtype='DIR_PATH',
            maxlen=1048
            )

    @staticmethod
    def draw_download_platform(layout):
        gumroad_ico = Icons.get("gumroad")
        market_ico = Icons.get("market")
        box = layout.box()
        box.label(text="New update available")
        row = box.row(align=True)
        row.alignment = "CENTER"
        row.scale_x = 1.5
        row.operator("wm.url_open",
                     text="Gumroad",
                     icon_value=gumroad_ico.icon_id
                     ).url = "https://gum.co/asset_management"
        row.operator("wm.url_open",
                     text="Blender Market",
                     icon_value=market_ico.icon_id
                     ).url = \
            "https://blendermarket.com/products/asset-management"

    def draw(self, layout):
        box = self.box_template(layout, self, 'draw_layout', "Addon")
        if self.draw_layout:
            row = box.row(align=True)
            split = row.split(factor=0.04)
            split.separator()
            col = split.column()
            if not 'PIL' in sys.modules:
                col.operator('asset_management.install_pillow',
                             text="Intall Pillow module",
                             icon='MODIFIER')
                col.separator()

            if 'PIL' in sys.modules:
                col.prop(self, 'icon_size')
                if self.icon_size == '256':
                    box = col.box()
                    box.label(text="INFO", icon='ERROR')
                    for line in wrap_text(_SIZE_ICONS_INFO):
                        box.label(text=line)

            col.separator()
            col.prop(self, "check_update")
            if Updater.update_available:
                self.draw_download_platform(col)
            col.operator('asset_management.check_for_update',
                         icon='FILE_REFRESH'
                         )
            col.separator()
            row = col.row()
            row.alignment = 'CENTER'
            row.label(text="RENDER LOGS")
            col.prop(self, 'file_debug_path', text="Path to save logs")
            col.operator('asset_management.print_render_logs', icon='TEXT')


class AssetManagementInterfacePreferences(PropertyGroup, Templates):
    draw_layout: BoolProperty(
            name="Interface",
            default=False,
            description="Display the interface preferences"
            )

    asset_types_labels: BoolProperty(
            name="Show asset types labels",
            default=True,
            description="Display the asset type labels"
            )

    show_labels: BoolProperty(
            name="Show asset names in the preview popup",
            default=True,
            description="Show asset names in the preview popup"
            )

    preview_size: FloatProperty(
            name="Preview size",
            default=6.0,
            min=1.0, max=100.0,
            description="Scale the button icon size"
            )

    popup_icon_size: FloatProperty(
            name="Popup icon size",
            default=7.0,
            min=1.0, max=100.0,
            description="Scale the popup icon size"
            )

    def draw(self, layout):
        box = self.box_template(layout, self, 'draw_layout', "Interface")
        if self.draw_layout:
            col = box.column()
            col.use_property_split = True
            col.prop(self, 'asset_types_labels')
            col.prop(self, 'show_labels')
            col.prop(self, 'preview_size')
            col.prop(self, 'popup_icon_size')


class CyclesPreferences(PropertyGroup, Templates):

    draw_layout: BoolProperty(
            name="Cycles options",
            default=False,
            description="Display the options for Cycles render"
            )

    device: EnumProperty(
            name="Device",
            items=(('CPU', "CPU", "Use CPU for rendering"),
                   ('GPU', "GPU compute", "Use GPU compute device for "
                                          "rendering")),
            default='CPU',
            description="Device to use for rendering"
            )

    samples: IntProperty(
            name="Samples",
            default=300,
            description="Number of samples for rendering"
            )

    def draw(self, layout):
        box = self.box_template(layout, self, 'draw_layout', "Cycles options")
        if self.draw_layout:
            col = box.column()
            col.use_property_split = True
            col.prop(self, 'device')
            col.prop(self, 'samples')


class AssetManagementImportExportPreferences(PropertyGroup,Templates):

    draw_layout: BoolProperty(
            name="Export",
            default=False,
            description="Display export preferences"
            )

    lock_import: BoolProperty(
            name="Lock Import from popup preview",
            default=False,
            description="Lock the append/link from the preview"
            )

    linked_to_coll: BoolProperty(
            name="Parent the linked asset to collection",
            default=False,
            description="Parent the linked asset to a collection"
            )

    load_ui: BoolProperty(
            name="Load UI",
            default=True,
            description="Load user interface setup when open scene asset"
            )

    object_import: EnumProperty(
            name="Object import behaviour",
            items=(('DRAG_REPEAT', "Drag repeat",
                    "Same as 'Drag' but repeats the import after dropping "
                    "the asset", 'ONIONSKIN_ON', 2),
                   ('DRAG', "Drag",
                    "Drag and click to drop the asset in  the desired "
                    "location", 'VIEW_PAN', 1),
                   ('ON_CURSOR', "On 3D cursor",
                    "append/link the asset on the 3D cursor",
                    'PIVOT_CURSOR', 0)
                   ),
            default='DRAG'
            )

    material_import: EnumProperty(
            name="Material import behaviour",
            items=(('ACTIVE', "Active slot",
                    "Apply the material to the active slot of the selected "
                    "objects", 'MATERIAL', 1),
                   ('PICKER', "Face picker",
                    "Apply the material to the picked faces", 'EYEDROPPER', 0)
                   ),
            default='PICKER'
            )

    save_to_root: BoolProperty(name="Save to root",
                               default=False,
                               description="Save the asset at the root of "
                                           "the category instead of in the "
                                           "'file' folder")

    thumb_resolution: IntProperty(
            name="Thumb resolution",
            default=256,
            min=64,
            max=1024,
            subtype="PIXEL",
            description="Number of vertical pixels in rendered thumbnail"
            )

    thumb_format: EnumProperty(
            name="Format",
            items=(("JPEG", ".jpeg", "Output thumbnail in JPEG format",
                    "FILE_IMAGE", 0),
                   ("PNG", ".png", "Output thumbnail in PNG format",
                    "FILE_IMAGE", 1)
                   ),
            default="JPEG",
            description="File format to save the thumbnail as")

    textures_backup: EnumProperty(
            name="Textures path remapping",
            items=(('PACK', "Pack", 'Pack the textures in the blendfile'),
                   ('RELATIVE', "Relative remap",
                    'Remaps the textures paths into a relative path'),
                   ('ABSOLUTE', "Absolute remap",
                    'Remaps the textures paths into a absolute path'),
                   ('TEX_FOLDER', "TEX folder",
                    'Created a TEX_ folder to save the textures and remap '
                    'their paths into the asset file')),
            default='RELATIVE',
            description="Type of texture path remapping"
            )

    eevee_options: BoolProperty(
            name="Eevee options",
            default=False,
            description="Display the options for eevee render"
            )

    eevee_samples: IntProperty(
            name="Samples",
            default=100,
            description="Number of samples for rendering"
            )

    cycles_options: PointerProperty(type=CyclesPreferences)

    def _cycles(self):
        return bpy.context.preferences.addons.get('cycles')

    def _eevee_options(self, layout):
        box = self.box_template(layout, self, 'eevee_options', "Eevee options")
        if self.eevee_options:
            col = box.column()
            col.use_property_split = True
            col.prop(self, 'eevee_samples')

    def draw(self, layout):
        box = self.box_template(layout, self, 'draw_layout', "Import/Export")
        if self.draw_layout:
            col = box.column()
            col.use_property_split = True
            col.prop(self, 'lock_import')
            col.prop(self, 'linked_to_coll')
            col.prop(self, 'object_import')
            col.prop(self, 'material_import')
            col.prop(self, 'load_ui')
            col.separator(factor=5)
            col.prop(self, 'save_to_root')
            col.separator()
            col.prop(self, 'thumb_resolution')
            col.prop(self, 'thumb_format')
            col.separator()
            col.prop(self, 'textures_backup')

            col = box.column(align=True)
            self._eevee_options(col)
            if self._cycles():
                self.cycles_options.draw(col)


class AssetManagementPreferences(AddonPreferences, Templates):
    bl_idname = __name__.split(".")[0]

    layout_preferences: EnumProperty(
            name="Layout Preferences",
            items=(("OPTIONS", "Options", "", "PREFERENCES", 0),
                   ("RELEASE_NOTE", "Release note", "", "FILE_TEXT", 1),
                   ("CREDITS", "Credits", "", "TEXT", 2)
                   ),
            default="OPTIONS"
            )

    addon_pref: PointerProperty(type=AssetManagementAddonPreferences)

    interface: PointerProperty(
            type=AssetManagementInterfacePreferences)

    import_export: PointerProperty(
            type=AssetManagementImportExportPreferences)

    keymaps: BoolProperty(name="Keymaps",
                          default=False,
                          description="Display keymaps preferences")

    def options_layout(self, layout):
        col = layout.column(align=True)
        self.addon_pref.draw(col)
        self.interface.draw(col)
        self.import_export.draw(col)
        box = self.box_template(col, self, 'keymaps', "Keymaps")
        if self.keymaps:
            AddonKeymaps.draw_keymap_items(bpy.context.window_manager, box)

    @staticmethod
    def release_note_layout(layout):
        box = layout.box()
        release_note = Updater._json.get("release_note")
        if release_note:
            for line in release_note.split("\r"):
                box.label(text=line.split("\n")[-1])
        else:
            box.label(text="No release note found")

    def credits_layout(self, layout):
        box = layout.box()
        for credit, content in _CREDITS.items():
            text, infos = content
            box.label(text=f"{credit}:")
            row = box.row(align=True)
            split = row.split(factor=0.05)
            split.separator()
            col = split.column()
            for line in wrap_text(text):
                col.label(text=line)
            for info in infos:
                title, url = info
                col.operator("wm.url_open", text=title).url = url

    def draw(self, context):
        layout = self.layout
        dicord_ico = Icons.get("discord")
        discord_row = layout.row()
        discord_row.scale_y = 1.2
        discord_row.alignment = 'CENTER'
        discord_row.operator("wm.url_open",
                             text="SUPPORT ON DISCORD FOR CUSTOMERS",
                             icon_value=dicord_ico.icon_id).url = \
            "https://discord.gg/ctQAdbY"

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.prop(self,
                 "layout_preferences",
                 expand=True
                 )
        getattr(self, f"{self.layout_preferences.lower()}_layout")(
                layout)


CLASSES = (ASSETM_OT_open_preferences,
           ASSETM_OT_check_for_update,
           AssetManagementAddonPreferences,
           AssetManagementInterfacePreferences,
           CyclesPreferences,
           AssetManagementImportExportPreferences,
           AssetManagementPreferences)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
