import threading
import socket
import peer_setting
import Client
import BTL_MMT.RequestBuilder as rb
import os
import time
import bcoding
import hashlib
import MetainfoBrowser as mib

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

#? Announce all trackers about the peer's existence.
class ServerRegularAnouncer(threading.Thread):
    def __init__(self, peer_id, peer_ip, peer_port, interval):
        threading.Thread.__init__(self, daemon=True)
        self.peer_id = peer_id
        self.peer_ip = peer_ip
        self.peer_port = peer_port
        self.interval = interval
    
    def run(self):
        #TODO Send start
        metainfos = mib.GetAll(peer_setting.METAINFO_FILE_PATH)
        
        for metainfo in metainfos:
            startRequest = rb.TrackerRequestBuilder()
            
            startRequest.SetPeerID(self.peer_id)
            startRequest.SetPeerIp
            
            info_hash = hashlib.sha1(bcoding.bencode(metainfo['info'])).hexdigest()       
            startRequest.SetInfoHash(info_hash)
                            
        
        #TODO Then send unspecified for every interval
        
        pass

class ServerUploader(threading.Thread):
    def __init__(self, server, sock, addr):
        threading.Thread.__init__(self, daemon=True)
        self.server = server
        self.sock = sock
        self.addr = addr
        
    def run(self):
        #TODO Run when a peer requests to download a piece of file.
        
        pass

#? Run a thread to loop on behalf of the main thread to accept incoming connections.
class ServerConnectionLoopHandler(threading.Thread):
    def __init__(self, server):
        self.isRunning = True
        self.server = server
        threading.Thread.__init__(self, daemon=True)
        
        
    def start(self):
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
        
        self.serverSocket.timeout = peer_setting.PEER_SERVER_TIMEOUT
        
        print("Listening on: {}:{}".format(self.ip, self.port))
        
        self.serverSocket.listen(peer_setting.PEER_SERVER_MAX_CONNECTION)
        
        # Generate peerID on startup 
        self.peerID = str(self.ip) + ":" + str(self.port) + time.strftime("%Y%m%d%H%M%S")
        
        # Start regular announcer
        regularAnouncer = ServerRegularAnouncer(self.peerID, self.ip, self.port, peer_setting.PEER_SERVER_ANNOUNCE_INTERVAL)
        regularAnouncer.start()
    
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

def Start():
    server = Server()
    server.Start()


