from struct import unpack, calcsize
from ..YMKs import YMKs  
import bpy
from mathutils import Vector, Euler

def safe_unpack(fmt, file, context="unknown"):
    size = calcsize(fmt)
    buf = file.read(size)
    if len(buf) < size:
        raise EOFError(f"Expected {size} bytes, got {len(buf)} at {context}")
    return unpack(fmt, buf)

def ReadXYZ(file):
	return unpack("<hhh", file.read(6))  # Reads all 3 shorts at once


def ReadZYX(file, count):
	return [unpack("<hhh", file.read(6))[::-1] for _ in range(count)]  # Z, Y, X


class EKey:
	def __init__(self):
		self.YMKs = YMKs()

	def ReadFrame(self, file):
		self.YMKs.GetAssetTable(file)
		self.FrameHeader = []
		self.Rotations = []
		self.Positions = []

		for entry in self.YMKs.AssetTable:
			RVA = entry["RVA"]
			FrameCount = entry["FrameCount"]

			table_offset = 256 + 4 + (self.YMKs.AssetCount * 16)
			file.seek(table_offset + RVA)


			for i in range(FrameCount):
				FrameLength = unpack("<B", file.read(1))[0]
				RealFrameLength = (FrameLength & 0x7F) << 1
				print(f"[Debug] Frame {i}, RealFrameLength: {RealFrameLength}, RVA: {RVA}")
				if RealFrameLength > 100:
					while True:
						LocalMarkerLength = safe_unpack("<B", file, context=f"marker @ frame {i}")[0]
						print(f"[Debug] Marker Byte: {LocalMarkerLength:02X}")
						RealLocalMarkerLength = LocalMarkerLength & 0x7F
						if LocalMarkerLength > 0x8F:
							break
						file.seek(
							RealLocalMarkerLength, 1
						)  # Aint dealing with this shit
						RealFrameLength -= RealLocalMarkerLength
				elif RealFrameLength >= 0x80 and RealFrameLength < 0xAC:
					GlobalMarkerLength = RealFrameLength & 0x7F
					for j in range(GlobalMarkerLength):
						if GlobalMarkerLength >= 0xAC:
							break
						file.seek(GlobalMarkerLength, 1)  # Aint dealing with this shit

				while 0 < RealFrameLength:
					ByteCount = unpack("<B", file.read(1))[0]
					RealByteCount = ByteCount & 0xF0
					RealChannelCount = RealByteCount >> 1
					Speed = ByteCount & 0x0F
					RealFrameLength -= 1
					self.FrameHeader.append({
						"AssetID": entry["ChildID"],
						"FrameIndex": i,
						"FrameLength": RealFrameLength,
						"ChannelCount": RealChannelCount
					})


					while 0 < RealByteCount:
						# Start reading root positions
						RealFrameLength -= 6
						RealByteCount -= 6
						XYZ = ReadXYZ(file)
						ZYX = ReadZYX(file, 0x5C)
						RealFrameLength -= 0x5C
						RealByteCount -= 0x5C
						file.seek(1, 1)
						RealFrameLength -= 1
						self.Rotations.append(ZYX)
						self.Positions.append(XYZ)
		return self.FrameHeader, self.Rotations, self.Positions

class ConvertToBlender:
	def __init__(self, armature_name="Armature"):
		self.armature_name = armature_name
		self.armature = bpy.data.objects.get(armature_name)
		if not self.armature or self.armature.type != 'ARMATURE':
			raise ValueError(f"Armature '{armature_name}' not found in the scene.")

	def ApplyAnimation(self, frame_headers, rotations, positions, action_name="YMK_Import_Action"):
		bpy.context.view_layer.objects.active = self.armature
		bpy.ops.object.mode_set(mode='POSE')

		pose_bones = self.armature.pose.bones
		action = bpy.data.actions.new(name=action_name)
		self.armature.animation_data_create()
		self.armature.animation_data.action = action

		frame_number = 1

		for i, (root_pos, bone_rots) in enumerate(zip(positions, rotations)):
			# Set root position (assumed bone[0] is root)
			if "root" in pose_bones:
				root_bone = pose_bones["root"]
				root_bone.location = Vector((root_pos[0] / 100.0, root_pos[1] / 100.0, root_pos[2] / 100.0))
				root_bone.keyframe_insert(data_path="location", frame=frame_number)

			# Set rotation for each bone
			for j, rot in enumerate(bone_rots):
				if j >= len(pose_bones):
					continue  # skip extra data
				bone = list(pose_bones)[j]
				# Convert to radians from short (assuming degrees * 0.01)
				rot_vector = Vector((rot[0] / 100.0, rot[1] / 100.0, rot[2] / 100.0))
				bone.rotation_mode = 'XYZ'
				bone.rotation_euler = Euler((rot_vector[0], rot_vector[1], rot_vector[2]))
				bone.keyframe_insert(data_path="rotation_euler", frame=frame_number)

			frame_number += 1

		bpy.ops.object.mode_set(mode='OBJECT')