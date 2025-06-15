import bpy
import sys

# Get the STL path from the command line args
argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"
stl_paths = argv

# Select all objects
bpy.ops.object.select_all(action='SELECT')

# Delete selected objects
bpy.ops.object.delete()

# Clear the default scene
# bpy.ops.wm.read_factory_settings(use_empty=True)

# Ensure Object Mode
# if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
# bpy.ops.object.mode_set(mode='OBJECT')

for stl in stl_paths:
    bpy.ops.wm.stl_import(filepath=stl)
    print(f"render {stl}")
    obj = bpy.context.selected_objects[0]

    if 'red' in stl:
        # Create and assign red material
        mat = bpy.data.materials.new(name="Red_Material")
        mat.diffuse_color = (1, 0, 0, 1)  # RGBA - red
        mat.metallic = 0.5  # Add some metallic for better look
        mat.roughness = 0.3  # Slightly glossy

        # Assign material to object
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

# Set up the scene
# bpy.context.view_layer.objects.active = obj

# Center object
#bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
# obj.location = (0, 0, 0)

# Add camera
bpy.ops.object.camera_add(location=(0, 0, 5000))
cam = bpy.context.object
bpy.context.scene.camera = cam
#cam.data.lens = 50
cam.data.lens = 25
cam.data.clip_start = 1  # Near clipping distance (default is usually 0.1)
cam.data.clip_end = 10000.0

#direction = mathutils.Vector((0.0, 0.0, 0.0)) - cam.location

# Create rotation quaternion from direction
#rot_quat = direction.to_track_quat('-Z', 'Y')  # Camera looks along -Z by default

# Set the rotation of the camera
#cam.rotation_mode = 'QUATERNION'
#cam.rotation_quaternion = rot_quat

#cam.rotation_euler = (1.1, 0, 0.785)

#bpy.ops.view3d.camera_to_view_selected()  # Adjusts camera to see the object


bpy.ops.object.light_add(type='SUN', location=(50, -5, 5))
bpy.context.object.data.energy = 5  # Adjust brightness

# Add light
bpy.ops.object.light_add(type='AREA', location=(50, -5, 5))
bpy.context.object.data.energy = 1000

# Set render settings
# bpy.context.scene.render.engine = 'CYCLES'
# bpy.context.scene.cycles.device = 'CPU'
# bpy.context.scene.render.filepath = output_path
# bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.cycles.device = 'CPU'
bpy.context.scene.render.filepath = "output.png"
bpy.context.scene.render.image_settings.file_format = 'PNG'

# Set output resolution
bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 1024
bpy.context.scene.render.resolution_percentage = 100

# Render
bpy.ops.render.render(write_still=True)
