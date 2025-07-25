import bpy
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
import hashlib
import numpy as np
import re
import zlib



ADDON_NAME = __name__.rsplit(".")[0]
ADDON_ROOT = __file__.rsplit(__name__.rsplit(".")[0])[0] + ADDON_NAME


DEFAULT_TEMPLATES_FOLDERPATH = os.path.join(ADDON_ROOT, "resources","default_materials_templates")





# ---- SWTOR TEMPLATE MATERIALS' ANALYSIS -----------------------

# Simple list of a SWTOR templates file's TOR materials.
def read_swtor_template_mats_names_in_file(blend_filepath):
    """
    returns a list of materials' names that start with "TOR-"

    Args:
        blend_filepath (str): Path to the .blend file.
        
    Returns:
        swtor_mats_names (list): list of names or None
    """    
    with bpy.data.libraries.load(str(blend_filepath), link=False) as (data_from, _ ):
        swtor_mats_names = [str(mat) for mat in data_from.materials if str(mat).startswith("TOR-")]
        if len(swtor_mats_names) > 0:
            return swtor_mats_names
        else:
            return None


# ---- SWTOR TEMPLATE MATERIALS LOADER ----------------------------
# PROCESS TO IMPORT AND CHECK EXT VS INTERNAL MATS
'''
NO CHECKS FOR PREVIOUS SWTOR MATS: THERE MIGHT BE MANUAL APPENDINGS,
SO, SCORCHED EARTH: ASSUME THERE COULD BE LINGERING NGs AND MATERIALS.
1. Rename NGs as "old-datetime"
2. Delete mats.
3. Import new mats.
4. Hash-compare-dedupe old NGs to new NGs
'''

def purge_old_tor_node_groups():
    count = 0
    for ng in bpy.data.node_groups:
        name = ng.name
        if ng.users == 0 and name.startswith("TOR") and "-OLD" in name:
            bpy.data.node_groups.remove(ng)
            count += 1
            print(f"Removed: {name}")
            
def append_swtor_materials_from_template_blend_file(blend_filepath):
    """
    Loads all SWTOR template materials in the .blend file at that filepath
    (those whose names start with "TOR"). Deletes previously existing ones
    but preserves their node groups if still in use in objects' materials
    by adding "OLD[DATETIME]" suffixes to their names.

    Args:
        blend_path (str): Path to the .blend file.
    """
    
    # Avoid appending if the currently opened project file is a templates file
    addon_prefs = bpy.context.preferences.addons["zg_swtor_tools"].preferences    

    working_blend_folderpath = os.path.dirname(bpy.data.filepath)
    internal_templates_folderpath = os.path.join(ADDON_ROOT, "resources","default_materials_templates")
    external_templates_folderpath = addon_prefs.external_swtor_template_mats_folderpath
    
    if working_blend_folderpath == internal_templates_folderpath or working_blend_folderpath == external_templates_folderpath:
        return
    
    # 1- Unprotect and delete all existing SWTOR materials templates
    for mat in list(bpy.data.materials):
        if mat.name.startswith("TOR-"):
            mat.use_fake_user = False
            bpy.data.materials.remove(mat)


    # 2- Rename existing SWTOR node groups in use by objects' materials to secure them from collisions
    #   with updated material templates' node groups by adding an "-OLD<datetime>" suffix
    #   (this scheme evades typical deduplicators).
    #   Directly remove zero user TOR node groups.
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    for ng in list(bpy.data.node_groups):
        if ng.name.startswith("TOR-") or ng.name.startswith("TOR_Aux-"):
            # Directly remove those not in use
            if ng.users == 0:
                bpy.data.node_groups.remove(ng)
                continue
            
            # Mark as old those in use and not marked so previously.
            if "-OLD" not in ng.name:
                ng.name = f"{ng.name}-OLD {timestamp}"
                # Make them garbage-collectable (just in case. It shouldn't be necessary, as we don't usually protect them)
                ng.use_fake_user = False


    # 3- Append new SWTOR materials templates (which also brings their own NGs)
    
    # This is bpy's current tomfoolery of a system for appending stuff:
    with bpy.data.libraries.load(str(blend_filepath), link=False) as (data_from, data_to):
        # data_from and data_to are proxies of the origin and destination .blend files'
        # internal hierarchies (which can be examined in the Outliner's File View):
        # subdirectories of Objects, Materials, Cameras…
        #
        # Typically, to move the materials we would just do:
        #
        #   data_to.materials = data_from.materials
        #
        # But we want to filter out any non-SWTOR stuff (drafts, some add-ons' trash…),
        # hence we do some data_from.materials pre-processing.
        #
        # While inside this "with" context, data_from and data_to's data can be
        # handled as simple lists of bpy items' names. The criteria, for now, is
        # that the material's name starts with "TOR" (if one is building draft
        # materials, prefix them in some other manner so that they aren't loaded).
        swtor_mats_to_append = [mat for mat in data_from.materials if str(mat).startswith("TOR-")]

        data_to.materials = swtor_mats_to_append
        
    # Protect them with fake users
    for mat in swtor_mats_to_append:
        mat.use_fake_user = True

    # Node Group deduplication pass? Could be costly.
    # WARNING:
    # (Any dedupe pass needs to be done outside the "with" because,
    # if it happens inside, the materials are retained by the
    # data.libraries.load() "with" context and don't get deleted)
    pass
        


# ---- BLENDER MATERIAL NODETREE REPLACER ------------------------------


def copy_material_non_rna_properties(target_mat, source_mat):
    """
   (Blender-generic)
    
    Copies a material's properties's values to a target material.
    Skips all dunder ones (names surrounded by double underlines).
    Avoids or traps copying those that are read-only.

    Args:
        bpy.Types.Materials: target material.
        bpy.Types.Materials: source material.
    """
    
    # Get built-in RNA properties to skip them
    builtin_keys = {prop.identifier for prop in source_mat.bl_rna.properties}

    for key in source_mat.keys():
        if key in builtin_keys or key.startswith("_"):
            continue  # Skip built-in or internal keys

        try:
            target_mat[key] = source_mat[key]
        except Exception as e:
            print(f"Warning: Couldn't copy custom property '{key}': {e}")

    # Copy custom UI layout only for valid keys
    if "_RNA_UI" in source_mat:
        target_mat["_RNA_UI"] = {}
        for key, value in source_mat["_RNA_UI"].items():
            if key in target_mat:
                try:
                    target_mat["_RNA_UI"][key] = value.copy()
                except Exception as e:
                    print(f"Warning: Couldn't copy _RNA_UI layout for '{key}': {e}")
                    
def replace_material_node_tree_OLD(target_mat, source_mat):
    """
   (Blender-generic)
    
    Rewrites a Blender material's node tree and material settings
    with those of another material.
    
    Args:
        target_mat (str or bpy.types.Material): material to overwrite.
        source_mat (str or bpy.types.Material): material to be the source of data.
    """    
    if not target_mat or not source_mat:
        print("Missing Materials in arguments")
        return


    # If materials args are strings, convert to material data blocks
    if not isinstance(target_mat, bpy.types.Material):
        target_mat = bpy.data.materials[target_mat]
        
    if not isinstance(source_mat, bpy.types.Material):
        source_mat = bpy.data.materials[source_mat]
    

    # -- General Material Properties --
    target_mat.use_nodes = True
    source_mat.use_nodes = True

    basic_mat_props_to_copy = [
        "blend_method",
        "shadow_method",
        "use_backface_culling",
        "show_transparent_back",
        "use_screen_refraction",
        "use_sss_translucency",
        "alpha_threshold",
        "use_transparency",
    ]


    # Copy basic properties (tolerates trying deprecated ones)
    for prop in basic_mat_props_to_copy:
        if hasattr(source_mat, prop) and hasattr(target_mat, prop):
            try:
                setattr(target_mat, prop, getattr(source_mat, prop))
            except Exception:
                pass

    # Clear existing nodes and links
    tgt_tree = target_mat.node_tree
    src_tree = source_mat.node_tree
    tgt_tree.nodes.clear()
    tgt_tree.links.clear()

    node_map = {}


    # Copy Nodes
    for node in src_tree.nodes:
        new_node = tgt_tree.nodes.new(type=node.bl_idname)
        new_node.location = node.location

        for attr in dir(node):
            if attr.startswith("_") or callable(getattr(node, attr)):
                continue
            try:
                setattr(new_node, attr, getattr(node, attr))
            except Exception:
                pass

        # Handle some specific node types
        if node.type == 'TEX_IMAGE' and node.image:
            new_node.image = node.image

        if node.type == 'GROUP' and node.node_tree:
            new_node.node_tree = node.node_tree

        if node.type == 'FRAME':
            # We are having problems with frames keeping their visible location: although
            # the data is correctly copied, they appear as if their origin was changed
            # from center to corner. TO INVESTIGATE. 
            pass

        node_map[node] = new_node


    # Copy Links
    for link in src_tree.links:
        from_node = node_map.get(link.from_node)
        to_node = node_map.get(link.to_node)
        if from_node and to_node:
            try:
                tgt_tree.links.new(
                    from_node.outputs.get(link.from_socket.name),
                    to_node.inputs.get(link.to_socket.name)
                )
            except Exception:
                pass


    # Copy Custom Properties (User-defined only)
    # DOES THIS MAKE COPYING BASIC MAT PROPS REDUNDANT?
    copy_material_non_rna_properties(target_mat, source_mat)


    print(f"Material '{target_mat.name}' was successfully overwritten with data from '{source_mat.name}'.")


def get_copyable_material_attributes(material):
    """
    Returns a list of material attributes that can be safely copied.
    """
    copyable_attrs = []
    for attr in dir(material):
        if attr in {"name", "_RNA_UI"}:
            continue  # don't copy material name or internal data
        if attr.startswith("_"):
            continue
        try:
            value = getattr(material, attr)
            if callable(value):
                continue
            if isinstance(value, (int, float, str, bool)):
                copyable_attrs.append(attr)
            elif attr == "node_tree":
                copyable_attrs.append(attr)
        except Exception:
            continue
    return copyable_attrs

def replace_material_node_tree(target_mat, source_mat):
    """
    Copies material settings and node tree from source to target material.
    """
    if not source_mat or not target_mat:
        print("Source or target material not found.")
        return

    # If materials args are strings, convert to material data blocks
    if not isinstance(target_mat, bpy.types.Material):
        target_mat = bpy.data.materials[target_mat]
        
    if not isinstance(source_mat, bpy.types.Material):
        source_mat = bpy.data.materials[source_mat]
        
        
    attrs = get_copyable_material_attributes(source_mat)

    for attr in attrs:
        try:
            if attr == "node_tree" and source_mat.use_nodes and target_mat.use_nodes:
                # Clear target node tree
                target_mat.node_tree.nodes.clear()
                target_mat.node_tree.links.clear()

                # Copy node setup
                node_map = {}

                for node in source_mat.node_tree.nodes:
                    new_node = target_mat.node_tree.nodes.new(type=node.bl_idname)
                    new_node.name = node.name
                    new_node.label = node.label
                    new_node.location = node.location
                    for prop in node.bl_rna.properties:
                        if not prop.is_readonly:
                            setattr(new_node, prop.identifier, getattr(node, prop.identifier))
                    node_map[node] = new_node

                for link in source_mat.node_tree.links:
                    from_node = node_map.get(link.from_node)
                    to_node = node_map.get(link.to_node)
                    if from_node and to_node:
                        target_mat.node_tree.links.new(
                            from_node.outputs[link.from_socket.name],
                            to_node.inputs[link.to_socket.name]
                        )
            else:
                setattr(target_mat, attr, getattr(source_mat, attr))
        except Exception as e:
            print(f"Failed to copy {attr}: {e}")

    print(f"Copied attributes from '{source_mat.name}' to '{target_mat.name}'.")







# ---- SWTOR MATERIAL DATA PARSERS -------------------------------------

def swtor_mat_file_to_dict(swtor_mat_filepath):
    """
    (SWTOR-specific)
    
    returns a flat dict of swtor-named inputs and values
    in the most appropriate data types, separating some
    into components (palette hue-sat-bg-con, etc.)

    Args:
        swtor_mat_filepath (str | Path): filepath to a SWTOR .mat xml file.

    Returns:
        dict: key:value is {.mat element: element's value}
              (value is converted to the type most appropriate
               to its use in Blender's node group inputs. Some
               elements are decomposed or rearranged if needed)
    """
    
    mat_dict = {}
    
    # Get SWTOR .mat file and its .xml data
    # mat_filepath = swtor_shaders_path / (mat.name + ".mat")
    
    try:
        tree = ET.parse(swtor_mat_filepath)
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return None
    except IOError as e:
        print(f"I/O error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    
    root = tree.getroot()


    for element in root:
        
        element_name = element.tag
        
        # swtor material's "parameters"
        if element_name != "input":
            
            element_value = element.text
            
            # AlphaMode is treated differently because it can't
            # be implemented as a radio button in node groups.
            if element_name.startswith("AlphaMode"):
                element_name = f"{element_name} {element_value}"
                element_value = True
            
            # Non-string value types to convert to Python ones
            if element_name   == "AlphaTestValue":
                element_value = float(element_value)
                
            elif element_name == "IsTwoSided":
                element_value = element_value.lower() == "true"  # Proper way to turn it into a bool version
                
            elif element_value == "":
                element_value = None

            mat_dict[element_name] = element_value


        # swtor material's "inputs"
        elif element_name == "input":
            
            element_semantic = element.find("semantic").text
            element_type     = element.find("type").text
            element_value    = element.find("value").text
            
            
            # Texturemaps
            if element_type == "texture":
                # normalize relative file path
                element_value = element_value.replace("\\", "/")
                if element_value[0:1] == "/":
                    element_value = element_value[1:]
                mat_dict[element_semantic] = element_value


            # SWTOR Types that require conversions to Blender node input types:
            
            # Convert Palette vector data to separate float entries
            elif element_semantic == "palette1" or element_semantic == "palette2":
                palette_vector = tuple(map(float, element_value.split(',')))
                mat_dict[f"{element_semantic} Hue"]        = palette_vector[0]
                mat_dict[f"{element_semantic} Saturation"] = palette_vector[1]
                mat_dict[f"{element_semantic} Brightness"] = palette_vector[2]
                mat_dict[f"{element_semantic} Contrast"]   = palette_vector[3]
                

            # Convert WrinkleMult vector data to separate float entries
            elif element_semantic.startswith("animatedWrinkleMult"):
                wrinklemult_vector = tuple(map(float, element_value.split(',')))
                mat_dict[f"{element_semantic} Right"]  = wrinklemult_vector[0]
                mat_dict[f"{element_semantic} Left"]   = wrinklemult_vector[1]
                mat_dict[f"{element_semantic} Eyes"]   = wrinklemult_vector[2]
                mat_dict[f"{element_semantic} Center"] = wrinklemult_vector[3]


            # Convert AnimatedUV's AnimTexTint float data to vector data.
            # Also, trim the .mat vect4 to vect3 by eliminating the 4th component,
            # as Blender's vect node inputs only do vect3. 
            elif element_semantic.startswith("animTexTint"):
                if element_type == "float":
                    mat_dict[element_semantic] = tuple(map(float, [element_value] * 3))
                else:
                    mat_dict[element_semantic] = tuple(map(float, element_value.split(',')[0:3]))


            # Common types:
            
            # RGBA (there might be no Alpha, requiring adding a default A value)
            elif element_type == "rgba":
                if element_value.count(",") == 2:
                    mat_dict[element_semantic] = tuple(map(float, element_value.split(','))) + (1.0,)
                else:
                    mat_dict[element_semantic] = tuple(map(float, element_value.split(',')))

            # Booleans
            elif element_type == "bool":
                mat_dict[element_semantic] = element_value.lower() == "true"  # Proper way to turn it into a bool version

            # Floats
            elif element_type == "float":
                mat_dict[element_semantic] = float(element_value)
                
            # Vectors
            elif element_type == "vector4":
                mat_dict[element_semantic] = tuple(map(float, element_value.split(',')))
                
            # uvscale (they are vector2. Blender inputs need them to be vector3)
            elif element_type == "uvscale":
                mat_dict[element_semantic] = tuple(map(float, element_value.split(','))) + (0.0,)


    return mat_dict

def swtor_garmenthue_file_to_dict(swtor_garmenthue_filepath, palette_number=1):
    """
    (SWTOR-specific)
    
    Returns a flat dict of swtor-named inputs and values
    in the most appropriate data types,
    
    Args:
        swtor_garmenthue_filepath (str | Path): garmenthue .xml file's path.
        palette_number (int, optional): which palette to adress.
                                        1, 2, or None for further manipulation.
                                        It's added to the "Palette" input name.

    Returns:
        mat_dict (dict):    keys:values are {.mat element's name: element's value}.
                            Values (str) are converted to the type most appropriate
                            to its use in Blender's node group inputs (floats, tuples).
    """
    
    if palette_number not in [1, 2, None]:
        print()
        print("WARNING: palette number is incorrect)\n")
        print()
        return None
    if palette_number is None:
        palette_number = ""


    # dict for renaming the garmenthue parameters' tags to .mat-style ones.
    # It is a bit of a bother having to do these things, but each type of
    # SWTOR material data source does its own thing, naming-wise, so…
    renamings = {
        "Hue"                   : f"Palette{palette_number} Hue",                   # float
        "Saturation"            : f"Palette{palette_number} Saturation",            # float
        "Brightness"            : f"Palette{palette_number} Brightness",            # float
        "Contrast"              : f"Palette{palette_number} Contrast",              # float
        "Specular"              : f"Palette{palette_number} Specular",              # RGBA
        "Metallicspecular"      : f"Palette{palette_number} MetallicSpecular",      # RGBA
        
        # The following parameters aren't clear how they could be used (they probably
        # modify other existing parameters instead of being part of the shaders)
        # We are using the "Palette"1/2 bit to set which palette they will affect.
        "CarPaintColor"         : f"Palette{palette_number} CarPaintColor",         # RGBA
        "MetallicAdjust"        : f"Palette{palette_number} MetallicAdjust",        # vector4 maybe
        "EnvMapAdjust"          : f"Palette{palette_number} EnvMapAdjust",          # vector4 maybe

        # Maybe could be used for non-editable color previews in node groups?
        "Representativecolor"   : f"Palette{palette_number} RepresentativeColor",   # RGB
    }
    
    
    mat_dict = {}
    
    # Get SWTOR .mat file and parse its .xml data
    # mat_filepath = swtor_shaders_path / (mat.name + ".mat")
    try:
        tree = ET.parse(swtor_garmenthue_filepath)
    except ET.ParseError as e:
        print(f"XML parsing error: {e}")
        return None
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return None
    except IOError as e:
        print(f"I/O error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    
    root = tree.getroot()

    for element in root:
        if element.tag in renamings:
            # if an element's text has components separated by commas, it is a vector or a RGB/RGBA:
            # turn it into a tuple of floats. If not, it is a float (there are no bools or strings in GarmentHues).
            if ',' in element.text:
                mat_dict[renamings[element.tag]] = tuple(map(float, element.text.split(',')))
            else:
                mat_dict[renamings[element.tag]] = float(element.text)

    return mat_dict

# TO DO.
def swtor_json_data_to_dict():
    pass




# ---- BLENDER MATERIAL MODIFIERS --------------------------------------

def apply_swtor_mat_dict_to_material(target_blender_mat, swtor_mat_dict, swtor_resources_folderpath):
    """
    (SWTOR-specific)

    Applies the data in a dictionary holding SWTOR material data in {input name: value} format
    to a Blender Material by searching for matched node group input names and texturemap node names.
    
    If the image to be assigned to a texturemap node doesn't exist in the project, it is imported
    from the 'resources' folder. It is set to Non-Color.

    Args:
        target_blender_mat (str or bpy.types.Material): Blender material to be processed
        swtor_mat_dict (dict): dictionary of SWTOR material data.
        swtor_resources_folderpath (str | Path): path to a SWTOR resources folder.
    """
    
    if not swtor_resources_folderpath:
        print("WARNING: NO SWTOR RESOURCES FOLDER PATH SET\n")
        return
    
    if isinstance(swtor_resources_folderpath, str):
        swtor_resources_folderpath = Path(swtor_resources_folderpath)
    
    
    nodegroups_inputs, texturemap_nodes = copy_material_inputs_objects_to_swtor_mat_dicts(target_blender_mat, exclude_linked=True)

    # Normalize keys to lowercase for easier, error-tolerant matching
    swtor_mat_dict    = {k.lower(): v for k, v in swtor_mat_dict.items()}
    nodegroups_inputs = {k.lower(): v for k, v in nodegroups_inputs.items()}
    texturemap_nodes  = {k.lower(): v for k, v in texturemap_nodes.items()}


    # Node group inputs
    print()
    print("Input data to copy vs. template's existing data")

    for input_name in nodegroups_inputs.keys():
        if input_name in swtor_mat_dict:
            print(input_name, nodegroups_inputs[input_name].default_value, swtor_mat_dict[input_name])

            nodegroups_inputs[input_name].default_value = swtor_mat_dict[input_name]


    # Texturemap nodes
    print()
    print("Texture data to copy")

    for node_name in texturemap_nodes:
        if node_name in swtor_mat_dict:
            texturemap_relative_filepath = swtor_mat_dict[node_name]
            texture_name = os.path.basename(texturemap_relative_filepath)
            
            print("Texturemap Node:", node_name)
            print("Texturemap     :", texture_name)

            texturemap_absolute_filepath = swtor_resources_folderpath / f"{texturemap_relative_filepath}.dds"
            try:
                texturemap = bpy.data.images.load(str(texturemap_absolute_filepath), check_existing=True)
                texturemap.colorspace_settings.name = 'Non-Color'
                
                texturemap_nodes[node_name].image = texturemap
            except:
                continue


# NOT IN USE YET BUT NEEDED FOR BETWEEN TEMPLATES-CONVERSION WHILE PRESERVING MATERIAL INPUTS DATA
# SWTOR-specific-ish because of filtering out linked inputs (risk of duplicates otherwise).
def copy_material_inputs_objects_to_swtor_mat_dicts(blender_mat, exclude_linked=True):
    """
   (Blender-generic)
    
    Goes through the material's node groups and texturemap nodes
    and builds for each kind a dictionary whose key:values are
    their names and objects. These dictionaries help manipulate
    the material's characteristics without needing to know what
    node holds what and in which position.
    
    For example, storing a key:value of
    "DiffuseMap":<bpy.data.materials.node_tree.node["DiffuseMap"]>
    will let us just give texturemap nodes messages such as:
    texturemap_nodes["DiffuseMap].image = <IMAGE>
    without having to know anything about the node at all.
    
    Same goes for node groups' inputs: the input objects know
    which node group they belong to, what type they are, etc.

    Args:
        blender_mat (str or bpy.types.Material): material to scan
        exclude_linked (bool, optional): exclude imputs that receive links

    # Returns:
    dict: {input name str: bpy.types.NodeLinks object}
    
    dict: {texturemap node's name str: bpy.types.TextureNode object}
    """

    if not isinstance(blender_mat, bpy.types.Material):
        blender_mat = bpy.data.materials[blender_mat]
        
    nodes = blender_mat.node_tree.nodes
    
    nodegroups_inputs = {}
    texturemap_nodes = {}
    
    for node in nodes:
        
        if node.type == "GROUP":
            for input in node.inputs:
                # if exclude_linked is True,
                # filter out inputs that receive their data
                # from other nodes they are linked to. This
                # prevents issues with auxiliary nodegroups
                # whose names match main nodegroup inputs.
                if exclude_linked and input.is_linked:
                    continue
                else:
                    nodegroups_inputs[input.name] = input
                
        if node.type == "TEX_IMAGE":
            texturemap_nodes[node.name] = node
    
    return nodegroups_inputs, texturemap_nodes




# ---- UNUSED!!!! TO DEVELOP OR THINK ABOUT ---------------------------

def copy_material_inputs_values_to_swtor_mat_dicts(blender_mat, exclude_linked=True):
    """
    Stores all node groups inputs' default_value data
    and texturemap nodes' image objects in dictionaries.
    
    Those can be used to keep the most approximate state
    of a SWTOR Blender material while its node_tree is
    being swapped by that of a new template material.
    The idea is to be able to restore those settings
    afterwards as best as the new node_tree allows for.

    Args:
        swtor_mat_filepath (str or bpy.Types.material).
        exclude_linked (bool, optional): exclude imputs that receive links

    Returns:
        (Two dicts, whose values' types are the ones required by the nodes' inputs.
         Separating into two dicts simplifies knowing what's what)
        dict of nodegroup input's name str: input's default_value and type.
        dict of texture map node's name str: bpy.Types.image object.
    """
    
    if not isinstance(blender_mat, bpy.types.Material):
        blender_mat = bpy.data.materials[blender_mat]
        
    nodes = blender_mat.node_tree.nodes
    
    nodegroups_values = {}
    texturemap_nodes_images = {}
    
    for node in nodes:
        
        if node.type == "GROUP":
            for input in node.inputs:
                # Filter out inputs that receive their data
                # from other nodes they are linked to. This
                # prevents issues with auxiliary nodegroups
                # whose names match main nodegroup inputs.
                if exclude_linked and input.is_linked:
                    continue
                else:
                    nodegroups_values[input.name] = input
                
        if node.type == "TEX_IMAGE":
            texturemap_nodes_images[node.name] = node.image
    
    return nodegroups_values, texturemap_nodes_images

def copy_material_inputs_to_swtor_mat_dict(blender_mat):
    """
    Stores all node groups inputs' default_value data
    and texturemap nodes' image objects in dictionaries.
    
    Those can be used to keep the most approximate state
    of a SWTOR Blender material while its node_tree is
    being swapped by that of a new template material.
    The idea is to be able to restore those settings
    afterwards as best as the new node_tree allows for.

    Args:
        swtor_mat_filepath (str or bpy.Types.material).

    Returns:
        dict: keys:values are {nodegroup input's name str: input's default_value}.
        dict: keys:values are {texture map node's name str: bpy.Types.image object}.
    """
    
    if not isinstance(blender_mat, bpy.types.Material):
        blender_mat = bpy.data.materials[blender_mat]
        
    nodes = blender_mat.node_tree.nodes
    
    nodegroups_values = {}
    texturemap_nodes_images = {}
    
    for node in nodes:
        
        if node.type == "GROUP":
            for input in node.inputs:
                # Filter out inputs that receive their data
                # from other nodes they are linked to. This
                # prevents issues with auxiliary nodegroups
                # whose names match main nodegroup inputs.
                if not input.is_linked:
                    nodegroups_values[input.name] = input.default_value
                
        if node.type == "TEX_IMAGE":
            texturemap_nodes_images[node.name] = node.image
    
    return nodegroups_values, texturemap_nodes_images

def process_blender_materials_with_swtor_mat_names(mats, swtor_resources_folderpath):
    pass

# Node Tree hasher for deduplicating node groups with matching names 
def compute_hash(data: str, method="crc32") -> str:
    encoded = data.encode("utf-8")
    '''
    Requires import zlib
    '''
    if method == "sha256":   # slower, high resistance to collisions
        return hashlib.sha256(encoded).hexdigest()
    elif method == "crc32":  # very fast, lower resistance to collisions
        return f"{zlib.crc32(encoded):08x}"
    else:
        raise ValueError(f"Unsupported hash method: {method}")

def hash_image(image):
    """Generate a hash from in-memory image pixel data using NumPy."""
    if not image.has_data:
        return "NO_IMAGE_DATA"
    try:
        pixels = np.array(image.pixels[:], dtype=np.float32)
        pixel_bytes = (pixels * 255).astype(np.uint8).tobytes()
        return hashlib.sha256(pixel_bytes).hexdigest()
    except Exception as e:
        return f"IMAGE_ERROR:{str(e)}"

def hash_drivers(anim_data):
    driver_data = []
    if anim_data:
        for fcurve in anim_data.drivers:
            dp = fcurve.data_path
            idx = fcurve.array_index
            expr = fcurve.driver.expression if fcurve.driver else ""
            driver_data.append(f"DRIVER:{dp}[{idx}]={expr}")
            for var in fcurve.driver.variables:
                vline = f"  VAR:{var.name}:{var.type}"
                for tgt in var.targets:
                    ref = f"{tgt.id.name if tgt.id else ''}.{tgt.data_path}"
                    vline += f" -> {ref}"
                driver_data.append(vline)
    return sorted(driver_data)

def hash_text_block(text_block):
    if text_block is None:
        return "NO_TEXT"
    try:
        content = text_block.as_string()
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    except Exception as e:
        return f"TEXT_ERROR:{str(e)}"

def hash_node_tree(node_tree: bpy.types.NodeTree, visited=None, method="sha256"):
    if not isinstance(node_tree, bpy.types.NodeTree):
        raise TypeError("Expected a NodeTree")

    # Vsited is used to check for cyclic references situations
    if visited is None:
        visited = set()

    if node_tree.name in visited:
        return f"CYCLIC_REF:{node_tree.name}"
    visited.add(node_tree.name)


    hash_data = []
    hash_data.append(f"NODETREE:{node_tree.name}:{node_tree.bl_idname}")

    # Custom properties on the node tree
    for key in sorted(node_tree.keys()):
        if key != "_RNA_UI":
            val = node_tree[key]
            hash_data.append(f"NODETREE_CUSTOM_PROP:{key}:{str(val)}")

    for node in sorted(node_tree.nodes, key=lambda n: n.name):
        hash_data.append(f"NODE:{node.name}:{node.bl_idname}:{node.label}")
        hash_data.append(f"LOC:{node.location[0]:.3f},{node.location[1]:.3f}")

        for socket in node.inputs:
            if hasattr(socket, "default_value"):
                try:
                    val = socket.default_value
                    val_str = str(tuple(val)) if hasattr(val, "__iter__") else str(val)
                    hash_data.append(f"INPUT:{socket.name}:{val_str}")
                except:
                    hash_data.append(f"INPUT:{socket.name}:UNREADABLE")

        for socket in node.outputs:
            if hasattr(socket, "default_value"):
                try:
                    val = socket.default_value
                    val_str = str(tuple(val)) if hasattr(val, "__iter__") else str(val)
                    hash_data.append(f"OUTPUT:{socket.name}:{val_str}")
                except:
                    hash_data.append(f"OUTPUT:{socket.name}:UNREADABLE")

        for prop in node.bl_rna.properties:
            if prop.identifier not in {'name', 'location', 'width'} and not prop.is_readonly:
                try:
                    val = getattr(node, prop.identifier)
                    hash_data.append(f"PROP:{node.name}:{prop.identifier}:{str(val)}")
                except:
                    continue

        for key in sorted(node.keys()):
            if key != "_RNA_UI":
                val = node[key]
                hash_data.append(f"CUSTOM_PROP:{node.name}:{key}:{str(val)}")

        if hasattr(node, "script") and isinstance(node.script, bpy.types.Text):
            text_hash = hash_text_block(node.script)
            hash_data.append(f"TEXTBLOCK:{node.name}:{node.script.name}:{text_hash}")

        if node.bl_idname == 'ShaderNodeTexImage' and node.image:
            img_hash = hash_image(node.image)
            hash_data.append(f"IMAGE:{node.name}:{img_hash}")

        if node.animation_data:
            for line in hash_drivers(node.animation_data):
                hash_data.append(f"NODE_DRIVER:{node.name}:{line}")

        if hasattr(node, "node_tree") and isinstance(node.node_tree, bpy.types.NodeTree):
            nested_hash = hash_node_tree(node.node_tree, visited, method)
            hash_data.append(f"NESTED_NODETREE:{node.name}:{nested_hash}")

    for link in sorted(node_tree.links, key=lambda l: (l.from_node.name, l.to_node.name)):
        hash_data.append(f"LINK:{link.from_node.name}:{link.from_socket.name}->{link.to_node.name}:{link.to_socket.name}")

    return compute_hash("\n".join(hash_data), method=method)

# Deduplicator based on such hashes
def deduplicate_swtor_node_groups():
    '''
    Deduplicates node groups whose name follow the
    TOR-<shader name>-OLD<number> scheme with
    TOR-<shader name> ones if having matching hashes.
    e.g.: TOR-Uber-OLD12345678 to TOR-Uber
    
    requires import re
    '''
    # Regex to match names like "TOR-something-OLDxxxx"
    # (parentheses divide a match's result into groups
    # that are retrievable as elements in a list by
    # the re.MatchObject.group() method.
    # 1st group's index in  in list is 1,
    # not 0 which is the whole string).
    old_pattern = re.compile(r"^(TOR-.+)-OLD \d+$")

    # Collect hashes of top-level (deduplicated) node groups
    dedup_map = {
        group.name: (hash_node_tree(group), group)
        for group in bpy.data.node_groups
        if group.name.startswith("TOR-") and not old_pattern.match(group.name)
    }

    # Process all node groups named like TOR-...-OLDxxxx
    for old_group in list(bpy.data.node_groups):
        match = old_pattern.match(old_group.name)
        if not match:
            continue

        base_name = match.group(1)  # remember, 1st element has index = 1
        old_hash = hash_node_tree(old_group)

        # Look for matching base group
        for name, (main_hash, main_group) in dedup_map.items():
            if name.startswith(base_name) and old_hash == main_hash:
                print(f"Deduplicating {old_group.name} → {main_group.name}")

                # Replace usage in other node groups (flat only)
                for container in bpy.data.node_groups:
                    for node in container.nodes:
                        if node.type == 'GROUP' and node.node_tree == old_group:
                            node.node_tree = main_group

                # Remove the OLD group
                bpy.data.node_groups.remove(old_group)
                break

# Simpler deduplicators (but better than others we have. For future reuse)
def deduplicate_materials(base_names=None):
    """
    (Blender-generic)

    Deduplicates materials that have a ".001"-style numerical suffix in their names.
    If there are suffixed materials that have no non-suffixed counterpart, the first
    of those found will be turned into a suffix-less base one.
    
    Args:
        base_materials_names (list of str, optional):   list of material names whose duplicates have to be deduplicated.
                                                        If None, it deduplicates all materials in the scene.
                                                         Defaults to None.
    """
    if bpy.data.materials:
        for mat in list(bpy.data.materials):  # loops through a copy of bpy.data.materials to avoid issues.
            # Get the material name as 3-tuple (base, separator, extension)
            mat_name = mat.name  # ought to be a little speed-up
            (base, sep, ext) = mat_name.partition('.')
            if base_names and base not in base_names:
                continue
            # Replace the numbered duplicate with the original if found
            if ext.isnumeric():
                original_mat = bpy.data.materials.get(base)
                if original_mat:
                    mat = original_mat
                    # Delete deduped material
                    bpy.data.materials.remove(bpy.data.materials[mat_name])
                else:
                    # If there is no suffix-less "original" material,
                    # rename the current one to become the original one.
                    mat.name = base

def deduplicate_node_groups(base_names=None):
    """
    (Blender-generic)

    Deduplicates node groups that have a ".001"-style numerical suffix in their names.
    If there are suffixed node groups that have no non-suffixed counterpart, the first
    of those found will be turned into a suffixless one.
    
    Args:
        base_names (list of str, optional):     list of node group names whose duplicates have to be deduplicated.
                                                If None, it deduplicates all node groups in the scene.
                                                Defaults to None.
    """
    if bpy.data.node_groups:
        for node_group in list(bpy.data.node_groups):  # loops through a copy of bpy.data.node_groups to avoid issues.
            # Get the material name as 3-tuple (base, separator, extension)
            node_group_name = node_group.name  # ought to be a little speed-up
            (base, sep, ext) = node_group.name.partition('.')
            if base_names and base not in base_names:
                continue
            # Replace the numbered duplicate with the original if found
            if ext.isnumeric():
                original_node_group = bpy.data.node_groups.get(base)
                if original_node_group:
                    node_group = original_node_group
                    # Delete deduped material
                    bpy.data.node_groups.remove(bpy.data.node_groups[node_group_name])
                else:
                    # If there is no suffix-less "original" node group,
                    # rename the current one to become the original one.
                    node_group.name = base






# TESTS BLOCK --------------------------------------------------------------------------------------------

def main():
    # IT PROCESSES THE ACTIVE OBJECT'S MATERIAL IN THE STYLE OF THE NAMED MATERIALS PROCESSOR TOOL,
    # CHECKING THE MATERIAL'S NAME AND LOOKING FOR A MATCHING .MAT FILE.
    # (IF THE OBJECT LACKS A MATERIAL OR THE MATERIAL DOESN'T USE NODES, IT WILL EXIT)
    
    # IT ALSO TESTS APPLYING A COUPLE OF GARMENTHUES (THEIR PATHS NEED TO BE SET IN THIS CODE,
    # ALONGSIDE THE PATHS TO THE MATERIAL TEMPLATES .BLEND FILE AND THE RESOURCES FOLDER).



    # ------------------------------------
    # MANUAL SETUP SECTION:
    
    # SWTOR ASSETS AND TEMPLATES SOURCES:
    swtor_resources_folderpath = r"D:\3D SWTOR\SWTOR ASSETS\SWTOR EXTRACTION 64\resources"
    swtor_template_filepath    = r"D:\3D SWTOR\SWTOR ASSETS\SWTOR EXTRACTION 64\SWTOR Materials Templates\ATRX SWTOR Shaders 4.2.blend"

    # A COUPLE OF GARMENTHUES TO PLAY WITH:
    garmenthue1_filepath = rf"{swtor_resources_folderpath}\art\dynamic\garmenthue\garmenthue_bh_h15_p.xml"
    garmenthue2_filepath = rf"{swtor_resources_folderpath}\art\dynamic\garmenthue\garmenthue_bh_h12_p.xml"
    # ------------------------------------


    # Get test object's material's name to determine which .mat file to use to "SWTORize" it.
    try:
        active_obj = bpy.context.active_object
        obj_mat = bpy.data.objects[active_obj.name].material_slots[0].material.name
    except:
        print("Object has no material")
        return

    swtor_mat_filepath = rf"{swtor_resources_folderpath}\art\shaders\materials\{obj_mat}.mat"
    if not os.path.isfile(swtor_mat_filepath):
        return




    # 1. Load SWTOR materials to current project    
    append_swtor_materials_from_template_blend_file(swtor_template_filepath, use_fake_user=True)
        

    # 2. Convert .mat file data to a dict of keys:values of the kind {input names: their values}. 
    mat_dict = swtor_mat_file_to_dict(swtor_mat_filepath)


    # 3. Read SWTOR shader type in that dict to decide which template material to use
    derived = mat_dict["Derived"]
    print(derived)
    swtor_template_material_name = f"SWTOR {derived} Material"


    # 4. Overwrite target Blender material with SWTOR template material nodes and links
    if swtor_template_material_name not in bpy.data.materials:
        return
    
    replace_material_node_tree(target_mat=obj_mat, source_mat=bpy.data.materials[swtor_template_material_name])


    # 5. Get palette data and overwrite the relevant .mat file data in the dict with it.
    garmenthue1_dict = swtor_garmenthue_file_to_dict(garmenthue1_filepath, palette_number=1)
    mat_dict.update(garmenthue1_dict)

    garmenthue2_dict = swtor_garmenthue_file_to_dict(garmenthue2_filepath, palette_number=2)
    mat_dict.update(garmenthue2_dict)


    # 6. Copy to its nodes the values stored in the dict derived from the .mat file
    apply_swtor_mat_dict_to_material(obj_mat, mat_dict, swtor_resources_folderpath=swtor_resources_folderpath)

 
pass