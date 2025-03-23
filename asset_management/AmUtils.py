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

__all__ = ('AmJson', 'AmPath', 'AmName')

import bpy
import os
import blf
import shutil
import json
import re
import subprocess
import rna_keymap_ui

from distutils import dir_util
from mathutils import Vector

from .ressources.constants import SUPPORTED_FILES, SUPPORTED_ICONS


def minimum_blender_version(major, minor, rev):
    return bpy.app.version >= (major, minor, rev)


def addon_prefs():
    """
    Get the addon preferences
    :return: Asset management preferences
    """
    addon_key = __package__.split(".")[0]
    return bpy.context.preferences.addons[addon_key].preferences


class AmJson:

    @staticmethod
    def save_as_json_file(file, data):
        with open(file, 'w', encoding="utf-8") as jsonf:
            json.dump(data, jsonf, indent=4)

    @staticmethod
    def load_json_file(file):
        if not os.path.exists(file):
            return None

        with open(file, 'r') as jsonf:
            content = json.load(jsonf)
        return content


class AmPath:

    @staticmethod
    def addon_path():
        """ Returns the addon path """

        (addon_path, current_dir) = os.path.split(os.path.dirname(
                os.path.abspath(__file__)))

        return addon_path

    @staticmethod
    def create_folder(path):
        os.makedirs(path)

    @classmethod
    def get_folder(cls, *args):
        full_path = os.path.join(*args)
        if not os.path.exists(full_path):
            cls.create_folder(full_path)
        return full_path

    @staticmethod
    def remove_tree(path):
        if path is not None and os.path.exists(path):
            dir_util.remove_tree(path)
            print(f"\"{path}\" has been completely deleted from your hard "
                  f"drive")

    @staticmethod
    def remove_file(path, output=True):
        if path is not None and os.path.exists(path):
            os.remove(path)
            if output:
                print(f"\"{path}\" has been completely deleted from your "
                      f"hard drive")

    @staticmethod
    def get_dirs(path):
        if path is None or not os.path.exists(path):
            return None
        return next(os.walk(path))[1]

    @staticmethod
    def sort_path_by_name(path_list, reverse=False):
        sorted_path = sorted(
                path_list, key=lambda path: os.path.basename(path).lower(),
                reverse=reverse
                )
        return sorted_path

    @classmethod
    def get_export_dirs(cls, path, from_root):
        asset_path = icon_path = path

        if not from_root:
            asset_path = cls.get_folder(asset_path, "files")
            icon_path = cls.get_folder(icon_path, "icons")

        return asset_path, icon_path

    @staticmethod
    def path_is_relative(path):
        return path.startswith("//")

    @classmethod
    def normalized_path(cls, path):
        if cls.path_is_relative(path):
            return path.replace("//", "./")
        return path

    @classmethod
    def _get_absolute_path_from_relative(cls, path):
        abspath = os.path.realpath(bpy.path.abspath(path))
        if os.path.exists(abspath):
            return abspath
        return None

    @classmethod
    def path_is_valid(cls, path):
        if cls.path_is_relative(path) and bpy.data.filepath:
            return os.path.exists(cls._get_absolute_path_from_relative(path))
        return os.path.exists(path)

    @classmethod
    def convert_path_to_absolute(cls, path):
        if not cls.path_is_valid(path):
            print(f"{path}: Invalid path. The path cannot be made "
                  f"absolute.")
            return None

        if not cls.path_is_relative(path):
            return path
        return cls._get_absolute_path_from_relative(path)

    @classmethod
    def convert_path_to_relative(cls, path):
        """
        Returns the relative file path to the path passed in parameter from
        the current file.
        If relative path conversion is not possible, the absolute path will
        be returned
        @param path: String, absolute path of the image
        """
        if not cls.path_is_valid(path):
            print(f"{path}: Invalid path. The path cannot be made relative.")
            return None

        if cls.path_is_relative(path):
            path = cls._get_absolute_path_from_relative(path)
        try:
            os.path.commonpath([bpy.data.filepath, path])
            return bpy.path.relpath(path)
        except:
            print("Paths don't have the same drive, filepath can't be made "
                  "relative")
            return path


class AmName:
    @staticmethod
    def get_splitted_name_from_ext(name):
        basename, ext = os.path.splitext(name)
        if ext.lower() in SUPPORTED_FILES or ext.lower() in SUPPORTED_ICONS:
            return basename, ext
        return name, ""

    @staticmethod
    def get_increment(name):
        """
        Get the increment of the name if there is one
        :param name: String, name to be tested
        :return: String, increment value
        """
        regex = r"[\._]*\d+$"
        result = re.search(regex, name)
        return result.group() if result is not None else None

    @classmethod
    def get_numerical_increment(cls, name):
        increment = cls.get_increment(name)
        if increment is not None:
            regex = r"\d+$"
            value = re.search(regex, increment)
            return value.group() if value is not None else increment
        return None

    @classmethod
    def incremented_name(cls, name):
        """
        Increment the name
        :param name: String, name to be incremented
        :return: String, incremented name
        """
        basename, ext = cls.get_splitted_name_from_ext(name)
        increment = cls.get_numerical_increment(basename)
        if increment:
            incremented = str(int(increment) + 1).zfill(len(increment))
            return f"{basename[:-len(increment)]}{incremented}{ext}"

        else:
            return f"{basename}_001{ext}"

    @classmethod
    def get_valid_name(cls, name, existing_names):
        """
        Generate a unique name
        :param name: String, name whose uniqueness must be tested
        :param existing_names: List, list of existing name
        :return: String, unique name
        """
        if name.count(" ") == len(name):
            name = "Untitled"

        if name not in existing_names:
            return name

        incremented_name = cls.incremented_name(name)
        if incremented_name not in existing_names:
            return incremented_name

        return cls.get_valid_name(incremented_name, existing_names)

    @classmethod
    def rename(cls, path, new_name):
        path_root = os.path.dirname(path)
        subfolders = AmPath.get_dirs(path_root)
        valid_name = cls.get_valid_name(new_name, subfolders)
        new_path = os.path.join(path_root, valid_name)
        shutil.move(path, new_path)
        return new_path


class AddonKeymaps:
    _addon_keymaps = []
    _keymaps = {}

    @classmethod
    def new_keymap(cls, name, kmi_name, kmi_value=None, km_name='3D View',
                   space_type="VIEW_3D", region_type="WINDOW",
                   event_type=None, event_value=None, ctrl=False, shift=False,
                   alt=False, key_modifier="NONE"):

        cls._keymaps.update({name: [kmi_name, kmi_value, km_name, space_type,
                                    region_type, event_type, event_value,
                                    ctrl, shift, alt, key_modifier]
                             })

    @classmethod
    def add_hotkey(cls, kc, keymap_name):

        items = cls._keymaps.get(keymap_name)
        if not items:
            return

        kmi_name, kmi_value, km_name, space_type, region_type = items[:5]
        event_type, event_value, ctrl, shift, alt, key_modifier = items[5:]
        km = kc.keymaps.new(name=km_name, space_type=space_type,
                            region_type=region_type)

        kmi = km.keymap_items.new(kmi_name, event_type, event_value,
                                  ctrl=ctrl,
                                  shift=shift, alt=alt,
                                  key_modifier=key_modifier
                                  )

        kmi.active = True

        cls._addon_keymaps.append((km, kmi))

    @classmethod
    def register_keymaps(cls):
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            return

        for keymap_name in cls._keymaps.keys():
            cls.add_hotkey(kc, keymap_name)

    @classmethod
    def unregister_keymaps(cls):
        kmi_names = [item[0] for item in cls._keymaps.values()]

        for km, kmi in cls._addon_keymaps:
            if kmi_names:
                if kmi.idname in kmi_names:
                    km.keymap_items.remove(kmi)

        cls._addon_keymaps.clear()

    @staticmethod
    def get_hotkey_entry_item(name, kc, km, kmi_name, col):
        if km.keymap_items.get(kmi_name):
            col.context_pointer_set('keymap', km)
            rna_keymap_ui.draw_kmi([], kc, km, km.keymap_items[kmi_name],
                                   col, 0)

        else:
            col.label(text=f"No hotkey entry found for {name}")
            col.operator('asset_management.restore_hotkey',
                         text="Restore keymap",
                         icon='ADD').km_name = km.name

    @classmethod
    def draw_keymap_items(cls, wm, layout):
        kc = wm.keyconfigs.user

        for name, items in cls._keymaps.items():
            kmi_name, kmi_value, km_name = items[:3]
            box = layout.box()
            split = box.split()
            col = split.column()
            col.label(text=name)
            col.separator()
            km = kc.keymaps[km_name]
            cls.get_hotkey_entry_item(name, kc, km, kmi_name, col)


class Console:
    output = []

    @classmethod
    def clear_output(cls):
        cls.output.clear()


class AmBackgroundProcessor:

    def __init__(self):
        self._cmd = [bpy.app.binary_path,
                    "--python",
                    "--"]

    def _fill_cmd(self, script_path, blendfile, background, *args):
        if background:
            commands = ["--background", "--factory-startup", "-noaudio"]
            for i, cmd in enumerate(commands):
                self._cmd.insert(i+1, cmd)

        if blendfile is not None:
            self._cmd.insert(1, blendfile)

        self._cmd.insert(self._cmd.index("--"), script_path)

        for arg in args:
            self._cmd.append(arg)

    def run_process(self, script_path, blendfile, background, *args):

        self._fill_cmd(script_path, blendfile, background, *args)

        print("############   Processing   ############")

        popen = subprocess.Popen(self._cmd,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True,
                                 encoding='utf-8'
                                 )

        for stdout_line in iter(popen.stdout.readline, ""):
            yield stdout_line

        popen.stdout.close()
        popen.wait()

        print("############   Process finished   ############")


class Thumbnailer(AmBackgroundProcessor):

    def _generate_thumbnail_cmd(self, data_paths, thumb_dir, engine):
        export_prefs = addon_prefs().import_export

        self._cmd.extend([f"package:{__package__}",
                          f"engine:{engine}",
                          f"thumb_reso:{export_prefs.thumb_resolution}",
                          f"file_format:{export_prefs.thumb_format}",
                          f"thumb_dir:{thumb_dir}",
                          f"files:{'|'.join(data_paths)}"])

        exec(f"self._fill_cmd_{engine.lower()}(export_prefs)")

    def _fill_cmd_blender_eevee(self, export_prefs):
        self._cmd.append(f"samples:{export_prefs.cycles_options.samples}")

    def _fill_cmd_cycles(self, export_prefs):
        cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
        cycles = export_prefs.cycles_options
        self._cmd.extend(
                [f"device_type:{cycles_prefs.compute_device_type}",
                 f"scn_device:{cycles.device}",
                 f"samples:{cycles.samples}"]
                )

    @staticmethod
    def is_view_camera(context):
        for area in context.screen.areas:
            if area.type != "VIEW_3D":
                continue
            return area.spaces[0].region_3d.view_perspective == "CAMERA"
        return

    @staticmethod
    def add_camera(context, name):
        render = context.scene.render
        scn = context.scene
        data_cam = bpy.data.cameras.new(name)
        camera = bpy.data.objects.new(name, data_cam)
        scn.collection.objects.link(camera)
        scn.camera = camera
        camera.data.lens = 75
        render.resolution_x = render.resolution_y = 256
        render.resolution_percentage = 100
        return camera

    @staticmethod
    def get_camera(name=None):
        if name is not None:
            return bpy.data.objects.get(name)
        return bpy.context.scene.camera

    @classmethod
    def set_camera_framing(cls, context, camera):
        if not cls.is_view_camera(context):
            bpy.ops.view3d.camera_to_view()
        bpy.ops.view3d.camera_to_view_selected()

        vec = Vector((0.0, 0.0, 0.3))
        inv = camera.matrix_world.copy()
        inv.invert()
        # vec aligned to local axis
        vec_rot = vec @ inv
        camera.location = camera.location + vec_rot

    @staticmethod
    def setup_render_setting(engine, reso, file_format, samples,
                             device_type=None, scn_device=None):
        scn = bpy.context.scene
        render = scn.render
        render.engine = engine
        render.resolution_x = render.resolution_y = reso
        render.image_settings.file_format = file_format.upper()
        render.resolution_percentage = 100
        if engine == "CYCLES":
            scn.cycles.device = scn_device
            if scn_device == 'GPU':
                cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
                cycles_prefs.compute_device_type = device_type
                devices = cycles_prefs.get_devices(compute_device_type=device_type)
                if devices:
                    for device in devices[0]:
                        if device.type == device_type:
                            device.use = True
                        else:
                            device.use = False

            scn.cycles.samples = samples
            scn.cycles.use_denoising = True

        else:
            scn.eevee.taa_render_samples = samples

    def run_background_render(self, script_path, blendfile, data_paths,
                           thumb_dir, engine):
        self._generate_thumbnail_cmd(data_paths, thumb_dir, engine)

        Console.output.append("#-------   RENDERING   -------#")

        for line in self.run_process(
                script_path,
                blendfile,
                True,
                *self._cmd):
            Console.output.append(line)
            print(line)

    def run_opengl_render(self, context, am_asset):
        if not self.get_camera("opengl_cam"):
            bpy.ops.asset_management.setup_opengl_camera()

        context.space_data.overlay.show_overlays = False
        file_format = addon_prefs().import_export.thumb_format
        image_path = os.path.join(
                am_asset.icon_dir, f"{am_asset.name}.{file_format.lower()}")
        context.scene.render.filepath = image_path
        bpy.ops.render.opengl(write_still=True)
        bpy.ops.asset_management.remove_opengl_camera()

    def save_rendered_image(self, io_export, am_asset):
        file_format = addon_prefs().import_export.thumb_format
        if io_export.thumbnail_source == 'RENDERED':
            try:
                image_path = os.path.join(
                        am_asset.icon_dir,
                        f"{am_asset.name}.{file_format.lower()}")
                bpy.data.images[io_export.rendered_image].save_render(
                        filepath=image_path)
                return
            except:
                return f"No rendered image found here"

        # FROM_COMPUTER
        src = io_export.image_from_computer
        if src:
            ext = os.path.splitext(src)[-1]
            dst = os.path.join(
                        am_asset.icon_dir,
                        f"{am_asset.name}{ext}")

            shutil.copy2(src, dst)
            return

        return f"Invalid image path given: {io_export.image_from_computer}"


def wrap_text(text: str):
    return_text = []
    row_text = ''

    width = bpy.context.region.width
    system = bpy.context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11)

    for word in text.split():
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)

        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word

    if row_text:
        return_text.append(row_text)

    return return_text