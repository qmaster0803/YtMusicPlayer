import sqlite3
import os

class DBWorker:
	def __init__(self):
		if(not os.path.exists("main.db")): db_empty = True
		else: db_empty = False
		self.db = sqlite3.connect("main.db")
		if(db_empty): self.init_empty_db()

	def init_empty_db(self):
		c = self.db.cursor()
		c.execute('CREATE TABLE "tracks" ("id" TEXT UNIQUE, "name" TEXT, "album" TEXT, "artist" TEXT, "year" INTEGER, "preview" TEXT);')
		c.execute('CREATE TABLE "playlists" ("id" INTEGER UNIQUE, "name" INTEGER, PRIMARY KEY("id" AUTOINCREMENT));');
		c.execute('CREATE TABLE "playlist_map" ("playlist_id" INTEGER, "track_id" INTEGER, "position" INTEGER);')
		self.db.commit()

	def save_track_data(self, track_id, name, album, artist, year, preview):
		c = self.db.cursor()
		c.execute('INSERT INTO `tracks`(`id`, `name`, `album`, `artist`, `year`, `preview`) VALUES ("{}", "{}", "{}", "{}", {}, "{}");'.format(str(track_id), str(name), str(album), str(artist), str(year), str(preview)))
		self.db.commit()

	def get_track_data(self, track_id):
		c = self.db.cursor()
		c.execute('SELECT * FROM `tracks` WHERE `id`="'+str(track_id)+'";')
		d = c.fetchone()
		if(d):
			data = {}
			data['title']        = d[1]
			data['album']        = d[2]
			data['artist']       = d[3]
			data['preview']      = d[5]
			data['release_year'] = d[4]
			return data
		else: return None

	def get_playlists(self):
		c = self.db.cursor()
		c.execute('SELECT * FROM `playlists`;')
		data = {}
		for i in c.fetchall():
			data[i[0]] = i[1]
		return data