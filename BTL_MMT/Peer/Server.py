import argparse
import threading
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import socket
import peer_setting
import Client
import BTL_MMT.TrackerProtocol as tp
import time
import bcoding
import hashlib
import BTL_MMT.Metainfo as mib
import global_setting
import PeerWireProtocol as pwp
import math

def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8',1))
        ip = s.getsockname()[0]
        port = s.getsockname()[1]
    except Exception:
        ip = 'localhost'
        port = peer_setting.PEER_SERVER_DEFAULT_PORT
    finally:
        s.close()
    return (ip, port)

class ServerRequester(threading.Thread):
    def __init__(self, server, trackerIP, trackerPort, request):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.trackerIP = trackerIP
        self.trackerPort = trackerPort
        self.request = request
        
        self.callback = None
    
    def SetCallback(self, callback):
        self.callback = callback
    
    def run(self):
        if (self.server == None):
            print("Server not started at ServerRequester.")
            return
        #? Send request to tracker
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.trackerIP, self.trackerPort))
        
        if (self.server.unique_map_key(self.trackerIP, self.trackerPort) in self.server.trackerIDMapping):
            self.request.set_tracker_id(self.server.trackerIDMapping[self.server.unique_map_key(self.trackerIP, self.trackerPort)])
                
        builtRequest = self.request.build()
        
        # print(builtRequest)
                
        sock.sendall(bcoding.bencode(builtRequest))
        
        #? Receive response from tracker
        response = sock.recv(global_setting.TRACKER_RESPONSE_SIZE)
        sock.close()
        
        # print(response.decode())
        
        #? Tracker_id from every response is stored
        response_decode = bcoding.bdecode(response)
        
        if ('failure_reason' in response_decode):
            print("[Failure reason] " + response_decode['failure_reason'])
            print("[Request] ", builtRequest)
            return
        
        # print(response_decode)
        
        # print("[Regular announcement] To tracker: {}:{}".format(self.trackerIP, self.trackerPort) + " for info_hash: " + builtRequest['info_hash'])

        if ('tracker_id' in response_decode):        
            self.server.map_tracker_id(self.trackerIP, self.trackerPort, response_decode['tracker_id'])
        self.server.map_peer(builtRequest['info_hash'], response_decode['peers'])
        
        #? Call callback if it exists
        if self.callback:
            self.callback(response)

#? Announce all trackers about the peer's existence.
class ServerRegularAnnouncer(threading.Thread):
    def __init__(self, server, peer_id, peer_ip, peer_port, interval):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.peer_id = peer_id
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        
        self.interval = interval
    
    def run(self):
        #? Send start request to all trackers, runs once
        startRequest = tp.TrackerRequestBuilder()
        startRequest.set_peer_id(self.peer_id)
        startRequest.set_port(self.peer_port)
        metainfos = mib.get_all(peer_setting.METAINFO_FILE_PATH)
        if len(metainfos) == 0:
            print("No metainfo found.")
        else: 
            for metainfo in metainfos:
                
                info_hash = hashlib.sha1(bcoding.bencode(metainfo['info'])).hexdigest()       
                startRequest.set_info_hash(info_hash)
                startRequest.set_port(self.peer_port)
                
                startRequest.set_uploaded(0)
                
                #TODO Change after local file mapping implementation
                startRequest.set_downloaded(0)
                startRequest.set_left(0)
                
                startRequest.set_event('started')
                startRequest.set_tracker_id(None)       
                
                for i in range(len(metainfo['announce_list'])):
                    announce = metainfo['announce_list'][i]
                    trackerIP = announce['ip']
                    trackerPort = announce['port']
                    
                    requester = ServerRequester(self.server, trackerIP, trackerPort, startRequest)
                    
                    requester.start()
            
        #? Regularly announce to all trackers, run every interval
        lastAnnounce = time.time()
        regularRequest = tp.TrackerRequestBuilder()
        regularRequest.set_peer_id(self.peer_id)
        regularRequest.set_port(self.peer_port)
        while True:
            #? Check if the interval has passed
            if (time.time() - lastAnnounce < self.interval):
                continue
            
            lastAnnounce = time.time()
            
            #? Update new metainfos
            metainfos = mib.get_all(peer_setting.METAINFO_FILE_PATH)
            
            if len(metainfos) == 0:
                continue
            
            for metainfo in metainfos:
                info_hash = hashlib.sha1(bcoding.bencode(metainfo['info'])).hexdigest()
                
                regularRequest.set_info_hash(info_hash)
                regularRequest.set_port(self.peer_port)
                
                #TODO Change after local file mapping implementation
                regularRequest.set_uploaded(0)
                regularRequest.set_downloaded(0)
                regularRequest.set_left(0)
                
                regularRequest.set_event(None)
                
                for announce in metainfo['announce_list']:
                    trackerIP = announce['ip']
                    trackerPort = announce['port']
                    trackerID = self.server.trackerIDMapping[self.server.unique_map_key(trackerIP, trackerPort)]
                    
                    regularRequest.set_tracker_id(trackerID)
                    
                    requester = ServerRequester(self.server, trackerIP, trackerPort, regularRequest)
                    requester.start()
        
class ServerUploader(threading.Thread):
    def __init__(self, server, sock, addr, timeout=peer_setting.PEER_CLIENT_CONNECTION_TIMEOUT):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.sock = sock
        self.addr = addr
        self.timeout = timeout
        
    def run(self):
        # TODO Receive request from peer client and respond
        self.sock.settimeout(self.timeout)     
        info_hash = ""   
        file  = ""
        metainfo = None
        pieces = None
        file_read = b''
        is_file_read = False
        try:
            while True:
                print("Waiting for data from peer: " + self.addr[0] + ":" + str(self.addr[1]))
                data = self.sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
                if not data:
                    break
                
                #? Parse request from peer client
                request = bcoding.bdecode(data)
                
                if (request['type'] == pwp.Type.HANDSHAKE):
                    #? Received handshake, set info_hash and check local file
                    
                    print('Received handshake from: ' + self.addr[0] + ":" + str(self.addr[1]))
                    print('Info hash: ' + request['info_hash'])
                    
                    info_hash = request['info_hash']
                    try: 
                        metainfo = mib.Get(os.path.join(peer_setting.METAINFO_FILE_PATH, info_hash + global_setting.METAINFO_FILE_EXTENSION))
                        print("Metainfo found for info_hash: " + info_hash)
                    except FileNotFoundError:
                        print("Metainfo not found for info_hash: " + info_hash)
                        self.sock.close()
                        return
                    
                    print("Found metainfo: ", metainfo)
                    
                    pieceLength = metainfo['info']['piece length']
                    pieces = metainfo['info']['pieces']
                    totalLength = 0
                    
                    #? Get totalLength in either file mode
                    if (len(metainfo['info']['files']) == 0):
                        isSingleFile = True
                        totalLength = metainfo['info']['length']
                    else:
                        isSingleFile = False
                        for file in metainfo['info']['files']:
                            totalLength += file['length']
                    
                    pieceCount = math.ceil(totalLength / pieceLength)
                    
                    print('File details: ' + str(pieceLength) + ", " + str(totalLength) + ", " + str(pieceCount))
                    
                    print("Piece count: " + str(pieceCount))
                    
                    print("Files in repo: " + str(os.listdir(peer_setting.REPO_FILE_PATH)))
                    
                    file = os.path.join('./',peer_setting.REPO_FILE_PATH, info_hash)
                    
                    if not os.path.exists(file):
                        response = pwp.handshake('huh?', self.server.peerID)
                        print("File not found for info_hash: " + file)
                    else:
                        response = pwp.handshake(request['info_hash'], self.server.peerID)
                        print("File found for info_hash: " + file + ", handshake sent.")
                        
                    self.sock.sendall(bcoding.bencode(response))
                elif (request['type'] == pwp.Type.BITFIELD):
                    print('Received bitfield: ', request)
                    
                    #? Respond with bitfield
                    if (file == ""):
                        response = pwp.handshake('huh?', self.server.peerID)
                    else:
                        response = pwp.bitfield(pwp.generate_bitfield(filePath=file, pieceCount=pieceCount, pieceLength=pieceLength, pieces=pieces))
                    
                    print("Bitfield response: ", response)
                    
                    self.sock.sendall(bcoding.bencode(response))
                elif (request['type'] == pwp.Type.REQUEST):
                    print('Received request: ', request)
                    
                    #? Respond with piece
                    if (file == ""):
                        response = pwp.handshake('huh?', self.server.peerID)
                        self.sock.sendall(bcoding.bencode(response))
                        continue
                    
                    index = request['index']
                    begin = request['begin']
                    length = request['length']
                    
                    # read only once
                    if (not is_file_read):
                        is_file_read = True
                        file_read += pwp.get_data_from_path(file)
                    
                    block = file_read[index * pieceLength + begin : index * pieceLength + begin + length]
                                        
                    response = pwp.piece(index, begin, block.decode("utf-8"))
                    
                    print('Piece response')
                    
                    self.sock.sendall(bcoding.bencode(response))
                
                elif (request['type'] == pwp.Type.KEEP_ALIVE):
                    pass
        except socket.timeout:
            print("Connection timeout for peer: " + self.addr[0] + ":" + str(self.addr[1]))
                    
#? Run a thread to loop on behalf of the main thread to accept incoming connections.
class ServerConnectionLoopHandler(threading.Thread):
    def __init__(self, server):
        self.isRunning = True
        self.server = server
        threading.Thread.__init__(self, daemon=True)    
        
    def run(self):
        print("ServerConnectionLoopHandler started.")
        #? Stop the loop when not isRunning during a socket timeout
        while self.isRunning:
            try:
                sock, addr = self.server.serverSocket.accept()
                print("Accepted connection from: " + addr[0] + ":" + str(addr[1]))
                uploader = ServerUploader(self.server, sock, addr, peer_setting.PEER_CLIENT_CONNECTION_TIMEOUT)
                uploader.start()
            except socket.timeout:
                pass
            
    def stop(self):
        self.isRunning = False
        
        #? Fake client to break the serverSocket.accept() loop
        fake_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        fake_client.connect((self.server.ip, self.server.port))
        fake_client.close()
        
class Server():
    def __init__(self):
        self.isRunning = True
        self.ip, self.port = get_host_ip()
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.ip, self.port))
        
        self.serverSocket.settimeout(peer_setting.PEER_SERVER_TIMEOUT)
        
        print("Listening on: {}:{}".format(self.ip, self.port))
        
        self.serverSocket.listen(peer_setting.PEER_SERVER_MAX_CONNECTION)
        
        # Generate peerID on startup 
        self.peerID = str(self.ip) + ":" + str(self.port) + time.strftime("%Y%m%d%H%M%S")
        
        # Start regular announcer
        regularAnnouncer = ServerRegularAnnouncer(self, self.peerID, self.ip, self.port, peer_setting.ANNOUNCE_INTERVAL)
        regularAnnouncer.start()
        
        #? Store tracker_id for each info_hash
        self.trackerIDMapping = {}
        
        #? Store list of peers for each info_hash, consumed in ClientDownloader
        self.peerMapping = {}
    
    def start(self):
        connectionLoopHandler = ServerConnectionLoopHandler(self)
        connectionLoopHandler.start()
        
        parser = argparse.ArgumentParser(prog='Server_cli', description='Server CLI for Peer-to-Peer Transmission tasks')
        subparsers = parser.add_subparsers(dest='operation', help='Choose an operation')

        # Clear task
        clear_parser = subparsers.add_parser('clear', help='Clear console')

        # Exit task
        exit_parser = subparsers.add_parser('exit', help='Stop the server')

        # Upload task
        upload_parser = subparsers.add_parser('upload', help='Upload a file')
        upload_parser.add_argument('--filePath', '-f', type=str, required=True, help='Path to the file to upload')
        upload_parser.add_argument('--tracker', '-t', type=str, action='append', nargs=2, metavar=('IP', 'PORT'), required=True, help='Tracker IP and port')

        # Download task
        download_parser = subparsers.add_parser('download', help='Download a file')
        download_parser.add_argument('--metainfo', '-m', type=str, required=True, help='Path to the metainfo file')

        parser.print_usage();
        while self.isRunning:
            
            # Parse the input
            operation = input("Enter operation: ")
            try:
                args = parser.parse_args(operation.split())
            except:
                continue
            if (args.operation == 'clear'):
                os.system('cls' if os.name == 'nt' else 'clear')
            elif args.operation == 'exit':
                self.isRunning = False
            elif args.operation == 'upload':
                filePath = args.filePath
                trackers = args.tracker
                tracker_list = [[ip, int(port)] for ip, port in trackers]
                Client.upload(filePath, tracker_list)
            elif args.operation == 'download':
                metainfo = args.metainfo
                Client.download(metainfo)
        
        connectionLoopHandler.stop()
        connectionLoopHandler.join()
        
        self.serverSocket.close()
    
    def unique_map_key(self, ip, port):
        return ip + ":" + str(port)
    
    def map_tracker_id(self, tracker_ip, tracker_port, tracker_id):           
        # print("[Mapping tracker_id] " + tracker_id + " for tracker: " + tracker_ip + ":" + str(tracker_port))
        self.trackerIDMapping[self.unique_map_key(tracker_ip, tracker_port)] = tracker_id
    
    def map_peer(self, info_hash, peerList):
        # print("[Mapping peer list] For info_hash: " + info_hash)
        self.peerMapping[info_hash] = []
        for peer in peerList:
            peer_id = peer['peer_id']
            ip = peer['ip']
            port = peer['port']
            
            # if info_hash not in self.peerMapping:
            self.peerMapping[info_hash].append({
                'peer_id': peer_id,
                'ip': ip,
                'port': port
            })
        
server = None
def start():
    global server
    server = Server()
    server.start()
    
def get_server():
    return server


