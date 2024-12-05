from hashlib import sha1
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import threading
import time
import socket
from tracker_setting import *
from bcoding import bencode, bdecode
from TrackerProtocol import *
import secrets

import copy
class TrackerDB():
    def __init__(self):
        self.swarm = {}
        
    def add(self, info_hash, peer_id, ip, port, tracker_id, seeder=False):
        if info_hash not in self.swarm:
            self.swarm[info_hash] = {}
              
        newPeer = {
            'peer_id': peer_id,
            'ip': ip,
            'port': port,
            'seeder': seeder,
            'last_announce': time.time()
        }
        self.swarm[info_hash][tracker_id] = newPeer
    
    def finish_download(self, info_hash, tracker_id):
        if info_hash not in self.swarm:
            raise Exception("Swarm not found")
        
        if tracker_id not in self.swarm[info_hash]:
            raise Exception("Peer not in swarm")
        self.swarm[info_hash][tracker_id]['seeder'] = True
        
    def update_status(self, info_hash, tracker_id):
        if info_hash not in self.swarm:
            raise Exception("Swarm not found")
        
        if tracker_id not in self.swarm[info_hash]:
            raise Exception("Peer not in swarm")
        self.swarm[info_hash][tracker_id]['last_announce'] = time.time()
            
    def delete(self, info_hash, tracker_id):
        if tracker_id not in self.swarm[info_hash]:
            raise Exception("Peer not in swarm")
        del self.swarm[info_hash][tracker_id]
            
    def get_peer_list(self, info_hash):
        peer_list = [
            {'peer_id': peer['peer_id'], 'ip': peer['ip'], 'port': peer['port']}
            for peer in self.swarm[info_hash].values()
        ]
        return peer_list
                    
    def generate_tracker_id(self):
        return secrets.token_hex(16)
    
class Tracker():
    def __init__(self, port):
        self.db = TrackerDB()
        self.host = get_host_default_interface_ip()
        self.port = port
        
    def check_timeout(self):
        while True:
            #? Clone self.db.swarm before altering
            dbSwarmClone = copy.deepcopy(self.db.swarm)
            
            for info_hash in dbSwarmClone:
                for peer in dbSwarmClone[info_hash]:
                    if time.time() - dbSwarmClone[info_hash][peer]['last_announce'] > TIMEOUT_PER_SWARM:
                        self.db.delete(info_hash, peer)
            time.sleep(TRACKER_INTERVAL)
            
    def require_fields(self, request, fields):
        for field in fields:
            if request.get(field) is None:
                raise Exception(f"'{field}' value is required")
        
    def handle_request(self, sock, addr):
        try:
            data = sock.recv(1024)
            if data:
                response = TrackerResponseBuilder()
                request = bdecode(data)
                
                self.require_fields(request, ['info_hash'])
                    
                event = request.get("event") # None if not found
                
                tracker_id = None
                # peer wanna join the swarm
                if event == RequestEvent.STARTED:
                    tracker_id = self.db.generate_tracker_id()
                    response.SetTrackerId(tracker_id)
                    
                    self.require_fields(request, ['peer_id', 'port', 'left'])
                    left = request["left"]
                    if left == 0:
                        # peer already has the file
                        self.db.add(request["info_hash"], request["peer_id"], addr[0], request["port"], tracker_id, seeder=True)
                    elif left > 0:
                        # peer want to download the file
                        self.db.add(request["info_hash"], request["peer_id"], addr[0], request["port"], tracker_id)
                    else:
                        raise Exception("Invalid 'left' value")
                else:
                    self.require_fields(request, ['tracker_id'])
                    tracker_id = request["tracker_id"]
                    # peer wanna leave the swarm
                    if event == RequestEvent.STOPPED:
                        self.db.delete(request["info_hash"], request["tracker_id"])
                    # peer completed the download
                    elif event == RequestEvent.COMPLETED:
                        self.db.finish_download(request["info_hash"], request["tracker_id"])
                
                self.db.update_status(request['info_hash'], tracker_id)
                response.SetPeers(self.db.get_peer_list(request["info_hash"]))
                    
        except Exception as e:
            response.SetFailureReason(str(e))
            raise e
        finally:
            sock.sendall(bencode(response.Build()))
            sock.close()
            print(f"[DISCONNECTED] {addr} disconnected.")
    
    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"[LISTENING] Server is listening on {self.host}:{self.port}")
        
        # start checker thread
        checker_thread = threading.Thread(target=self.check_timeout)
        checker_thread.start()
        
        while True:
            client_socket, addr = server_socket.accept()
            print(f"[CONNECTION] Accepted connection from {addr}")
            client_thread = threading.Thread(target=self.handle_request, args=(client_socket, addr))
            client_thread.start()
            
            # print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}") # -1 because the main thread is also counted as a thread
        
def start():
    tracker = Tracker(TRACKER_DEFAULT_PORT)
    tracker.start()

def stat(self):
    print("Tracker Stats")
        
def list(self):
    print("List Files in Tracker")
    
    
def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '192.168.56.106'
    finally:
       s.close()
    return ip