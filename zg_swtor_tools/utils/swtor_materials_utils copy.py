import bpy
import os
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime



# ---- SWTOR TEMPLATE MATERIALS' ID READING -----------------------

# Simple reader of a SWTOR templates file's materials and node groups' ID.
def read_swtor_template_mats_id_from_file(blend_filepath):
    """
    Determines the ID string of a SWTOR template material
    from a .blend file at the given filepath.
    Meant as a simple way to get the ID string
    of the template materials used in the project
    if for some reason the data isn't available.

    Args:
        blend_filepath (str): Path to the .blend file.
        
    Returns:
        selected_swtor_template_mats_id (str): string that the templates use in their names
                                              between the "TOR-" prefix and the shader name.
                                              Returns None if no SWTOR material is found.
    """    
    selected_swtor_template_mats_id = None
    with bpy.data.libraries.load(str(blend_filepath), link=False) as (data_from, _ ):
        for mat in data_from.materials:
            mat_name = str(mat)
            if not mat_name.startswith("TOR-"):
                continue
            
            # Get the ID string between "TOR-" and the shader's name
            selected_swtor_template_mats_id = mat_name.split("-")[1]
            break
    return selected_swtor_template_mats_id


# Simple reader of a SWTOR templates file's TOR materials.
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





# ---- SWTOR TEMPLATE MATERIALS' CHANGES CHECKING -----------------
# Checks if SWTOR template materials with same names are different
# (calculates hashes out of a SWTOR templates file's materials and
# compares them to the working project's materials with same names). 
def compare_swtor_mat_templates_in_file_with_resident_ones(blend_filepath):
    """
    Reports differences between a SWTOR materials templates in a .blend file and
    those inside the working project, so that other tools can decide whether to
    re-append them or not.
    
    (It produces signatures of "TOR"-prefixed materials and node groups
    as a comparison criteria) 

    Args:
        blend_filepath (str): Blender project file (.blend) path.

    Raises:
        FileNotFoundError: _description_

    Returns:
        differences (dict): contaims two pairs of key:values:
                            {materials:list of materials with differences}
                            {node_groups:list of node groups with differences}
                            or
                            None if there are no differences at all.
    """    
    differences = {"materials": [], "node_groups": []}

    # Pre-check: file exists
    if not os.path.exists(blend_filepath):
        raise FileNotFoundError(f"File not found: {blend_filepath}")

    # Load external materials and node groups
    with bpy.data.libraries.load(str(blend_filepath), link=False) as (data_from, data_to):
        ext_materials = [name for name in data_from.materials if name.startswith("TOR") and name in bpy.data.materials]
        ext_node_groups = [name for name in data_from.node_groups if name.startswith("TOR") and name in bpy.data.node_groups]

        data_to.materials = ext_materials
        data_to.node_groups = ext_node_groups

    # Compare materials
    for mat in ext_materials:
        mat_name = mat.name
        local = bpy.data.materials.get(mat_name)
        external = bpy.data.materials.get(mat_name)
        if not local or not external or not compare_materials(local, external):
            differences["materials"].append(mat_name)
            if external:
                bpy.data.materials.remove(external)

    # Compare node groups
    for ng in ext_node_groups:
        group_name = ng.name
        local = bpy.data.node_groups.get(group_name)
        external = bpy.data.node_groups.get(group_name)
        if not local or not external or not compare_node_groups(local, external):
            differences["node_groups"].append(group_name)
            if external:
                bpy.data.node_groups.remove(external)
    
    # Return None if there are no differences at all, for simplicity's sake
    if not differences["materials"] and not differences["node_groups"]:
        return None

    return differences

    # Example usage
    # external_blend_path = "/path/to/your/file.blend"
    # diffs = compare_swtor_mat_templates_in_file_with_resident_ones(external_blend_path)

    # if diffs["materials"] or diffs["node_groups"]:
    #     print("Differences found:")
    #     for mat in diffs["materials"]:
    #         print(f" - Material differs: {mat}")
    #     for group in diffs["node_groups"]:
    #         print(f" - Node Group differs: {group}")
    # else:
    #     print("All matched materials and node groups are identical.")

# Auxilliary functions:

def get_node_signature(node):
    """Get a signature for a node based on its type and input values."""
    inputs = []
    for socket in node.inputs:
        try:
            value = socket.default_value
            if hasattr(value, "__len__") and not isinstance(value, str):
                value = tuple(value)
        except:
            value = None
        inputs.append((socket.name, value))
    return (node.bl_idname, node.label, tuple(inputs), node.location)

def get_links_signature(tree):
    """Return a list of link signatures: from node name/output to node name/input."""
    return sorted([
        (link.from_node.name, link.from_socket.name, link.to_node.name, link.to_socket.name)
        for link in tree.links
    ])

def compare_node_trees(tree_a, tree_b):
    if len(tree_a.nodes) != len(tree_b.nodes):
        return False
    if len(tree_a.links) != len(tree_b.links):
        return False

    nodes_a = sorted([get_node_signature(n) for n in tree_a.nodes], key=lambda x: x[0])
    nodes_b = sorted([get_node_signature(n) for n in tree_b.nodes], key=lambda x: x[0])

    if nodes_a != nodes_b:
        return False

    if get_links_signature(tree_a) != get_links_signature(tree_b):
        return False

    return True

def compare_materials(mat_a, mat_b):
    if mat_a.use_nodes != mat_b.use_nodes:
        return False
    if mat_a.use_nodes:
        return compare_node_trees(mat_a.node_tree, mat_b.node_tree)
    return True  # Both non-node materials

def compare_node_groups(group_a, group_b):
    return compare_node_trees(group_a, group_b)




# ---- SWTOR TEMPLATE MATERIALS LOADER AND DEDUPLICATORS ----------

def append_materials_from_template_blend_file(blend_filepath, update_if_full_match=False, use_fake_user=True):
    """
    (Blender-generic)
     
    Loads all SWTOR materials in the .blend file at that filepath
    (those whose names start with "TOR")

    * Replaces pre-existing loaded ones with the same names.
    * Deduplicates materials and node groups whose base names match
      the loaded materials and node groups' ones instead of just all
      in the Blender project.
    * Can add fake users to the loaded materials if wished so.

    Args:
        blend_path (str): Path to the .blend file.
        update_if_full_match (bool):  if True, updates templates with same ID with the ones in file.
                                      If False, it preserves the existing ones.
        use_fake_user (bool): defaults to False.
        
    Returns:
        selected_swtor_template_mats_id (str):  string that the templates use in their names
                                                between the "TOR-" prefix and the shader name.
                                                e.g.: the "Basic" in "TOR-Basic-Uber". It helps
                                                to know what templates are in use and select
                                                them in lists.

    """

    
    if not os.path.isfile(blend_filepath):
        raise FileNotFoundError(f"Blend file not found: {blend_filepath}")

    
    mat_names_to_import = read_swtor_template_mats_names_in_file(blend_filepath)
    if not mat_names_to_import:  # This shouldn't be possible to happen
        return None
    
        
    selected_swtor_template_mats_id = mat_names_to_import[0].split("-")[1]

    # Check if the materials already exist in the working project and act in consequence
    full_match_exists = len(mat_names_to_import) == len([mat for mat in bpy.data.materials if mat.name.startswith(f"TOR-{selected_swtor_template_mats_id}-")])
    
    if full_match_exists:
        if update_if_full_match:
            return selected_swtor_template_mats_id
        else:
            # Check that there are differences between the existing materials
            # and the ones in the template.
            
            if not compare_swtor_mat_templates_in_file_with_resident_ones(blend_filepath):
                # If there are differences, preserve materials applied to objects and then
                # delete the existing templates before appending updated ones.
                # Steps:
                #
                # 1- Suffix all existing TOR-ID-xxx and TOR_Aux-ID-xxx node groups with a .timedate-"old",
                #    to preserve the ones in use by objects' materials (named differently to the templates),
                #    and set them to no Fake User so that they are garbage-collectable.
                # 2- Delete all existing TOR-ID-xxx material templates and their associated NGs (CHECK IF LATTER IS NEEDED).
                # 3. Append the TOR material templates from the templates file.

                 
                # 1- Suffix current NGs with the same ID. to preserve materials applied to objects
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                print(timestamp)
                ngs_to_timestamp = [ng for ng in bpy.data.node_groups if ng.name.startswith(f"TOR-{selected_swtor_template_mats_id}-") or ng.name.startswith(f"TOR_Aux-{selected_swtor_template_mats_id}-")]
                for ng in ngs_to_timestamp:
                    # Timestamp in a manner that evades typical deduplicators
                    # (adding some text to the suffix is enough).
                    bpy.data.node_groups[ng].name = f"{bpy.data.node_groups[ng].name}.{timestamp}-old"
                    # And make them garbage-collectable
                    bpy.data.node_groups[ng].use_fake_user = False

                    
                # 2- Delete template materials with the same ID.
                delete_swtor_mat_templates_by_id(selected_swtor_template_mats_id)
                
                # 3- Append template materials from the templates file:
                
                swtor_mats_names = []
                # bpy's current tomfoolery of a system for appending stuff:
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
                    #
                    # The str() in the blend_filepath is just in case it comes as a Path object.

                    # Build list of materials to append.
                    swtor_mats = []
                    for mat in data_from.materials:
                        if not str(mat).startswith("TOR-"):
                            continue
                        swtor_mats.append(mat)
                        swtor_mats_names.append(str(mat))

                    # actual loading (Materials suffice: any node groups involved come along)
                    data_to.materials = swtor_mats
                
                # Set fake user
                for mat_name in swtor_mats_names:
                    bpy.data.materials[mat_name].use_fake_user = True
                        
    else:
        delete_swtor_mat_templates_by_id(selected_swtor_template_mats_id)

        swtor_mats_names = []
        with bpy.data.libraries.load(str(blend_filepath), link=False) as (data_from, data_to):
            swtor_mats = []
            for mat in data_from.materials:
                if not str(mat).startswith("TOR-"):
                    continue
                swtor_mats.append(mat)
                swtor_mats_names.append(str(mat))


            data_to.materials = swtor_mats
            
        for mat_name in swtor_mats_names:
            bpy.data.materials[mat_name].use_fake_user = True
    
    return selected_swtor_template_mats_id
    
    

def append_materials_from_template_blend_file_OLD(blend_filepath, use_fake_user=True):
    """
    (Blender-generic)
     
    Loads all SWTOR materials in the .blend file at that filepath
    (those whose names start with "TOR")

    * Replaces pre-existing loaded ones with the same names.
    * Deduplicates materials and node groups whose base names match
      the loaded materials and node groups' ones instead of just all
      in the Blender project.
    * Can add fake users to the loaded materials if wished so.

    Args:
        blend_path (str): Path to the .blend file.
        mat_names_start_with (re.Pattern, optional):    Regex for filtering in what materials are loaded.
                                                        If None, no filtering is done.
        use_fake_user (bool): defaults to False.
        
    Returns:
        selected_swtor_template_mats_id (str):  string that the templates use in their names
                                                between the "TOR-" prefix and the shader name.
                                                e.g.: the "Basic" in "TOR-Basic-Uber". It helps
                                                to know what templates are in use and select
                                                them in lists.

    """

    
    if not os.path.isfile(blend_filepath):
        raise FileNotFoundError(f"Blend file not found: {blend_filepath}")


    # Declare variable for returning ID string that will go between the materials
    # and node group names' fixed bits (e.g.: the "Basic" in "SWTOR-Basic-Uber"):
    selected_swtor_template_mats_id = None


    # Check if appending the templates is really necessary:
    
    # - Read the templates file's materials and node groups names' common ID.
    selected_swtor_template_mats_id = read_swtor_template_mats_id_from_file(blend_filepath)
    
    # - If there is an Uber node group template with the same ID ("TOR-<ID>-Uber"),
    #   in the current project, do a full comparison between the file and the open
    #   project's templates, else there is no need to append a templates set
    #   (checking for node groups should be marginally faster in cases such as
    #   assembled areas where there can be hundreds of materials)
    protect_previous_swtor_node_groups = False
    if f"TOR-{selected_swtor_template_mats_id}-Uber" in bpy.data.node_groups:
        protect_previous_swtor_node_groups = compare_swtor_mat_templates_in_file_with_resident_ones(blend_filepath) is not None
        if not protect_previous_swtor_node_groups:
            return selected_swtor_template_mats_id
        else:
            protect_previous_swtor_node_groups = True
            delete_swtor_mat_templates_by_id(selected_swtor_template_mats_id)
        

    swtor_mats = []
    swtor_mats_to_dedupe = []
    swtor_node_groups_to_dedupe = []

    # bpy's current tomfoolery of a system for appending stuff:
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
        #
        # The str() in the blend_filepath is just in case it comes as a Path object.

        if protect_previous_swtor_node_groups:
            # Rename all node groups whose names match the incoming templates' ones
            # to avoid destroying them before the templates in the receiving project
            # are replaced. Also, revoke their use of Fake Users so that they are
            # garbage-collected from then on.

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            print(timestamp)
            for ng in data_from.node_groups:
                if not str(ng).startswith("TOR-"):
                    continue
                if str(ng) in bpy.data.node_groups:
                    bpy.data.node_groups[ng].use_fake_user = False
                    # Rename in a manner that is compatible with typical deduplicators
                    # (numerical suffix separated by a period)
                    temp_ng_name = f"OLD_{bpy.data.node_groups[ng].name}.{timestamp}"
                    bpy.data.node_groups[ng].name = temp_ng_name


        # Start working on the template materials.
        for mat in data_from.materials:
            if not str(mat).startswith("TOR-"):
                continue
            swtor_mats.append(mat)

            # Build a list of materials' names to feed a deduplicator afterwards
            # (to be of use as simple names to be used outside this "with" context,
            # they need to have been copied to other variable).
            # swtor_mats_to_dedupe.append(str(mat))  # Is str necessary?
            swtor_mats_to_dedupe.append(mat)
        if not swtor_mats:
            return selected_swtor_template_mats_id
        
        # actual loading (Materials suffice: any node groups involved come along)
        data_to.materials = swtor_mats
        
        # Build list to feed the node groups deduplicator
        swtor_node_groups_to_dedupe = [str(ng) for ng in data_from.node_groups]

    
    # Determine selected_swtor_template_mats_id
    # (analyze the name of the first material in the list):
    selected_swtor_template_mats_id = swtor_mats[0].name.split("-")[1]


    # Instead of preemptively deleting any materials with the same names,
    # we dedupe so as not to destroy any materials being assigned to any
    # object: they'll get auto-replaced instead.
    #
    # (The dedupe pass needs to be done outside the "with" because,
    # if it happens inside, the materials are retained by the
    # data.libraries.load() "with" context and don't get deleted)
    deduplicate_materials(base_names= swtor_mats_to_dedupe)
    deduplicate_node_groups(base_names= swtor_node_groups_to_dedupe)
    
    # Set fake user if desired
    if use_fake_user:
        for mat_name in swtor_mats_to_dedupe:
            bpy.data.materials[mat_name].use_fake_user = True
    
    
    return selected_swtor_template_mats_id

# Auxilliary functions:

def delete_swtor_mat_templates_by_id(templates_id):
    """
    Deletes all materials whose names start with f"TOR-{templates_id}-".
    
    Args:
        templates_id (string):  string that the templates use in their names
                                between the "TOR-" prefix and the shader name.
                                e.g.: the "Basic" in "TOR-Basic-Uber".
    """    
    mats_to_delete = [mat for mat in bpy.data.materials if mat.name.startswith(f"TOR-{templates_id}-")]
    
    for mat in mats_to_delete:
        bpy.data.materials.remove(mat, do_unlink=True)

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




# ---- BLENDER MATERIAL NODETREE REPLACER ------------------------------

def replace_material_node_tree(target_mat, source_mat, duplicate_groups=False):
    """
   (Blender-generic)
    
    Rewrites a Blender material's node tree and material settings
    with those of another material.
    
    Args:
        target_mat (str or bpy.types.Material): material to overwrite.
        source_mat (str or bpy.types.Material): material to be the source of data.
        duplicate_groups (bool, optional):  make any node groups independent duplicates.
                                            Defaults to False.
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
        "roughness",
        "specular_intensity",
        "metallic",
    ]


    # Copy basic properties (tolerates trying deprecated ones)
    for prop in basic_mat_props_to_copy:
        if hasattr(source_mat, prop) and hasattr(target_mat, prop):
            try:
                setattr(target_mat, prop, getattr(source_mat, prop))
            except Exception:
                pass

    # -- Viewport Display Settings --
    # try:
    #     target_mat.diffuse_color = source_mat.diffuse_color
    #     target_mat.specular_color = source_mat.specular_color
    #     target_mat.roughness = source_mat.roughness
    # except Exception:
    #     pass

    # if hasattr(target_mat, 'preview') and source_mat.preview:
    #     target_mat.preview = source_mat.preview

    # # -- Line Art Settings (if available) --
    # if hasattr(target_mat, 'lineart'):
    #     try:
    #         target_mat.lineart.use_material_mask = source_mat.lineart.use_material_mask
    #         target_mat.lineart.material_mask_bits = source_mat.lineart.material_mask_bits
    #     except Exception:
    #         pass


    # -- Clear existing nodes and links --
    tgt_tree = target_mat.node_tree
    src_tree = source_mat.node_tree
    tgt_tree.nodes.clear()
    tgt_tree.links.clear()

    node_map = {}


    # -- Copy Nodes --
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
            new_node.node_tree = node.node_tree.copy() if duplicate_groups else node.node_tree

        if node.type == 'FRAME':
            # We are having problems with frames keeping their visible location: although
            # the data is correctly copied, they appear as if their origin was changed
            # from center to corner. TO INVESTIGATE. 
            pass

        node_map[node] = new_node


    # -- Copy Links --
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


    # -- Copy Custom Properties (User-defined only) --
    # DOES THIS MAKE COPYING BASIC MAT PROPS REDUNDANT?
    copy_material_non_rna_properties(target_mat, source_mat)



    print(f"Material '{target_mat.name}' was successfully overwritten with data from '{source_mat.name}'.")

def copy_material_non_rna_properties(target_mat, source_mat):
    """
   (Blender-generic)
    
    Copies a material's properties's values to a target material.
    Skips all dunder (names surrounded by double underlines) ones.
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
                element_value = bool(element_value)
                
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
                mat_dict[element_semantic] = bool(element_value)

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




# ---- UNUSED!!!! TO THINK ABOUT -------------------------------------

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
                if exclude_linked and input.is_linked:
                    continue
                else:
                    nodegroups_values[input.name] = input
                
        if node.type == "TEX_IMAGE":
            texturemap_nodes_images[node.name] = node.image
    
    return nodegroups_values, texturemap_nodes_images


# UNUSED!!!! TO THINK ABOUT:
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
    append_materials_from_template_blend_file(swtor_template_filepath, use_fake_user=True)
        

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