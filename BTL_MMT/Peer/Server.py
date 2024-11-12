import threading
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import socket
import peer_setting
import Client
import RequestBuilder as rb
import time
import bcoding
import hashlib
import BTL_MMT.Metainfo as mib
import global_setting
import PeerWireProtocol as pwp

def GetHostIP():
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
    def __init__(self, trackerIP, trackerPort, request):
        threading.Thread.__init__(self, daemon=True)
        self.server = GetServer()
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
        
        #? Add port to request after the connection is established
        self.request['port'] = sock.getsockname()[1]
        
        if (self.server.UniqueMapKey(self.trackerIP, self.trackerPort) in self.server.trackerIDMapping):
            self.request['tracker_id'] = self.server.trackerIDMapping[self.server.UniqueMapKey(self.trackerIP, self.trackerPort)]
                
        sock.sendall(bcoding.bencode(self.request.build()))
        
        #? Receive response from tracker
        response = sock.recv(global_setting.TRACKER_RESPONSE_SIZE)
        sock.close()
        
        #? Tracker_id from every response is stored
        response_decode = bcoding.bdecode(response)
        
        print("Regular announcement to tracker: {}:{}".format(self.trackerIP, self.trackerPort) + "for info_hash: " + response_decode['info_hash'])
        self.server.MapTrackerID(self.trackerIP, self.trackerPort, response_decode['tracker_id'])
        self.server.MapPeer(self.request['info_hash'], response_decode['peers'])
        
        #? Call callback if it exists
        if self.callback:
            self.callback(response)

#? Announce all trackers about the peer's existence.
class ServerRegularAnnouncer(threading.Thread):
    def __init__(self, peer_id, peer_ip, peer_port, interval):
        threading.Thread.__init__(self, daemon=True)
        self.peer_id = peer_id
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        
        self.interval = interval
    
    def run(self):
        #? Send start request to all trackers, runs once
        #? Only handle files already downloaded at startup, for newly uploaded files are handled in ClientUploader
        startRequest = rb.TrackerRequestBuilder()
        startRequest.SetPeerID(self.peer_id)
        startRequest.SetPort(self.peer_port)
        metainfos = mib.GetAll(peer_setting.METAINFO_FILE_PATH)
        for metainfo in metainfos:    

            info_hash = hashlib.sha1(metainfo['info']).hexdigest()       
            startRequest.SetInfoHash(info_hash)
            
            startRequest.SetUploaded(0)
            
            #TODO Change after local file mapping implementation
            startRequest.SetDownloaded(0)
            startRequest.SetLeft(0)
            
            startRequest.SetEvent('started')
            startRequest.SetTrackerId(None)        
                        
            request = startRequest.Build()
            
            for announce in metainfo['announce_list']:
                trackerIP = announce['ip']
                trackerPort = announce['port']
                
                requester = ServerRequester(trackerIP, trackerPort, request)
                
                requester.start()
        
        #? Regularly announce to all trackers, run every interval
        lastAnnounce = time.time()
        regularRequest = rb.TrackerRequestBuilder()
        regularRequest.SetPeerID(self.peer_id)
        regularRequest.SetPort(self.peer_port)
        while True:
            #? Check if the interval has passed
            if (time.time() - lastAnnounce < self.interval):
                continue
            
            #? Update metainfos
            metainfos = mib.GetAll(peer_setting.METAINFO_FILE_PATH)
            
            for metainfo in metainfos:
                info_hash = hashlib.sha1(metainfo['info']).hexdigest()
                tracker_id = self.server.trackerIDTable[info_hash]
                
                regularRequest.SetInfoHash(info_hash)
                regularRequest.SetTrackerId(tracker_id)
                
                #TODO Change after local file mapping implementation
                regularRequest.SetUploaded(0)
                regularRequest.SetDownloaded(0)
                regularRequest.SetLeft(0)
                
                regularRequest.SetEvent(None)
                regularRequest.SetCompact(True)
                
                request = regularRequest.Build()
                
                for announce in metainfo['announce_list']:
                    trackerIP = announce['ip']
                    trackerPort = announce['port']
                    
                    requester = ServerRequester(self.server, trackerIP, trackerPort, request)
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
        try:
            while True:
                data = self.sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
                if not data:
                    break
                
                #? Parse request from peer client
                request = bcoding.bdecode(data)
                
                if (request['type'] == pwp.Type.HANDSHAKE):
                    #? Received handshake, set info_hash and check local file
                    info_hash = request['info_hash']
                    file = info_hash + peer_setting.TEMP_DOWNLOAD_FILE_EXTENSION
                    
                    if os.path.exists(file):
                        response = pwp.Handshake('huh?', self.server.peerID)
                    else:
                        response = pwp.Handshake(request['info_hash'], self.server.peerID)
                        
                    self.sock.sendall(bcoding.bencode(response))
                elif (request['type'] == pwp.Type.BITFIELD):
                    #? Respond with bitfield
                    if (file == ""):
                        response = pwp.Handshake('huh?', self.server.peerID)
                    else:
                        response = pwp.Bitfield(pwp.GenerateBitfield(file))
                    
                    self.sock.sendall(bcoding.bencode(response))
                elif (request['type'] == pwp.Type.REQUEST):
                    #? Respond with piece
                    if (file == ""):
                        response = pwp.Handshake('huh?', self.server.peerID)
                        self.sock.sendall(bcoding.bencode(response))
                        continue
                    
                    index = request['index']
                    begin = request['begin']
                    length = request['length']
                    
                    with open(file, 'rb') as f:
                        f.seek(index * peer_setting.PIECE_SIZE + begin)
                        block = f.read(length)
                    
                    response = pwp.Piece(index, begin, block)
                    self.sock.sendall(bcoding.bencode(response))
                    
        except socket.timeout:
            print("Connection timeout for peer: " + self.addr[0] + ":" + str(self.addr[1]))
                    
            
#? Run a thread to loop on behalf of the main thread to accept incoming connections.
class ServerConnectionLoopHandler(threading.Thread):
    def __init__(self, server):
        self.isRunning = True
        self.server = server
        threading.Thread.__init__(self, daemon=True)    
        
    def start(self):
        print("ServerConnectionLoopHandler started.")
        #? Stop the loop when not isRunning during a socket timeout
        while self.isRunning:
            try:
                sock, addr = self.server.serverSocket.accept()
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
        self.ip, self.port = GetHostIP()
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.ip, self.port))
        
        self.serverSocket.settimeout(peer_setting.PEER_SERVER_TIMEOUT)
        
        print("Listening on: {}:{}".format(self.ip, self.port))
        
        self.serverSocket.listen(peer_setting.PEER_SERVER_MAX_CONNECTION)
        
        # Generate peerID on startup 
        self.peerID = str(self.ip) + ":" + str(self.port) + time.strftime("%Y%m%d%H%M%S")
        
        # Start regular announcer
        regularAnouncer = ServerRegularAnnouncer(self.peerID, self.ip, self.port, peer_setting.ANNOUNCE_INTERVAL)
        regularAnouncer.start()
        
        #? Store tracker_id for each info_hash
        self.trackerIDMapping = {}
        
        #? Store list of peers for each info_hash, consumed in ClientDownloader
        self.peerMapping = {}
    
    def Start(self):
        connectionLoopHandler = ServerConnectionLoopHandler(self)
        connectionLoopHandler.start()
        
        while self.isRunning:
            operation = input("Enter 'exit' to stop the server: ")
            if operation == 'exit':
                self.isRunning = False
        
        connectionLoopHandler.stop()
        connectionLoopHandler.join()
        
        self.serverSocket.close()
    
    def UniqueMapKey(self, ip, port):
        return ip + ":" + str(port)
    
    def MapTrackerID(self, tracker_ip, tracker_port, tracker_id):           
        print("Mapping tracker_id: " + tracker_id + " for tracker: " + tracker_ip + ":" + str(tracker_port))
        self.trackerIDMapping[self.UniqueMapKey(tracker_ip, tracker_port)] = tracker_id
    
    def MapPeer(self, info_hash, peerList):
        
        print("Mapping peer list for info_hash: " + info_hash)
        
        for peer in peerList:
            peer_id = peer['peer_id']
            ip = peer['ip']
            port = peer['port']
            
            key = self.UniqueMapKey(ip, port)
            
            if info_hash not in self.peerMapping:
                self.peerMapping[info_hash] = {}
            
            self.peerMapping[info_hash][key] = {
                'id': peer_id,
                'ip': ip,
                'port': port
            }
        
server = None
def Start():
    server = Server()
    server.Start()
    
def GetServer():
    return server


