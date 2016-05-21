'''Without knowing the HMAC key used to calculate X-Message-Code, it may be 
possible to query a Tor hidden service for the correct code. Note that the 
hidden service is not guaranteed to be up at any time. Also note that in order
to calculate X-Message-Code, the contents of the API call is sent to the 
hidden service, therefore the operator of said service CAN HAZ ALL YOUR 
PASSWORDZ! You have been warned.

Requirement: connectivity to the Tor network.

After getting Tor up and running, change TOR_HOST and TOR_PORT below 
accordingly.
'''

import socket
import binascii
import logging

TOR_HOST = '127.0.0.1'
TOR_PORT = 9150

HIDDEN_SERVICE_ADDRESS = 'vdhl6tjtue6dv6js.onion'
HIDDEN_SERVICE_PORT = 25252

CONNECT_RETRY = 3
CONNECT_TIMEOUT = 30

def gen_xmessagecode(data):
    logger = logging.getLogger('XMsgCodeTor')
    
    for attempt in range(CONNECT_RETRY):
        try:
            s = socket.socket()
            s.settimeout(CONNECT_TIMEOUT)
            s.connect((TOR_HOST, TOR_PORT))
            
            s.sendall(b'\x05\x01\x00')
            r = socket_recv_exactly(s, 2)
            if r[1] != 0:
                raise RuntimeError('Tor SOCKS5 server rejected authentication attempt, return code {}'.format(r[1]))
            
            s.sendall(b'\x05\x01\x00\x03' + len(HIDDEN_SERVICE_ADDRESS).to_bytes(1, 'big') + HIDDEN_SERVICE_ADDRESS.encode() + HIDDEN_SERVICE_PORT.to_bytes(2, 'big'))
            r = socket_recv_exactly(s, 4)
            if r[1] != 0:
                raise RuntimeError('Tor SOCKS5 server rejected connection attempt, return code {}'.format(r[1]))
            
            if r[3] == 1:
                socket_recv_exactly(s, 4+2)
            elif r[3] == 3:
                r = socket_recv_exactly(s, 1)
                socket_recv_exactly(s, r[0] + 2)
            elif r[3] == 4:
                socket_recv_exactly(s, 16+2)
            else:
                raise RuntimeError('Tor SOCKS5 server sent malformed connection reply')
            
            s.sendall(len(data).to_bytes(2, 'big'))
            s.sendall(data)
            digest = socket_recv_exactly(s, 20)
        
        except Exception as e:
            logger.exception('Attempt {} retrieving X-Message-Code failed'.format(attempt+1))
        else:
            break
        finally:
            s.close()
    else: # Fell through the loop, i.e. all retries exhausted
        raise RuntimeError('All attempts retrieving X-Message-Code failed. Maybe Tor is not working correctly, or the hidden service is not currently running.')
        
    return binascii.hexlify(digest).decode()

def socket_recv_exactly(socket, length):
    d = bytearray()
    
    while len(d) < length:
        d.extend(socket.recv(length - len(d)))
    
    return d