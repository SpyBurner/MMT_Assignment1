import os
import global_setting
import bcoding

#? Get all metainfo files in the directory, transform to dictionary, and return all
def GetAll(metainfoPath):
    
    result = []
    
    for file in os.listdir(metainfoPath):
        if file.endswith(global_setting.METAINFO_FILE_EXTENSION):
            metainfo_decode = bcoding.bdecode(open(metainfoPath + file, "rb").read())
            result.append(metainfo_decode)
    
    return result

#? Get a single metainfo
def Get(metainfoPath):
    return bcoding.bdecode(open(metainfoPath, "rb").read())
            
def MetainfoBuilder():
    def __init__(self):
        self.info = {
            'piece length': None,
            'name': None,
            #? Single file mode
            'length': None,
            #? Multifile mode
            #? files: [{'length': None, 'path': None}]
            'files' : []
        }
        self.announce_list = []
        
        #? Example
        self.announce_list.append({'ip': None, 'port': None})
            
    def AddAnnounce(self, announce):
        self.announce_list.append(announce)
        return self

    def SetPieceLength(self, piece_length):
        self.info['piece length'] = piece_length
        return self

    def SetName(self, name):
        self.info['name'] = name
        return self

    def SetLength(self, length):
        self.info['length'] = length
        return self
    
    def AddFile(self, length, path):
        self.info.files.append({'length': length, 'path': path})
        return self

    def Build(self):
        return {
            'info': self.info,
            'announce_list': self.announce_list
        }