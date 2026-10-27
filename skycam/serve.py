"""One controller worker, explicitly bound to the operator interfaces only."""
import os
import socket
import uvicorn

def bind_listeners(addresses,port):
    listeners=[]
    try:
        for address in dict.fromkeys(addresses):
            address=address.strip()
            socket.inet_pton(socket.AF_INET,address)
            if address=='0.0.0.0':raise ValueError('Choose explicit operator addresses, not every interface')
            listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            listeners.append(listener)
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind((address,port))
            listener.listen(128)
        return listeners
    except Exception:
        for listener in listeners:listener.close()
        raise

def main():
    listeners=bind_listeners(os.getenv('SKYCAM_LISTEN_ADDRESSES','127.0.0.1').split(','),8765)
    try:
        server=uvicorn.Server(uvicorn.Config('skycam.app:app',workers=1,access_log=False))
        server.run(sockets=listeners)
    finally:
        for listener in listeners:listener.close()

if __name__=='__main__':main()
