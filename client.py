import socket
from time import sleep
from datetime import datetime
import argparse
from multiprocessing.connection import Listener
import sys
from scapy.all import *

parser = argparse.ArgumentParser()

parser.add_argument('-s', '--server', dest='srv_host', required=True, help='Server ip address')
parser.add_argument('-i', '--interval', dest='interval', required=True, help='Time interval', type=float)
parser.add_argument('-e', '--ethernet', dest='interface', required=True, help='Interface name')
parser.add_argument('-q', '--qos', dest='dscp', help='DSCP Marking (af11, ef, etc..)')

args = parser.parse_args()

if args.dscp == 'cs1':
	tos = 32
elif args.dscp == 'af11':
	tos = 40
elif args.dscp == 'af12':
	tos = 48
elif args.dscp == 'af13':
	tos = 56
elif args.dscp == 'af21':
	tos = 72
elif args.dscp == 'af22':
	tos = 80
elif args.dscp == 'af23':
	tos = 88
elif args.dscp == 'cs3':
	tos = 96
elif args.dscp == 'af31':
	tos = 104
elif args.dscp == 'af32':
	tos = 112
elif args.dscp == 'af33':
	tos = 120
elif args.dscp == 'cs4':
	tos = 128
elif args.dscp == 'af41':
	tos = 136
elif args.dscp == 'af42':
	tos = 144
elif args.dscp == 'af43':
	tos = 152
elif args.dscp == 'cs5':
	tos = 160
elif args.dscp == 'ef':
	tos = 184
elif args.dscp == 'cs6':
	tos = 192
elif args.dscp == 'cs7':
	tos = 224
else:
	tos = 0

srv_port = 12000

client_ports = [ i for i in range(53530,53534)]

i = 0

while True:
	current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
	msg = ('Packet #{0} sent at {1}'.format(i, current_time))
	sendp(Ether()/
		IP(dst=args.srv_host,tos=tos)/
		UDP(sport=client_ports, dport=srv_port)/
		msg,
		iface=args.interface, 
		verbose=0)
	i += 1
	sleep(args.interval)