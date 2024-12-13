from hashlib import sha1
import sys
import os


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import global_setting
import threading
import time
import socket
from tracker_setting import *
from bcoding import bencode, bdecode
from TrackerProtocol import *
import secrets

import copy

db_lock = threading.Lock()
class TrackerDB():
    def __init__(self):
        self.swarm = {}
        
    def add(self, info_hash, peer_id, ip, port, tracker_id, seeder=False):
        db_lock.acquire()
        
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
        
        db_lock.release()
    
    def finish_download(self, info_hash, tracker_id):
        db_lock.acquire()
        if info_hash not in self.swarm:
            db_lock.release()
            raise Exception("Swarm not found")
        
        if tracker_id not in self.swarm[info_hash]:
            db_lock.release()
            raise Exception("finish_download: Peer not in swarm")
        
        self.swarm[info_hash][tracker_id]['seeder'] = True
        db_lock.release()
        
    def update_status(self, info_hash, tracker_id):
        db_lock.acquire()
        if info_hash not in self.swarm:
            db_lock.release()
            raise Exception("update_status: Swarm not found")
        
        if tracker_id not in self.swarm[info_hash]:
            db_lock.release()
            raise Exception("update_status: Peer not in swarm")
        
        self.swarm[info_hash][tracker_id]['last_announce'] = time.time()
        db_lock.release()
            
    def delete(self, info_hash, tracker_id):
        db_lock.acquire()
        if tracker_id not in self.swarm[info_hash]:
            db_lock.release()
            raise Exception("delete: Peer not in swarm")
        
        del self.swarm[info_hash][tracker_id]
        db_lock.release()
            
    def get_peer_list(self, info_hash):
        peer_list = [
            {'peer_id': peer['peer_id'], 'ip': peer['ip'], 'port': peer['port']}
            for peer in self.swarm[info_hash].values()
        ]
        return peer_list
                    
    def generate_tracker_id(self):
        return secrets.token_hex(16)

class TrackerPeerStat():
    def __init__(self):
        # Format peers[(ip, port)]['info_hash'] = {
        #     uploaded: 0,
        #     downloaded: 0,
        #     left: 0
        # }
        self.peers = {}
    
    def add(self, info_hash, ip, port, uploaded, downloaded, left):
        if (ip, port) not in self.peers:
            self.peers[(ip, port)] = {}
        
        if (info_hash) not in self.peers[(ip, port)]:
            self.peers[(ip, port)][info_hash] = {
                'uploaded': 0,
                'downloaded': 0,
                'left': 0
            }
        
        self.peers[(ip, port)][info_hash] = {
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': left
        }
        
    def remove(self, info_hash, ip, port):
        peers_copy = copy.deepcopy(self.peers)
        
        if (ip, port) in peers_copy:
            if info_hash in peers_copy[(ip, port)]:
                del self.peers[(ip, port)][info_hash]
        
        if len(self.peers[(ip, port)]) == 0:
            del self.peers[(ip, port)]

class Tracker():
    def __init__(self, port):
        self.db = TrackerDB()
        self.peer_stat = TrackerPeerStat()
        self.host = get_host_default_interface_ip()
        self.port = port
        self.is_running = True
        
    def check_timeout(self):
        while self.is_running:
            #? Clone self.db.swarm before altering
            dbSwarmClone = copy.deepcopy(self.db.swarm)
            
            for info_hash in dbSwarmClone:
                for peer in dbSwarmClone[info_hash]:
                    if time.time() - dbSwarmClone[info_hash][peer]['last_announce'] > TIMEOUT_PER_SWARM:
                        self.db.delete(info_hash, peer)
                        print(f"[TIMEOUT] Peer {peer} in swarm {info_hash} has timed out: no announce for {TIMEOUT_PER_SWARM} seconds")
            time.sleep(TRACKER_INTERVAL)
            
    def require_fields(self, request, fields):
        for field in fields:
            if request.get(field) is None:
                raise Exception(f"'{field}' value is required")
        
    def handle_request(self, sock, addr):
        if (not self.is_running):
            return
        
        sock.settimeout(TRACKER_REQUEST_TIMEOUT)
        try:
            data = sock.recv(global_setting.TRACKER_RESPONSE_SIZE)
            if data:
                response = TrackerResponseBuilder()
                request = bdecode(data)
                
                self.require_fields(request, ['info_hash'])
                    
                event = request.get("event") # None if not found
                
                tracker_id = None
                # peer wanna join the swarm
                if event == RequestEvent.STARTED:
                    print("Peer request STARTED")
                    tracker_id = self.db.generate_tracker_id()
                    response.set_tracker_id(tracker_id)
                    
                    self.require_fields(request, ['peer_id', 'port', 'left'])
                    
                    uploaded = request['uploaded']
                    downloaded = request['downloaded']
                    left = request["left"]
                    
                    self.peer_stat.add(request['info_hash'], addr[0], request['port'], uploaded, downloaded, left)
                    
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
                        print("Peer request STOPPED")
                        self.db.delete(request["info_hash"], request["tracker_id"])
                        
                        self.peer_stat.remove(request['info_hash'], addr[0], request['port'])
                    # peer completed the download
                    elif event == RequestEvent.COMPLETED:
                        print("Peer request COMPLETED")
                        self.db.finish_download(request["info_hash"], request["tracker_id"])
                
                self.db.update_status(request['info_hash'], tracker_id)
                response.set_peers(self.db.get_peer_list(request["info_hash"]))
                    
        except Exception as e:
            response.set_failure_reason('handle_request: ' + str(e))
            raise e
        finally:
            sock.sendall(bencode(response.build()))
            sock.close()
            print(f"[DISCONNECTED] {addr} disconnected.")
    
    def connection_loop(self):
        while self.is_running:
            client_socket, addr = self.server_socket.accept()
            print(f"[CONNECTION] Accepted connection from {addr}")
            client_thread = threading.Thread(target=self.handle_request, args=(client_socket, addr))
            client_thread.start()
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        print(f"[LISTENING] Server is listening on {self.host}:{self.port}")
        
        # start checker thread
        checker_thread = threading.Thread(target=self.check_timeout)
        checker_thread.start()
        
        # start connection loop
        loop_thread = threading.Thread(target=self.connection_loop)
        loop_thread.start()
        
        while self.is_running:
            command = input("Type 'exit' to stop the server, 'stat' to show stats, 'list' to list files: ")
            if command == 'exit':
                self.stop()
                break
            elif command == 'stat':
                self.showStat()
            elif command == 'list':
                self.showList()
            
        print("[STOPPED] Server stopped.")
    
    def stop(self):
        self.is_running = False    
        # Connect to the same IP to stop the accept thread
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.close()
        self.server_socket.close()
    
    def showStatHandler(self):
        print("[Tracker Stats]")
        
        for key, value in self.peer_stat.peers.items():
            print(f"[Peer]: {key}")
            for info_hash, stat in value.items():
                print(f"Info Hash: {info_hash}, Uploaded: {stat['uploaded']}, Downloaded: {stat['downloaded']}, Left: {stat['left']}")
    
    def showStat(self):
        stat_thread = threading.Thread(target=self.showStatHandler)
        stat_thread.start()
    
    def showListHandler(self):
        print("[Tracker Files]")
        
        for key, value in self.db.swarm.items():
            print(f"[Info Hash]: {key}")
            for peer in value.values():
                print(f"Peer ID: {peer['peer_id']}, IP: {peer['ip']}, Port: {peer['port']}, Seeder: {peer['seeder']}")
            print()
        
    
    def showList(self):
        list_thread = threading.Thread(target=self.showListHandler)
        list_thread.start()
    
def start():
    tracker = Tracker(TRACKER_DEFAULT_PORT)
    tracker.start()
    
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