import bpy
import os
import shutil

from .utils.addon_checks import requirements_checks

ADDON_NAME = __name__.rsplit(".")[0]
ADDON_ROOT = __file__.rsplit(__name__.rsplit(".")[0])[0] + ADDON_NAME


# SWTOR MATERIALS TEMPLATES DEFAULTS
# Name of desired default templates file:
DEFAULT_TEMPLATE_FILENAME = "SWTOR Materials 4.2.blend"

DEFAULT_TEMPLATES_FOLDERPATH = os.path.join(ADDON_ROOT, "resources","default_materials_templates")

DEFAULT_TEMPLATE_FILEPATH    = os.path.join(DEFAULT_TEMPLATES_FOLDERPATH, DEFAULT_TEMPLATE_FILENAME)



# UI stuff
Y_SCALING_GRAL = 0.9
Y_SCALING_INFO = 0.65
Y_SCALING_SPACER = 0.3
    
# Helper functions for building or updating a menu EnumProperty
# of SWTOR material templates .blend files in a directory.

# Get .blend Files present in a directory (Blender-generic)
def list_blend_files_in_directory(directory):
    """
    (Blender-generic)
    Returns a list of all .blend files in the given directory.
    Returns an empty list if directory is invalid or has no matching files.
    """
    if not directory or not os.path.isdir(directory):
        return []
    blend_files = [f for f in os.listdir(directory) if f.lower().endswith(".blend")]
    return blend_files

# Create a list of .blend files as an EnumProp-friendly list of tuples.
# It is a selected_swtor_template_mats_file's (templates selector menu EnumProp) callback Function.
def enumerate_internal_and_external_template_files(self, context):
    """
    Generates the combined list of .blend files for the EnumProperty dropdown menu.
    It is called every time the dropdown menu is shown, enabling auto-refresh.
    - Includes files from a default templates subfolder inside the add-on.
    - Includes files from a user-selected external templates directory, if set.
    - Tags entries as [internal] or [external] for clarity.
    - Uses a unique ID string so we can tell their source later.
    """
    items = []

    # === Files from defaults folder ===
    internal_files = list_blend_files_in_directory(DEFAULT_TEMPLATES_FOLDERPATH)
    for f in internal_files:
        identifier = f"INTERNAL::{f}"  # Unique ID for selection. The "::" is arbitrary
        name = f"Internal - {f}"       # Displayed name
        description = f"Internal file: {f}"
        items.append((identifier, name, description))

    # === Files from user-selected external directory ===
    user_files = list_blend_files_in_directory(self.external_swtor_template_mats_folderpath)
    for f in user_files:
        identifier = f"EXTERNAL::{f}"  # Unique ID for selection. The "::" is arbitrary
        name = f"External - {f}"       # Displayed name
        description = f"External file: {f}"
        items.append((identifier, name, description))

    # === Fallback: No files found ===
    if not items:
        return [("NONE", "No .blend files found", "No .blend files in selected or default folders")]

    return items

# Filepath solver to convert a selected template filename into a filepath.
def template_filename_to_filepath(prefs):
    """
    Resolves the absolute path to the currently selected .blend file
    based on whether it comes from the user-selected "external" directory
    or from the "internal" one.
    Returns an empty string if nothing is selected or path is invalid.
    """
    selected = prefs.selected_swtor_template_mats_filename

    # No file selected or dummy fallback
    if not selected or selected == "NONE":
        return ""

    # Decode the identifier to determine source
    if selected.startswith("INTERNAL::"):
        filename = selected.split("::", 1)[1]
        return os.path.join(DEFAULT_TEMPLATES_FOLDERPATH, filename)
    elif selected.startswith("EXTERNAL::"):
        filename = selected.split("::", 1)[1]
        return os.path.join(prefs.external_swtor_template_mats_folderpath, filename)

    return ""  # Unknown source format




class addonPreferences(bpy.types.AddonPreferences):
    bl_idname = "zg_swtor_tools"

    # ------ Resources-related Properties ----------------------------------

    # SWTOR Assets extraction's resources folderpath
    swtor_resources_folderpath: bpy.props.StringProperty(
        name = "Resources Folder",
        description = 'Path to the "resources" folder produced by a SWTOR assets extraction',
        subtype = "DIR_PATH",
        default = "Choose or type the folder's path",
        maxlen = 1024
    )
    
    
    
    # ------ SWTOR Template Materials-related Properties and Methods -------

    # Updates list of template files. It is called back by the selected_swtor_template_mats_filename property.
    def update_template_files_list(self, context=None):
        blend_list = list_blend_files_in_directory(self.external_swtor_template_mats_folderpath)
        
        enum_items = [(f, f, "") for f in blend_list] or [("NONE", "No .blend files found", "")]
        self.selected_swtor_template_mats_filename = enum_items[0][0]
        self.__class__.selected_swtor_template_mats_filename = bpy.props.EnumProperty(
            name="Blend Files",
            items=lambda self, context: enum_items
        )

    # Produces an appropriate full templates filepath when selected_swtor_template_mats_filename updates.
    def resolve_template_filepath(self, context=None):
        self.selected_swtor_template_mats_filepath = template_filename_to_filepath(self)


    # SWTOR Template Materials blendfiles folderpath
    external_swtor_template_mats_folderpath: bpy.props.StringProperty(
        name = "External SWTOR Materials Templates Folder",
        subtype ='DIR_PATH',
        default = "Choose or type the folder's path",
        maxlen = 1024,
    )

    # EnumProperty (for templates selection menu) with dynamic item list of .blend files.
    # Calls enumerate_internal_and_external_template_files() back to fill the menu.
    # And calls resolve_template_filepath() to format the selection as a filepath
    # and store it in selected_swtor_template_mats_filepath.
    selected_swtor_template_mats_filename: bpy.props.EnumProperty(
        name="Blend Files",
        items=enumerate_internal_and_external_template_files,
        update=resolve_template_filepath
    )
    
    # Stores the selected template's filepath.
    selected_swtor_template_mats_filepath: bpy.props.StringProperty(
        name="Selected SWTOR materials templates .blend file's full path",
    )
    
    # Stores the selected template's filepath that was in use previous to a new selection
    selected_swtor_template_mats_filepath_previous: bpy.props.StringProperty(
        name="Previous to selected SWTOR materials templates .blend file's full path",
    )

    # ------ Customizable Shaders-related Properties -----------------------

    # Customizable SWTOR shaders blendfile filepath (eventually will be replaced by a "standard" template)
    swtor_custom_shaders_blendfile_path: bpy.props.StringProperty(
        name = "Custom Shaders File",
        description = "Path to a Blend file holding custom replacement SWTOR shaders\nfor the current modern ones.\n\n• It defaults to the one stored inside the addon",
        subtype = "FILE_PATH",
        default = os.path.join(ADDON_ROOT, "resources", "Custom SWTOR Shaders.blend"),
        maxlen = 1024
    )

    
    
    # ------ .gr2 import-related Properties --------------------------------

    # Behavior of some tools when processing SWTOR objects with custom mesh scaling
    # (the new scale settings in the .gr2 importer Add-on, which are recorded in the
    # imported objects' as a 'gr2_scale' custom property)
    use_gr2_scale_custom_prop: bpy.props.BoolProperty(
        name = "Use SWTOR Objects' Mesh Scale Data If Available",
        description = "If a SWTOR object has a 'gr2_scale' custom property, added by a .gr2 Importer Add-on,\nmesh size-sensitive tools will consider that data over any other assumed or set scalings\n(such as the default 1.0 or a .gr2 Add-on's importing prefs settings)",
        default = True,
    )




    # UI ----------------------------------------
    
    def draw(self, context):
        
        checks = requirements_checks()
        
        layout = self.layout

        # resources folderpath preferences UI
        # region
        pref_box = layout.box()
        pref_box.label(text="SWTOR ASSETS SETTINGS:")

        col=pref_box.column(align=True)
        col.scale_y = Y_SCALING_INFO
        col.label(text="Set the path to the 'resources' folder in a SWTOR assets extraction")
        col.label(text="produced by ExtracTOR, Slicers GUI or any similar tool.")

        col=pref_box.column()
        col.prop(self, 'swtor_resources_folderpath', expand=True, )
        
        col.alert = not checks["resources"]
        col.label(text="• Status: " + checks["resources_status_verbose"])
        # endregion


        # ----------------


        # SWTOR Template Materials preferences UI
        # region
        pref_box = layout.box()
        pref_box.label(text="SWTOR MATERIALS SETTINGS  (EXPERIMENTAL):")

        col=pref_box.column(align=True)
        col.scale_y = Y_SCALING_INFO
        
        # Auto-refreshed dropdown Templates Menu showing .blend files
        col.label(text="Select a .blend file with a set of SWTOR materials templates.")
        col.label(text="By default it uses one included inside this Add-on.")
        
        col=pref_box.column(align=True)
        col.alert = False
        col.prop(self, "selected_swtor_template_mats_filename", text="Select a Templates File")

        col.alert = not checks["template"]
        col.label(text="• Status: " + checks["template_status_verbose"])


        # Optional user templates materials folder path
        col=pref_box.column(align=True)
        col.scale_y = Y_SCALING_INFO
        col.label(text="")
        col.label(text="OPTIONAL: Use your own templates files by choosing an external folder")
        col.label(text="where to place them. They will appear in the Templates menu above, too.")

        col=pref_box.column(align=True)
        # Folder picker for external_swtor_template_mats_folderpath directory
        col.prop(self, "external_swtor_template_mats_folderpath", text="Templates Folder")

        col.alert = not checks["templates_folder"]
        col.label(text="• Status: " + checks["templates_folder_status_verbose"])
        
        col.alert = not checks["templates_folder"]
        col.operator("zgswtor.copy_internal_material_templates_to_external_folder", text="Copy the default templates to this folder as examples to tinker with")
        # endregion
        
        
        # ----------------


        # Custom ZG SWTOR shaders blendfile folder path UI
        # region
        pref_box = layout.box()
        pref_box.label(text="ZG SWTOR CUSTOM SHADERS SETTINGS:")

        col=pref_box.column(align=True)
        col.scale_y = Y_SCALING_INFO
        col.label(text="Set the path to a .blend file with customizable replacement SWTOR shaders.")
        col.label(text="By default it uses one inside this Add-on.")
        
        col=pref_box.column()
        col.prop(self, 'swtor_custom_shaders_blendfile_path', expand=True, )
        
        col.alert = not checks["custom_shaders"]
        col.label(text="• Status: " + checks["custom_shaders_status_verbose"])

        col.operator("zgswtor.reset_custom_shaders_prefs_to_internal", text="Reset to internal Custom Shaders file")
        # endregion
        
        
        # ----------------


        # SWTOR objects' scaling data usage UI
        # region
        pref_box = layout.box()
        pref_box.label(text="SWTOR OBJECTS IMPORT SETTINGS:")

        col=pref_box.column()
        col.prop(self, 'use_gr2_scale_custom_prop', text="Use SWTOR objects' mesh scale data if available and relevant to any ZG Tool.")
        # endregion




# reset_custom_shaders_prefs_to_internal Operator button ------------------
class ZGSWTOR_OT_reset_custom_shaders_prefs_to_internal(bpy.types.Operator):
    bl_idname = "zgswtor.reset_custom_shaders_prefs_to_internal"
    bl_label = "ZG Custom Shaders Reset To Internal"
    bl_options = {'REGISTER', "UNDO"}
    bl_description = "Resets the Custom Shaders .blend file Preference\nto use the file inside this Add-on's folder"

    @classmethod
    def poll(cls,context):
        checks = requirements_checks()
        if checks["templates_folder"]:
            return True
        else:
            return False

    def execute(self, context):
        
        # Default Custom shaders .blend file's filepath
        default_custom_shaders_blend_filepath = os.path.join(os.path.dirname(__file__), "resources" + os.sep + "Custom SWTOR Shaders.blend")

        context.preferences.addons["zg_swtor_tools"].preferences["swtor_custom_shaders_blendfile_path"] = default_custom_shaders_blend_filepath
        
        return {"FINISHED"}
    

# Copy internal Materials Templates files to external folder button ------------------
class ZGSWTOR_OT_copy_internal_material_templates_to_external_folder(bpy.types.Operator):
    bl_idname = "zgswtor.copy_internal_material_templates_to_external_folder"
    bl_label = "ZG Copy Internal Default Templates To External Folder"
    bl_options = {'REGISTER', "UNDO"}
    bl_description = "Copies SWTOR material templates .blend files\nto the selected templates folder"

    @classmethod
    def poll(cls,context):
        checks = requirements_checks()
        if not checks["templates_folder"]:
            return False
        else:
            return True


    def execute(self, context):
        
        # Default SWTOR materials templates .blend file's filepath
        # default_custom_shaders_blend_filepath = os.path.join(os.path.dirname(__file__), "resources" + os.sep + "Custom SWTOR Shaders.blend")

        # Default Custom shaders .blend file's filepath
        default_custom_shaders_blend_filepath = os.path.join(os.path.dirname(__file__), "resources", "Custom SWTOR Shaders.blend")

        context.preferences.addons["zg_swtor_tools"].preferences["swtor_custom_shaders_blendfile_path"] = default_custom_shaders_blend_filepath
        
        

        # Set your source and destination directories
        addon_prefs = bpy.context.preferences.addons["zg_swtor_tools"].preferences
    
        src_dir = DEFAULT_TEMPLATES_FOLDERPATH
        dest_dir = addon_prefs.external_swtor_template_mats_folderpath

        # Iterate over all files in the source directory
        for filename in os.listdir(src_dir):
            if filename.lower().endswith('.blend'):
                src_file = os.path.join(src_dir, filename)
                dest_file = os.path.join(dest_dir, f"Copy of {filename}")
                
                shutil.copy2(src_file, dest_file)
                
                print(f"Copied: {src_file} -> {dest_file}")

        
        return {"FINISHED"}




 

# Registrations

classes = (
    addonPreferences,
    ZGSWTOR_OT_reset_custom_shaders_prefs_to_internal,
    ZGSWTOR_OT_copy_internal_material_templates_to_external_folder,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Set the default template upon enabling the Add-on and registering this module's classes:
    addon_prefs = bpy.context.preferences.addons["zg_swtor_tools"].preferences
    
    addon_prefs.selected_swtor_template_mats_filepath           = DEFAULT_TEMPLATE_FILEPATH
    addon_prefs.selected_swtor_template_mats_filepath_previous  = DEFAULT_TEMPLATE_FILEPATH
    addon_prefs.selected_swtor_template_mats_filename           = (f"INTERNAL::{DEFAULT_TEMPLATE_FILENAME}")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
