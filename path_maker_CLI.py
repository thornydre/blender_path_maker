import subprocess
import sys
import os
import bpy
import json

from bpy.props import (StringProperty,
					   BoolProperty,
					   IntProperty,
					   EnumProperty)

from bpy.types import (Operator,
					   PropertyGroup,
					   UIList,
					   AddonPreferences)


class PATHMAKER_PG_ReplacementsSet(PropertyGroup):
	replacement_tag: bpy.props.StringProperty(name="Tag", description="Tag to be replaced by the result of the expression")
	script: bpy.props.StringProperty(name="Expression", description="Expression from which the result will be replacing the tag")
	replacement_type: bpy.props.EnumProperty(
		name="Expression Type",
		description="Indicates how to interprete the expression",
		items=(
			("EXPR", "Expression", ""),
			("PATH", "Path", ""),
			("SCRIPT", "Script", "")
		)
	)


class PathMakerPreferences(AddonPreferences):
	bl_idname = "bl_ext.blender_org.blender_path_maker"
	print("ohai name=====>>"+ bl_idname)

	replacements: bpy.props.CollectionProperty(type=PATHMAKER_PG_ReplacementsSet)
	replacement_index: IntProperty(name="Tag", description="Tag to be replaced by the result of the expression")
	replacements_init: BoolProperty(default=False)

def makePathStartHandler(scene):
	scene.path_maker_rendering = True

	# List node and paths that are going to change during rendering
	original_filepaths_dict = {"render": scene.render.filepath}

	original_filepaths_dict["nodes"] = {}
	if scene.node_tree is not None:
		for node in scene.node_tree.nodes:
			if node.type == "OUTPUT_FILE":
				original_filepaths_dict["nodes"][node.name] = {
				"base_path": node.base_path,
				"file_slots": {}
				}
				for i, file_slot in enumerate(node.file_slots):
					original_filepaths_dict["nodes"][node.name]["file_slots"][str(i)] = file_slot.path

	scene.original_filepaths = json.dumps(original_filepaths_dict)

	makePathHandler(scene)


def makePathHandler(scene):
	if scene.path_maker_rendering:
		original_filepaths_dict = json.loads(scene.original_filepaths)

		# Generate replacement in association with the tokens
		replacements_dict = generateReplacements()

		# Reset paths
		scene.render.filepath = original_filepaths_dict["render"]
		for node_name, node_path in original_filepaths_dict["nodes"].items():
			if scene.node_tree is not None:
				node = scene.node_tree.nodes[node_name]
				node.base_path = original_filepaths_dict["nodes"][node_name]["base_path"]

				for i, file_slot in enumerate(node.file_slots):
					node.file_slots[i].path = original_filepaths_dict["nodes"][node_name]["file_slots"][str(i)]

		# Replace tokens
		for replace_token, replace_by in replacements_dict.items():
			scene.render.filepath = scene.render.filepath.replace(replace_token, replace_by)

			for node_name in original_filepaths_dict["nodes"].keys():
				node = scene.node_tree.nodes[node_name]
				node.base_path = node.base_path.replace(replace_token, replace_by)
				for file_slot in node.file_slots:
					file_slot.path = file_slot.path.replace(replace_token, replace_by)


def generateReplacements():
	replacements_dict = {}
	addon_prefs = bpy.context.preferences.addons["bl_ext.blender_org.blender_path_maker"].preferences

	for replacement in addon_prefs.replacements:
		match replacement.replacement_type:
			case "EXPR":
				try:
					result = eval(replacement.script)
				except:
					pass
				else:
					if type(result) == str:
						replacements_dict[replacement.replacement_tag] = result
			case "PATH":
				if type(replacement.script) == str:
					replacements_dict[replacement.replacement_tag] = replacement.script
			case "SCRIPT":
				try:
					python_path = os.path.abspath(sys.executable)
					proc = subprocess.Popen([python_path, replacement.script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
					result = proc.communicate()[0]
				except:
					pass
				else:
					if type(result.decode().strip()) == str:
						replacements_dict[replacement.replacement_tag] = result.decode().strip()

	return replacements_dict


def setDefaultReplacements():
	addon_prefs = bpy.context.preferences.addons["bl_ext.blender_org.blender_path_maker"].preferences

	if not addon_prefs.replacements_init:
		addon_prefs.replacements_init = True

		item = addon_prefs.replacements.add()
		item.replacement_tag = "<camera>"
		item.script = "bpy.context.scene.camera.name"
		item = addon_prefs.replacements.add()
		item.replacement_tag = "<layer>"
		item.script = "bpy.context.view_layer.name"
		item = addon_prefs.replacements.add()
		item.replacement_tag = "<scene>"
		item.script = "bpy.context.scene.name"
		item = addon_prefs.replacements.add()
		item.replacement_tag = "<filename>"
		item.script = "bpy.path.display_name_from_filepath(bpy.data.filepath)"
		item = addon_prefs.replacements.add()
		item.replacement_tag = "<dirname>"
		item.script = '"/".join(bpy.data.filepath.replace("\\\\", "/").split("/")[:-1])'


def exportersPanel(self, context):
	layout = self.layout
	layout.label(text="Path Maker Exporters")
	split = layout.split(factor=0.5)
	col = split.column()
	col.operator("pathmaker.export_all")
	col = split.column()
	col.operator("pathmaker.export_selected")
	layout.separator()



bpy.types.Scene.original_filepaths = StringProperty()
bpy.types.Scene.path_maker_rendering = BoolProperty(default=False)

setDefaultReplacements()
makePathStartHandler(bpy.context.scene)
 

