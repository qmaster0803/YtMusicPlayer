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
		options_main = {'format': 'm4a/bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}], 'outtmpl': 'cache/%(id)s', 'progress_hooks': [self.progress_hook], 'quiet': True, 'logger': supLogger, 'noprogress': True}
		options_search = {'format': 'm4a/bestaudio/best', 'quiet': True, 'logger': supLogger, 'noprogress': True, 'extract_flat': True}
		self.client = yt_dlp.YoutubeDL(options_main)
		self.search = yt_dlp.YoutubeDL(options_search)

	def get_info(self, video_id):
		try:
			data = self.client.extract_info(video_id, download=False)
		except yt_dlp.utils.DownloadError as e:
			if(e.exc_info[0] == yt_dlp.utils.ExtractorError):        return {"error": "video_blocked"}
			if(e.exc_info[0] == yt_dlp.utils.urllib.error.URLError): return {"error": "no_network"}
		output = {"error": "ok"}
		output["title"] = data["title"]
		output["album"] = (data["album"] if ("album" in data and data['album']!=None) else "")
		output["artist"] = (data["artist"] if ("artist" in data and data['artist']!=None) else data['channel'])
		output["preview"] = data["thumbnail"]
		output["release_year"] = (data["release_year"] if ("release_year" in data and data['release_date']!=None) else data["upload_date"][:4])
		return output

	def get_audio(self, video_id):
		self.downloaded_bytes = None
		self.total_bytes = None
		self.download_status = None
		code = self.client.download(video_id)

	def progress_hook(self, data):
		self.downloaded_bytes = (data['downloaded_bytes'] if 'downloaded_bytes' in data else None)
		self.total_bytes = (data['total_bytes_estimate'] if 'total_bytes_estimate' in data else data['total_bytes'])
		self.downloaded_status = data['status']

	def get_search_results(self, query):
		#yt-dlp "ytsearch10:<query>" --get-id --get-title --flat-playlist
		data = self.search.extract_info("ytsearch100:"+str(query), download=False)
		res = [i['id'] for i in data['entries']]
		return res