# Usage

## keepalive.py
```
python3 /root/keepalive.py <remote ip> <remote port>
```

## generate_xfrm.py
```
➜  setup-ipsec-by-hand git:(main) ✗ python tools/generate_xfrm.py -h
usage: generate_xfrm.py [-h] [-t {state,policy}] [--in_id IN_ID] [--out_id OUT_ID] [-s SRC] [-d DST] [-l LEFT] [-r RIGHT]
                        [--sport SPORT] [--dport DPORT] [--inbond_spi INBOND_SPI] [--inbond_sec INBOND_SEC]
                        [--outbond_spi OUTBOND_SPI] [--outbond_sec OUTBOND_SEC]

options:
  -h, --help            show this help message and exit
  -t {state,policy}, --type {state,policy}
                        Type of xfrm, state or policy
  --in_id IN_ID         In-bond reqid of xfrm state
  --out_id OUT_ID       Out-bond reqid of xfrm state
  -s SRC, --src SRC     Source ip of IPSec SA
  -d DST, --dst DST     Destination ip of IPSec SA
  -l LEFT, --left LEFT  Local subnet cidr
  -r RIGHT, --right RIGHT
                        Remote subnet cidr
  --sport SPORT         Local port
  --dport DPORT         Remote port
  --inbond_spi INBOND_SPI
                        In-bond spi
  --inbond_sec INBOND_SEC
                        In-bond security key
  --outbond_spi OUTBOND_SPI
                        Out-bond spi
  --outbond_sec OUTBOND_SEC
                        Out-bond security key
```

**Generate new xfrm state**
```
(qingcloud) ➜  ~ python3 generate_xfrm.py -t state -s 10.10.0.1 -d 192.168.100.2 --dport 4500
####################Out-bond xfrm state#####################
ip xfrm state add src 10.10.0.1 dst 192.168.100.2 proto esp spi 0x35a4db48 mode tunnel reqid 58899 flag af-unspec aead 'rfc4106(gcm(aes))' 0x604a1b01406ac6b30cd88ef23ee8dc1c86b68fd3 128 encap espinudp 4500 4500 0.0.0.0
#####################In-bond xfrm state#####################
ip xfrm state add src 192.168.100.2 dst 10.10.0.1 proto esp spi 0xde688143 mode tunnel reqid 9531 flag af-unspec aead 'rfc4106(gcm(aes))' 0x61417dc6f48555dc9d880ea780db413e3b78a661 128 encap espinudp 4500 4500 0.0.0.0
```

**Generate xfrm state according to peer xfrm state**
```
(qingcloud) ➜  ~ python3 generate_xfrm.py -t state --inbond_spi 35a4db48 --inbond_sec 604a1b01406ac6b30cd88ef23ee8dc1c86b68fd3 --outbond_spi de688143 --outbond_sec 61417dc6f48555dc9d880ea780db413e3b78a661 -s 192.168.100.2 -d 192.168.100.123 --dport 5544
####################Out-bond xfrm state#####################
ip xfrm state add src 192.168.100.2 dst 192.168.100.123 proto esp spi 0xde688143 mode tunnel reqid 49168 flag af-unspec aead 'rfc4106(gcm(aes))' 0x61417dc6f48555dc9d880ea780db413e3b78a661 128 encap espinudp 4500 5544 0.0.0.0
#####################In-bond xfrm state#####################
ip xfrm state add src 192.168.100.123 dst 192.168.100.2 proto esp spi 0x35a4db48 mode tunnel reqid 47869 flag af-unspec aead 'rfc4106(gcm(aes))' 0x604a1b01406ac6b30cd88ef23ee8dc1c86b68fd3 128 encap espinudp 5544 4500 0.0.0.0
```

**Generate xfrm policy**
```
(qingcloud) ➜  ~ python3 generate_xfrm.py -t policy -l 10.10.0.0/16 -r 172.16.10.0/24 --in_id 9531 --out_id 58899 -s 10.10.0.1 -d 192.168.100.2
##################Xfrm policy for local net 10.10.0.0/16 remote net 172.16.10.0/24##################
ip xfrm policy add src 172.16.10.0/24 dst 10.10.0.0/16 dir in tmpl src 192.168.100.2 dst 10.10.0.1 proto esp mode tunnel reqid 9531
ip xfrm policy add src 172.16.10.0/24 dst 10.10.0.0/16 dir fwd tmpl src 192.168.100.2 dst 10.10.0.1 proto esp mode tunnel reqid 9531
ip xfrm policy add src 10.10.0.0/16 dst 172.16.10.0/24 dir out tmpl src 10.10.0.1 dst 192.168.100.2 proto esp mode tunnel reqid 58899
```