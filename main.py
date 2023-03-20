import DBImportWorker
import DBWorker
import YTWorker
import curses
import time
import os

class MainWorker:
	def __init__(self, screen, yt_worker, db_worker, db_import_worker):
		self.screen = screen
		self.yt_worker = yt_worker
		self.db_worker = db_worker
		self.db_import_worker = db_import_worker

		#current playing data
		self.first_displayed_playlist = 0
		self.selected_playlist = None
		self.playlists_count = 0

		self.playback_id = 'pTYIf2pkxzQ'
		self.timecode = None

		self.do_window_prepare()


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
		playlist_ids = sorted(list(self.playlists.keys()))
		self.playlists_count = len(playlist_ids)

		if(self.selected_playlist == None):
			self.selected_playlist = 0

		i = 0
		for i, playlist_id in enumerate(playlist_ids[self.first_displayed_playlist:self.first_displayed_playlist+self.global_lists_height]):
			s = "["+("*" if (i+self.first_displayed_playlist)==self.selected_playlist else " ")+"] "+self.playlists[playlist_id]
			self.playlists_window.addstr(1+i, 1, s+(" "*(self.playlists_win_width-2-len(s))))

		for i in range(i+1, self.global_lists_height):
			self.playlists_window.addstr(1+i, 1, " "*(self.playlists_win_width-2))
		self.playlists_window.refresh()


	def update_player(self):
		self.player_heading_window.addstr(0, 0, 'test')
		self.player_heading_window.refresh()


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
					import_window.addstr(i+6, 1, ("[*] " if selected==first_displayed+i else "[ ] ")+file+" "*(win_width-6-len(file)))
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
					import_window.addstr(i+5, 1, ("[*] " if selected==first_displayed+i else "[ ] ")+("[x] " if pid in current_selected else "[ ] ")+playlists_data[pid][0]+" "*(win_width-10-len(playlists_data[pid][0])))
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
		time.sleep(2)
		self.playlists_window.redrawwin()
		self.playlists_window.refresh()
		self.tracks_window.redrawwin()
		self.tracks_window.refresh()
		self.update_playlists_list()

	def update_tracks_db(self):
		update_list = self.db_worker.get_tracks_db_updates()

		win_height = int(curses.LINES*0.5)
		win_width  = int(curses.COLS*0.5)
		update_window = curses.newwin(win_height, win_width, int((curses.LINES-win_height)/2), int((curses.COLS-win_width)/2))
		update_window.keypad(True)
		update_window.border('|', '|', '-', '-', '+', '+', '+', '+')
		update_window.addstr(1, 1, "Need to get info about"+str(len(update_list))+"track(s)")
		s = "Progress: "+str(0)+"/"+str(len(update_list))+"; Errors: "+str(0)
		update_window.addstr(2, 1, s+(" "*(win_width-2-len(s))))

		#draw progressbar
		s = "-"*(win_width-2)
		update_window.addstr(3, 1, s)
		update_window.refresh()

		#start work
		success = 0
		error = 0
		for track in update_list:
			data = self.yt_worker.get_info(track)
			if(data):
				success += 1
				with open("a", "w") as file:
					file.write(str([track, data['title'], data['album'], data['artist'], data['release_year'], data['preview']]))
				self.db_worker.save_track_data(track, data['title'], data['album'], data['artist'], data['release_year'], data['preview'])
			else:
				self.db_worker.purge_broken(track)
				error += 1
			#redraw text and progressbar
			s = "Progress: "+str(success)+"/"+str(len(update_list))+"; Errors: "+str(error)
			update_window.addstr(2, 1, s+(" "*(win_width-2-len(s))))
			l = ((win_width-2) / float(len(update_list))) * (success+error)
			s = "="*round(l)+"-"*(win_width-2-round(l))
			update_window.addstr(3, 1, s)
			update_window.refresh()
		time.sleep(2)
		self.playlists_window.redrawwin()
		self.playlists_window.refresh()
		self.tracks_window.redrawwin()
		self.tracks_window.refresh()
		self.update_playlists_list()


	def mainloop(self):
		while(True):
			c = self.playlists_window.getch()
			if(c == ord('w') and self.selected_playlist > 0): #playlist up
				self.selected_playlist -= 1
				if(self.selected_playlist-self.first_displayed_playlist < 5 and self.first_displayed_playlist != 0): self.first_displayed_playlist -= 1
				self.update_playlists_list()
			if(c == ord('s') and self.selected_playlist < self.playlists_count-1): #playlist down
				self.selected_playlist += 1
				if(self.global_lists_height+self.first_displayed_playlist-self.selected_playlist < 5): self.first_displayed_playlist += 1
				self.update_playlists_list()

			if(c == ord('i')): #import
				self.do_import()
			if(c == ord('u')):
				self.update_tracks_db()
			if(c == ord('q')):
				break


def main(screen):
	db_import_worker = DBImportWorker.DBImportWorker()
	db_worker = DBWorker.DBWorker()
	yt_worker = YTWorker.YTWorker()
	#playlists = db_import_worker.get_playlists()

	main_worker = MainWorker(screen, yt_worker, db_worker, db_import_worker)
	main_worker.update_player_heading()
	main_worker.mainloop()
	#for i in range(1000):
	#	main_worker.set_player_progressbar(i)
	#	time.sleep(0.1)
	#print(playlists)
	#print(yt_worker.get_info("pTYIf2pkxzQ"))
	#yt_worker.get_audio("pTYIf2pkxzQ")

if(__name__ == "__main__"):
	curses.wrapper(main)