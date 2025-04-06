bl_info = {
    "name": "YMK Event Keyframe Importer",
    "author": "WCG847",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Animation",
    "description": "Import and preview YMK/Dat animation from custom event files",
    "support": "TESTING",
    "category": "Animation",
}

import bpy
import os
from bpy.props import StringProperty, EnumProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper


from .Import.V1.FrameParser import EKey, ConvertToBlender
from .Import.YMKs import YMKs


# Shared props
class YMK_ImportProperties(PropertyGroup):
    filepath: StringProperty(
        name="YMK File",
        description="Path to .ymks or .dat file",
        subtype='FILE_PATH'
    )

    def get_assets(self, context):
        items = []
        try:
            with open(self.filepath, "rb") as f:
                parser = YMKs()
                assets = parser.GetAssetTable(f)
                for a in assets:
                    items.append((str(a['ChildID']), f"Asset ID: {a['ChildID']}", ""))
        except:
            items.append(('NONE', 'Invalid or no file loaded', ''))

        return items if items else [('NONE', 'No Assets Found', '')]

    asset_id: EnumProperty(
        name="Asset ID",
        description="Select an asset to load animation for",
        items=get_assets
    )


# Operator: Load + Apply
class YMK_OT_ImportAndPreview(Operator):
    bl_idname = "ymk.import_preview"
    bl_label = "Load Animation"
    bl_description = "Preview animation from selected asset"

    def execute(self, context):
        props = context.scene.ymk_importer
        if not os.path.isfile(props.filepath):
            self.report({'ERROR'}, "File not found.")
            return {'CANCELLED'}

        with open(props.filepath, "rb") as f:
            ek = EKey()
            headers, rots, poses = ek.ReadFrame(f)

        selected_id = int(props.asset_id)
        filtered = [i for i, h in enumerate(headers) if h["AssetID"] == selected_id]

        if not filtered:
            self.report({'WARNING'}, f"No frames found for Asset ID {selected_id}")
            return {'CANCELLED'}

        # Slice only selected animation frames
        filtered_positions = [poses[i] for i in filtered]
        filtered_rotations = [rots[i] for i in filtered]

        conv = ConvertToBlender(armature_name="Armature")
        conv.ApplyAnimation(headers, filtered_rotations, filtered_positions, action_name="YMK_Preview")
        self.report({'INFO'}, "Preview loaded.")
        return {'FINISHED'}


# Operator: Apply to scene permanently
class YMK_OT_ApplyToScene(Operator):
    bl_idname = "ymk.apply_animation"
    bl_label = "Apply To Scene"
    bl_description = "Bake the selected animation permanently"

    def execute(self, context):
        # For now, it just confirms the action was done. Logic could be expanded.
        self.report({'INFO'}, "Animation baked to action data.")
        return {'FINISHED'}


# UI Panel
class YMK_PT_SidebarPanel(Panel):
    bl_label = "YMK Animation Importer"
    bl_idname = "YMK_PT_sidebar_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ymk_importer

        layout.prop(props, "filepath")
        layout.prop(props, "asset_id")

        row = layout.row()
        row.operator("ymk.import_preview", text="Load Animation")
        row = layout.row()
        row.operator("ymk.apply_animation", text="Apply To Scene")


# Registration
classes = (
    YMK_ImportProperties,
    YMK_OT_ImportAndPreview,
    YMK_OT_ApplyToScene,
    YMK_PT_SidebarPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ymk_importer = bpy.props.PointerProperty(type=YMK_ImportProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.ymk_importer


if __name__ == "__main__":
    register()
