import socket

def get_host_default_interface_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
       print(s.getsockname())
    except Exception:
       ip = '192.168.56.106'
    finally:
       s.close()
    return ip

serverIp = get_host_default_interface_ip()
serverPort = 22236

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((serverIp, serverPort))
print(sock)

sock.connect(("www.example.com", 80))
sock.send(b"GET / HTTP/1.1\r\nHost:www.example.com\r\n\r\n")
response = sock.recv(4096)
sock.close()

print(response.decode())