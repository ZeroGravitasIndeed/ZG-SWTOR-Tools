import bpy
import os
from pathlib import Path

class addonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # Preferences properties --------------------

    # resources folderpath
    swtor_resources_path: bpy.props.StringProperty(
        name = "SWTOR Resources",
        description = 'Path to the "resources" folder produced by a SWTOR assets extraction',
        subtype = "DIR_PATH",
        default = "/Volumes/RECURSOS/3D SWTOR/extracted_swtor/resources/",
#        default = "Choose or type the folder's path",
        maxlen = 1024
    )
    # Custom SWTOR shaders blendfile folderpath
    swtor_custom_shaders_blendfile_path: bpy.props.StringProperty(
        name = "Custom Shaders Template",
        description = "Path to a Blend file holding custom SWTOR shaders.\nPoints to a default one held in this Add-on's folder",
        subtype = "DIR_PATH",
        default = os.path.dirname(os.path.abspath(__file__)),
        maxlen = 1024
    )


    # UI ----------------------------------------
    
    def draw(self, context):
        layout = self.layout

        # resources folderpath preferences UI
        pref_box = layout.box()
        col=pref_box.column()
        col.scale_y = 0.7
        col.label(text="Path to the 'resources' folder in a SWTOR assets extraction")
        col.label(text="produced by the Slicers GUI app, EasyMYP, or any similar tool.")
        pref_box.prop(self, 'swtor_resources_path', expand=True)

        # Custom SWTOR shaders blendfile folderpath UI
        pref_box = layout.box()
        col=pref_box.column()
        col.scale_y = 0.7
        col.label(text="Path to .blend file holding custom SWTOR shaders")
        col.label(text="(defaults to .blend file inside this add-on)")
        pref_box.prop(self, 'swtor_custom_shaders_blendfile_path', expand=True)


# Registrations

def register():
    bpy.utils.register_class(addonPreferences)

def unregister():
    bpy.utils.unregister_class(addonPreferences)

if __name__ == "__main__":
    register()