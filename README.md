# ZeroGravitas' SWTOR Tools.

This Blender Add-on provides with a miscellanea of tools to use on **Star Wars: The Old Republic**'s game assets, including an Uber Materials Processor for static game models. It will grow in features as new ideas come up. Quality of code-wise, "this is not a place of honor": It Just (Hardly) Works™.

* [Installation.](#installation)
* [Materials Tools:](#swtor-materials-tools)
  * [Process Uber Materials.](#process-uber-materials)
  * [Custom SWTOR Shaders (beta):](#custom-swtor-shaders)
	  * [Add Custom SWTOR Shaders.](add-custom-swtor-shaders)
	  * [Convert to Custom SWTOR Shaders.](#convert-to-custom-swtor-shaders)
	  * [About the included Custom Shaders.](#about-the-included-custom-shaders)
	  * [Shaders' Extras.](#about-the-included-custom-shaders)
	  * [About the current Beta state.](#about-the-beta-state)
  * [Deduplicate Scene's Nodegroups.](#deduplicate-scenes-nodegroups)
  * [Set Backface Culling On/Off.](#set-backface-culling-onoff)
* [Objects Tools:](#swtor-objects-tools)
  * [Quickscaler.](#quickscaler)
  * [Merge Double Vertices.](#merge-double-vertices)
  * [Modifiers Tools.](#modifiers-tools)
* [Misc. Tools:](#swtor-misc-tools)
  * [Set all .dds to Raw/Packed.](#set-all-dds-to-rawpacked)
  * [Simplify Scene.](#simplify)
  * [Switch Skeleton between Pose and Rest Position.](#pose-position--rest-position)
  * [Camera to View.](#camera-to-view)


## Installation:

The installation of the Add-on in Blender follows the usual directions:

1. [**Download the Add-on's "zg_swtors_tool.zip" file from this link**](https://github.com/ZeroGravitasIndeed/zg_swtor_tools/raw/main/zg_swtor_tools.zip). Don't unZip it: it's used as such .zip.
2. In Blender, go to Edit menu > Preferences option > Add-ons tab > Install… button.
3. Select the Add-on in the file dialog box and click on the Install Add-on button.
4. The Add-on will appear in the Add-ons list with its checkbox un-ticked. Tick it to enable the Add-on.
5. Twirl the arrow preceding the check-box to reveal some information and, most importantly, **the Add-on's Preference settings**. Filling those is crucial for some of the tools to work correctly. They are:

	![](/images/010.png)
	* **Path of a "resources" folder**: some of the Add-on's features depend on looking for information and game assets inside a SWTOR assets extraction (typically produced by apps such as SWTOR Slicers or EasyMYP). In the case of a SWTOR Slicers extraction, the "resources" folder is inside the folder set as that app's Output Folder.
	
		Click on the folder icon to produce a file browser dialog window where to locate the "resources" folder, or type or copy its path inside the filepath field.
		
	* **Path to a Custom Shaders .blend file (if any)**: needed for a tool that allows us to replace the current .gr2 Add-on's modern SWTOR shaders with custom ones held in one Blender file, meant for us to experiment with and improve upon. See: [Custom SWTOR Shaders (beta)](#custom-swtor-shaders).

		Click on the file icon to produce a file browser dialog window where to select a such a Blender project file, or type or copy its path inside the filepath field.
        
The Add-on's tools will appear in the 3D Viewport's Sidebar ('n' key), in the "ZG SWTOR" tab.

![](/images/020.png)

The current tools are:

## SWTOR Materials Tools:

### Process Uber Materials.
**Requirements:**

* **Selecting a "resources" folder in this Add-on's preferences settings.**
* **An enabled SWTOR .gr2 Add-on, be it the Legacy or the modern current one.**
* **A selection of objects.**

Processes all the Uber-type materials detected in a selection of objects, locating their related texturemaps and linking them to a SWTOR Uber shader (modern or legacy, whichever are active). It processes any EmissiveOnly-type (glass) materials, too. It's particularly fast, as it (only) works with an asset extraction's "resources" folder.

Options:
* **Overwrite Uber Materials** (off by default): overwrites already present Uber and EmissiveOnly objects's materials, which allows for regenerating materials that might have lost texturemaps, converting Uber materials from Legacy to modern and viceversa, etc.
* **Collect Collider Objects** (on by default): adds all objects with an "Util_collision_hidden" material type or texturemap to a Collection named "Collider Objects".

**It needs the presence of an enabled [SWTOR importer Add-on ("io_scene_gr2")](https://github.com/SWTOR-Slicers/Granny2-Plug-In-Blender-2.8x)** in Blender, either the latest version or the [**Legacy**](https://github.com/SWTOR-Slicers/Granny2-Plug-In-Blender-2.8x/releases/tag/v.3.0) one, as it uses their Uber materials. In the case of the Legacy materials, importing any throwaway game object might be needed in order to generate the required material template if none are there.

This tool produces a simplistic glass material, Principled Shader-based, for EmissiveOnly-type materials such as those in spaceship windows, too.

As some sets of objects, such as spaceship interiors, can easily have a hundred materials or more, Blender might look like being unresponsive while processing them. Its progress can be followed in Blender's Console output, which will show the objects and materials being processed. Some error messages are prone to appear in the console, due to some unintended interactions with the modern version of the SWTOR Importer Add-on: those are expected, and don't affect the final result.

**If a selected object's material is shared with objects that haven't been selected** (and that's very typical in architectural objects like spaceships or buildings) **they'll show those processed materials, too, as if they would have been included in the selection.** This is their expected behavior. If needed, the way to avoid this would be to isolate the material we don't want to be processed by changing its name to one that doesn't exist in SWTOR's shaders folder.

### Custom SWTOR Shaders.
**THIS FEATURE IS IN A BETA STAGE. It shouldn't break anything but itself at its worst, though.**

**Requirements:**

* **Selecting a custom SWTOR shaders-holding .blend file in this Add-on's preferences settings.**
* **An enabled current modern SWTOR .gr2 Add-on, only needed at the moment this tool is being used (supporting the Legacy one is being condidered).**
* **A selection of objects.**
* **Blender 3.x** (Blender 2.8x-9.x support coming soon).

As convenient as our modern, *smart* SWTOR shaders for Blender are, especially for the novice (no dangling texturemap nodes, not having to manually adjust Material or texturemap images' settings, no risk of overwriting template materials), they are a little harder to customize than the previous, now Legacy ones. Both versions, being generated programmatically (the .gr2 Add-ons' code produce them on the fly while importing SWTOR object files), are harder to customize in a reusable manner, too: most modifications can be done once applied to objects, but those modifications have to be redone or copied (if feasible) between projects.

So, what we've done here is two things:

* We've "dumbed down" the modern shaders: no smarts, the texturemap nodes are back to dangling from the SWTOR Shader nodegroups (so allowing to interpose color correction nodes and stuff as usual).
* Instead of having an Add-on code generate the shaders on the fly, the shaders are stored in a .blend file, and the Add-on replaces the normal modern shaders with these dumb ones, placing the texturemaps' nodes alongside and linking them correctly.

What are the advantages to this?

* The most important one is that any modifications to our SWTOR shaders "library" of sorts can be tried and saved quickly just by playing in that Blender project. What's more: if we choose to have the Add-on replace the modern shaders in a given object with these dumb ones by **linking** to them instead of **appending** them, any improvement done to the shaders in the future will become available to older projects automatically. And if we need to do a per-project custom work, we can always convert a linked shader into a permanent one.
* Another one: **these customizable shaders can coexist with the modern, automated ones**. What's more: one can keep both in a given material and alternate linking them to the Material Output node for comparison sake (or put a Mix Shader in-between) or as a backup of sorts.
* We can even keep several SWTOR shader library files. As the linking data is stored in our Blender projects, we can keep several library files with different names and just set the one we want to use in a given moment in the Add-on's preference settings.
* Finally: this setup makes comparing notes extremely easy, just by sharing the library .blend files!

So, how does this work at a practical level? The available tools are:

#### Add Custom SWTOR Shaders:
It simply adds the customizable shaders to the currently open Blender project, which will become available through add > Group submenu (if one can see an add > SWTOR submenu, too, that one leads to the modern shaders instead). This operator is disabled if we happen to be editing the .blend file we selected as a library in the Add-on's preference settings, to avoid accidental duplications or loopbacks. Its options are:

* **Link instead of Append**: as explained, Append adds a fully modifiable copy of the shaders. Link, instead, inserts an instance of the shader stored in the library .blend project. One can adjust its settings but cannot modify the node tree inside the node group. Blender saves the location of the library .blend file, so, we could even use several different library files and don't break anything, even if care would be required (not moving those library files around or we will have to reconnect them, keeping a sensible naming scheme, the usual).

	This option is on by default except when editing a library file, in which case it wouldn't make sense to use linking.

#### Convert to Custom SWTOR Shaders:
**Doesn't require to previously use the Add Custom SWTOR Shaders**: it does that by itself.

It goes through all the materials in a selection of objects, detects the presence of the modern SWTOR shaders, and inserts the customizable versions with the same settings plus the needed texturemap nodes. Its options are:

* **Link instead of Append**: it works exactly like in the previous tool.
* **Preserve Original Shaders**: it doesn't delete the original modern shaders, simply pushing them aside inside the material, unlinked. If anything were to go wrong, sometime further on our experimentations, we can always unlink the customizable ones and relink the originals. This option is on by default.

	![](/images/040.png)

#### About the included custom shaders:
Alongside this Add-on's .zip file, there comes a sample .blend file holding just the customizable shaders. It can be renamed and stored wherever however and wherever we want, although we should decide a stable location for it and its derivatives, and moving it somewhere else after being applied in linked mode would lead to having to tell each Blender project using it where it was moved to.

The only rule for the [Convert to Custom SWTOR Shaders](#convert-to-custom-swtor-shaders) tool not to fail is to keep the names of the shaders intact. These are:

* SWTOR - Uber
* SWTOR - Creature
* SWTOR - Garment
* SWTOR - SkinB
* SWTOR - Eye
* SWTOR - HairC

All the auxiliary custom shaders inside their nodegroups have been renamed by adding a "SW Aux - " prefix (e.g.: "SW Aux - ManipulateHSL"). Such renaming helps us avoid conflicts with the original .gr2 Add-on's own shaders in the case of us wanting to modify them, too. Strictly speaking, there is no need to keep any specific convention: the important one regards only the main SWTOR shaders. Still, keeping their names different is safer.

Everything else inside these Blender project files can be altered any way we want. The most typical thing to do would be to populate it with objects representative of the shaders' usage, so that we can try stuff on them. Say, some ship interiors for the Uber shader; some animals for the Creature one; Player Characters of diverse species for SkinB, HairC and Eye, some armor sets for the Garment shader…

#### Custom Shader Extras:
Just as a first example of adding custom stuff to the shaders, the ones included in the .blend file come with a few extras already, not just in their inputs and settings but in their outputs, too:

![](/images/050.png)

Inputs:
* **Specular and Roughness strength**: they try to simulate the Principled BSDF shader's settings of the same name.
* **Emission Strength**: for turning dashboard and gear's glowy bits decidedly incandescent! 
* **Normal Strength**: raised above 1.0, it emphasizes objects's surface relief, if in a somewhat wonky way. It doesn't work terribly great on solid surface objects, but in characters it provides a very striking "**League of Legends: Arcane**" look (which in the series was achieved through hand-painted textures), so, I suspect it's going to be a favorite.
* **Transparency**: this is a global material transparency factor, different to its opacity map. Its main mission is to allow us to invisibilize a part of an object, such as the feet of a Player Character that has been turned into a single mesh and happens to be protruding through its boots.
* **Complexion Gamma**: to contrast a character's complexion without the need to play with its Color Space to sRGB or interpose some. color correction node.
* **Scar Gamma, Color and Normal Strength**, to adjust scars and age maps just the way we want them.
* **Direction Map**: it's been added to the SkinB shader in a provisional manner (I'm not sure if it's correctly done).

Not everything works well: the ones in the Eye Shader hardly show any effect and need rethinking (also, we need Sith Glowy Eyes. Coming soon :D ). DirectionMaps seem to get extremely wonky in some objects when rendering through Cycles.

Outputs:
* **Diffuse Color AUX**: the diffuse color in RGB, with the PaletteMap re-hue already applied!
* **Specular Color AUX**: the specular color on black, in RGB. Typically, one would mix it with the diffuse in Add mode.
* **Emission Strength AUX**: it's the emissive channel from the _n RotationMap.
* **Alpha AUX**: it's the opacity channel from the _n RotationMap.
* **Normal AUX**: this is the Normal information, processed to be directly usable in any Blender node already.

These channels are mostly there for experimenting with adding our own node trees for things like, say, trying comic book or anime-like Non Photorealistic Rendering (NPR), or maybe to produce baking information.

* **DirectionMap Vector**: as DirectionMaps (a kind of anisotropic glossmap used in hairs, some species' furs and skins, and other cases) require pre-calculated data that is internally generated in the automatic modern shaders, this is a bit of a cludgey way to produce that information and link it to the DirectionMaps' vector input. The Converter tool puts those links by itself.

#### About the beta state:
The Add-on, as it is now, needs work in things like failing gracefully to errors, providing support for older Blender and .gr2 add-on versions, refining the existing extra features (for example, per dye area-Spec/Rough/Emissive/Normal strength settings), and most probably rearranging the shaders' node trees into something a bit more wieldable.

That said, we should point out that these shaders, as such, are meant to be further customized and evolved by everybody based on their particular interests. For example, the current implementation of glossiness is meant to replicate SWTOR's own, but someone might prefer to discard that and do their own Blender specular node or Principled BSDF node-based one, or substitute its Flush Tone-based pseudo-subsurface scattering effect with Blender's own, add adjustable noise-based skin pores, etc. The sky is the limit.



### Deduplicate Scene's Nodegroups.
**Requirements: none.**

Consolidates all duplicates of a node in the scene ("node.001", "node.002", etc.) so that they become instances of the original instead of independent ones. The copies are marked as "zero users" so that, after saving the project, the next time it is opened they will be discarded (that's how Blender deals with such things).
* It acts on all the nodes of a scene, and doesn't require a selection of objects.

### Set Backface Culling On/Off.
**Requirements: none.**

It sets all the materials in the selected objects' Backface Culling setting to on or off (the setting is fully reversible). Many SWTOR objects, especially floors, walls, and ceilings of spaceships and some buildings, are single-sided by nature, which ought to make their sides facing away from the camera invisible. Blender, by default, renders single-sided objects as double-sided unless Backface Culling is enabled.
* It **doesn't** depend on the presence of a .gr2 importer Add-on: this setting works in any kind of Blender material, no matter if SWTOR-based or any other kind.
* **The setting only acts through the Eevee renderer** (either while in Viewport Shading mode or as a final renderer). Cycles enforces double-sidedness, despite ticking the Material Properties Inspector's Backface Culling checkbox. If the intention is to do the final render through Cycles, a dual 3D Viewer setup, one in Material Preview mode (Eevee) and the other displaying the Render Preview might be the best way to finetune lighting and texturing. 

The usefulness of this tool becomes apparent when having to deal with interior scenes such as spaceship rooms, where we have to place models (characters, furniture, props.) while having the walls and ceilings occluding our view. There are cumbersome solutions to that, such as hiding polygons, playing with the camera clipping settings, or using a booleaning object to "eat" walls or ceilings away. This is simpler and faster. Also, it doesn't affect the rendering when placing the camera inside, as there the one-sided objects are facing the camera in the intended manner.

![](/images/030.jpg)

When assembling multi-object locations, it's typical that a same material is shared between several objects. That can lead to unselected objects showing the effects of this tool as if they would have been included in the selection. This is an expected behavior.

**Warning: if a selected object's material is shared with objects that haven't been selected, the effect will be visible in those objects, too.** This is normal, and, for the intended use, it doesn't seem to be anything beyond a nuisance. The only way to avoid this would be to isolate the material we don't want to be affected by changing its name.

## SWTOR Objects Tools:

### Quickscaler.
**Requirements: a selection of objects.**

Scales all selected objects up or down by a factor, preserving their relative distances if their origins don't match. The idea behind the tool is to be able to quickly upscale all objects of a character or a scene to real life-like sizes (1 Blender unit = 1 m. or equivalent), as Blender requires such sizes to successfully calculate things like automatic weightmaps, physics, etc.

**Cameras, lights and armatures are correctly scaled, and it acts only on non-parented and parent objects**, to avoid double-scaling children objects (typically, objects parented to a skeleton). **Objects set as insensitive to selection operations in the Outliner aren't affected by this tool**.

Any number between 1 and 100 can be manually entered. Recommended factors are:
* 10, for simplicity. It results in rather superheroically-sized characters.
* Around 7-8 for more realistic human heights.

### Merge Double Vertices.
**Requirements: a selection of objects.**

Merges "duplicate" vertices (applies a "Merge By Distance" with a tolerance of 0.000001 m.), which usually solves many issues when fusing body parts or applying Subdivision or Multiresolution Modifiers.
* Requires a selection of one or several game objects.
* When selecting multiple objects, the tool acts on each of them separately so as not to merge vertices of different objects by accident.
* To correct any possible normals problems derived from the operation, it performs a face area normals' averaging operation, too.
* Also, it sets each object's Auto Smooth to On (it's typically on by default, but, just in case…).

### Modifiers Tools.
**Requirements: a selection of objects.**

They add to all selected objects Modifiers like Subdivision or Multires (for hiding SWTOR's models' low poly nature) and Displace and Solidify (to facilitate gear-over-full body workflows), with sensible settings as an easy starting point. There is a Modifiers removal button that only affects those Modifier types, preserving any other, such as the Armature modifier that results from parenting a skeleton. Also, there are buttons for moving such Armature modifiers to the top or the bottom of the Modifier Stack, for both usefulness and experimentation.

* Requires a selection of one or several game objects.
* The Armature Modifier re-ordering buttons don't work by selecting Armature objects yet: only by selecting objects with Armature Modifiers. The former functionality will be considered for an update.

## SWTOR Misc. Tools:
For now these are simply a few already existing Blender tools that are a little too buried inside their panels and would be nice to have more at hand.

### Set all .dds to Raw/Packed.
**Requirements: none.**

It sets all images in the blender project whose names end with the .dds extension to Color Space: Raw and Alpha: Channel Packed, which are the settings our SWTOR shaders expect in order to work properly.
* It acts on all the images of a scene, and doesn't require a selection of objects.
(It's typical to set some texturemap images, such as complexion maps, to sRGB because that makes them appear a little bit darker. Such a thing should be no longer necessary by using the new customizable shaders' extra Complexion Gamma settings).

### Simplify.
**Requirements: a selection of objects.**

Usually in the Properties Editor > Render Properties >Simplify section, it lets us temporarily switch a few common and somewhat costly options, such as Subdivision Modifiers' levels, number of particles, etc., to lower values, at the scene level. For example, we can disable subdivision while animating a character, which will make its meshes react to our posing far faster.

### Pose Position / Rest Position.
**Requirements: a selection of objects including an armature.**

It shows the Pose Position and Rest Position buttons that appear at the Properties Editor > Object Properties, Skeleton section when a skeleton is selected, letting us quickly alternate between those two states. It only acts on the Active armature (the Active Object that happens to be an armature at the moment) instead of all selected armatures. Having it act on all of them is in the works.

### Camera to View.
**Requirements: none.**

Same checkbox as View Tab > View Lock section > Lock Camera to View, for easily switching from framing the scene from the camera POV to keeping the camera unaffected while navigating the viewport.
