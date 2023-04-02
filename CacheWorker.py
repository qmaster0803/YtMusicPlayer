class CacheWorker:
	def __init__(self, db_worker, yt_worker):
		self.db_worker = db_worker
		self.yt_worker = yt_worker

	def cache(self, video_id, MainWorker, local_db_worker=None):
		if(local_db_worker == None): local_db_worker = self.db_worker
		if(not local_db_worker.is_track_in_cache(video_id)):
			MainWorker.show_caching_sign()
			self.yt_worker.get_audio(video_id)
			local_db_worker.add_track_to_cache(video_id)
			MainWorker.close_caching_sign()
		else:
			local_db_worker.update_cache_used_time(video_id)