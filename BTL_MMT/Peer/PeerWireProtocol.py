import hashlib
import os
import threading

file_lock = threading.Lock()

# read all files in path and return the data
def get_data_from_path(path):
    print("Current running path: ", os.getcwd())
    print("Getting data from path: ", path)
    data = b''
    
    # Single file
    if (os.path.isfile(path)):
        # print("Path is a file")
        file_lock.acquire()
        with open(path, 'rb') as f:
            data += f.read()
            # print('Data: ', data)
        file_lock.release()
        return data
    
    # Directory
    for root, _, files in os.walk(path):
        # print('Working in path: ', root)
        for file in files:
            # print('Reading file: ', file)
            file_path = os.path.join(root, file)
            
            file_lock.acquire()
            
            with open(file_path, 'rb') as f:
                current_data = f.read()
                # print('Current data: ', current_data)
                data += current_data
                
            file_lock.release()
    # print('Data: ', data)
    return data

class Type:
    HANDSHAKE = 'handshake'
    KEEP_ALIVE = 'keep_alive'
    CHOKE = 'choke'
    UNCHOKE = 'unchoke'
    INTERESTED = 'interested'
    NOT_INTERESTED = 'not_interested'
    HAVE = 'have'
    BITFIELD = 'bitfield'
    REQUEST = 'request'
    PIECE = 'piece'
    CANCEL = 'cancel'
    PORT = 'port'

def handshake(info_hash, peer_id):      
    return {
        'type' : Type.HANDSHAKE,
        'info_hash': info_hash,
        'peer_id': peer_id,
    }
    
# unused
def keep_alive():
    return {
        'type': Type.KEEP_ALIVE,
    }

def bitfield(bitfield):
    return {
        'type': Type.BITFIELD,
        'bitfield': bitfield,
    }

def request(index, begin, length):
    return {
        'type': Type.REQUEST,
        'index': index,
        # ununsed
        'begin': begin,
        # unused
        'length': length,        
    }

def piece(index, begin, block):
    return {
        'type': Type.PIECE,
        'index': index,
        # unused
        'begin': begin,
        'block': block
    }
    
def generate_bitfield(pieces, pieceCount, pieceLength, filePath):
    # print('Generating bitfield...')
    
    # print('Current directory: ', os.getcwd())
        
    # print(f"Piece count: {pieceCount}")
    # print(f"Piece length: {pieceLength}")
    # print(f"File path: {filePath}")
    # print(f"pieces: ", pieces)
    
    bitfield = [0] * pieceCount
    
    try:
        data = get_data_from_path(filePath)
        for i in range(pieceCount):
            piece = data[i * pieceLength : (i + 1) * pieceLength]
            metainfo_piece = pieces[i * 20 : (i + 1) * 20]
            if hashlib.sha1(piece).digest() == metainfo_piece:
                bitfield[i] = 1
        return bitfield
    except IOError as e:
        print(f"Error reading file {filePath}: {e}")

    return bitfield