# _*_ coding: utf-8 _*_

import argparse
import sys

from random import choice
from typing import Union


KEY_LEN = 40
inbond_spi = None
inbond_sec = None
outbond_spi = None
outbond_sec = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', '--type', choices=['state', 'policy'],
                        help='Type of xfrm, state or policy')
    parser.add_argument('--in_id', help='In-bond reqid of xfrm state')
    parser.add_argument('--out_id', help='Out-bond reqid of xfrm state')
    parser.add_argument('-s', '--src', help='Source ip of IPSec SA')
    parser.add_argument('-d', '--dst', help='Destination ip of IPSec SA')
    parser.add_argument('-l', '--left', help='Local subnet cidr')
    parser.add_argument('-r', '--right', help='Remote subnet cidr')
    parser.add_argument('--sport', help='Local port', type=int, default=4500)
    parser.add_argument('--dport', help='Remote port', type=int)
    parser.add_argument('--inbond_spi', help='In-bond spi')
    parser.add_argument('--inbond_sec', help='In-bond security key')
    parser.add_argument('--outbond_spi', help='Out-bond spi')
    parser.add_argument('--outbond_sec', help='Out-bond security key')

    return parser.parse_args()


def generate_hex(len: int) -> str:
    return ''.join([choice('0123456789abcdef') for i in range(len)])


def generate_state_info(len: int) -> Union[int, str, str]:
    spi = generate_hex(8)
    req_id = generate_hex(4)
    sec_key = generate_hex(len)
    return spi, int(req_id, 16), sec_key


def _generate_xfrm_state(
        spi: str, reqid: int, sec_key: str,
        sip: str, dip: str, sport: int, dport: int) -> int:
    xfrm_state_add_cmd = "ip xfrm state add src {sip} dst {dip} " \
        "proto esp spi 0x{spi} mode tunnel reqid {reqid} flag af-unspec " \
        "aead 'rfc4106(gcm(aes))' 0x{sec} 128 " \
        "encap espinudp {sport} {dport} 0.0.0.0".format(
            sip=sip, dip=dip, spi=spi,
            reqid=reqid, sec=sec_key,
            sport=sport, dport=dport)
    print(xfrm_state_add_cmd)
    return 0


def generate_xfrm_state(len: int, sip: str, dip: str,
                        sport: int, dport: int) -> int:

    global inbond_spi, inbond_sec, outbond_spi, outbond_sec

    # Out bond
    print('Out-bond xfrm state'.center(60, '#'))
    spi, reqid, sec_key = generate_state_info(len)

    if outbond_spi:
        spi = outbond_spi
        sec_key = outbond_sec
    if 0 != _generate_xfrm_state(spi, reqid, sec_key,
                                 sip, dip, sport, dport):
        return 1

    # In bond
    print('In-bond xfrm state'.center(60, '#'))
    spi, reqid, sec_key = generate_state_info(len)

    if inbond_spi:
        spi = inbond_spi
        sec_key = inbond_sec
    return _generate_xfrm_state(spi, reqid, sec_key,
                                dip, sip, dport, sport)


def __generate_xfrm_policy(dir: str, id: str, left: str,
                           right: str, src: str, dst: str) -> int:
    xfrm_policy_add_cmd = "ip xfrm policy add src {left} dst {right} dir {dir} " \
        "tmpl src {src} dst {dst} proto esp mode tunnel reqid {id}".format(
            left=left, right=right, dir=dir, src=src, dst=dst, id=id)
    print(xfrm_policy_add_cmd)
    return 0


def _generate_xfrm_policy(in_id: str, out_id: str, left: str,
                          right: str, src: str, dst: str) -> int:
    # Dir in
    if 0 != __generate_xfrm_policy('in', in_id, right, left, dst, src):
        print("ERR: failed to generate in xfrm policy")

    # Dir fwd
    if 0 != __generate_xfrm_policy('fwd', in_id, right, left, dst, src):
        print("ERR: failed to generate fwd xfrm policy")

    # Dir out
    if 0 != __generate_xfrm_policy('out', out_id, left, right, src, dst):
        print("ERR: failed to generate out xfrm policy")
    return 0


def generate_xfrm_policy(in_id: str, out_id, lnet: str,
                         rnet: str, src: str, dst: str) -> int:
    lnet_list = lnet.split(',')
    rnet_list = rnet.split(',')

    for lnet_item in lnet_list:
        for rnet_item in rnet_list:
            print("Xfrm policy for local net {} remote net {}".format(
                lnet_item, rnet_item).center(100, '#'))
            if 0 != _generate_xfrm_policy(in_id, out_id, lnet_item,
                                          rnet_item, src, dst):
                print("ERR: generate xfrom policy failed")
                return 1
    return 0


def main() -> int:
    args = parse_args()

    exist_info = False
    global inbond_spi, inbond_sec, outbond_spi, outbond_sec
    if args.inbond_spi:
        inbond_spi = args.inbond_spi
        exist_info = True
    if args.inbond_sec:
        inbond_sec = args.inbond_sec
        exist_info = True
    if args.outbond_spi:
        outbond_spi = args.outbond_spi
        exist_info = True
    if args.outbond_sec:
        outbond_sec = args.outbond_sec
        exist_info = True
    if exist_info:
        if not all([inbond_spi, inbond_sec, outbond_spi, outbond_sec]):
            print("ERR: inbond spi sec and outbond spi sec required")
            return 1

    if args.type == 'state':
        if not args.src or not args.dst or not args.dport:
            print("ERR: For xfrm state src, dst ip and remote port required")
            return 1
        return generate_xfrm_state(KEY_LEN, args.src, args.dst,
                                   args.sport, args.dport)

    if not args.in_id or not args.out_id or not args.left \
            or not args.right or not args.src or not args.dst:
        print("ERR: For xfrm policy local and remote " \
              "subnet and xfrm state inbond outbond reqid " \
              "and src dst ip required")
        return 1
    return generate_xfrm_policy(args.in_id, args.out_id, args.left,
                                args.right, args.src, args.dst)


if __name__ == '__main__':
    sys.exit(main())
