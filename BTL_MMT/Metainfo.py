import os
import sys
import hashlib

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import global_setting
import bcoding
from Metainfo import MetainfoBuilder as mib

#? Get all metainfo files in the directory, transform to dictionary, and return all
def get_all(metainfoPath):
    
    result = []
    
    if not os.path.exists(metainfoPath):
        return result
    
    for file in os.listdir(metainfoPath):
        if file.endswith(global_setting.METAINFO_FILE_EXTENSION):
            metainfo_decode = bcoding.bdecode(open(metainfoPath + file, "rb").read())
            result.append(metainfo_decode)
    
    return result

#? Get a single metainfo
def Get(metainfoPath):
    return bcoding.bdecode(open(metainfoPath, "rb").read())

def GetInfoHash(metainfoPath):
    metainfo = bcoding.bdecode(open(metainfoPath, 'rb').read())
    info = metainfo['info']
    return hashlib.sha1(bcoding.bencode(info)).hexdigest()     
       
class MetainfoBuilder():
    def __init__(self):
        self.info = {
            'piece length': None,
            'pieces': None,
            'name': None,
            #? Single file mode
            'length': None,
            #? Multifile mode
            #? files: [{'length': None, 'path': []}]
            'files' : []
        }
        #? announce_list: [{'ip': None, 'port': None}]
        self.announce_list = []
        
        #? Example
        #? self.announce_list.append({'ip': None, 'port': None})
            
    def add_announce(self, announce):
        self.announce_list.append(announce)
        return self

    def set_piece_length(self, piece_length):
        self.info['piece length'] = piece_length
        return self

    def set_pieces(self, pieces):
        self.info['pieces'] = pieces

    def set_name(self, name):
        self.info['name'] = name
        return self

    def set_length(self, length):
        self.info['length'] = length
        return self
    
    def add_file(self, length, path):
        self.info['files'].append({'length': length, 'path': path})
        return self

    def build(self):
        info = {k: v for k, v in self.info.items() if v is not None}
        return {
            'info': info,
            'announce_list': self.announce_list
        }