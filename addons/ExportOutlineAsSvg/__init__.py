import bpy
import os
import csv
from pathlib import Path

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


def get_polylines(object):
    edges = object.data.edges    
    polylines = [[edge.vertices[0], edge.vertices[1]] for edge in edges]
    remove = 0
    
    while remove >= 0:
        remove = -1
        i = 0
        while i < len(polylines) and remove < 0:
            j = i + 1
            while j < len(polylines) and remove < 0:
                polyline_a = polylines[i]
                polyline_b = polylines[j]
                if (polyline_a[0] == polyline_b[0] or
                        polyline_a[-1] == polyline_b[-1]):
                    polyline_b.reverse()
                
                if polyline_a[0] == polyline_b[-1]:
                    remove = i
                    del polyline_b[-1]
                    polyline_b.extend(polyline_a)
                    
                elif polyline_a[-1] == polyline_b[0]:
                    remove = j
                    del polyline_a[-1]
                    polyline_a.extend(polyline_b)
                j += 1
            i += 1
        
        if remove >= 0:
            del polylines[remove]
    
    return polylines


def get_polyline_string(object, polyline, scale):
    vertices = object.data.vertices
    min_horizontal = filter_object_co(object, 0, min)
    max_vertical = filter_object_co(object, 1, max)
    points = []
    for point in polyline:
        x_point = vertices[point].co.x - min_horizontal
        y_point = max_vertical - vertices[point].co.y
        points.append(f"{x_point * scale}, {y_point * scale}")
    point_con = " ".join(points)
    return f"""
<polyline id="{object.name}" style="stroke:black;stroke-width:.5;fill:none;"
points="{point_con}"/>
"""


def filter_object_co(object, plane, f):
    return f([v.co[plane] for v in object.data.vertices])


# TODO:
# - add option for specifying the projection plane (currently Z is hardcoded)
# - add option to use coordinates where transformations are applied
# - handle split path and not only polylines
def write_outline_as_svg(
        context = bpy.context,
        file_path = None,
        active_only = False,
        fail_on_non_closing_edge_loops = False,
        transform_relative_to_active = True,
        use_different_file_per_object = False,
        scale_via_svg_scaling = True,
        scale_factor = 3.7795275590551):

    active_object = context.active_object
    if file_path is None:
        file_path = Path(f'~/{active_object.name}.svg').expanduser()

    objects = context.selected_objects
    if active_only:
        objects = [active_object]

    files = {}
    if len(objects) != 1 and use_different_file_per_object:
        path = Path(file_path)
        for object in objects:
            key = f"{path.parent}/{path.stem}_{object.name}{path.suffix}"
            files[key] = [object]

    else:
        files[file_path] = objects
    
    for file_path, objects in files.items():
        with open(file_path, 'w', encoding='UTF-8') as f:
            size_relavant_objects = objects.copy()
            if transform_relative_to_active:
                size_relavant_objects.append(active_object)
            width = (max([filter_object_co(o, 0, max) for o in size_relavant_objects]) - min([filter_object_co(o, 0, min) for o in size_relavant_objects])) * scale_factor
            height = (max([filter_object_co(o, 1, max) for o in size_relavant_objects]) - min([filter_object_co(o, 1, min) for o in size_relavant_objects])) * scale_factor
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" viewbox="0 0 {width} {height}" width="{width}px" height="{height}px">\n')
            for object in objects:
                transformX = 0
                transformY = 0
                if transform_relative_to_active:
                    transformX = filter_object_co(object, 0, min) - filter_object_co(active_object, 0, min)
                    transformY = -1 * (filter_object_co(object, 1, max) - filter_object_co(active_object, 1, max))
                    if not scale_via_svg_scaling:
                        transformX = (filter_object_co(object, 0, min) - filter_object_co(active_object, 0, min)) * scale_factor
                        transformY = -1 * (filter_object_co(object, 1, max) - filter_object_co(active_object, 1, max)) * scale_factor

                if scale_via_svg_scaling:
                    f.write(f'<g transform="scale({scale_factor}) translate({transformX},{transformY})">')
                else:
                    f.write(f'<g transform="translate({transformX},{transformY})">')
                for polyline in get_polylines(object):
                    if fail_on_non_closing_edge_loops and polyline[0] != polyline[-1]:
                        context.scene.cursor.location = object.data.vertices[polyline[0]].co
                        error = f'Object: {object_name}; non polyline from vert at {polyline[0]} to vert at {polyline[-1]}'
                        raise RuntimeError(error)

                    if scale_via_svg_scaling:
                        f.write(get_polyline_string(object, polyline, 1))
                    else:
                        f.write(get_polyline_string(object, polyline, scale_factor))

                f.write("</g>\n")
            f.write("</svg>\n");

    return {'FINISHED'}


class ExportOutlineAsSvg(Operator, ExportHelper):
    """Exports the 3d model to an 2d svg consisting of polylines by eliminating one dimension by projecting it and mapping edges to polylines."""

    bl_idname = "export.outline_svg"
    bl_label = "Export outline as SVG"

    # ExportHelper mix-in class uses this.
    filename_ext = ".svg"

    filter_glob: StringProperty(
        default="*.svg",
        options={'HIDDEN'},
        maxlen=255,
    )

    export_only_active: BoolProperty(
        name="Export only active object",
        description="Export only active object instead of every selected object",
        default=False,
    )

    fail_on_non_closing_edge_loops: bpy.props.BoolProperty(
        name="Fail on non closing edge loops",
        description="Throw exception and stop export and finding at least one open edge loop",
        default=False,
    )

    transform_relative_to_active: bpy.props.BoolProperty(
        name="Transform relative to active",
        description="Don't use absolute coordinates but take the active object as frame of reference",
        default=True,
    )

    use_different_file_per_object: bpy.props.BoolProperty(
        name="Use different file per object",
        description="Don't use absolute coordinates but take the active object as frame of reference",
        default=True,
    )

    scale_via_svg_scaling: bpy.props.BoolProperty(
        name="Use svg scaling tag",
        description="Use scaling via svg transform tag instead of scaling the points inside the plugin.",
        default=True,
    )

    scale_factor: bpy.props.FloatProperty(
        name="Scale factor",
        description="Scale object by this factor (eg for converting from px to mm)",
        default = 3.7795275590551,
    )


    def execute(self, context):
        return write_outline_as_svg(
                context,
                self.filepath,
                self.export_only_active,
                self.fail_on_non_closing_edge_loops,
                self.transform_relative_to_active,
                self.use_different_file_per_object,
                self.scale_via_svg_scaling,
                self.scale_factor)


def menu_func_export(self, context):
    self.layout.operator(ExportOutlineAsSvg.bl_idname, text="Export Outline as SVG")

bl_info = {
    "name": "Export Outline as SVG",
    "description": "Export Outline as SVG",
    "author": "Markus Schoetz <holzwurmi>",
    "version": (0, 0, 0),
    "blender": (2, 93, 0),
    "location": "File > Export > Scalable Vector Graphics (.svg)",
    "category": "Export"}

# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(ExportOutlineAsSvg)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportOutlineAsSvg)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export.outline_svg('INVOKE_DEFAULT')
