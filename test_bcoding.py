from bcoding import bencode, bdecode
# decoding from binary files or streams:
with open('sample.torrent', 'rb') as f:
        torrent = bdecode(f)
        print(torrent)

# # decoding from (byte)strings:
# one = bdecode(b'i1e')
# two = bdecode('3:two')