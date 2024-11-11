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
            
    