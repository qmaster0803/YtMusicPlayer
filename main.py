import DBImportWorker
import DBWorker
import YTWorker
import curses
import time

class MainWorker:
	def __init__(self, screen, yt_worker, db_worker):
		self.screen = screen
		self.yt_worker = yt_worker
		self.db_worker = db_worker

		#current playing data
		self.first_displayed_playlist = 0
		self.playback_id = 'pTYIf2pkxzQ'
		self.timecode = None

		self.do_window_prepare()

	def do_window_prepare(self):
		win_height = curses.LINES-1
		win_width  = curses.COLS -1
		self.global_width = int(win_width*0.3)+int(win_width*0.7)
		self.global_lists_height = win_height-6

		self.player_heading_window        = curses.newwin(1, self.global_width+1, 0, 0)
		self.player_progressbar_window    = curses.newwin(1, self.global_width+1, 1, 0)
		self.playlists_window             = curses.newwin(win_height-4, int(win_width*0.3), 2, 0)
		self.tracks_window                = curses.newwin(win_height-4, int(win_width*0.7), 2, int(win_width*0.3))

		self.playlists_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		self.tracks_window.border('|', '|', '-', '-', '+', '+', '+', '+')

		self.player_heading_window.noutrefresh()
		self.playlists_window.noutrefresh()
		self.tracks_window.noutrefresh()

		self.update_player()
		self.update_playlists_list()
		curses.doupdate()

	def update_playlists_list(self):
		self.playlists = self.db_worker.get_playlists()
		for i, playlist_id in enumerate(sorted(list(self.playlists.keys()))[self.first_displayed_playlist:self.first_displayed_playlist+self.global_lists_height]):
			self.playlists_window.addstr(1+i, 1, "[ ] "+self.playlists[playlist_id])
		self.playlists_window.refresh()

	def update_player(self):
		self.player_heading_window.addstr(0, 0, 'test')
		self.player_heading_window.noutrefresh()

	#values from 0 to 1000!!
	def set_player_progressbar(self, value):
		l = (self.global_width / float(1000)) * value
		s = "="*round(l)+"-"*(self.global_width-round(l))
		self.player_progressbar_window.addstr(0, 0, s)
		self.player_progressbar_window.refresh()

	def update_player_heading(self):
		data = self.db_worker.get_track_data(self.playback_id)
		#for safety
		if(data == None):
			data = self.yt_worker.get_info(self.playback_id)
			self.db_worker.save_track_data(self.playback_id, data['title'], data['album'], data['artist'], data['release_year'], data['preview'])
		s = data['title']+" - "+data['album']+" "+"["+data['artist']+']['+str(data['release_year'])+']'
		self.player_heading_window.addstr(0, 0, s)
		self.player_heading_window.refresh()

def main(screen):
	db_import_worker = DBImportWorker.DBImportWorker("vimusic.db")
	db_worker = DBWorker.DBWorker()
	yt_worker = YTWorker.YTWorker()
	#playlists = db_import_worker.get_playlists()

	main_worker = MainWorker(screen, yt_worker, db_worker)
	main_worker.update_player_heading()
	for i in range(1000):
		main_worker.set_player_progressbar(i)
		time.sleep(0.1)
	input()
	#print(playlists)
	#print(yt_worker.get_info("pTYIf2pkxzQ"))
	#yt_worker.get_audio("pTYIf2pkxzQ")

if(__name__ == "__main__"):
	curses.wrapper(main)