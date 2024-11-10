import threading
import socket
import peer_setting
import Client
import TrackerGetRequestBuilder
import os
import time
import bcoding
import hashlib

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
    
    info = metainfo[b'info']
    
    return hashlib.sha1(bcoding.bencode(info)).hexdigest()

class ServerUploader(threading.Thread):
    def __init__(self, server, sock, addr):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.sock = sock
        self.addr = addr
        
    def run(self):
        #TODO Run when a peer requests to download a piece of file.
        
        pass

class ServerRegularAnouncer(threading.Thread):
    def __init__(self, peer_id, peer_ip, peer_port, metainfo, interval):
        threading.Thread.__init__(self, daemon=True)
        self.peer_id = peer_id
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.metainfo = metainfo
        self.interval = interval
    
    def run(self):
        #TODO Handle regular announcements to the tracker.
        #TODO Loop through all metainfos and send the announce request with "unspecified" event (no event field) to the tracker.
        #TODO Sleep for the interval time then repeat.
        pass

#? Run a thread to loop on behalf of the main thread to accept incoming connections.
class ServerConnectionLoopHandler(threading.Thread):
    def __init__(self, server):
        self.isRunning = True
        self.server = server
        threading.Thread.__init__(self, daemon=True)
        
        
    def run(self):
        while True:
            sock, addr = self.serverSocket.accept()
            uploader = ServerUploader(self.server, sock, addr)
            uploader.start()
            
    def stop(self):
        
        self.isRunning = False

class Server():
    def __init__(self):
        self.isRunning = True
        self.ip, self.port = GetHostIP()
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind((self.ip, self.port))
        
        print("Listening on: {}:{}".format(self.ip, self.port))
        
        self.serverSocket.listen(peer_setting.PEER_SERVER_MAX_CONNECTION)
        
        # Generate peerID on startup
        self.peerID = str(self.ip) + ":" + str(self.port) + time.strftime("%Y%m%d%H%M%S")
        
        self.StartupAnnouncer()
        
    def StartupAnnouncer(self):
        #TODO Loop through all locally available metainfos and send a "started" request for each.
        directory = os.fsencode(peer_setting.METAINFO_FILE_PATH)
        
        #? Common fields for all requests
        #! Example only
        startRequestBuilder = TrackerGetRequestBuilder.TrackerGetRequestBuilder()
        startRequestBuilder.SetPeerId(self.peerID)
        startRequestBuilder.SetPeerIP(self.ip)
        startRequestBuilder.SetPort(self.port)
        startRequestBuilder.SetEvent("started")
        
        for file in os.listdir(directory):
            #TODO Read the metainfo file and create a tracker get request.
            #TODO Please calculate and set the info_hash field too.
            info_hash = ""
            startRequestBuilder.SetInfoHash(info_hash)
            startRequest = bcoding.bencode(startRequestBuilder.Build())
            
            #TODO Send to the tracker to announce that the peer has started.                
    
    def Run(self):
        connectionLoopHandler = ServerConnectionLoopHandler(self)
        connectionLoopHandler.start()
        
        while self.isRunning:
            operation = input("Enter 'exit' to stop the server: ")
            if operation == 'exit':
                self.isRunning = False
        
        connectionLoopHandler.stop()
        connectionLoopHandler.join()
        
        self.serverSocket.close()


def Start():
    server = Server()
    server.Run()


