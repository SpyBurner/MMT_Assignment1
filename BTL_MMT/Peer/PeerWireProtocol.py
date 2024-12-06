import hashlib
import os

# read all files in path and return the data
def get_data_from_path(path):
    print("Getting data from path: ", os.getcwd())
    data = b''
    
    # Single file
    if (os.path.isfile(path)):
        # print("Path is a file")
        with open(path, 'rb') as f:
            data = f.read()
            # print('Data: ', data)
        return data
    
    # Directory
    for root, _, files in os.walk(path):
        # print('Working in path: ', root)
        for file in files:
            # print('Reading file: ', file)
            file_path = os.path.join(root, file)
            with open(file_path, 'rb') as f:
                data += str(f.read())
                # print('Data: ', f.read())
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
        'begin': begin,
        'length': length,        
    }

def piece(index, begin, block):
    return {
        'type': Type.PIECE,
        'index': index,
        'begin': begin,
        'block': block
    }

def generate_bitfield(pieces, pieceCount, pieceLength, filePath):
    print('Generating bitfield...')
    
    print('Current directory: ', os.getcwd())
        
    print(f"Piece count: {pieceCount}")
    print(f"Piece length: {pieceLength}")
    print(f"File path: {filePath}")
    print(f"pieces: ", pieces)
    
    bitfield = [0] * pieceCount
    
    try:
        data = get_data_from_path(filePath)
        for i in range(pieceCount):
            piece = data[i * pieceLength : (i + 1) * pieceLength]
            metainfo_piece = pieces[i * pieceLength : (i + 1) * pieceLength]
            print(f"Piece {i} hash: {hashlib.sha1(piece).digest()}")
            print(f"Metainfo piece {i} hash: {metainfo_piece}")
            if hashlib.sha1(piece).digest() == metainfo_piece:
                bitfield[i] = 1
            print('Bit: ', bitfield[i])
        return bitfield
    except IOError as e:
        print(f"Error reading file {filePath}: {e}")

    return bitfield