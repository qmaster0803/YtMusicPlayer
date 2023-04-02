import sqlite3
import os
import time

class DBWorker:
	def __init__(self):
		if(not os.path.exists("main.db")): db_empty = True
		else: db_empty = False
		self.db = sqlite3.connect("main.db")
		if(db_empty): self.init_empty_db()

	def init_empty_db(self):
		c = self.db.cursor()
		c.execute('CREATE TABLE "tracks" ("id" TEXT UNIQUE, "name" TEXT, "album" TEXT, "artist" TEXT, "year" INTEGER, "preview" TEXT);')
		c.execute('CREATE TABLE "playlists" ("id" INTEGER UNIQUE, "name" INTEGER, PRIMARY KEY("id" AUTOINCREMENT));')
		c.execute('CREATE TABLE "playlist_map" ("playlist_id" INTEGER, "track_id" INTEGER, "position" INTEGER);')
		c.execute('CREATE TABLE "cache" ("id" TEXT UNIQUE, "last_used_timestamp" INTEGER);')
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

	def add_playlist(self, name):
		c = self.db.cursor()
		c.execute('INSERT INTO `playlists` (`name`) VALUES ("'+str(name)+'");')
		self.db.commit()
		c = self.db.cursor()
		c.execute('SELECT `id` FROM `playlists` ORDER BY `id` DESC LIMIT 1;')
		return int(c.fetchone()[0])

	def add_track_to_playlist(self, track_id, playlist_id):
		c = self.db.cursor()
		c.execute('SELECT `position` FROM `playlist_map` WHERE `playlist_id`='+str(playlist_id)+' ORDER BY `position` DESC LIMIT 1;')
		last_pos = -1
		f = c.fetchone()
		if(f): last_pos = int(f[0])
		c = self.db.cursor()
		c.execute('INSERT INTO `playlist_map` (`playlist_id`, `track_id`, `position`) VALUES ('+str(playlist_id)+', "'+str(track_id)+'", '+str(last_pos+1)+');')
		self.db.commit()

	def get_tracks_db_updates(self):
		c = self.db.cursor()
		c.execute('SELECT `track_id` FROM `playlist_map`;')
		c2 = self.db.cursor()
		c2.execute('SELECT `id` FROM `tracks`;')
		already_listed = set([i[0] for i in c2.fetchall()])
		ret = []
		for i in [i[0] for i in c.fetchall()]:
			if(i not in already_listed):
				ret.append(i)
		return ret

	def purge_broken(self, track_id):
		c = self.db.cursor()
		c.execute('DELETE FROM `tracks` WHERE `id`="'+str(track_id)+'";')
		c = self.db.cursor()
		c.execute('DELETE FROM `playlist_map` WHERE `track_id`="'+str(track_id)+'";')
		self.db.commit()

	def get_tracks_from_playlist(self, playlist_id):
		c = self.db.cursor()
		c.execute('SELECT `track_id` FROM `playlist_map` WHERE `playlist_id`='+str(playlist_id)+';')
		return [i[0] for i in c.fetchall()]

	def is_track_in_cache(self, video_id):
		c = self.db.cursor()
		c.execute('SELECT `id` FROM `cache` WHERE `id`=="'+str(video_id)+'";')
		return len(c.fetchall()) != 0

	def add_track_to_cache(self, video_id):
		c = self.db.cursor()
		c.execute('INSERT INTO `cache` (`id`, `last_used_timestamp`) VALUES ("'+str(video_id)+'", '+str(int(time.time()))+');')
		self.db.commit()

	def update_cache_used_time(self, video_id):
		c = self.db.cursor()
		c.execute('UPDATE `cache` SET `last_used_timestamp`='+str(int(time.time()))+' WHERE `id`="'+str(video_id)+'";')
		self.db.commit()

	def shorten(self, string, shorten_l):
		if(len(string) > shorten_l): string = string[:shorten_l-3]+"..."
		return string

	def close(self):
		self.db.close()