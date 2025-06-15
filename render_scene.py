import bpy
import sys


# Clear the default scene
bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.wm.stl_import(filepath="/home/adam/dev/2025/cadcompliance/shape.stl")


# Get the STL path from the command line args
argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"
stl_path = argv[0]
output_path = argv[1]

# Set up the scene
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

# Center object
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
obj.location = (0, 0, 0)

# Add camera
bpy.ops.object.camera_add(location=(3, -30, 2))
cam = bpy.context.object
bpy.context.scene.camera = cam
cam.data.lens = 50
cam.rotation_euler = (1.1, 0, 0.785)

# Add light
bpy.ops.object.light_add(type='AREA', location=(5, -5, 5))
bpy.context.object.data.energy = 1000

# Set render settings
# bpy.context.scene.render.engine = 'CYCLES'
# bpy.context.scene.cycles.device = 'CPU'
# bpy.context.scene.render.filepath = output_path
# bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.cycles.device = 'CPU'
bpy.context.scene.render.filepath = output_path
bpy.context.scene.render.image_settings.file_format = 'PNG'

# Set output resolution
bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 1024
bpy.context.scene.render.resolution_percentage = 100

# Render
bpy.ops.render.render(write_still=True)
