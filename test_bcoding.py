from bcoding import bencode, bdecode

# decoding from binary files in bencode format to json
with open('sample.torrent', 'rb') as f:
    torrent = bdecode(f)
    print(torrent)

# # decoding from (byte)strings:
# one = bdecode(b'i1e')
# two = bdecode('3:two')

# test = bdecode(b'l4:dir14:dir28:file.exte')
# print(test)