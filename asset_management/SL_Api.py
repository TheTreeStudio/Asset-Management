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


from mathutils import Matrix, Vector
from math import log2
from .AmUtils import minimum_blender_version

X_AXIS = Vector((1, 0, 0))
Y_AXIS = Vector((0, 1, 0))
Z_AXIS = Vector((0, 0, 1))
ALL_AXIS = Vector((1, 1, 1))
ZERO = Vector()

class SL_Raycast:
    def __init__(self):
        # distance from polygon for next cast
        self._cast_threshold = 0.001
        # clipping
        self._near_clip = 0
        self._far_clip = 1e32

        # limit to nth intersection of ray cast
        self._max_depth = 100
        self._back_faces = True

        # exclude objects by name
        self._exclude = set()

        self._rv3d = None
        self._region = None

    def start(self, context, exclude):
        self._region = context.region
        self._rv3d = context.space_data.region_3d
        if self._exclude:
            self._exclude.clear()
        for obj in exclude:
            self._exclude.add(obj.name)

    def exit(self):
        self._exclude.clear()

    def _scene_ray_cast(self, context, orig, vec):
        if minimum_blender_version(2, 91, 0):
            return context.scene.ray_cast(
                    depsgraph=context.view_layer.depsgraph,
                    origin=orig,
                    direction=vec)
        else:
            return context.scene.ray_cast(
                    view_layer=context.view_layer,
                    origin=orig,
                    direction=vec)

    @staticmethod
    def event_pixel_coord(event):
        return Vector((event.mouse_region_x, event.mouse_region_y))

    def _region_2d_to_orig_and_view_vector(self, coord):
        viewinv = self._rv3d.view_matrix.inverted()
        persinv = self._rv3d.perspective_matrix.inverted()
        dx = (2.0 * coord[0] / self._region.width) - 1
        dy = (2.0 * coord[1] / self._region.height) - 1

        if self._rv3d.is_perspective:
            origin_start = viewinv.translation.copy()
            out = Vector((dx, dy, -0.5))
            w = out.dot(persinv[3].xyz) + persinv[3][3]
            view_vector = ((persinv @ out) / w) - origin_start
        else:
            view_vector = -viewinv.col[2].xyz
            origin_start = ((persinv.col[0].xyz * dx) +
                            (persinv.col[1].xyz * dy) +
                            persinv.translation)
            if self._rv3d.view_perspective != 'CAMERA':
                # this value is scaled to the far clip already
                origin_offset = persinv.col[2].xyz
                # S.L in ortho view, origin may be plain wrong so add arbitrary distance ..
                origin_start -= origin_offset
        view_vector.normalize()
        return origin_start, view_vector

    def _deep_cast(self, context, screen_pixel_coord):
        """ Find objects below mouse
        :param context:
        :param screen_pixel_coord:
        :return:
        """
        origin, direction = self._region_2d_to_orig_and_view_vector(
                screen_pixel_coord)
        hit = True
        ray_depth = 0
        far_clip = self._far_clip
        dist = self._near_clip
        orig = origin + (direction * dist)
        max_depth = 1
        # ray cast origin may be too close in ortho mode ..
        if not self._rv3d.is_perspective:
            far_clip += 100000
            orig -= direction * 100000

        while hit and dist < far_clip and ray_depth < max_depth:
            hit, pos, normal, face_index, o, matrix_world = \
                self._scene_ray_cast(context,
                                     orig,
                                     direction
                                     )
            if hit:
                dist = (orig - pos).length
                # adjust threshold in single precision range to prevent numerical issues on large objects
                axis = max(o.dimensions[:])
                if axis > 0:
                    # use larger value eg 1 magnitude for exponent ?
                    # exponent = int(log2(axis))
                    exponent = max(0, int(log2(axis)))
                    threshold = pow(2, exponent - 16)
                else:
                    # fallback to default
                    threshold = self._cast_threshold
                orig += direction * (dist + threshold)
                if o.name not in self._exclude and o.visible_get():
                    return hit, pos, normal, face_index, o, \
                           matrix_world

    def cast(self, context, event):
        coords = self.event_pixel_coord(event)
        return self._deep_cast(context, coords)


class SL_Snap:
    changeAxesDict = {
        ("X", "Z"): lambda x, y, z: (z, -y, x),
        ("X", "Y"): lambda x, y, z: (z, x, y),
        ("Y", "Z"): lambda x, y, z: (y, z, x),
        ("Y", "X"): lambda x, y, z: (x, z, -y),

        ("Z", "X"): lambda x, y, z: (x, y, z),
        ("Z", "Y"): lambda x, y, z: (-y, x, z),
        ("-X", "Z"): lambda x, y, z: (-z, y, x),
        ("-X", "Y"): lambda x, y, z: (-z, x, -y),

        ("-Y", "Z"): lambda x, y, z: (-y, -z, x),
        ("-Y", "X"): lambda x, y, z: (x, -z, y),
        ("-Z", "X"): lambda x, y, z: (x, -y, -z),
        ("-Z", "Y"): lambda x, y, z: (y, x, -z),
        }

    @classmethod
    def safe_vectors(cls, direction, guide, main_axis="X", guide_axis="Z"):
        """
        :param direction: Vector, main axis, will be preserved if guide is not perpendicular
        :param guide: Vector or None, may change if not perpendicular to main axis
        :param main_axis: ("X", "Y", "Z", "-X", "-Y", "-Z")
        :param guide_axis: ("X", "Y", "Z")
        :return: 3 non null Vectors as x, y, z axis for orthogonal Matrix
         where direction is on main_axis, guide is on guide_axis
        """
        if guide_axis[-1:] == main_axis[-1:]:
            return X_AXIS, Y_AXIS, Z_AXIS

        if direction == ZERO:
            z = Z_AXIS
        else:
            z = direction.normalized()

        # skip invalid guide
        if guide is None:
            y = ZERO
        else:
            y = z.cross(guide.normalized())

        if y.length < 0.5:
            if guide_axis == "X":
                y = z.cross(X_AXIS)
                if y.length < 0.5:
                    y = Z_AXIS
            elif guide_axis == "Y":
                y = z.cross(Y_AXIS)
                if y.length < 0.5:
                    y = Z_AXIS
            elif guide_axis == "Z":
                y = z.cross(Z_AXIS)
                if y.length < 0.5:
                    y = Y_AXIS

        x = y.cross(z)

        x, y, z = [v.normalized() for v in [x, y, z]]

        unsafe = [v.length < 0.0001 for v in [x, y, z]]

        if any(unsafe):
            raise ValueError("Null vector found %s %s / %s %s %s  %s" % (
                direction, guide, x, y, z, unsafe))

        return cls.changeAxesDict[(main_axis, guide_axis)](x, y, z)

    @classmethod
    def _make_matrix(cls, o, x, y, z):
        return Matrix([
            [x.x, y.x, z.x, o.x],
            [x.y, y.y, z.y, o.y],
            [x.z, y.z, z.z, o.z],
            [0, 0, 0, 1]
            ])

    @classmethod
    def safe_matrix(cls, o, x, z, main_axis="X", guide_axis="Z"):
        vx, vy, vz = cls.safe_vectors(x, z, main_axis, guide_axis)
        return cls._make_matrix(o, vx, vy, vz)

    @classmethod
    def _matrix_from_normal(cls, o, z):
        return cls.safe_matrix(o, z, Z_AXIS, "Z", "Y")
