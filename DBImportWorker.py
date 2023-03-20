import sqlite3
import os

class DBImportWorker:
	def check_vimusic(self, path):
		try:
			db = sqlite3.connect(path)
			c = db.cursor()
			c.execute('PRAGMA table_info(`Playlist`);')
			return (c.fetchall() == [(0, 'id', 'INTEGER', 1, None, 1), (1, 'name', 'TEXT', 1, None, 0), (2, 'browseId', 'TEXT', 0, None, 0)])
		except:
			db.close()
			return False

	def autoparse(self, path):
		if(os.path.splitext(path)[1] == '.db'):
			#import vimusic playlist
			pass


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