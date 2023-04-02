import DBImportWorker
import DBWorker
import YTWorker
import CacheWorker
import curses
import time
import os
import unicodedata
import vlc
import threading

def len_ea(string):
	nfc_string = unicodedata.normalize('NFC', string)
	return sum((2 if unicodedata.east_asian_width(c) in 'WF' else 1) for c in nfc_string)

#generates string in format mm:ss
#if more than 99 minutes, expands to mmm:ss and so
def gen_time_marker(time_ms, m_digits=None):
	seconds = round(time_ms/1000)
	minutes = seconds//60
	if(m_digits):
		return ('0'*m_digits+str(minutes))[-m_digits:]+':'+('0'+str(seconds%60))[-2:], m_digits
	else:
		m_digits = max(len(str(minutes)), 2)
		return ('0'*m_digits+str(minutes))[-m_digits:]+':'+('0'+str(seconds%60))[-2:], m_digits

class MainWorker:
	def __init__(self, screen, yt_worker, db_worker, db_import_worker, cache_worker):
		self.SEEK_TIME = 5000
		self.ALBUM_NAME_SHORTEN  = int(curses.COLS*0.10)
		self.ARTIST_NAME_SHORTEN = int(curses.COLS*0.15)
		self.TRACK_NAME_SHORTEN  = int(curses.COLS*0.25)
		self.PLAYER_PROGRESSBAR_UPDATE_DELAY = 0.2
		self.screen = screen
		self.yt_worker = yt_worker
		self.db_worker = db_worker
		self.db_import_worker = db_import_worker
		self.cache_worker = cache_worker

		#current playing data
		self.first_displayed_playlist = 0
		self.first_displayed_track = 0
		self.playlists = None
		self.playlists_ids = None
		self.selected_playlist = None
		self.selected_track = 0
		self.playlists_count = 0

		self.playback_id = None
		self.playback_volume = 100
		self.playback_paused = True
		self.playback_playlist = None
		self.playback_playlist_index = None #index in self.tracks
		self.player_instance = vlc.Instance("-q")
		self.player = self.player_instance.media_player_new()
		self.player.audio_set_volume(self.playback_volume)

		self.do_window_prepare()

		self.exit = False
		self.progressbar_updater_thread = threading.Thread(target=self.update_player_progressbar, daemon=True)
		self.progressbar_updater_thread.start()


	def do_window_prepare(self):
		win_height = curses.LINES-1
		win_width  = curses.COLS -1
		self.playlists_win_width = int(win_width*0.3)
		self.tracks_win_width =    int(win_width*0.7)
		self.global_width = self.playlists_win_width+self.tracks_win_width
		self.global_lists_height = win_height-6

		self.player_heading_window        = curses.newwin(1, self.global_width+1, 0, 0)
		self.player_progressbar_window    = curses.newwin(1, self.global_width+1, 1, 0)
		self.playlists_window             = curses.newwin(win_height-4, self.playlists_win_width, 2, 0)
		self.tracks_window                = curses.newwin(win_height-4, self.tracks_win_width, 2, int(win_width*0.3))
		self.hotkeys_help_window          = curses.newwin(2, self.global_width+1, win_height-2, 0)

		self.playlists_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		self.tracks_window.border('|', '|', '-', '-', '+', '+', '+', '+')

		self.player_heading_window.noutrefresh()
		self.playlists_window.noutrefresh()
		self.tracks_window.noutrefresh()

		self.update_player_heading()
		self.update_playlists_list()
		self.show_hotkeys()
		self.set_player_progressbar(0, '--:--', '--:--')
		curses.doupdate()

	def show_hotkeys(self):
		s  = self.db_worker.shorten("W/S - Scroll playlists            P - Delete playlist    I - Import playlist    A - Download playlist to cache", curses.COLS-1)
		s2 = self.db_worker.shorten("Arrows up/down - Scroll tracks    D - Delete track       Space - Play/Pause     V - Play selected                 E - Open search window    L/K - Volume up/down", curses.COLS-1)
		self.hotkeys_help_window.addstr(0, 0, s)
		self.hotkeys_help_window.addstr(1, 0, s2)
		self.hotkeys_help_window.noutrefresh()

	def update_tracks_list(self, local_db_worker=None):
		if(local_db_worker == None): local_db_worker = self.db_worker
		self.tracks = local_db_worker.get_tracks_from_playlist(self.playlists_ids[self.selected_playlist])
		i = 0
		for i, track_id in enumerate(self.tracks[self.first_displayed_track:self.first_displayed_track+self.global_lists_height]):
			data = local_db_worker.get_track_data(track_id)
			if(data):
				data['album']  = local_db_worker.shorten(data['album'], self.ALBUM_NAME_SHORTEN)
				data['artist'] = local_db_worker.shorten(data['artist'], self.ARTIST_NAME_SHORTEN)
				data['title']  = local_db_worker.shorten(data['title'], self.TRACK_NAME_SHORTEN)
				s = ("[*] " if (i+self.first_displayed_track)==self.selected_track else "[ ] ")+("[x] " if track_id==self.playback_id else "[ ] ")+data['title']+" - "+data['album']
				s1 = "["+data['artist']+']'+" "*(self.ARTIST_NAME_SHORTEN-len_ea(data['artist']))+'['+str(data['release_year'])+']'+("[*]" if (i+self.first_displayed_track)==self.selected_track else "[ ]")
			else:
				s = ("[*] " if (i+self.first_displayed_track)==self.selected_track else "[ ] ")+"[ ] NO DATA"
				s1 = "[NO DATA][NO DATA]"+("[*]" if (i+self.first_displayed_track)==self.selected_track else "[ ]")
			self.tracks_window.addstr(1+i, 1, s+(" "*(self.tracks_win_width-2-len_ea(s)-len_ea(s1)))+s1)

		if(i == 0):
			self.tracks_window.addstr(1, 1, "Playlist is empty!"+(" "*(self.tracks_win_width-20)))
		for i in range(i+1, self.global_lists_height):
			self.tracks_window.addstr(1+i, 1, " "*(self.tracks_win_width-2))
		self.tracks_window.refresh()


	def update_playlists_list(self):
		self.playlists = self.db_worker.get_playlists()
		self.playlists_ids = sorted(list(self.playlists.keys()))
		self.playlists_count = len(self.playlists_ids)

		if(self.selected_playlist == None and self.playlists_ids):
			self.selected_playlist = 0

		i = 0
		for i, playlist_id in enumerate(self.playlists_ids[self.first_displayed_playlist:self.first_displayed_playlist+self.global_lists_height]):
			s = "["+("*" if (i+self.first_displayed_playlist)==self.selected_playlist else " ")+"] "+self.db_worker.shorten(self.playlists[playlist_id], self.playlists_win_width-6)
			self.playlists_window.addstr(1+i, 1, s+(" "*(self.playlists_win_width-2-len_ea(s))))

		for i in range(i+1, self.global_lists_height):
			self.playlists_window.addstr(1+i, 1, " "*(self.playlists_win_width-2))
		if(self.selected_playlist != None): self.update_tracks_list()
		self.playlists_window.refresh()

	def update_player_progressbar(self):
		progressbar_updater_thread_db_worker = DBWorker.DBWorker() #need it here because it's other thread
		while(not self.exit):
			if(self.playback_id == None): self.set_player_progressbar(0, '--:--', '--:--')
			else:
				if(int(self.player.get_position()) == -1): self.set_player_progressbar(0, '--:--', '--:--')
				else:
					overall_time_str, m_digits = gen_time_marker(self.player.get_length())
					curr_time = gen_time_marker(self.player.get_time(), m_digits=m_digits)[0]
					self.set_player_progressbar(round(self.player.get_position()*1000), curr_time, overall_time_str)
			if(not self.playback_paused and not self.player.is_playing()):
				#going to next track if exists
				if(self.playback_playlist_index != len(self.playback_playlist)):
					while(True):
						if(self.playback_playlist_index != len(self.playback_playlist)):
							self.playback_playlist_index += 1
							if(progressbar_updater_thread_db_worker.get_track_data(self.playback_playlist[self.playback_playlist_index])):
								self.start_playing(self.playback_playlist[self.playback_playlist_index], local_db_worker=progressbar_updater_thread_db_worker)
								break
						else:
							break
				else: self.playback_paused = True
			time.sleep(self.PLAYER_PROGRESSBAR_UPDATE_DELAY)
		progressbar_updater_thread.close()

	#values from 0 to 1000!!
	def set_player_progressbar(self, value, curr_time_str, overall_time_str):
		progressbar_width = self.global_width - len(curr_time_str) - len(overall_time_str) - 8
		l = (progressbar_width / float(1000)) * value
		s = ("[▶] " if self.player.is_playing() else "[‖] ")+"="*round(l)+"-"*(progressbar_width-round(l))+" ["+curr_time_str+"/"+overall_time_str+"]"
		self.player_progressbar_window.addstr(0, 0, s)
		self.player_progressbar_window.refresh()

	def update_player_heading(self, local_db_worker=None):
		if(local_db_worker == None): local_db_worker = self.db_worker
		if(self.playback_id):
			data = local_db_worker.get_track_data(self.playback_id)
			#for safety
			if(data == None):
				data = self.yt_worker.get_info(self.playback_id)
				local_db_worker.save_track_data(self.playback_id, data['title'], data['album'], data['artist'], data['release_year'], data['preview'])
			s1 = local_db_worker.shorten(data['title'], int(curses.COLS*0.35))+" - "+local_db_worker.shorten(data['album'], int(curses.COLS*0.35))
			s2 = "["+local_db_worker.shorten(data['artist'], int(curses.COLS*0.15))+']['+str(data['release_year'])+']'+" [VOL:"+("00"+str(self.playback_volume))[-3:]+"%]"
			self.player_heading_window.addstr(0, 0, s1+(" "*(self.global_width-len(s1)-len(s2)))+s2)
			self.player_heading_window.refresh()
		else:
			s1 = "Nothing is playing right now!"
			s2 = "[VOL:"+("00"+str(self.playback_volume))[-3:]+"%]"
			self.player_heading_window.addstr(0, 0, s1+(" "*(self.global_width-len(s1)-len(s2)))+s2)
			self.player_heading_window.refresh()


	def do_import(self):
		win_height = int(curses.LINES*0.5)
		win_width  = int(curses.COLS*0.5)
		import_window = curses.newwin(win_height, win_width, int((curses.LINES-win_height)/2), int((curses.COLS-win_width)/2))
		import_window.keypad(True)
		import_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		import_window.addstr(1, 1, "Use arrows for navigation")
		import_window.addstr(2, 1, "Use Enter to choose")
		import_window.addstr(4, 1, "Pick file to import:")
		import_window.addstr(5, 1, "-"*(win_width-2))
		#small file explorer here
		current_path = os.getcwd()
		chosen_file = None
		exit = False
		while(chosen_file == None):
			path_list = os.listdir(current_path)
			dir_list = []
			files_list = []
			for path in path_list:
				if(os.path.isdir(path)): dir_list.append(path)
				else: files_list.append(path)
			path_list = []
			path_list.append("..")
			dir_list.sort()
			files_list.sort()
			path_list += dir_list+files_list
			first_displayed = 0
			selected = 0
			while(True):
				i = 0
				for i,file in enumerate(path_list[first_displayed:first_displayed+(win_height-7)]):
					import_window.addstr(i+6, 1, ("[*] " if selected==first_displayed+i else "[ ] ")+file+" "*(win_width-6-len_ea(file)))
				for i in range(i+1, win_height-7):
					import_window.addstr(i+6, 1, " "*(win_width-2))
				c = import_window.getch()
				if(c == curses.KEY_UP and selected > 0):
					selected -= 1
					if(selected-first_displayed < 3 and first_displayed != 0): first_displayed -= 1
				if(c == curses.KEY_DOWN and selected < len(path_list)-1):
					selected += 1
					if(win_height-6+first_displayed-selected < 3): first_displayed += 1
				if(c == curses.KEY_BACKSPACE):
					current_path = os.path.normpath(os.path.join(current_path, ".."))
					break 
				if(c == ord('\n')):
					if(os.path.isdir(os.path.join(current_path, path_list[selected]))): current_path = os.path.normpath(os.path.join(current_path, path_list[selected]))
					else: chosen_file = os.path.join(current_path, path_list[selected])
					break
				if(c == ord('q')):
					chosen_file = ""
					exit = True
					break
		if(not exit):
			#clear window and try to parse selected file
			import_window.erase()
			import_window.border('|', '|', '-', '-', '+', '+', '+', '+')
			import_window.refresh()
			import_window.addstr(1, 1, "Parsing file...")
			#just throw object to db_importer
			playlists_data = self.db_import_worker.autoparse(chosen_file)
			if(playlists_data):
				import_window.addstr(2, 1, "Done! Select playlists to import:")
				import_window.addstr(3, 1, "Use space to select, enter to continue")
				import_window.addstr(4, 1, "-"*(win_width-2))
				#playlists selector
				playlists_ids = list(playlists_data.keys())
				current_selected = []
				first_displayed = 0
				selected = 0
				while(True):
					i = 0
					for i,pid in enumerate(playlists_ids[first_displayed:first_displayed+(win_height-6)]):
						import_window.addstr(i+5, 1, ("[*] " if selected==first_displayed+i else "[ ] ")+("[x] " if pid in current_selected else "[ ] ")+playlists_data[pid][0]+" "*(win_width-10-len_ea(playlists_data[pid][0])))
					for i in range(i+1, win_height-7):
						import_window.addstr(i+5, 1, " "*(win_width-2))
					c = import_window.getch()
					if(c == curses.KEY_UP and selected > 0):
						selected -= 1
						if(selected-first_displayed < 3 and first_displayed != 0): first_displayed -= 1
					if(c == curses.KEY_DOWN and selected < len(path_list)-1):
						selected += 1
						if(win_height-5+first_displayed-selected < 3): first_displayed += 1
					if(c == ord(" ")):
						if(playlists_ids[selected] in current_selected): current_selected.remove(playlists_ids[selected])
						else: current_selected.append(playlists_ids[selected])
					if(c == ord('\n')):
						if(os.path.isdir(os.path.join(current_path, path_list[selected]))): current_path = os.path.normpath(os.path.join(current_path, path_list[selected]))
						else: chosen_file = os.path.join(current_path, path_list[selected])
						break
				#work on selected
				import_window.erase()
				import_window.border('|', '|', '-', '-', '+', '+', '+', '+')
				import_window.refresh()
				import_window.addstr(1, 1, "Importing...")
				for i in current_selected:
					pid = self.db_worker.add_playlist(playlists_data[i][0])
					for track in playlists_data[i][1:]:
						self.db_worker.add_track_to_playlist(track, pid)
			else:
				import_window.addstr(2, 1, "Unsupported format!")
			import_window.refresh()
			time.sleep(1)
		self.playlists_window.redrawwin()
		self.playlists_window.refresh()
		self.tracks_window.redrawwin()
		self.tracks_window.refresh()
		self.update_playlists_list()
		self.update_tracks_db()


	def update_tracks_db(self):
		update_list = self.db_worker.get_tracks_db_updates()

		if(len(update_list) == 0): return

		win_height = 7
		win_width  = int(curses.COLS*0.5)
		update_window = curses.newwin(win_height, win_width, int((curses.LINES-win_height)/2), int((curses.COLS-win_width)/2))
		update_window.keypad(True)
		update_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		update_window.addstr(2, 2, "Need to get info about "+str(len(update_list))+" track(s)")
		s = "Progress: "+str(0)+"/"+str(len(update_list))+"; Errors: "+str(0)
		update_window.addstr(3, 2, s+(" "*(win_width-4-len(s))))

		#draw progressbar
		s = "-"*(win_width-4)
		update_window.addstr(4, 2, s)
		update_window.refresh()

		#start work
		success = 0
		error = 0
		for track in update_list:
			data = self.yt_worker.get_info(track)
			if(data["error"] == "ok"):
				success += 1
				self.db_worker.save_track_data(track, data['title'], data['album'], data['artist'], data['release_year'], data['preview'])
			elif(data["error"] == "video_blocked"):
				self.db_worker.purge_broken(track)
				error += 1
			elif(data["error"] == "no_network"):
				s = "Network error!"
				update_window.addstr(3, 2, s+(" "*(win_width-4-len(s))))
				update_window.refresh()
				time.sleep(1)
				break
			#redraw text and progressbar
			s = "Progress: "+str(success)+"/"+str(len(update_list))+"; Errors: "+str(error)
			update_window.addstr(3, 2, s+(" "*(win_width-4-len(s))))
			l = ((win_width-4) / float(len(update_list))) * (success+error)
			s = "="*round(l)+"-"*(win_width-4-round(l))
			update_window.addstr(4, 2, s)
			update_window.refresh()
		time.sleep(1)
		self.playlists_window.redrawwin()
		self.playlists_window.refresh()
		self.tracks_window.redrawwin()
		self.tracks_window.refresh()
		self.update_playlists_list()

	#triggered from CacheWorker
	def show_caching_sign(self):
		win_height = 5
		win_width  = 30
		caching_window = curses.newwin(win_height, win_width, int((curses.LINES-win_height)/2), int((curses.COLS-win_width)/2))
		caching_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		caching_window.addstr(2, 10, "Caching...")
		caching_window.refresh()

	def close_caching_sign(self):
		self.playlists_window.redrawwin()
		self.playlists_window.refresh()
		self.tracks_window.redrawwin()
		self.tracks_window.refresh()

	def start_playing(self, video_id, local_db_worker=None):
		self.playback_id = video_id
		self.cache_worker.cache(self.playback_id, self, local_db_worker=local_db_worker)
		self.player.set_media(vlc.Media("cache/"+str(self.playback_id)+".mp3"))
		self.player.play()
		self.playback_paused = False
		self.update_player_heading(local_db_worker=local_db_worker)
		self.update_tracks_list(local_db_worker=local_db_worker)


	def mainloop(self):
		curses.curs_set(0)
		self.update_tracks_db()
		while(True):
			self.playlists_window.keypad(True)
			curses.mousemask(-1)
			c = self.playlists_window.getch()
			if(c == ord('w') and self.selected_playlist > 0): #playlist up
				self.selected_track = 0
				self.selected_playlist -= 1
				if(self.selected_playlist-self.first_displayed_playlist < 5 and self.first_displayed_playlist != 0): self.first_displayed_playlist -= 1
				self.update_playlists_list()
			if(c == ord('s') and self.selected_playlist < self.playlists_count-1): #playlist down
				self.selected_track = 0
				self.selected_playlist += 1
				if(self.global_lists_height+self.first_displayed_playlist-self.selected_playlist < 5): self.first_displayed_playlist += 1
				self.update_playlists_list()

			if(c == curses.KEY_UP and self.selected_track > 0):
				self.selected_track -= 1
				if(self.selected_track - self.first_displayed_track < 5 and self.first_displayed_track != 0): self.first_displayed_track -= 1
				self.update_tracks_list()
			if(c == curses.KEY_DOWN and self.selected_track < len(self.tracks)-1):
				self.selected_track += 1
				if(self.global_lists_height+self.first_displayed_track-self.selected_track < 5): self.first_displayed_track += 1
				self.update_tracks_list()

			if(c == curses.KEY_MOUSE):
				mouse_state = curses.getmouse()[4]
				if(mouse_state == curses.BUTTON4_PRESSED and self.selected_track > 0): #same as arrow up
					self.selected_track -= 1
					if(self.selected_track - self.first_displayed_track < 5 and self.first_displayed_track != 0): self.first_displayed_track -= 1
					self.update_tracks_list()
				if(mouse_state == curses.BUTTON5_PRESSED and self.selected_track < len(self.tracks)-1):
					self.selected_track += 1
					if(self.global_lists_height+self.first_displayed_track-self.selected_track < 5): self.first_displayed_track += 1
					self.update_tracks_list()

			#seeking
			if(c == curses.KEY_RIGHT and self.playback_id != None and self.player.get_time() != -1):
				self.player.set_time(min(self.player.get_length(), self.player.get_time()+self.SEEK_TIME))

			if(c == ord('v')):
				if(self.db_worker.get_track_data(self.tracks[self.selected_track])):
					self.start_playing(self.tracks[self.selected_track])
					self.playback_playlist_index = self.selected_track
					self.playback_playlist = self.tracks.copy()

			if(c == ord(" ")):
				if(self.playback_paused): self.player.play()
				else: self.player.pause()
				self.playback_paused = not self.playback_paused

			#volume
			if(c == ord("k") and self.playback_volume > 0):
				self.playback_volume -= 1
				self.player.audio_set_volume(self.playback_volume)
				self.update_player_heading()
			if(c == ord("l") and self.playback_volume < 100):
				self.playback_volume += 1
				self.player.audio_set_volume(self.playback_volume)
				self.update_player_heading()

			if(c == ord('i')): #import
				self.do_import()
			if(c == ord('u')):
				self.update_tracks_db()
			if(c == ord('q')):
				self.db_worker.close()
				self.exit = True
				self.progressbar_updater_thread.join()
				break


def main(screen):
	db_import_worker = DBImportWorker.DBImportWorker()
	db_worker = DBWorker.DBWorker()
	yt_worker = YTWorker.YTWorker()
	cache_worker = CacheWorker.CacheWorker(db_worker, yt_worker)
	#playlists = db_import_worker.get_playlists()

	main_worker = MainWorker(screen, yt_worker, db_worker, db_import_worker, cache_worker)
	main_worker.update_player_heading()
	main_worker.mainloop()
	#print(playlists)
	#print(yt_worker.get_info("pTYIf2pkxzQ"))
	#yt_worker.get_audio("pTYIf2pkxzQ")

if(__name__ == "__main__"):
	curses.wrapper(main)