import bpy
import os

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

# see: https://stackoverflow.com/questions/34439/finding-what-methods-a-python-object-has
def get_methods(object):
    return [method_name for method_name in dir(object) if callable(getattr(object, method_name))]

def write_gcode_section(section_name, data, file):
    print(f"({section_name})", file=file)
    for command, description in data:
        d = f"({description})\n" if description else ""
        print(f"{d}{command}", file=file)
    
    print("", file=file)

def write_gcode_head(file):
    data = [
        ("G21", "interprete given data in mm"),
        ("G17", "select X Y plane"),
        ("G90", "use absolute coordinates"),
        ("G92 X0 Y0 Z0", "specify that the head’s current XYZ position is 0, 0, 0"),
        #("G1 X0 Y0 Z0", "use non rapid linear movement for coordinates"),
    ]
    write_gcode_section("head", data, file)
    
def write_gcode_foot(file):
    data = [
        #("G28", "home all axes")
    ]
    write_gcode_section("foot", data, file)

def get_gcode_move_string(base_co, to_co, factor):
    return f"G1 X{(to_co[0] - base_co[0]) * factor} Y{(to_co[1] - base_co[1]) * factor} Z{(to_co[2] - base_co[2]) * factor}"

def get_gcode_path(
        object,
        starting_index,
        apply_transformations,
        feed_down,
        feed_plane,
        scale_factor):

    verts = [[round(axis, 5) for axis in object.matrix_world @ v.co] for v in object.data.vertices]
    if not apply_transformations:
        verts = [[round(axis, 5) for axis in v.co] for v in object.data.vertices]
    path = []
    edges = object.data.edges
    c = starting_index
    previous_edge = -1
    feed = feed_plane
    
    for _ in edges:
        pots = [e.index for e in edges if (e.vertices[0] == c or e.vertices[1] == c) and e.index != previous_edge]
        if len(pots) != 1:
            raise ValueError(f'At vertice [{c}] no unique path could be found.')
        previous_edge = pots[0]
        e = edges[previous_edge]
        p = c
        c = e.vertices[0] if e.vertices[0] != c else e.vertices[1]
        gcode = get_gcode_move_string(verts[starting_index], verts[c], scale_factor)

        # setting the feedrate for one move sets it for each subsequent move
        if verts[p][2] != verts[c][2]:
            if feed != feed_down:
                gcode = f"G1 F{feed_down}\n{gcode}"
                feed = feed_down
        elif feed != feed_plane:
            gcode = f"G1 F{feed_plane}\n{gcode}"
            feed = feed_plane

        path.append((gcode, f"{p}->{c}"))

    return path
        
def write_outline_as_gcode(
        context = bpy.context,
        file_path = None,
        apply_transformations = True,
        feed_speed_down = 50,
        feed_speed_plane = 100,
        scale_factor = 1):

    object = context.active_object
    mode = object.mode
    bpy.ops.object.mode_set(mode='OBJECT')
    try:
        selected_verts = [v for v in object.data.vertices if v.select]
        if len(selected_verts) != 1:
            raise ValueError('Please select exactly one vertice befor exporting.')
        starting_index = selected_verts[0].index

        path_gcode = get_gcode_path(
                object,
                starting_index,
                apply_transformations,
                feed_speed_down,
                feed_speed_plane,
                scale_factor)

        with open(os.path.expanduser(file_path), "w") as file:
            write_gcode_head(file)
            write_gcode_section("main", path_gcode, file)
            write_gcode_foot(file)

        return {'FINISHED'}

    finally:
        bpy.ops.object.mode_set(mode=mode)


class ExportOutlineAsGcode(Operator, ExportHelper):
    """Exports the active objects to a Gcode path. The path follows the edges of the model. The path of the edges has to be deterministic. The starting vertice has to be selected."""

    bl_idname = "export.outline_gcode"
    bl_label = "Export edges as Gcode path"

    # ExportHelper mix-in class uses this.
    filename_ext = ".gcode"

    filter_glob: StringProperty(
        default="*.gcode",
        options={'HIDDEN'},
        maxlen=255,
    )

    apply_transformations: bpy.props.BoolProperty(
        name="Apply transformations temporarily when exporting",
        description="Applies transformations to coordinates",
        default=True,
    )

    feed_speed_down: bpy.props.IntProperty(
        name="Feed speed moving down",
        description="Feed speed moving down",
        default = 50,
    )

    feed_speed_plane: bpy.props.IntProperty(
        name="Feed speed moving in one plane",
        description="Feed speed moving in one plane",
        default = 100,
    )

    scale_factor: bpy.props.FloatProperty(
        name="Scale factor",
        description="Scale object by this factor (Gcodes expect mm dimensions)",
        default = 1,
    )


    def execute(self, context):
        return write_outline_as_gcode(
                context,
                self.filepath,
                self.apply_transformations,
                self.feed_speed_down,
                self.feed_speed_plane,
                self.scale_factor)


def menu_func_export(self, context):
    self.layout.operator(ExportOutlineAsGcode.bl_idname, text="Export Outline as Gcode")

bl_info = {
    "name": "Export Outline as Gcode",
    "description": "Export Outline as Gcode",
    "author": "Markus Schoetz <holzwurmi>",
    "version": (0, 0, 0),
    "blender": (2, 93, 0),
    "location": "File > Export > Scalable Vector Graphics (.svg)",
    "category": "Export"}

# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access).
def register():
    bpy.utils.register_class(ExportOutlineAsGcode)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportOutlineAsGcode)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
    bpy.ops.export.outline_gcode('INVOKE_DEFAULT')
