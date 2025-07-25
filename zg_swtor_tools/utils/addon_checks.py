import bpy
import addon_utils
from pathlib import Path
import os
from .swtor_materials_utils import read_swtor_template_mats_names_in_file



ADDON_NAME = __name__.rsplit(".")[0]
ADDON_ROOT = __file__.rsplit(__name__.rsplit(".")[0])[0] + ADDON_NAME



def requirements_checks():
    '''
    Returns a dict with both boolean and string reports on the existence
    and validity of some resources necessary for certain tools to work.
    For every resource there is usually:
    * A plain boolean.
    * A short status string.
    * And a long, verbose status string.
    '''


    addon_prefs = bpy.context.preferences.addons[ADDON_NAME].preferences

    checks = {}



    # -----------------------------
    # Blender version checks
    # region

    blender_version_major_number, blender_version_minor_number , _ = bpy.app.version
    checks["blender_version"] = float(str(blender_version_major_number) + "." + str(blender_version_minor_number))
    checks["blender_version_status"] = bpy.app.version
    checks["blender_version_status_verbose"] = bpy.app.version
    # endregion



    # -----------------------------
    # .gr2 Add-on checks
    # region

    if "io_scene_gr2" not in [mod.__name__ for mod in addon_utils.modules()]:
        checks["gr2"] = False
        checks["gr2_status"] = "NOT INSTALLED"
        checks["gr2_status_verbose"] = "NOT INSTALLED. No .gr2 Importer Add-on is currently installed."
        
        checks["gr2HasParams"] = False
        checks["gr2HasParams_status"] = "NOT AVAILABLE"
        checks["gr2HasParams_status_verbose"] = "NOT AVAILABLE. No .gr2 Importer Add-on is currently installed."
        
    else:
        # if "io_scene_gr2" in bpy.context.preferences.addons:  # More robust?
        if addon_utils.check("io_scene_gr2")[1]:
            checks["gr2"] = True
            checks["gr2_status"] = "ENABLED"
            checks["gr2_status_verbose"] = "ENABLED. A .gr2 Importer Add-on is installed and enabled."
            
            if hasattr(bpy.context.preferences.addons["io_scene_gr2"].preferences, "gr2_scale_object"):
                checks["gr2HasParams"] = True
                checks["gr2HasParams_status"] = "AVAILABLE"
                checks["gr2HasParams_status_verbose"] = "AVAILABLE. This .gr2 Importer Add-on has Prefs settings."
            else:
                checks["gr2HasParams"] = False
                checks["gr2HasParams_status"] = "NOT AVAILABLE"
                checks["gr2HasParams_status_verbose"] = "NOT AVAILABLE. This .gr2 Importer Add-on has no Prefs settings, might be an old version."
                
        else:
            checks["gr2"] = False
            checks["gr2_status"] = "DISABLED"
            checks["gr2_status_verbose"] = "DISABLED. A .gr2 Importer Add-on is installed, but still needs to be enabled."
                    
            checks["gr2HasParams"] = False
            checks["gr2HasParams_status"] = "NOT AVAILABLE"
            checks["gr2HasParams_status_verbose"] = "NOT AVAILABLE. A .gr2 Importer Add-on is installed, but still needs to be enabled."
    # endregion



    # -----------------------------
    # 'resources' folder checks
    # region

    swtor_resources_folderpath = getattr(bpy.context.preferences.addons["zg_swtor_tools"].preferences, "swtor_resources_folderpath", "")
    is_badly_written = os.sep not in swtor_resources_folderpath
    is_unfilled = swtor_resources_folderpath == "Choose or type the folder's path"
    is_a_folder = Path(swtor_resources_folderpath).exists()
    is_a_resources_folder = ( Path(swtor_resources_folderpath) / "art/shaders/materials").exists()

    if is_unfilled:
        checks["resources_status"] = "NOT SET"
        checks["resources_status_verbose"] = "NOT SET."
    else:
        if is_badly_written:
            checks["resources_status"] = "NOT VALID"
            checks["resources_status_verbose"] = "NOT VALID. This is not a folder path."
        else:
            if is_a_resources_folder:
                checks["resources_status"] = "SET"
                checks["resources_status_verbose"] = "SET. This is a valid 'resources' folder."
            else:
                if is_a_folder:
                    checks["resources_status"] = "NOT VALID"
                    checks["resources_status_verbose"] = "NOT VALID. This folder isn't a valid 'resources' directory root."
                else:
                    checks["resources_status"] = "NOT FOUND"
                    checks["resources_status_verbose"] = "NOT FOUND. No folder can't be found at the specified path."

    checks["resources"] = is_a_resources_folder
    # endregion



    # -----------------------------
    # SWTOR materials templates folder and file checks
    # region

    # Checks for optional external custom materials templates folder.
    external_swtor_template_mats_folderpath = getattr(bpy.context.preferences.addons["zg_swtor_tools"].preferences, "external_swtor_template_mats_folderpath", "")
    is_badly_written = os.sep not in external_swtor_template_mats_folderpath
    is_unfilled = external_swtor_template_mats_folderpath == "Choose or type the folder's path"
    is_a_folder = Path(external_swtor_template_mats_folderpath).exists()
    
    if is_unfilled:
        is_a_templates_folder = False
        checks["templates_folder"] = False
        checks["templates_folder_status"] = "NOT SET"
        checks["templates_folder_status_verbose"] = "NOT SET."
    else:
        if is_badly_written:
            is_a_templates_folder = False
            checks["templates_folder"] = False
            checks["templates_folder_status"] = "NOT VALID"
            checks["templates_folder_status_verbose"] = "NOT VALID. This is not a folder path."
        else:
            if is_a_folder:
                is_a_templates_folder = False
                for entry in os.scandir(external_swtor_template_mats_folderpath):
                    if entry.is_file() and entry.name.endswith("blend"):
                        is_a_templates_folder = True
                        break
                if is_a_templates_folder:
                    checks["templates_folder"] = True
                    checks["templates_folder_status"] = "SET"
                    checks["templates_folder_status_verbose"] = "SET. This is a valid templates folder."
                else:
                    checks["templates_folder"] = False
                    checks["templates_folder_status"] = "NOT VALID"
                    checks["templates_folder_status_verbose"] = "NOT VALID. This folder does not contain .blend files."
            else:
                checks["templates_folder"] = False
                checks["templates_folder_status"] = "NOT FOUND"
                checks["templates_folder_status_verbose"] = "NOT FOUND. No folder can't be found at the specified path."
    
    
    
    # Checks for chosen custom materials templates file.
    selected_swtor_template_mats_filepath = getattr(addon_prefs, "selected_swtor_template_mats_filepath", "")
    if selected_swtor_template_mats_filepath != "":
        
        is_a_templates_file = read_swtor_template_mats_names_in_file(addon_prefs.selected_swtor_template_mats_filepath)
        
        if not is_a_templates_file:
            checks["template"] = False
            checks["template_status"] = "NOT VALUD"
            checks["template_status_verbose"] = "NOT VALID. This .blend file lacks appropriately named materials."
        else:
            if external_swtor_template_mats_folderpath in selected_swtor_template_mats_filepath:
                checks["template"] = True
                checks["template_status"] = "EXTERNAL"
                checks["template_status_verbose"] = "EXTERNAL. This .blend file has appropriately named materials."
            else:
                checks["template"] = True
                checks["template_status"] = "INTERNAL"
                checks["template_status_verbose"] = "INTERNAL. This .blend file has appropriately named materials."
    



    # endregion




    # -----------------------------
    # customizable shaders checks
    # region

    # Default one
    default_custom_shaders_blend_filepath = os.path.join(ADDON_ROOT, "resources", "Custom SWTOR Shaders.blend")

    # Current one
    custom_shaders_blend_filepath = getattr(bpy.context.preferences.addons["zg_swtor_tools"].preferences, "swtor_custom_shaders_blendfile_path", "")
        
    blend_file_badly_written = (".blend" not in custom_shaders_blend_filepath or os.sep not in custom_shaders_blend_filepath)
    blend_file_exists = Path(custom_shaders_blend_filepath).is_file()
    blend_file_is_internal = (custom_shaders_blend_filepath == default_custom_shaders_blend_filepath)

    # Check .blend file's insides for a custom Garment shader to validate it:
    # (see https://devtalk.blender.org/t/traverse-blend-file-to-get-list-of-collections/10348/14 
    # the '_' avoids loading anything in the destination)
    if blend_file_exists:
        blend_file_is_valid = False
        with bpy.data.libraries.load(str(custom_shaders_blend_filepath)) as (data_from, _):
            blend_file_is_valid = "SWTOR - Garment Shader" in data_from.node_groups
    else:
        blend_file_is_valid = False

    checks["custom_shaders"] = blend_file_exists

    if blend_file_exists:
        if blend_file_is_valid:
            checks["custom_shaders"] = True
            if blend_file_is_internal:
                checks["custom_shaders_status"] = "INTERNAL"
                checks["custom_shaders_status_verbose"] = "INTERNAL. Uses the Custom SWTOR Shaders .blend file inside the Add-on."
            else:
                checks["custom_shaders_status"] = "EXTERNAL"
                checks["custom_shaders_status_verbose"] = "EXTERNAL. Uses a Custom SWTOR Shaders .blend file outside the Add-on."
        else:
            checks["custom_shaders"] = False
            checks["custom_shaders_status"] = "NOT VALID"
            checks["custom_shaders_status_verbose"] = "NOT VALID. This .blend file doesn't contain valid Custom SWTOR Shaders."
    else:
        if blend_file_badly_written:
            checks["custom_shaders"] = False
            checks["custom_shaders_status"] = "NOT VALID"
            checks["custom_shaders_status_verbose"] = "NOT VALID. This is not a .blend file path."
        else:
            checks["custom_shaders"] = False
            checks["custom_shaders_status"] = "NOT FOUND"
            checks["custom_shaders_status_verbose"] = "NOT FOUND. No .blend file can't be found at the specified path."
    # endregion




    return checks