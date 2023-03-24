import yt_dlp

#used to suppress any output
class supLogger:
    def error(msg):
        pass
    def warning(msg):
        pass
    def debug(msg):
    	pass

class YTWorker:
	def __init__(self):
		options = {'format': 'm4a/bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}], 'outtmpl': '%(id)s.mp3', 'progress_hooks': [self.progress_hook], 'quiet': True, 'logger': supLogger, 'noprogress': True}
		self.client = yt_dlp.YoutubeDL(options)
	
	def get_info(self, video_id):
		try:
			data = self.client.extract_info(video_id, download=False)
		except yt_dlp.utils.DownloadError:
			return None
		output = {}
		output["title"] = data["title"]
		output["album"] = (data["album"] if ("album" in data and data['album']!=None) else "")
		output["artist"] = (data["artist"] if ("artist" in data and data['artist']!=None) else data['channel'])
		output["preview"] = data["thumbnail"]
		output["release_year"] = (data["release_year"] if ("release_year" in data and data['release_date']!=None) else data["upload_date"][:4])
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