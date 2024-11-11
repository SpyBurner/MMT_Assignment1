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

def GetInfoHash(metainfoPath):
    metainfo = bcoding.bdecode(open(metainfoPath, 'rb').read())
    info = metainfo['info']
    return hashlib.sha1(bcoding.bencode(info)).hexdigest()

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
        #? Send request to tracker
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.trackerIP, self.trackerPort))
        
        #? Add port to request after the connection is established
        self.request['port'] = self.server.port
        
        sock.sendall(bcoding.bencode(self.request))
        
        #? Receive response from tracker
        response = sock.recv(peer_setting.PEER_SERVER_MAX_RESPONSE_SIZE)
        sock.close()
        
        #? Store info_hash for each tracker_id
        
        response_decode = bcoding.bdecode(response)
        self.server.AddTrackerID(self.trackerIP, self.trackerPort, response_decode['tracker_id'])
        
        
        #? Call callback if it exists
        if self.callback:
            self.callback(response)

#? Announce all trackers about the peer's existence.
class ServerRegularAnnouncer(threading.Thread):
    def __init__(self, server, peer_id, peer_ip, peer_port, interval):
        threading.Thread.__init__(self, daemon=True)
        self.server = server;
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
            metainfo_decode = bcoding.bdecode(open(metainfo, 'rb'))

            info_hash = hashlib.sha1(metainfo_decode['info']).hexdigest()       
            startRequest.SetInfoHash(info_hash)
            
            startRequest.SetUploaded(0)
            
            #TODO Change after local file mapping implementation
            startRequest.SetDownloaded(0)
            startRequest.SetLeft(0)
            
            startRequest.SetEvent('started')
            startRequest.SetCompact(True)
            startRequest.SetTrackerId(None)        
                        
            request = startRequest.Build()
            
            for announce in metainfo['announce_list']:
                trackerIP = announce['ip']
                trackerPort = announce['port']
                
                requester = ServerRequester(self.server, trackerIP, trackerPort, request)
                
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
                metainfo_decode = bcoding.bdecode(open(metainfo, 'rb'))
                info_hash = hashlib.sha1(metainfo_decode['info']).hexdigest()
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
    def __init__(self, server, sock, addr):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.sock = sock
        self.addr = addr
        
    def run(self):
        # TODO Receive request from peer client and respond with the right piece
        #? Receive request from peer client
        request = self.sock.recv(peer_setting.PEER_CLIENT_MAX_REQUEST_SIZE)
        
        pass

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
                uploader = ServerUploader(self.server, sock, addr)
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
        regularAnouncer = ServerRegularAnnouncer(self, self.peerID, self.ip, self.port, peer_setting.ANNOUNCE_INTERVAL)
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
    
    def AddTrackerID(self, tracker_ip, tracker_port, tracker_id):            
        self.trackerIDMapping[(tracker_ip, tracker_port)] = tracker_id
        
    def AddPeerMapping(self, info_hash, peer):
        if info_hash not in self.peerMapping:
            self.peerMapping[info_hash] = []
        self.peerMapping[info_hash].append(peer)

server = None
def Start():
    server = Server()
    server.Start()
    
def GetServer():
    if (server == None):
        print ("Server not started.")
    return server


