import asyncio
import torch.multiprocessing as mp
import websockets

class ttsWebsocket:
	def __init__(self, host: str = 'localhost', port: int = 1515):
		self.host = host
		self.port = port
		self.server = None
		self.current_speaker = 'none'

	 # Frontend WebSocket service
	async def handler(self, server):
		while True:
			try:
				client_message = await server.recv()
			except websockets.ConnectionClosed:
				print(f"Websocket server connection terminated")
				break

			response = None
			if client_message == "Connect":
				response = "Connected"
				print("Client connected, sending connection response.")
			if client_message.split(':')[0] == "Speaker" and client_message.split(':')[1] != self.current_speaker:
				response = f"Speaker:{self.current_speaker}"
				print(f"Client speaker update: {response}")
			
			if response:
				try:
					await server.send(response)
				except websockets.ConnectionClosed:
					print("Websocket server connection terminated")
					break

	async def start(self):
		print("Starting websocket server")
		self.server = await websockets.serve(self.handler, self.host, self.port)
		await self.server.serve_forever()

	async def stop(self):
		if self.server:
			self.server.close()
			await self.server.wait_closed()
