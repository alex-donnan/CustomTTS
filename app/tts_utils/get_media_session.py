import winsdk.windows.media.control as wmc

async def get_media_session():
	sessions = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
	session = sessions.get_current_session()
	return session