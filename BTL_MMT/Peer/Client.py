import copy
import threading
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import Metainfo as mi
import socket
import peer_setting
import global_setting
import bcoding
import math
import hashlib
import shutil
import TrackerProtocol as tp
import Server
import PeerWireProtocol as pwp
import time

file_lock = threading.Lock()
    
    
class ClientUploader(threading.Thread):
    def __init__(self, filePath, announce_list):
        threading.Thread.__init__(self)
        self.filePath = filePath
        self.announce_list = announce_list
        
        
    def get_piece_hashes(self, piece_count):
        piece_hashes = []
        data = pwp.get_data_from_path(self.filePath)
        for i in range(piece_count):
            start = i * global_setting.PIECE_SIZE
            end = min(start + global_setting.PIECE_SIZE, len(data))
            piece = data[start:end]
            piece_hash = hashlib.sha1(piece).digest()
            piece_hashes.append(piece_hash)
        return piece_hashes
    
    def run(self):
        singleFileMode = os.path.isfile(self.filePath)
        metainfo = mi.MetainfoBuilder()

        for announce in self.announce_list:
            metainfo.add_announce({
                'ip': announce[0],
                'port': int(announce[1])
            })

        metainfo.set_piece_length(global_setting.PIECE_SIZE)
        
        print('basename', os.path.basename(self.filePath))
        metainfo.set_name(os.path.basename(self.filePath))
        piece_count = 0

        if singleFileMode:
            file_size = os.path.getsize(self.filePath)
            metainfo.set_length(file_size)
            piece_count = math.ceil(file_size / global_setting.PIECE_SIZE)
        else:
            total_size = 0
            # loop for all files in the directory, get the relative path from the self.filePath
            for root, _, files in os.walk(self.filePath):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    
                    relative_path = os.path.relpath(file_path, self.filePath)
                    segments_of_path = relative_path.split(os.sep)

                    metainfo.add_file(file_size, segments_of_path)
                    total_size += file_size
            piece_count = math.ceil(total_size / global_setting.PIECE_SIZE)

        # for both single file and multiple files
        piece_hashes = self.get_piece_hashes(piece_count)
        metainfo.set_pieces(b''.join(piece_hashes))

        try:
            os.makedirs(peer_setting.METAINFO_FILE_PATH, exist_ok=True)
        except OSError as e:
            print(f"Error creating metainfo directory: {e}")

        print(f"Metainfo: {metainfo.build()}")

        # Build into dictionary
        metainfo = metainfo.build()
        
        infohash = hashlib.sha1(bcoding.bencode(metainfo['info'])).hexdigest()
        
        #? Write metainfo to file with infohash as filename           
        metainfo_path = os.path.join(peer_setting.METAINFO_FILE_PATH, infohash + global_setting.METAINFO_FILE_EXTENSION)
        with open(metainfo_path, 'wb') as f:
            f.write(bcoding.bencode(metainfo))

        #? Copy file to repo
        repo_path = os.path.join(peer_setting.REPO_FILE_PATH, infohash)
        try:
            os.makedirs(peer_setting.REPO_FILE_PATH, exist_ok=True)
            
            if (singleFileMode):
                shutil.copy(self.filePath, repo_path)
            else:
                shutil.copytree(self.filePath, repo_path)
        except OSError as e:
            print(f"Error copying file to repo: {e}")
            # raise(e)
            
        #? Send request to all trackers
        for announce in self.announce_list:
            request = tp.TrackerRequestBuilder()
            request.set_info_hash(infohash)
            request.set_port(Server.get_server().port)
            request.set_event("started")
            request.set_uploaded(0)
            request.set_downloaded(0)
            request.set_left(0)
            request.set_peer_id(Server.get_server().peerID)

            requester = Server.ServerRequester(Server.get_server(), announce[0], announce[1], request)
            requester.start()

class ClientKeepAlive(threading.Thread):
    def __init__(self, sock, interval):
        self.sock = sock
        self.interval = interval
        self.isRunning = True
        threading.Thread.__init__(self)

    def run(self):
        while self.isRunning:
            try:
                self.sock.sendall(bcoding.bencode(pwp.keep_alive()))
                time.sleep(self.interval)
            except Exception as e:
                print(f"Error in ClientKeepAlive: {e}")
                self.isRunning = False
    
    def stop(self):
        self.isRunning = False

class ClientPieceRequester(threading.Thread):
    def __init__(self, sock, index, begin, length, filePath):
        self.sock = sock
        self.index = index
        self.begin = begin
        self.length = length
        self.filePath = filePath
        threading.Thread.__init__(self)
    
    def run(self):
        #? Request a piece and write to file on sucess
        print(f"Requesting piece {self.index} from peer " + self.sock.getpeername()[0])
        self.sock.settimeout(peer_setting.PEER_CLIENT_CONNECTION_TIMEOUT)
        try:
            self.sock.sendall(bcoding.bencode(pwp.request(self.index, self.begin, self.length)))
            
            print('Request sent')
            
            print('Waiting for response...')
            response = self.sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
            print('Response received')
            
            response = bcoding.bdecode(response)
            
            if (response['type'] != pwp.Type.PIECE):
                print("Peer did not respond with correct piece.")
                return

            block = response['block']
            print("Received block: ", block, " type: ", type(block))
            
            data = block.encode('utf-8')
            print("Data: ", data, " type: ", type(data))

            file_lock.acquire()
            
            with open(self.filePath, 'r+b') as f:
                f.seek(self.index * global_setting.PIECE_SIZE + self.begin)
                f.write(data)
                
            file_lock.release()
            
        except Exception as e:
            print(f"Error in ClientPieceRequester: {e}")
class ClientDownloader(threading.Thread):
    def __init__(self, metainfoPath):
        threading.Thread.__init__(self)
        self.metainfoPath = metainfoPath

    def run(self):        
        #TODO Get info_hash from metainfo
        metainfo = mi.Get(self.metainfoPath)
        
        info_hash = hashlib.sha1(bcoding.bencode(metainfo['info'])).hexdigest()
        
        print("[Downloading] name: ", metainfo['info']['name'], " and info_hash: ", info_hash)
        
        print("[Metainfo] ", metainfo)
        
        #? Create metainfo directory if it does not exist
        try:
            os.makedirs(peer_setting.METAINFO_FILE_PATH, exist_ok=True)
            print("Metainfo directory ensured.")
        except Exception as e:
            print("Error creating metainfo directory: ", e)
        
        #? Copy metainfo into the metainfo directory
        #TODO Rename metainfo file to info_hash
        try:
            shutil.copy(self.metainfoPath, peer_setting.METAINFO_FILE_PATH)
            print("Metainfo file copied.")
        except Exception as e:
            print("Metainfo file copy error: ", e)
        
        server = Server.get_server()
        
        request = tp.TrackerRequestBuilder()
        request.set_info_hash(info_hash)
        request.set_port(server.port)
        request.set_event("started")
        request.set_uploaded(0)
        request.set_downloaded(0)
        request.set_left(0)
        request.set_peer_id(server.peerID)
        
        requesters = []
        
        print('Sending started requests...')
        
        #? Send request to all trackers to get peer list
        for announce in metainfo['announce_list']:
            requester = Server.ServerRequester(server, announce['ip'], announce['port'], request)  
            requesters.append(requester)
            requester.start()
            print('Started request sent to tracker: ', announce)
        
        #? Wait for all threads to terminate before continueing
        for requester in requesters:
            requester.join()
        
        #? Create repo file path
        try:
            os.makedirs(peer_setting.REPO_FILE_PATH, exist_ok=True)
            os.makedirs(os.path.join(peer_setting.REPO_FILE_PATH, info_hash), exist_ok=True)
        except Exception as e:
            print("Error creating repo file path: ", e)
        
        pieceLength = metainfo['info']['piece length']
        totalLength = 0
        
        #? Get totalLength in either file mode
        isSingleFile = True
        if (len(metainfo['info']['files']) == 0):
            totalLength = metainfo['info']['length']
        else:
            isSingleFile = False
            for file in metainfo['info']['files']:
                totalLength += file['length']
        
        pieceCount = math.ceil(totalLength / pieceLength)
        
        #? Create file in repo with filler bytes
        tempFilePath = os.path.join(peer_setting.REPO_FILE_PATH, info_hash, info_hash)
        try: 
            if (not os.path.exists(tempFilePath)):
                with open(tempFilePath, 'wb') as f:
                    f.write(b'\0' * totalLength)
            else: 
                print("File already exist in repo.")
        except Exception as e:
            print("Error creating file in repo: ", e)
        
        print('Temp file created')
        
        pieces = metainfo['info']['pieces']
        
        print('Metainfo extracts: ', pieceLength, totalLength, pieceCount, pieces)
        
        tryCount = 0;
        tryLimit = 5;
        
        print('Starting download...')
        
        while True:
            tryCount += 1
            if (tryCount > tryLimit):
                print("Download failed after ", tryLimit, " attempts.")
                #? Leave swarm
                stop_request = tp.TrackerRequestBuilder()
                stop_request.set_info_hash(info_hash)
                stop_request.set_event(tp.RequestEvent.STOPPED)
                for announce in metainfo['announce_list']:
                    requester = Server.ServerRequester(server, announce['ip'], announce['port'], stop_request)  
                    requesters.append(requester)
                    requester.start()
                #? Delete temp file
                try:
                    os.remove(tempFilePath)
                except Exception as e:
                    print("Error deleting temp file: ", e)
                #? Delete metainfo file
                try:
                    os.remove(os.path.join(peer_setting.METAINFO_FILE_PATH, info_hash + global_setting.METAINFO_FILE_EXTENSION))
                except Exception as e:
                    print("Error deleting metainfo file: ", e)
                return
            
            this_bitfield = pwp.bitfield(pwp.generate_bitfield(pieces, pieceCount, pieceLength, tempFilePath))
            
            print("Current number of pieces downloaded: ", sum(this_bitfield['bitfield']))
            
            #? Break when all pieces are downloaded
            if (sum(this_bitfield['bitfield']) == pieceCount):
                break
            
            peerList = Server.get_server().peerMapping[info_hash]
            
            #? Print list of peers
            print("[Acquired peer list] ")
            print(peerList)
            
            #? Connect to peers for handshake and bitfield exchange            
            # Format: (socket, bitfield)
            peerConnections = []
            keepAliveThreads = []
            server = Server.get_server()
            
            for peer in peerList:
                #? Skip self
                if (peer['ip'] == server.ip and peer['port'] == server.port):
                    continue
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(peer_setting.PEER_CLIENT_CONNECTION_TIMEOUT)
                try: 
                    sock.connect((peer['ip'], peer['port']))
                except Exception as e:
                    print("Error connecting to peer: ", e)
                    continue
                
                #? Send handshake
                handshake = pwp.handshake(info_hash, Server.get_server().peerID)
                sock.sendall(bcoding.bencode(handshake))
                
                print("[Handshake] sent to peer: ", peer['ip'])
                
                #? Receive handshake
                response = sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
                response = bcoding.bdecode(response)
                
                print("[Handshake] received from peer: ", peer['ip'])
                
                if (response['type'] != pwp.Type.HANDSHAKE or response['info_hash'] != info_hash):
                    print("Peer " + peer['ip'] + " did not respond with correct handshake.")
                    sock.close()
                    continue

                #? Create keep alive thread
                # keepAlive = ClientKeepAlive(sock, peer_setting.KEEP_ALIVE_INTERVAL)
                # keepAlive.start()
                # keepAliveThreads.append(keepAlive)

                #? ALWAYS send bitfield
                request = pwp.bitfield(this_bitfield['bitfield'])
                sock.sendall(bcoding.bencode(request))
                
                #? Receive bitfield
                response = sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
                response = bcoding.bdecode(response)
                
                if (response['type'] != pwp.Type.BITFIELD):
                    print("Peer " + peer['ip'] + " did not respond with correct bitfield.")
                    sock.close()
                    continue
                
                print("[Bitfield] received from peer: ", peer['ip'], " bitfield: ", response['bitfield'])
                
                peerConnections.append((sock, response['bitfield']))

            #? Check connection list
            if (len(peerConnections) == 0):
                print("[Download attempt", tryCount," ] No peers connected.")
                continue

            requestedBitfield = copy.deepcopy(this_bitfield['bitfield'])
            
            print('peerList: ', peerList)
            print('Update bitfield: ', requestedBitfield)
            
            #? Choose which piece to download from which peer
            #? Spread the load evenly
            pieceRequesterThreads = []
            
            piecePerPeer = math.ceil(pieceCount / len(peerConnections))
            for connection in peerConnections:
                pieceRequested = 0
                #? Check if piece is already downloaded
                for i in range(pieceCount):
                    if (requestedBitfield[i] == 0 and connection[1][i] == 1):
                        requester = ClientPieceRequester(connection[0], i, 0, pieceLength, tempFilePath)
                        requestedBitfield[i] = 1
                        requester.start()
                        pieceRequested += 1
                        pieceRequesterThreads.append(requester)
                        
                    if (pieceRequested >= piecePerPeer):
                        break
            
            
            #? Wait for all threads to terminate before continueing
            for thread in pieceRequesterThreads:
                thread.join()
            
            #? Stop keep alive threads
            for thread in keepAliveThreads:
                thread.stop()
        
        #TODO Multiple file case where
        #? Map temp file to the actual file(s)
        # if isSingleFile:
        #     try:
        #         os.rename(tempFilePath, os.path.join(peer_setting.REPO_FILE_PATH, info_hash, metainfo['info']['name']))
        #     except Exception as e:
        #         print("Error renaming file: ", e)
            
        # else:
        #     try:
        #         with open(tempFilePath, 'rb') as tempFile:
        #             for file in metainfo['info']['files']:
        #                 filePath = os.path.join(peer_setting.REPO_FILE_PATH, info_hash, *file['path'])
        #                 fileLength = file['length']
                        
        #                 os.makedirs(os.path.dirname(filePath), exist_ok=True)
                        
        #                 with open(filePath, 'wb') as f:
        #                     f.write(tempFile.read(fileLength))
        #     except Exception as e:
        #         print("Error in file mapping ", e)
        
        print("Download for file(s) ", metainfo['info']['name'], " with info_hash ", info_hash, " completed.")        
            
class ClientLister(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Implement listing logic here.")

#! Create the right type of thread and start it.
def upload(filePath, announce_list):
    print("Uploading file: ", filePath, " to tracker: ")
    for announce in announce_list:
        print(announce)

    uploader = ClientUploader(filePath, announce_list)
    uploader.start()

def download(metainfo):
    print("Downloading file with metainfo: ", metainfo)
    
    downloader = ClientDownloader(metainfo)
    downloader.start()
    
def ListFiles():
    print("Listing local files.")
    
    lister = ClientLister()
    lister.start()
