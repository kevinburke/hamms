import socket

print socket.gethostname()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('127.0.0.1', 5500))
server_socket.listen(5)

while 1:
    clientsocket, address = server_socket.accept()
