import hashlib

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

    
def Handshake(info_hash, peer_id):      
    return {
        'type' : Type.HANDSHAKE,
        'info_hash': info_hash,
        'peer_id': peer_id,
    }
    
def KeepAlive():
    return {
        'type': Type.KEEP_ALIVE,
    }

def Bitfield(bitfield):
    return {
        'type': Type.BITFIELD,
        'bitfield': bitfield,
    }

def Request(index, begin, length):
    return {
        'type': Type.REQUEST,
        'index': index,
        'begin': begin,
        'length': length,        
    }

def Piece(index, begin, block):
    return {
        'type': Type.PIECE,
        'index': index,
        'begin': begin,
        'block': block
    }

def GenerateBitfield(pieces, pieceCount, pieceLength, filePath):
    bitfield = [0] * pieceCount
    
    try:
        with open(filePath, 'rb') as f:
            for i in range(pieceCount):
                piece = f.read(pieceLength)
                if (hashlib.sha1(piece).digest() == pieces[i]):
                    bitfield[i] = 1
    except IOError as e:
        print(f"Error reading file {filePath}: {e}")

    return bitfield