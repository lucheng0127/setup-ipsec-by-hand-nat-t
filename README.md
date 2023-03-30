# setup-ipsec-by-hand

## Intro

I gonna create IPSec VPN by manual add static xfrm state 
and xfrm policy, in this article I gonna setup an IPSec
VPN, that server with a public IP, but EP under a nat.

*You can use generate_xfrm.py to generate xfrm state and poliy add cmd*

## Topology

```
----------------------------------------------(Pub net)
  |                               +-|---------------------+
  |                               |eth0 192.168.100.123/24| (iptables -A POSTROUTING -s
  |                               |          R2           | 10.10.0.0/16 -j SNAT
+-|-------------------+           |br0      10.10.0.254/16| --to-source 192.168.100.123)
|eth0 192.168.100.2/24|--IPSec    +-|---------------------+
|        R1           |  SA---|     | (default via 10.10.0.254)
|br0  172.16.10.254/24|       |   +-|---------------------+
+-|-------------------+       |---|e1 10.10.0.1/16   (vm1)|
(net 172.16.10.0/24)===IPSec Tun==+-----------------------+

# R1 R2 with an public IP belong to 192.168.100.0/24
# R1 connect to subnet 172.16.10.0/24，R2 connect to subnet 10.10.0.0/16
# vm1 with ip 10.10.0.1/16 under R2
# vm1 try to connect to 172.16.10.0/24 subnet by IPSec Tun
```

## Prerequisite

1. R1 get the public ip and port, that vm1 got after nat
2. Keep nat conntrack alive

## Start

### vm1 connect to R1 4500 with keepalive.py script
```
root@i-q6fcsdt9:~# ip netns exec vm1 python3 /root/keepalive.py 192.168.100.2 4500
2023-03-30 02:20:01: Send keepalive ping to 192.168.100.2:4500 with source port 4500
2023-03-30 02:20:11: Send keepalive ping to 192.168.100.2:4500 with source port 4500
```

### R1 send package back to keep nat alive every 10 second
Got public ip and port that vm1 got by tcpdump, then launch keepalive.py script
```
[root@i-pi6sxtgz ~]# python3 keepalive.py 192.168.100.123 5544
2023-03-30 02:20:41: Send keepalive ping to 192.168.100.123:5544 with source port 4500
2023-03-30 02:20:51: Send keepalive ping to 192.168.100.123:5544 with source port 4500
```
Check the port correct in R1 use conntrack command
```
root@i-q6fcsdt9:~# conntrack -L |grep 10.10.0.1| grep udp
conntrack v1.4.6 (conntrack-tools): 2 flow entries have been shown.
udp      17 116 src=10.10.0.1 dst=192.168.100.2 sport=4500 dport=4500 src=192.168.100.2 dst=192.168.100.123 sport=4500 dport=5544 [ASSURED] mark=0 use=1
```

### Generate SPI, reqid and secret
```
echo SPI >> sec_info
echo `xxd -p -l 4 /dev/random` >> sec_info
echo `xxd -p -l 4 /dev/random` >> sec_info
echo  >> sec_info
echo Req ID >> sec_info
echo `xxd -p -l 2 /dev/random` >> sec_info
echo `xxd -p -l 2 /dev/random` >> sec_info
echo  >> sec_info
echo PSK >> sec_info
echo `xxd -p -l 16 /dev/random` >> sec_info
echo `xxd -p -l 16 /dev/random` >> sec_info
echo  >> sec_info
echo Check >> sec_info
echo `xxd -p -l 16 /dev/random` >> sec_info
echo `xxd -p -l 16 /dev/random` >> sec_info
```

### Confiure
#### R1
**xfrm state**
```
## out bond SA
ip xfrm state add src 192.168.100.2 dst 192.168.100.123 proto esp spi 0x8f0e56d9 \
  mode tunnel reqid 0x985d flag af-unspec auth sha256 0x9da46b46ed7c637863662adf2aa5bafc \
  enc aes 0x64f7f3366bb6d38c268dae7aef579e9b encap espinudp 4500 5544 0.0.0.0

## in bond SA
ip xfrm state add src 192.168.100.123 dst 192.168.100.2 proto esp spi 0x529561e0 \
  mode tunnel reqid 0x9f74 flag af-unspec auth sha256 0x9ae03071952c554f39767a1b958eeb53 \
  enc aes 0xc3c404f5719867fc70d4034dbdec24bf encap espinudp 5544 4500 0.0.0.0
```
**xfrm policy**
```
ip xfrm policy add src 172.16.10.0/24 dst 10.10.0.0/16 dir out \
  tmpl src 192.168.100.2 dst 192.168.100.123 \
  proto esp mode tunnel reqid 0x985d
ip xfrm policy add src 10.10.0.0/16 dst 172.16.10.0/24 dir in \
  tmpl src 192.168.100.123 dst 192.168.100.2 \
  proto esp mode tunnel reqid 0x9f74
ip xfrm policy add src 10.10.0.0/16 dst 172.16.10.0/24 dir fwd \
  tmpl src 192.168.100.123 dst 192.168.100.2 \
  proto esp mode tunnel reqid 0x9f74
```
**policy route**
```
ip rule add pref 2000 lookup 2000
ip route add 10.10.0.0/16 dev eth0 src 192.168.100.2 table 2000
```

#### vm1
I setup vm1 by netns so don't forget entry netns
```
ip netns exec vm1 bash
```
**xfrm state**
```
## out bond SA
ip xfrm state add src 10.10.0.1 dst 192.168.100.2 proto esp spi 0x529561e0 \
  mode tunnel reqid 0x9f74 flag af-unspec auth sha256 0x9ae03071952c554f39767a1b958eeb53 \
  enc aes 0xc3c404f5719867fc70d4034dbdec24bf encap espinudp 4500 4500 0.0.0.0

## in bond SA
ip xfrm state add src 192.168.100.2 dst 10.10.0.1 proto esp spi 0x8f0e56d9 \
  mode tunnel reqid 0x985d flag af-unspec auth sha256 0x9da46b46ed7c637863662adf2aa5bafc \
  enc aes 0x64f7f3366bb6d38c268dae7aef579e9b encap espinudp 4500 4500 0.0.0.0
```
**xfrm policy**
```
ip xfrm policy add src 10.10.0.0/16 dst 172.16.10.0/24 dir out \
  tmpl src 10.10.0.1 dst 192.168.100.2 \
  proto esp mode tunnel reqid 0x9f74
ip xfrm policy add src 172.16.10.0/24 dst 10.10.0.0/16 dir in \
  tmpl src 192.168.100.2 dst 10.10.0.1 \
  proto esp mode tunnel reqid 0x985d
ip xfrm policy add src 172.16.10.0/24 dst 10.10.0.0/16 dir fwd \
  tmpl src 192.168.100.2 dst 10.10.0.1 \
  proto esp mode tunnel reqid 0x985d
```
**policy ruote**
```
ip rule add pref 2000 lookup 2000
ip route add 172.16.10.0/24 dev e1 src 10.10.0.1 table 2000
```

### Verify
**vm1**
```
root@i-q6fcsdt9:~# ping 172.16.10.1 -c 1
PING 172.16.10.1 (172.16.10.1) 56(84) bytes of data.
64 bytes from 172.16.10.1: icmp_seq=1 ttl=63 time=0.434 ms

--- 172.16.10.1 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.434/0.434/0.434/0.000 ms
root@i-q6fcsdt9:~# ping 172.16.10.254 -c 1
PING 172.16.10.254 (172.16.10.254) 56(84) bytes of data.
64 bytes from 172.16.10.254: icmp_seq=1 ttl=64 time=0.470 ms

--- 172.16.10.254 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.470/0.470/0.470/0.000 ms
```
**R1**
```
[root@i-pi6sxtgz ~]# tcpdump -i eth0 -nvel udp and port 4500
tcpdump: listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes
10:30:21.896087 52:54:96:47:db:c1 > 52:54:96:c6:c0:9f, ethertype IPv4 (0x0800), length 46: (tos 0x0, ttl 64, id 60990, offset 0, flags [DF], proto UDP (17), length 32)
    192.168.100.2.4500 > 192.168.100.123.5544: UDP-encap:  [|esp]
10:30:22.053641 52:54:96:c6:c0:9f > 52:54:96:47:db:c1, ethertype IPv4 (0x0800), length 46: (tos 0x0, ttl 63, id 31557, offset 0, flags [DF], proto UDP (17), length 32)
    192.168.100.123.5544 > 192.168.100.2.4500: UDP-encap:  [|esp]
10:30:24.267976 52:54:96:c6:c0:9f > 52:54:96:47:db:c1, ethertype IPv4 (0x0800), length 174: (tos 0x0, ttl 63, id 7730, offset 0, flags [DF], proto UDP (17), length 160)
    192.168.100.123.5544 > 192.168.100.2.4500: UDP-encap: ESP(spi=0x529561e0,seq=0x6), length 132
10:30:24.268130 52:54:96:47:db:c1 > 52:54:96:c6:c0:9f, ethertype IPv4 (0x0800), length 174: (tos 0x0, ttl 64, id 19369, offset 0, flags [none], proto UDP (17), length 160)
    192.168.100.2.4500 > 192.168.100.123.5544: UDP-encap: ESP(spi=0x8f0e56d9,seq=0x6), length 132
10:30:26.631059 52:54:96:c6:c0:9f > 52:54:96:47:db:c1, ethertype IPv4 (0x0800), length 174: (tos 0x0, ttl 63, id 8125, offset 0, flags [DF], proto UDP (17), length 160)
    192.168.100.123.5544 > 192.168.100.2.4500: UDP-encap: ESP(spi=0x529561e0,seq=0x7), length 132
10:30:26.631186 52:54:96:47:db:c1 > 52:54:96:c6:c0:9f, ethertype IPv4 (0x0800), length 174: (tos 0x0, ttl 64, id 19573, offset 0, flags [none], proto UDP (17), length 160)
    192.168.100.2.4500 > 192.168.100.123.5544: UDP-encap: ESP(spi=0x8f0e56d9,seq=0x7), length 132
```
Now enjoy it
***
### Attachment

keepalived.py use to keep nat alive

### Reference

[ipsec-with-iproute2](https://backreference.org/2014/11/12/on-the-fly-ipsec-vpn-with-iproute2/)

[udp esp encapsulation for nat-t](http://techblog.newsnow.co.uk/2011/11/simple-udp-esp-encapsulation-nat-t-for.html)