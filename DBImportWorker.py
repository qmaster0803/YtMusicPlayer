import sqlite3

class DBImportWorker:
	def __init__(self, path):
		self.db = sqlite3.connect(path)

	def get_playlists(self):
		c = self.db.cursor()
		c.execute("SELECT * FROM `Playlist`;")
		output = {}
		for line in c.fetchall():
			c2 = self.db.cursor()
			c2.execute("SELECT `songId` FROM `SongPlaylistMap` WHERE `playlistId`="+str(line[0])+" ORDER BY `position` ASC;")
			playlist = []
			for i in c2.fetchall():
				playlist.append(i[0])
			output[line[0]] = [line[1]]+playlist
		return output