import sys
argv = sys.argv
argv = argv[argv.index("--") + 1:] 

import bpy

import os
from pathlib import Path
import json
from decimal import Decimal
import math
import mathutils
import json

print(argv)
config_path = Path(argv[0])

with open(config_path, 'r') as f:
    config = json.load(f)

# отчистка сцены
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

override = bpy.context.copy()
bpy.ops.outliner.orphans_purge() 

# вводные данные
path_to_gltfs = Path(config['path_to_gltfs'])
path_to_rtc_centers = Path(config['path_to_rtc_centers'])

path_to_render_result = Path(config['path_to_render_result'])
path_to_corners = Path(config['path_to_corners'])

surface_lon, surface_lat = Decimal(config['surface_lat']), Decimal(config['surface_lon'])
x_rotation, y_rotation, z_rotation = Decimal(0), Decimal(90) - surface_lon, surface_lat

horizontal_resolution = config['horizontal_resolution']

camera_z_margin = config['camera_z_margin']

with open(path_to_rtc_centers, 'r') as f:
    rtc_centers = json.load(f)


max_count = None
if 'max_count' in config:
    max_count = config['max_count']

# импортировать и расположить тайлы
tile_origin = None
tiles = []

for i, file in enumerate(os.listdir(path_to_gltfs)):   
    if (max_count is not None and i > max_count):
        break
    
    if not file.endswith('.gltf'):
        continue

    file_path = Path(file)
    
    bpy.ops.import_scene.gltf(filepath=str(path_to_gltfs / file_path))
    
    rtc_centers[file][0] = Decimal(rtc_centers[file][0])
    rtc_centers[file][1] = Decimal(rtc_centers[file][1])
    rtc_centers[file][2] = Decimal(rtc_centers[file][2])
    
    if tile_origin is None:
        tile_origin = rtc_centers[file]
    
    tile = bpy.data.objects['Mesh_0']
    tile.name = str(i)
    tile.data.name = str(i)
    
    tile.location = (rtc_centers[file][0] - tile_origin[0], rtc_centers[file][1] - tile_origin[1], rtc_centers[file][2] - tile_origin[2])
    
    tiles.append(tile)

# повернуть тайлы к плоскости
jioned_name = tiles[-1].name

bpy.ops.object.select_all(action='DESELECT')
for tile in tiles:
    tile.select_set(True)
bpy.ops.object.join()

mesh_obj = bpy.data.objects[jioned_name]

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')

bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
axis_obj = bpy.data.objects['Empty']
axis_obj.rotation_euler = math.radians(x_rotation), math.radians(y_rotation), math.radians(z_rotation)

bpy.ops.object.select_all(action='DESELECT')

mesh_obj.select_set(True)
bpy.context.view_layer.objects.active = axis_obj
bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

axis_obj.rotation_euler = 0, 0, 0

bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
mesh_obj.location = 0, 0, 0
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.data.objects.remove(axis_obj)

#создать и настроить кмеру
bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
camera_obj = bpy.data.objects['Camera']
camera_obj.data.type = 'ORTHO'

camera_obj.data.clip_start = 1
camera_obj.data.clip_end = 100000

x_bb_min, y_bb_min, z_bb_min = math.inf, math.inf, math.inf
x_bb_max, y_bb_max, z_bb_max = -math.inf, -math.inf, -math.inf

for corner in mesh_obj.bound_box:
    for i, co in enumerate(corner):
        if i == 0:
            x_bb_min = min(co, x_bb_min)
            x_bb_max = max(co, x_bb_max)
        if i == 1:
            y_bb_min = min(co, y_bb_min)
            y_bb_max = max(co, y_bb_max)
        if i == 2:
            z_bb_min = min(co, z_bb_min)
            z_bb_max = max(co, z_bb_max)

camera_obj.location = mesh_obj.matrix_world @ mathutils.Vector(((x_bb_min + x_bb_max) / 2, (y_bb_min + y_bb_max) / 2, z_bb_max + camera_z_margin))

camera_obj.data.ortho_scale = mesh_obj.dimensions.x
bpy.data.scenes["Scene"].render.resolution_x = horizontal_resolution
bpy.data.scenes["Scene"].render.resolution_y = int(horizontal_resolution * (mesh_obj.dimensions.y / mesh_obj.dimensions.x))

# сохранить левый верхний и правый нижний углы
bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(mesh_obj.matrix_world @ mathutils.Vector((x_bb_min, y_bb_max, z_bb_min))), scale=(1, 1, 1))
top_left_empty_obj = bpy.data.objects['Empty']
bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(mesh_obj.matrix_world @ mathutils.Vector((x_bb_max, y_bb_max, z_bb_min))), scale=(1, 1, 1))
top_right_empty_obj = bpy.data.objects['Empty.001']
bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(mesh_obj.matrix_world @ mathutils.Vector((x_bb_min, y_bb_min, z_bb_min))), scale=(1, 1, 1))
bottom_left_empty_obj = bpy.data.objects['Empty.002']
bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(mesh_obj.matrix_world @ mathutils.Vector((x_bb_max, y_bb_min, z_bb_min))), scale=(1, 1, 1))
bottom_right_empty_obj = bpy.data.objects['Empty.003']

bpy.ops.object.select_all(action='DESELECT')
top_left_empty_obj.select_set(True)
top_right_empty_obj.select_set(True)
bottom_left_empty_obj.select_set(True)
bottom_right_empty_obj.select_set(True)
bpy.context.view_layer.objects.active = mesh_obj
bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)

mesh_obj.rotation_mode = "XYZ"
mesh_obj.rotation_euler = math.radians(x_rotation), math.radians(y_rotation), math.radians(z_rotation)

bpy.context.view_layer.update()
corners = {
    'top_left': [str(Decimal(top_left_empty_obj.matrix_world.translation[0]) + tile_origin[0]), str(Decimal(top_left_empty_obj.matrix_world.translation[1]) + tile_origin[1]), str(Decimal(top_left_empty_obj.matrix_world.translation[2]) + tile_origin[2])],
    'top_right': [str(Decimal(top_right_empty_obj.matrix_world.translation[0]) + tile_origin[0]), str(Decimal(top_right_empty_obj.matrix_world.translation[1]) + tile_origin[1]), str(Decimal(top_right_empty_obj.matrix_world.translation[2]) + tile_origin[2])],
    'bottom_left': [str(Decimal(bottom_left_empty_obj.matrix_world.translation[0]) + tile_origin[0]), str(Decimal(bottom_left_empty_obj.matrix_world.translation[1]) + tile_origin[1]), str(Decimal(bottom_left_empty_obj.matrix_world.translation[2]) + tile_origin[2])],
    'bottom_right': [str(Decimal(bottom_right_empty_obj.matrix_world.translation[0]) + tile_origin[0]), str(Decimal(bottom_right_empty_obj.matrix_world.translation[1]) + tile_origin[1]), str(Decimal(bottom_right_empty_obj.matrix_world.translation[2]) + tile_origin[2])]
}

mesh_obj.rotation_euler = 0, 0, 0

with open(path_to_corners, 'w') as f:
    json.dump(corners, f)

# подготовка к рендеру
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.data.scenes["Scene"].render.filepath = str(path_to_render_result)
bpy.context.scene.camera = camera_obj

bpy.ops.render.render(write_still=True)