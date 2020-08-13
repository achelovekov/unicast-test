import socket
import struct
import textwrap
import datetime
from time import sleep
import redis
import sys
import pickle
import re
import aiohttp
import asyncio
import argparse
import yaml
import netifaces

def get_mac_addr(addr):
	bytes_str = map('{:02x}'.format, addr)
	return ':'.join(bytes_str).upper()

def ipv4(addr):
	return '.'.join(map(str, addr))

def ethernet_frame(data):
	dst_mac, src_mac, proto = struct.unpack('! 6s 6s H', data[:14])
	return get_mac_addr(dst_mac), get_mac_addr(src_mac), socket.htons(proto), data[14:]

def ipv4_packet(data):
	version_header_length = data[0]
	version = version_header_length >> 4
	header_length = (version_header_length & 15) * 4

	ttl, proto, src, dst = struct.unpack('! 8x B B 2x 4s 4s', data[:20])

	return version, header_length, ttl, proto, ipv4(src), ipv4(dst), data[header_length:]

def icmp_packet(data):
	icmp_type, code, checksum = struct.unpack('! B B H', data[:4])
	return icmp_type, code, checksum, data[4:]

def elapsed_ms(timedelta):
	return (timedelta.days * 86400000) + (timedelta.seconds * 1000) + (timedelta.microseconds / 1000)

async def put(url,data, cookies):
	async with aiohttp.ClientSession(cookies=cookies) as session:
		async with session.put(url, data=data) as response:
			return await response.read() 

async def worker(r, ipv4_src, icmp_type, code, checksum, data):
	
	current_number = pickle.loads(r.get('unicast_intra_current_number'))
	count = r.get('unicast_intra_count')
	timestamps = pickle.loads(r.get('unicast_intra_timestamps'))
	last_successful = pickle.loads(r.get('unicast_intra_last_successful'))

	if icmp_type == 8 and int(count.decode('utf-8')) != 0:
		packet_data = data.decode('utf-8')
		packet_number = int(re.search(r'\d+',packet_data).group(0))
		if packet_number != current_number + 1 and packet_number != current_number:
			timestamps[0] = timestamps[1]
			timestamps[1] = datetime.datetime.now()
			delta = elapsed_ms(timestamps[1] - timestamps[0])
			data = pickle.dumps([ipv4_src, [i for i in range(current_number+1,packet_number)], last_successful, delta])
			await put("http://172.16.99.25:8081", data, {'client_type': 'unicast_intra_client', 'type': 'packets_missed'})
		elif packet_number == current_number:
			data = pickle.dumps([ipv4_src, packet_number, last_successful])
			await put("http://172.16.99.25:8081", data, {'client_type': 'unicast_intra_client', 'type': 'packets_dup'})

		current_number = packet_number
		last_successful = packet_data
		timestamps[0] = timestamps[1]						
		timestamps[1] = datetime.datetime.now()

		r.set('unicast_intra_current_number', pickle.dumps(current_number))
		r.set('unicast_intra_last_successful', pickle.dumps(last_successful))
		r.set('unicast_intra_timestamps', pickle.dumps(timestamps))
		r.incr('unicast_intra_count')

	elif icmp_type == 8:
		r.incr('unicast_intra_count')
		timestamps[1] = datetime.datetime.now()
		r.set('unicast_intra_timestamps', pickle.dumps(timestamps))

def args_parser():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--interface', dest='interface', required=True, help='interface name to bind')
	parser.add_argument('-f', '--file', dest='file', required=True, help='clients yml file')
	args = parser.parse_args()

	return args

def initialize(args):
	with open(args.file, 'r') as stream:
		try:
			config = yaml.safe_load(stream)
		except yaml.YAMLError as e:
			print(e)

	clients = {}
	interfaces = [ ip for ip in config['interfaces']]
	db_num = 0

	for client_ip in config['clients']:
		clients[client_ip] = [ db_num, redis.Redis(db = db_num) ]
		clients[client_ip][1].set('unicast_intra_addr', pickle.dumps(client_ip))
		clients[client_ip][1].set('unicast_intra_current_number', pickle.dumps(0))
		clients[client_ip][1].set('unicast_intra_count', 0)
		clients[client_ip][1].set('unicast_intra_timestamps', pickle.dumps([0 for i in range(0,2)]))
		clients[client_ip][1].set('unicast_intra_last_successful', pickle.dumps(0))
		db_num += 1

	return interfaces, clients

async def main(args):

	try:
		conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(3))
		conn.bind((args.interface, 0))
		interfaces, clients = initialize(args)

		while True:
			raw_data, addr = conn.recvfrom(65536)
			dst_mac, src_mac, proto, data = ethernet_frame(raw_data)

			if proto == 8 and iface_mac == dst_mac:
				version, header_length, ttl, proto, ipv4_src, ipv4_dst, data = ipv4_packet(data)

				if proto == 1 and ipv4_src in clients and ipv4_dst in interfaces:
					icmp_type, code, checksum, data = icmp_packet(data)
					print(data)
					await worker(clients[ipv4_src][1], ipv4_src, icmp_type, code, checksum, data)

	except KeyboardInterrupt:
		print('Exit..')
		for client, db in clients.items():
			db[1].flushdb()
		sys.exit()
					
if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	args = args_parser()
	coroutines = [main(args)]
	results = loop.run_until_complete(asyncio.gather(*coroutines))
	