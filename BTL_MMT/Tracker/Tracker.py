from hashlib import sha1
import threading
import time
import socket
from tracker_setting import *
from bcoding import bencode, bdecode
from RequestBuilder import *
import secrets

class TrackerDB():
    def __init__(self):
        self.swarm = {}
        self.last_announce = {}
        
    
    def add(self, info_hash, peer_id, ip, port, tracker_id, seeder=False):
        if info_hash not in self.swarm:
            self.swarm[info_hash] = {}
              
        newPeer = {
            'peer_id': peer_id,
            'ip': ip,
            'port': port,
            'seeder': seeder,
        }
        self.swarm[info_hash][tracker_id] = newPeer
    
    def finish_download(self, info_hash, tracker_id):
        if tracker_id not in self.swarm[info_hash]:
            raise Exception("Peer not in swarm")
        self.swarm[info_hash][tracker_id]['seeder'] = True
        
    def update_status(self, tracker_id):
        self.last_announce[tracker_id] = time.time()
            
    def delete(self, info_hash, tracker_id):
        if tracker_id not in self.swarm[info_hash]:
            raise Exception("Peer not in swarm")
        del self.swarm[info_hash][tracker_id]
        del self.last_announce[tracker_id]
            
    def get_peer_list(self, info_hash):
        peer_list = [
            {'peer_id': peer['peer_id'], 'ip': peer['ip'], 'port': peer['port']}
            for peer in self.swarm[info_hash].values()
        ]
        return peer_list
        
                    
    def generate_tracker_id(self):
        # regenerate tracker id if it already exists
        tracker_id = secrets.token_hex(16)
        while tracker_id in self.last_announce:
            tracker_id = secrets.token_hex(16)
        return tracker_id

# class TrackerResponder(threading.Thread):
#     def __init__(self, sock, addr):
#         threading.Thread.__init__(self, daemon=True)
#         self.sock = sock
#         self.addr = addr
        
#     def start(self):
#         pass
    
class Tracker():
    def __init__(self, port):
        self.db = TrackerDB()
        self.host = get_host_default_interface_ip()
        self.port = port
        
    def check_timeout(self):
        while True:
            for info_hash in self.db.swarm:
                for peer in self.db.swarm[info_hash]:
                    if time.time() - self.db.last_announce[peer] > TIMEOUT_PER_SWARM:
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
                request = data.bdecode()
                
                self.require_fields(request, ['info_hash'])
                    
                event = request.get("event") # None if not found
                # peer wanna join the swarm
                if event == RequestEvent.STARTED:
                    if request.get("tracker_id") is None:
                        response.SetTrackerId(self.db.generate_tracker_id())
                    
                    self.require_fields(request, ['peer_id', 'port', 'left'])
                    left = request["left"]
                    if left == 0:
                        # peer already has the file
                        self.db.add(request["info_hash"], request["peer_id"], addr[0], request["port"], request["tracker_id"], seeder=True)
                    elif left > 0:
                        # peer want to download the file
                        self.db.add(request["info_hash"], request["peer_id"], addr[0], request["port"], request["tracker_id"])
                    else:
                        raise Exception("Invalid 'left' value")
                else:
                    self.require_fields(request, ['tracker_id'])
                    # peer wanna leave the swarm
                    if event == RequestEvent.STOPPED:
                        self.db.delete(request["info_hash"], request["tracker_id"])
                    # peer completed the download
                    elif event == RequestEvent.COMPLETED:
                        self.db.finish_download(request["info_hash"], request["tracker_id"])
                
                self.db.update_status(request["tracker_id"])
                response.SetPeers(self.db.get_peer_list(request["info_hash"]))
                    
        except Exception as e:
            response.SetFailureReason(str(e))
        finally:
            sock.sendall(bencode(response.Build()))
            sock.close()
            print(f"[DISCONNECTED] {addr} disconnected.")
    
    def start(self):
        print("Starting Tracker")
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
        
def Start():
    tracker = Tracker(TRACKER_DEFAULT_PORT)
    tracker.start()

def Stat(self):
    print("Tracker Stats")
        
def List(self):
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