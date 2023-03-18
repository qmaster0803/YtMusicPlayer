import yt_dlp

class YTWorker:
	def __init__(self):
		options = {'format': 'm4a/bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}], 'outtmpl': '%(id)s.mp3', 'progress_hooks': [self.progress_hook], 'quiet': True, 'noprogress': True}
		self.client = yt_dlp.YoutubeDL(options)
	
	def get_info(self, video_id):
		data = self.client.extract_info(video_id, download=False)
		output = {}
		output["title"] = data["title"]
		output["album"] = data["album"]
		output["artist"] = data["artist"]
		output["preview"] = data["thumbnail"]
		output["release_year"] = data["release_year"]
		return output

	def get_audio(self, video_id):
		code = self.client.download(video_id)

	def progress_hook(self, data):
		print(data['status'], end=' ')
		try:
			print(data['downloaded_bytes'], end=' ')
		except:
			print('---', end=' ')
		try:
			print(data['total_bytes'], end=' ')
		except:
			print('---', end=' ')
		print()