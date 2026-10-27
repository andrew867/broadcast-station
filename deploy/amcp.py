"""Send one explicit command to the isolated local CasparCG instance."""
import socket
import sys

def command(text):
    with socket.create_connection(('127.0.0.1',5250),timeout=5) as connection:
        connection.settimeout(3)
        connection.sendall((text+'\r\n').encode())
        chunks=[]
        while True:
            try:
                data=connection.recv(65536)
                if not data:break
                chunks.append(data)
                if b'\r\n' in b''.join(chunks):
                    connection.settimeout(.3)
            except socket.timeout:
                break
        return b''.join(chunks).decode(errors='replace')

if __name__=='__main__':
    print(command(' '.join(sys.argv[1:])))
