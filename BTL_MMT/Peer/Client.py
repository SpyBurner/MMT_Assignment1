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
import RequestBuilder as rb
import Server
import PeerWireProtocol as pwp
import time

#TODO Implement sending requests to the tracker.
#TODO Request format is defined in the project description.
class ClientUploader(threading.Thread):
    def __init__(self, filePath, announce_list):
        threading.Thread.__init__(self)
        self.filePath = filePath
        self.announce_list = announce_list

    def run(self):
        try:
            singleFileMode = os.path.isfile(self.filePath)
            metainfo = mi.MetainfoBuilder()

            for announce in self.announce_list:
                metainfo.add_announce(announce)

            metainfo.set_piece_length(global_setting.PIECE_SIZE)

            def get_piece_hashes(file_path, piece_count):
                piece_hashes = []
                try:
                    with open(file_path, 'rb') as file:
                        for _ in range(piece_count):
                            piece = file.read(global_setting.PIECE_SIZE)
                            if not piece:
                                break
                            piece_hashes.append(hashlib.sha1(piece).digest())
                except IOError as e:
                    print(f"Error reading file {file_path}: {e}")
                return piece_hashes

            if singleFileMode:
                file_size = os.path.getsize(self.filePath)
                metainfo.set_name(os.path.basename(self.filePath))
                metainfo.set_length(file_size)

                piece_count = math.ceil(file_size / global_setting.PIECE_SIZE)
                piece_hashes = get_piece_hashes(self.filePath, piece_count)
                metainfo.set_pieces(b''.join(piece_hashes))
            else:
                piece_hashes = []
                total_size = 0

                for root, _, files in os.walk(self.filePath):
                    for file in files:
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, self.filePath)
                        path_array = relative_path.split(os.sep)

                        file_size = os.path.getsize(file_path)
                        metainfo.add_file(file_size, path_array)
                        total_size += file_size

                        piece_count = math.ceil(file_size / global_setting.PIECE_SIZE)
                        piece_hashes.extend(get_piece_hashes(file_path, piece_count))

                metainfo.set_pieces(b''.join(piece_hashes))

            try:
                os.makedirs(peer_setting.METAINFO_FILE_PATH, exist_ok=True)
            except OSError as e:
                print(f"Error creating metainfo directory: {e}")

            infohash = hashlib.sha1(bcoding.bencode(metainfo.info)).hexdigest()
            
            #? Write metainfo to file with infohash as filename           
            metainfo_path = os.path.join(peer_setting.METAINFO_FILE_PATH, infohash + global_setting.METAINFO_FILE_EXTENSION)
            with open(metainfo_path, 'wb') as f:
                f.write(bcoding.bencode(metainfo.build()))

            #? Copy file to repo
            repo_path = os.path.join(peer_setting.REPO_FILE_PATH, infohash)
            try:
                os.makedirs(repo_path, exist_ok=True)
                shutil.copy(self.filePath, repo_path)
            except OSError as e:
                print(f"Error copying file to repo: {e}")

            for announce in self.announce_list:
                request = rb.TrackerRequestBuilder()
                request.set_info_hash(infohash)
                request.set_event("started")
                request.set_uploaded(0)
                request.set_downloaded(0)
                request.set_left(0)
                request.set_peer_id(Server.GetServer().peerID)
                request.set_port(peer_setting.PEER_SERVER_DEFAULT_PORT)

                requester = Server.ServerRequester(Server.GetServer(), announce['ip'], announce['port'], request)
                requester.start()
        except Exception as e:
            print(f"Error in ClientUploader: {e}")

class ClientKeepAlive(threading.Thread):
    def __init__(self, sock, interval):
        self.sock = sock
        self.interval = interval
        self.isRunning = True
        threading.Thread.__init__(self)

    def run(self):
        while self.isRunning:
            try:
                self.sock.sendall(pwp.KeepAlive())
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
        try:
            self.sock.sendall(bcoding.bencode(pwp.Request(self.index, self.begin, self.length)))
            
            response = self.sock.recv(global_setting.PIECE_SIZE)
            response = bcoding.bdecode(response)
            
            if (response['type'] != pwp.Type.PIECE):
                print("Peer did not respond with correct piece.")
                return

            with open(self.filePath, 'r+b') as f:
                f.seek(self.index * global_setting.PIECE_SIZE + self.begin)
                f.write(response['block'])
            
        except Exception as e:
            print(f"Error in ClientPieceRequester: {e}")

class ClientDownloader(threading.Thread):
    def __init__(self, metainfoPath):
        threading.Thread.__init__(self)
        self.metainfoPath = metainfoPath

    def run(self):        
        #TODO Get info_hash from metainfo
        metainfo = mi.Get(self.metainfoPath)
        
        info_hash = hashlib.sha1(metainfo['info']).hexdigest()
        
        print("Downloading file(s) with name: ", metainfo['info']['name'], " and info_hash: ", info_hash)
        
        #? Copy metainfo into the metainfo directory
        try:
            shutil.copy(self.metainfoPath, peer_setting.METAINFO_FILE_PATH)
        except Exception as e:
            print("Metainfo file already in position: ", e)
            
        request = rb.TrackerRequestBuilder()
        request.set_info_hash(info_hash)
        request.set_event("started")
        request.set_uploaded(0)
        request.set_downloaded(0)
        request.set_left(0)
        request.set_peer_id(Server.GetServer().peerID)
        
        server = Server.GetServer()
        
        requesters = []
        
        #? Send request to all trackers to get peer list
        for announce in metainfo['announce_list']:
            requester = Server.ServerRequester(server, announce['ip'], announce['port'], request)  
            requesters.append(requester)
            requester.start()
        
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
        
        #? Check if file is single file mode
        if (metainfo['info']['files'] == None):
            totalLength = metainfo['info']['length']
        else:
            for file in metainfo['info']['files']:
                totalLength += file['length']
        
        pieceCount = math.ceil(totalLength / pieceLength)
        
        #? Create file in repo with filler bytes
        tempFilePath = os.path.join(peer_setting.REPO_FILE_PATH, info_hash, info_hash + global_setting.TEMP_DOWNLOAD_FILE_EXTENSION)
        try: 
            with open(tempFilePath, 'wb') as f:
                f.write(b'\0' * totalLength)
        except Exception as e:
            print("Error creating file in repo: ", e)
        
        pieces = metainfo['info']['pieces']
        
        while True:
            bitfield = pwp.Bitfield(pwp.GenerateBitfield(pieces, pieceCount, pieceLength, tempFilePath))
            
            #? Break when all pieces are downloaded
            if (sum(bitfield) == pieceCount):
                break
            
            peerList = Server.GetServer().peerMapping[info_hash]
            
            #? Print list of peers
            print("Aquired peer list: ")
            for key, peer in peerList:
                print(peer)
            
            #? Connect to peers for handshake and bitfield exchange            
            # Format: (socket, bitfield)
            peerConnections = []
            
            for peer in peerList:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(peer_setting.PEER_CLIENT_CONNECTION_TIMEOUT)
                sock.connect((peer['ip'], peer['port']))
                
                #? Send handshake
                handshake = pwp.Handshake(info_hash, Server.GetServer().peerID)
                sock.sendall(bcoding.bencode(handshake))
                
                #? Receive handshake
                response = sock.recv(peer_setting.PEER_WIRE_MESSAGE_SIZE)
                response = bcoding.bdecode(response)
                
                if (response['type'] != pwp.Type.HANDSHAKE or response['info_hash'] != info_hash):
                    print("Peer " + peer['ip'] + " did not respond with correct handshake.")
                    sock.close()
                    continue

                
                #? ALWAYS send bitfield
                sock.sendall(bcoding.bencode(bitfield))
                
                #? Receive bitfield
                response = sock.recv(global_setting.BITFIELD_SIZE)
                response = bcoding.bdecode(response)
                
                if (response['type'] != pwp.Type.BITFIELD):
                    print("Peer " + peer['ip'] + " did not respond with correct bitfield.")
                    sock.close()
                    continue
                
                peerConnections.append((sock, response['bitfield']))
            
            #? Start keep alive threads
            keepAliveThreads = []
            
            for connection in peerConnections:
                keepAlive = ClientKeepAlive(connection[0], global_setting.KEEP_ALIVE_INTERVAL)
                keepAlive.start()
                keepAliveThreads.append(keepAlive)
            
            updateBitfield = bitfield
            
            #? Choose which piece to download from which peer
            #? Spread the load evenly
            
            pieceRequesterThreads = []
            
            piecePerPeer = math.ceil(pieceCount / len(peerConnections))
            for connection in peerConnections:
                pieceRequested = 0
                #? Check if piece is already downloaded
                for i in range(pieceCount):
                    if (updateBitfield[i] == 0 and connection[1][i] == 1):
                        requester = ClientPieceRequester(connection[0], i, 0, pieceLength, tempFilePath)
                        updateBitfield[i] = 1
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
        
        #? Rename temp file to actual file
        try:
            os.rename(tempFilePath, os.path.join(peer_setting.REPO_FILE_PATH, info_hash, metainfo['info']['name']))
        except Exception as e:
            print("Error renaming file: ", e)
        
        print("Download for file(s) ", metainfo['info']['name'], " with info_hash ", info_hash, " completed.")        
                
            
            
            
                
                
            
            
        
               
        
        
        
        

class ClientLister(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Implement listing logic here.")

#! Create the right type of thread and start it.
def Upload(filePath, announce_list):
    print("Uploading file: ", filePath, " to tracker: ")
    for announce in announce_list:
        print(announce)

    uploader = ClientUploader(filePath, announce_list)
    uploader.start()

def Download(metainfo):
    print("Downloading file with metainfo: ", metainfo)
    
    downloader = ClientDownloader(metainfo)
    downloader.start()
    
def ListFiles():
    print("Listing local files.")
    
    lister = ClientLister()
    lister.start()
