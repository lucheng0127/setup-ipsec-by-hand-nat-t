import asyncio
import socket
import sys
import time


def ping(sock: socket, dst: str, port: int) -> int:
    ret = sock.sendto("ping".encode('utf-8'), (dst, port))
    print("{}: Send keepalive ping to "
          "{}:{} with source port 4500".format(
              time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), dst, port))
    return ret


async def keepalive(sock: socket, dst: str, port: int) -> None:
    while True:
        ping(sock, dst, port)
        time.sleep(10)


# HACK(shawnlu): setsockopt udp 100 2, nor hyper receive 
# espinudp package but will not decode it
# ref: http://techblog.newsnow.co.uk/2011/11/simple-udp-esp-encapsulation-nat-t-for.html
def init_socket(port: int) -> socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_UDP, 100, 2)
    sock.bind(('0.0.0.0', port))
    return sock


if __name__ == '__main__':
    sock = init_socket(4500)
    asyncio.run(keepalive(sock, sys.argv[1], int(sys.argv[2])))
