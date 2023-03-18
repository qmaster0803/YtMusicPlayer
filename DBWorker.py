import sqlite3

class DBWorker:
	def __init__(self):
		self.db = sqlite3.connect("main.db")