METAINFO_FILE_EXTENSION = ".meta"

PIECE_SIZE = 16 * 2**10

TRACKER_RESPONSE_SIZE = 16 * 2**10 + 1024


def recv(sock, max_size):
    data = b''
    while True:
        data_chunk = sock.recv(1024)
        if data_chunk:
            data+=data_chunk
        else:
            break
        if len(data) >= max_size:
            break
    return data