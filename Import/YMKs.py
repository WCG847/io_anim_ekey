from struct import unpack

class YMKs:
	def GetAssetTable(self, file):
		file.seek(256)
		self.AssetCount = unpack('<I', file.read(4))[0]
		self.AssetTable = []
		for i in range(self.AssetCount):
			ChildID = unpack('<H', file.read(2))[0]
			ParentID = unpack('<H', file.read(2))[0]
			RVA = unpack('<I', file.read(4))[0]
			FrameCount = unpack('<I', file.read(4))[0]
			file.seek(4, 1)
			self.AssetTable.append(
				{
					'ChildID': ChildID,
					'ParentID': ParentID,
					'RVA': RVA,
					'FrameCount': FrameCount
				}
			)
		return self.AssetTable

