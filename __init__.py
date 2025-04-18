import subprocess
import sys
import os
import bpy
import json
from bpy.app.handlers import persistent

from bpy.props import (StringProperty,
					   BoolProperty,
					   IntProperty,
					   EnumProperty)

from bpy.types import (Operator,
					   PropertyGroup,
					   UIList,
					   AddonPreferences)


class PATHMAKER_OT_ReplacementsActions(Operator):
	"""Move items up and down, add and remove"""
	bl_idname = "pathmaker.list_action"
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
				info = f"Item {item.replacement_tag} moved to position {addon_prefs.replacement_index + 1}"
				self.report({"INFO"}, info)

			elif self.action == "UP" and idx >= 1:
				item_prev = addon_prefs.replacements[idx - 1].name
				addon_prefs.replacements.move(idx, idx - 1)

				addon_prefs.replacement_index -= 1
				info = f"Item {item.replacement_tag} moved to position {addon_prefs.replacement_index + 1}"
				self.report({"INFO"}, info)

			elif self.action == "REMOVE":
				if addon_prefs.replacement_index > -1:
					info = f"Item {addon_prefs.replacements[idx].name} removed from list"

					addon_prefs.replacements.remove(idx)

					if addon_prefs.replacement_index >= len(addon_prefs.replacements):
						addon_prefs.replacement_index = len(addon_prefs.replacements) - 1

					self.report({"INFO"}, info)
					
		if self.action == "ADD":
			if addon_prefs:
				item = addon_prefs.replacements.add()
				list_length = len(addon_prefs.replacements)

				addon_prefs.replacement_index = list_length - 1

				info = f"{item.replacement_tag} added to list"
				self.report({"INFO"}, info)
			else:
				self.report({"INFO"}, "No addon preferences found")
		return {"FINISHED"}


class PATHMAKER_OT_ResetPaths(Operator):
	bl_idname = "pathmaker.reset_paths"
	bl_label = "Reset Paths Tags"
	bl_description = "If the paths did not go back to the tag state, press this button"

	def execute(self, context):
		resetPaths(context.scene)

		return{"FINISHED"}


class PATHMAKER_OT_ExportJson(Operator):
	bl_idname = "pathmaker.export_json"
	bl_label = "Export JSON"
	bl_description = "Export the preferences to a JSON file"

	filepath: bpy.props.StringProperty(subtype="FILE_PATH")
	filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

	def execute(self, context):
		addon_prefs = bpy.context.preferences.addons[__name__].preferences

		replacements_list = []

		for replacement in addon_prefs.replacements:
			replacements_list.append({
				"replacement_tag": replacement.replacement_tag,
				"script": replacement.script,
				"replacement_type": replacement.replacement_type
			})

		with open(self.filepath, "w") as f:
			json.dump(replacements_list, f, indent=2)

		return {"FINISHED"}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)

		return {"RUNNING_MODAL"}


class PATHMAKER_OT_ImportJson(Operator):
	bl_idname = "pathmaker.import_json"
	bl_label = "Import JSON"
	bl_description = "Import the preferences from a JSON file"

	filepath: bpy.props.StringProperty(subtype="FILE_PATH")
	filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

	def execute(self, context):
		addon_prefs = bpy.context.preferences.addons[__name__].preferences
		addon_prefs.replacements.clear()

		replacements_list = []

		with open(self.filepath, "r") as f:
			replacements_list = json.load(f)

		for replacement in replacements_list:
			item = addon_prefs.replacements.add()
			item.replacement_tag = replacement["replacement_tag"]
			item.replacement_type = replacement["replacement_type"]
			item.script = replacement["script"]

		return{"FINISHED"}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)

		return {"RUNNING_MODAL"}


class PATHMAKER_UL_Replacements(UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		if self.layout_type in {"DEFAULT", "COMPACT"}:
			general_split = layout.split(factor=0.3)
			col1 = general_split.column()
			left_split = col1.split(factor=0.5)
			left_split.prop(item, "replacement_tag", text="", emboss=False)
			left_split.prop(item, "replacement_type", text="", emboss=True)
			general_split.prop(item, "script", text="", emboss=True)
		elif self.layout_type in {"GRID"}:
			pass


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
	bl_idname = __name__

	replacements: bpy.props.CollectionProperty(type=PATHMAKER_PG_ReplacementsSet)
	replacement_index: IntProperty(name="Tag", description="Tag to be replaced by the result of the expression")
	replacements_init: BoolProperty(default=False)

	def draw(self, context):
		layout = self.layout

		row = layout.row()
		col = row.column(align=True)
		col.operator("pathmaker.reset_paths")
		col = row.column(align=True)
		col.operator("pathmaker.export_json")
		col = row.column(align=True)
		col.operator("pathmaker.import_json")

		row = layout.row()
		row.template_list(
			listtype_name="PATHMAKER_UL_Replacements",
			list_id="",
			dataptr=self,
			propname="replacements",
			active_dataptr=self,
			active_propname="replacement_index"
		)
		
		col = row.column(align=True)
		col.operator("pathmaker.list_action", icon="ADD", text="").action = "ADD"
		col.operator("pathmaker.list_action", icon="REMOVE", text="").action = "REMOVE"
		col.separator()
		col.operator("pathmaker.list_action", icon="TRIA_UP", text="").action = "UP"
		col.operator("pathmaker.list_action", icon="TRIA_DOWN", text="").action = "DOWN"

		error_messages = []
		priority_error_messages = []
		names_list = []
		duplicates_list = []

		addon_prefs = bpy.context.preferences.addons[__name__].preferences

		for replacement in addon_prefs.replacements:
			if replacement.replacement_tag in names_list:
				if replacement.replacement_tag not in duplicates_list:
					duplicates_list.append(replacement.replacement_tag)
					priority_error_messages.append(f"{replacement.replacement_tag} : Multiple instances with the same tag")

			else:
				names_list.append(replacement.replacement_tag)

			valid = True
			match replacement.replacement_type:
				case "EXPR":
					string_result = ""
					try:
						string_result = eval(replacement.script)
					except:
						error_messages.append(f"{replacement.replacement_tag} : Invalid expression")
						valid = False

				case "SCRIPT":
					if not os.path.isfile(replacement.script):
						error_messages.append(
							f"{replacement.replacement_tag} : File '{replacement.script}' does not exist"
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
						error_messages.append(f"{replacement.replacement_tag} : Invalid script")
						valid = False

				case _:
					continue

			if valid:
				if string_result == "":
					error_messages.append(f"{replacement.replacement_tag} : Script returns empty String")

				if type(string_result) != str:
					error_messages.append(f"{replacement.replacement_tag} : Script does not return String type")

		for msg in priority_error_messages:
			row = layout.row()
			row.label(text=msg, icon="ERROR")

		for msg in error_messages:
			row = layout.row()
			row.label(text=msg, icon="ERROR")


class PATHMAKER_OT_ExportAll(Operator):
	bl_idname = "pathmaker.export_all"
	bl_label = "Export All Exporters"

	@classmethod
	def poll(cls, context):
		return len(context.collection.exporters) > 0

	def execute(self, context):
		replacements_dict = generateReplacements()
		original_filepaths_lists = []

		for exporter in context.collection.exporters:
			original_filepaths_lists.append(exporter.export_properties.filepath)
			for replace_token, replace_by in replacements_dict.items():
				exporter.export_properties.filepath = exporter.export_properties.filepath.replace(replace_token, replace_by)

		bpy.ops.collection.export_all()

		for index, exporter in enumerate(context.collection.exporters):
			exporter.export_properties.filepath = original_filepaths_lists[index]

		return{"FINISHED"}


class PATHMAKER_OT_ExportSelected(Operator):
	bl_idname = "pathmaker.export_selected"
	bl_label = "Export Selected Exporter"

	@classmethod
	def poll(cls, context):
		return len(context.collection.exporters) > 0

	def execute(self, context):
		selected_index = context.collection.active_exporter_index
		selected_exporter = context.collection.exporters[selected_index]
		original_filepath = selected_exporter.export_properties.filepath

		replacements_dict = generateReplacements()

		for replace_token, replace_by in replacements_dict.items():
			selected_exporter.export_properties.filepath = selected_exporter.export_properties.filepath.replace(replace_token, replace_by)

		bpy.ops.collection.exporter_export(index=selected_index)

		selected_exporter.export_properties.filepath = original_filepath

		return{"FINISHED"}


@persistent
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


@persistent
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


@persistent
def resetPathHandler(scene):
	resetPaths(scene)


def resetPaths(scene):
	scene.path_maker_rendering = False

	if scene.original_filepaths:
		original_filepaths_dict = json.loads(scene.original_filepaths)

		scene.render.filepath = original_filepaths_dict["render"]

		for node_name, node_data in original_filepaths_dict["nodes"].items():
			node = scene.node_tree.nodes[node_name]
			node.base_path = node_data["base_path"]

			for i, file_slot in enumerate(node.file_slots):
				node.file_slots[i].path = node_data["file_slots"][str(i)]


def generateReplacements():
	replacements_dict = {}
	addon_prefs = bpy.context.preferences.addons[__name__].preferences

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
	addon_prefs = bpy.context.preferences.addons[__name__].preferences

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


### REGISRTATION / UNREGISRTATION ###
classes = (
			PATHMAKER_OT_ReplacementsActions,
			PATHMAKER_UL_Replacements,
			PATHMAKER_PG_ReplacementsSet,
			PATHMAKER_OT_ExportAll,
			PATHMAKER_OT_ExportSelected,
			PATHMAKER_OT_ResetPaths,
			PATHMAKER_OT_ExportJson,
			PATHMAKER_OT_ImportJson,
			PathMakerPreferences
)

def register():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)

	bpy.types.Scene.original_filepaths = StringProperty()
	bpy.types.Scene.path_maker_rendering = BoolProperty(default=False)

	bpy.types.COLLECTION_PT_exporters.prepend(exportersPanel)

	bpy.app.handlers.render_init.append(makePathStartHandler)
	bpy.app.handlers.frame_change_pre.append(makePathHandler)
	bpy.app.handlers.render_cancel.append(resetPathHandler)
	bpy.app.handlers.render_complete.append(resetPathHandler)

	setDefaultReplacements()
 

def unregister():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)

	bpy.types.COLLECTION_PT_exporters.remove(exportersPanel)

	bpy.app.handlers.render_complete.remove(resetPathHandler)
	bpy.app.handlers.render_cancel.remove(resetPathHandler)
	bpy.app.handlers.frame_change_pre.remove(makePathHandler)
	bpy.app.handlers.render_init.remove(makePathStartHandler)
	

if __name__ == "__main__":
	register()
