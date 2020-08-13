import aiohttp
import asyncio
import pickle 
import json
from aiohttp import web
from collections import OrderedDict

async def fetch(client, json_data):
	json_data = {"sourcetype": "_json", "event": json_data}
	async with client.post('https://172.16.99.26:8088/services/collector', headers = {'Authorization': 'Splunk 80f70e07-c027-40c8-89c7-97209ac01ca2'}, json = json_data, verify_ssl=False) as resp:
		return await resp.text()

async def put_hello(request):
	data = pickle.loads(await request.read())
	cookies = request.cookies

	if cookies['client_type'] == 'unicast_inter_client' and cookies['type'] == 'packets_missed':
		json_data = json.dumps(OrderedDict(
			client_type=cookies['client_type'], 
			issue_type=cookies['type'], 
			server=request.remote, 
			client=data[0],
			port=data[1],
			packets_missed=data[2],
			missed_packets_count=data[3],
			last_successful=data[4], 
			packet_data=data[5],
			timedelta=data[6]))
	
	elif cookies['client_type'] == 'unicast_inter_client' and cookies['type'] == 'packets_dup':
		json_data = json.dumps(OrderedDict(
			client_type=cookies['client_type'], 
			issue_type=cookies['type'], 
			server=request.remote, 
			client=data[0],
			port=data[1], 
			duplicated_packet=data[2], 
			packet_info=data[3]))

	async with aiohttp.ClientSession() as client:
		html = await fetch(client, json_data)

	return web.Response(text="OK!")

def Collector():

	app = web.Application()
	app.add_routes([web.put('/', put_hello)])
	web.run_app(app, port=8082)

def main():
	Collector()

if __name__ == '__main__':
	main()