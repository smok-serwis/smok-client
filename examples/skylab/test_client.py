import ssl, socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_ctxt = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_ctxt.load_cert_chain('dev.crt', 'key.crt')
ssl_ctxt.check_hostname = False
sock = ssl_ctxt.wrap_socket(sock, server_hostname='http-api')
sock.connect(('127.0.0.1', 8080))
sock.do_handshake(True)
while True:
    sock.write(b'dupa')
    time.sleep(5)

