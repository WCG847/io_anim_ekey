from io import BytesIO
from struct import unpack
from typing import BinaryIO
from gc import collect

class CEKey:
	def __init__(self, IO_BPYFILE:BinaryIO):
		self.File = IO_BPYFILE

	def _dt(self):
		collect()
		self.File.close()
		self.File = None
		del self.File

	def Search(self, assetID, variation, actorPropertyType) -> int:
		mainID = (assetID << 16) | (variation << 8) | actorPropertyType
		self.File.seek(256)
		entries = unpack('<I', self.File.read(4))[0]  # total count

		low = 0
		high = entries - 1

		while low <= high:
			mid = (low + high) // 2
			offset = mid * 16
			self.File.seek(offset)
			gotID = unpack('<I', self.File.read(4))[0]

			if gotID == mainID:
				return gotID, self.File.tell()
			elif mainID < gotID:
				high = mid - 1
			else:
				low = mid + 1

		return -1

	def GetData(self, assetID, variation, actorPropertyType):
		index = []
		gotID, midpoint = self.Search(assetID, variation, actorPropertyType)
		self.File.seek(256)
		entries = unpack('<I', self.File.read(4))[0] << 4
		self.File.seek(260 + entries)
		dataStart = self.File.tell()
		self.File.seek(midpoint - 4) # backtrack to actual start
		Record = self.File.tell()
		self.File.seek(8, 1)
		Frames = unpack('<I', self.File.read(4))[0]
		self.File.seek(Record + 4)
		Offset = unpack('<I', self.File.read(4))[0]
		CUTOFF = 0x000FFFFF
		if Offset == CUTOFF:
			return False
		self.File.seek(dataStart + Offset)
		animStart = self.File.tell()
		indexLength = unpack('<B', self.File.read(1))[0]
		if indexLength & 0x80 == 0:
			return False
		index.append(indexLength)
		decodedLength = ((indexLength & 0x7F) << 1) + 1
		return self.File.tell(), Frames, decodedLength

	def ChkData(self, assetID, variation, actorPropertyType, framesRead):
		gotID, midpoint = self.Search(assetID, variation, actorPropertyType)
		self.File.seek(midpoint - 4) # backtrack to actual start
		Record = self.File.tell()
		self.File.seek(8, 1)
		Frames = unpack('<I', self.File.read(4))[0]
		var1 = int(framesRead < Frames)
		var1 ^= 1
		return var1








