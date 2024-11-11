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

            metainfo_path = os.path.join(peer_setting.METAINFO_FILE_PATH, metainfo.info['name'] + global_setting.METAINFO_FILE_EXTENSION)
            with open(metainfo_path, 'wb') as f:
                f.write(bcoding.bencode(metainfo.build()))

            infohash = hashlib.sha1(bcoding.bencode(metainfo.info)).hexdigest()

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
                request = request.build()

                requester = Server.ServerRequester(Server.GetServer(), announce['ip'], announce['port'], request)
                requester.start()
        except Exception as e:
            print(f"Error in ClientUploader: {e}")
    
class ClientDownloader(threading.Thread):
    def __init__(self, metainfoPath):
        threading.Thread.__init__(self)
        self.metainfoPath = metainfoPath

    def start(self):
        #TODO Get info_hash from metainfo
        metainfo = mi.Get(self.metainfoPath)
        
        info_hash = hashlib.sha1(metainfo['info']).hexdigest()
        
        #TODO Send request to tracker
        request = rb.TrackerRequestBuilder()
        request.set_info_hash(info_hash)
        request.set_event("started")
        request.set_uploaded(0)
        request.set_downloaded(0)
        request.set_left(0)
        request.set_peer_id(Server.GetServer().peerID)
        
        server = Server.GetServer()
        
        responses = []
        
        def AppendResponse(response):
            responses.append(response)
        
        for announce in metainfo['announce_list']:
            requester = Server.ServerRequester(server, announce['ip'], announce['port'], request)
            
            requester.SetCallback(lambda response: server.StoreTrackerID(response))
            
            requester.start()

        
        #TODO Receive response from tracker
        
        
        
        
        

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
