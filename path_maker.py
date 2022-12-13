'''
<scene>
bpy.path.display_name_from_filepath(bpy.data.filepath)
<shot>
bpy.path.display_name_from_filepath(bpy.data.filepath)[:7]
'''


bl_info = {
    "name": "Path Maker",
    "author": "Lucas BOUTROT",
    "version": (1, 0),
    "blender": (3, 4, 0),
    "description": "Automatic naming for render filepath",
    "warning": "",
    "wiki_url": "",
    "category": "Render"
}

import subprocess
import sys
import os
import bpy
from bpy.app.handlers import persistent

from bpy.props import (StringProperty,
                       IntProperty,
                       EnumProperty)

from bpy.types import (Operator,
                       PropertyGroup,
                       UIList,
                       AddonPreferences)


class PATHMAKER_OT_ReplacementsActions(Operator):
    """Move items up and down, add and remove"""
    bl_idname = "replacements.list_action"
    bl_label = "List Actions"
    bl_description = "Move items up and down, add and remove"
    bl_options = {"REGISTER"}
    
    action: EnumProperty(
        items=(
            ("UP", "Up", ""),
            ("DOWN", "Down", ""),
            ("REMOVE", "Remove", ""),
            ("ADD", "Add", "")
        )
    )

    def invoke(self, context, event):
        addon_prefs = context.preferences.addons[__name__].preferences
        idx = addon_prefs.replacement_index

        try:
            item = addon_prefs.replacements[idx]
        except IndexError:
            pass
        else:
            if self.action == "DOWN" and idx < len(addon_prefs.replacements) - 1:
                item_next = addon_prefs.replacements[idx + 1].name
                addon_prefs.replacements.move(idx, idx + 1)

                addon_prefs.replacement_index += 1
                info = f"Item {item.replacement_name} moved to position {addon_prefs.replacement_index + 1}"
                self.report({"INFO"}, info)

            elif self.action == "UP" and idx >= 1:
                item_prev = addon_prefs.replacements[idx - 1].name
                addon_prefs.replacements.move(idx, idx - 1)

                addon_prefs.replacement_index -= 1
                info = f"Item {item.replacement_name} moved to position {addon_prefs.replacement_index + 1}"
                self.report({"INFO"}, info)

            elif self.action == "REMOVE":
                if addon_prefs.replacement_index > -1:
                    info = f"Item {addon_prefs.replacements[idx].name} removed from list"

                    addon_prefs.replacement_index -= 1

                    addon_prefs.replacements.remove(idx)
                    self.report({"INFO"}, info)
                    
        if self.action == "ADD":
            if addon_prefs:
                item = addon_prefs.replacements.add()
                list_length = len(addon_prefs.replacements)

                addon_prefs.replacement_index = list_length - 1

                item.replacement_name = "<camera>"
                item.script = "bpy.context.scene.camera.name"

                info = f"{item.replacement_name} added to list"
                self.report({"INFO"}, info)
            else:
                self.report({"INFO"}, "Nothing selected in the Viewport")
        return {"FINISHED"}


class PATHMAKER_UL_Replacements(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            general_split = layout.split(factor=0.3)
            col1 = general_split.column()
            left_split = col1.split(factor=0.5)
            left_split.prop(item, "replacement_name", text="", emboss=False)
            left_split.prop(item, "replacement_type", text="", emboss=True)
            general_split.prop(item, "script", text="", emboss=False)
        elif self.layout_type in {"GRID"}:
            pass


class PATHMAKER_PG_ReplacementsSet(PropertyGroup):
    replacement_name: bpy.props.StringProperty()
    script: bpy.props.StringProperty()
    replacement_type: bpy.props.EnumProperty(
        items=(
            ("EXPR", "Expression", ""),
            ("PATH", "Path", ""),
            ("SCRIPT", "Script", "")
        ),
        name="fixed list"
    )


class PathMakerPreferences(AddonPreferences):
    bl_idname = __name__

    replacements: bpy.props.CollectionProperty(type=PATHMAKER_PG_ReplacementsSet)
    replacement_index: IntProperty()

    def draw(self, context):
        layout = self.layout

        row = layout.row()

        row.template_list("PATHMAKER_UL_Replacements", "", self, "replacements", self, "replacement_index")
        
        col = row.column(align=True)
        col.operator("replacements.list_action", icon="ADD", text="").action = "ADD"
        col.operator("replacements.list_action", icon="REMOVE", text="").action = "REMOVE"
        col.separator()
        col.operator("replacements.list_action", icon="TRIA_UP", text="").action = "UP"
        col.operator("replacements.list_action", icon="TRIA_DOWN", text="").action = "DOWN"

        error_messages = []
        priority_error_messages = []
        names_list = []
        duplicates_list = []

        addon_prefs = bpy.context.preferences.addons[__name__].preferences

        for replacement in addon_prefs.replacements:
            if replacement.replacement_name in names_list:
                if replacement.replacement_name not in duplicates_list:
                    duplicates_list.append(replacement.replacement_name)
                    priority_error_messages.append(f"{replacement.replacement_name} : Multiple instances of the same tag")

            else:
                names_list.append(replacement.replacement_name)

            valid = True
            match replacement.replacement_type:
                case "EXPR":
                    string_result = ""
                    try:
                        string_result = eval(replacement.script)
                    except:
                        error_messages.append(f"{replacement.replacement_name} : Invalid expression")
                        valid = False

                case "SCRIPT":
                    if not os.path.isfile(replacement.script):
                        error_messages.append(
                            f"{replacement.replacement_name} : File '{replacement.script}' does not exist"
                        )

                    string_result = ""
                    try:
                        python_path = os.path.abspath(sys.executable)
                        proc = subprocess.Popen(
                            [python_path, replacement.script],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT
                        )
                        result = proc.communicate()[0]
                        string_result = result.decode().strip()
                    except:
                        error_messages.append(f"{replacement.replacement_name} : Invalid script")
                        valid = False

                case _:
                    break

            if valid:
                if not string_result:
                    error_messages.append(f"{replacement.replacement_name} : Script returns empty String")

                if type(string_result) != str:
                    error_messages.append(f"{replacement.replacement_name} : Script does not return String type")

        for msg in priority_error_messages:
            row = layout.row()
            row.label(text=msg, icon="ERROR")

        for msg in error_messages:
            row = layout.row()
            row.label(text=msg, icon="ERROR")



@persistent
def makePathHandler(scene):
    scene.original_filepath = scene.render.filepath

    addon_prefs = bpy.context.preferences.addons[__name__].preferences

    new_file_path = scene.original_filepath

    for replacement in addon_prefs.replacements:
        match replacement.replacement_type:
            case "EXPR":
                new_file_path = new_file_path.replace(replacement.replacement_name, eval(replacement.script))
            case "PATH":
                new_file_path = new_file_path.replace(replacement.replacement_name, replacement.script)
            case "SCRIPT":
                python_path = os.path.abspath(sys.executable)
                proc = subprocess.Popen([python_path, replacement.script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                result = proc.communicate()[0]
                new_file_path = new_file_path.replace(replacement.replacement_name, result.decode().strip())

    scene.render.filepath = new_file_path


@persistent
def resetPathHandler(scene):
    scene.render.filepath = scene.original_filepath


def setDefaultReplacements():
    addon_prefs = bpy.context.preferences.addons[__name__].preferences

    if not addon_prefs:
        item = addon_prefs.replacements.add()
        item.replacement_name = "<camera>"
        item.script = "scene.camera.name"
        item = addon_prefs.replacements.add()
        item.replacement_name = "<scene>"
        item.script = "bpy.path.display_name_from_filepath(bpy.data.filepath)"


### REGISRTATION / UNREGISRTATION ###
classes = (
            PATHMAKER_OT_ReplacementsActions,
            PATHMAKER_UL_Replacements,
            PATHMAKER_PG_ReplacementsSet,
            PathMakerPreferences
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.original_filepath = StringProperty()
    
    bpy.app.handlers.render_init.append(makePathHandler)
    bpy.app.handlers.render_complete.append(resetPathHandler)
    bpy.app.handlers.render_cancel.append(resetPathHandler)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    bpy.app.handlers.render_init.remove(makePathHandler)
    bpy.app.handlers.render_complete.remove(resetPathHandler)
    bpy.app.handlers.render_cancel.remove(resetPathHandler)
    

if __name__ == "__main__":
    register()


