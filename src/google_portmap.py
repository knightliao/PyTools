#!/usr/bin/env python
# coding=utf8

"""自动更换Google地址的本地服务器
"""

import re, os, time
import urllib2
import urllib
import socket
import threading
import logging
import logging.config

logging.config.fileConfig("../conf/logging.conf")


ip_info = ["保加利亚", "93.123.23.1/59",
"埃及", "197.199.253.1/59",
"埃及", "197.199.254.1/59",
"香港", "218.189.25.129/187",
"香港", "218.253.0.76/92", "218.253.0.140/187",
"冰岛", "149.126.86.1/59",
"印度尼西亚", "111.92.162.4/6", "111.92.162.12/59",
"伊拉克", "62.201.216.196/251",
"日本", "218.176.242.4/251",
"肯尼亚", "41.84.159.12/30",
"韩国", "121.78.74.68/123",
"毛里求斯", "41.206.96.1/251",
"荷兰", "88.159.13.196/251",
"挪威", "193.90.147.0/7", "193.90.147.12/59", "193.90.147.76/123",
"菲律宾", "103.25.178.4/6", "103.25.178.12/59",
"俄罗斯", "178.45.251.4/123",
"沙特阿拉伯", "84.235.77.1/251",
"塞尔维亚", "213.240.44.5/27",
"新加坡", "203.116.165.129/255",
"新加坡", "203.117.34.132/187",
"斯洛伐克", "62.197.198.193/251",
"斯洛伐克", "87.244.198.161/187",
"台湾", "123.205.250.68/190",
"台湾", "123.205.251.68/123",
"台湾", "163.28.116.1/59",
"台湾", "163.28.83.143/187",
"台湾", "202.39.143.1/123",
"台湾", "203.211.0.4/59",
"台湾", "203.66.124.129/251",
"台湾", "210.61.221.65/187",
"台湾", "60.199.175.1/187",
"台湾", "61.219.131.65/123", "61.219.131.193/251",
"泰国", "1.179.248.4/59", "1.179.248.68/123", "1.179.248.132/187", "1.179.248.196/251",
"泰国", "1.179.249.4/59", "1.179.249.68/123", "1.179.249.132/187", "1.179.249.196/251",
"泰国", "1.179.250.4/59", "1.179.250.68/123", "1.179.250.132/187", "1.179.250.196/251",
"泰国", "1.179.251.4/59", "1.179.251.68/123", "1.179.251.140/187", "1.179.251.196/251",
"泰国", "1.179.252.68/123", "1.179.252.132/187", "1.179.252.196/251",
"泰国", "1.179.253.4/59", "1.179.253.76/123",
"泰国", "118.174.25.4/59", "118.174.25.68/123", "118.174.25.132/187", "118.174.25.196/251"];


#
#
#
def getHtml(url):
    # print "Open: %s ..." %url
    page = urllib2.urlopen(url, timeout = 5)
    html = page.read()
    return html


#
#
#
def getIpRange(str):

    ipList = []
    elmList = str.split(".")
    if len(elmList) != 4: return ipList

    tmp = elmList[3].split("/")
    min = int(tmp[0])
    max = int(tmp[1])
    for i in range(min, max + 1, 1):
        ipList.append("%s.%s.%s.%s" % (elmList[0], elmList[1], elmList[2], i))
    return ipList


# 当前活跃的线程数
aliveThreadNum = 0
# 可用的IP列表
aliveIpList = []
mutex = threading.Lock()


#
# 测试google地址是否可用的线程
#
class testIpThread(threading.Thread):

    def __init__(self, country, ip):
        threading.Thread.__init__(self)
        self.ip = ip
        self.country = country

    def run(self):
        global aliveThreadNum
        mutex.acquire()
        aliveThreadNum += 1
        mutex.release()

        url = r"http://%s" % self.ip

        try:
            html = getHtml(url)
            logging.info("success, [%s] %s , total %d, %d threads" % (self.country, url, len(aliveIpList) + 1), aliveThreadNum)
            mutex.acquire()
            aliveIpList.append((self.country, self.ip))
            mutex.release()
        except:
            pass
            logging.info("failed, [%s] %s" % (self.country, url))

        mutex.acquire()
        aliveThreadNum -= 1
        mutex.release()


#
# 多线程方式测试可用的google地址
#
class findAliveIpThread(threading.Thread):

    def __init__(self, ip_info):
        threading.Thread.__init__(self)
        self.ip_info = ip_info

    def find_alive_google(self):

        country = ""

        for elm in self.ip_info:

            ipList = getIpRange(elm)

            if len(ipList) == 0:
                country = elm  # 解析不了，说明是国家名称字符串
                continue

            for ip in ipList:

                if aliveThreadNum > 50:  # 最多并发 20 个线程。 如果机器配置比较低，可以适当减少
                    # logging.info("There are %d threads to test goolge hosts. Alive ip size %d and they are: %s" % (aliveThreadNum , len(aliveIpList), str(aliveIpList)))
                    time.sleep(2)

                # 只有IP地址快被消耗掉光的时候才继续寻找新的IP。过早测试容易失效。
                while len(aliveIpList) > 5:
                    time.sleep(0.2)

                t = testIpThread(country, ip)
                t.start()

    def run(self):
        while 1:
            self.find_alive_google()


#
# 将 remotesocket的数据写到 localsocket 里面
#
class portmapRcvThread(threading.Thread):

    def __init__(self, id, localsocket, remotesocket):
        threading.Thread.__init__(self)
        self.id = id
        self.localsocket = localsocket
        self.remotesocket = remotesocket

    def run(self):

        remotePort = 80

        while 1:
            try:
                buf = self.remotesocket.recv(20480)
                self.myPrint("recv %d bytes" % len(buf))
                if len(buf) == 0:
                    return
                    time.sleep(0.5)
                    continue
                self.localsocket.send(buf)
            except Exception, e:
                self.myPrint(e)
                self.myPrint("rcv thread exit.")
                return

        self.myPrint("recv thread exit.")
        return

    def myPrint(self, msg):
        logging.info("[ID: %s] %s" % (self.id, msg))


#
# 获取远程IP，并进行数据转换
#
class portmapThread(threading.Thread):

    def __init__(self, id, localsocket):
        threading.Thread.__init__(self)
        self.localsocket = localsocket
        self.id = id

    def connectRemote(self):
        remotePort = 80

        while 1:
            try:

                # 获取一个可用的IP
                remoteIp = self.getRemoteIp()
                logging.info("Connect to %s ..." % remoteIp)

                self.remotesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.remotesocket.settimeout(1)
                self.remotesocket.connect((remoteIp, remotePort))
                self.remotesocket.settimeout(100)

                logging.info("Connect to %s success!" % remoteIp)
                self.remoteIp = remoteIp
                return

            except:
                logging.info("Connect to %s failed!" % remoteIp)

    #
    # 获取远程可用的Google IP
    #
    def getRemoteIp(self):

        global aliveIpList
        while len(aliveIpList) == 0:
            time.sleep(2)

        mutex.acquire()
        aliveip = aliveIpList[0]
        del aliveIpList[0]
        mutex.release()

        # return "117.79.157.211"
        return aliveip[1]

    #
    # 1. 先获取可用的远程IP
    # 2.
    #
    def run(self):

        #
        # 获取可用IP
        #
        self.myPrint(" run 1")
        self.connectRemote()
        self.sendThread = portmapRcvThread(self.id, self.localsocket, self.remotesocket)
        self.sendThread.start()
        # self.localsocket.settimeout(10)

        #
        # 本地接收数据，并返回给远程端口
        #
        self.myPrint(" run 2")
        while 1:
            try:
                msg = self.localsocket.recv(2048)
                self.myPrint("send %d bytes" % len(msg))
                if len(msg) == 0:
                    break
                    time.sleep(0.5)
                    continue
                self.remotesocket.send(msg)

            except Exception, e:
                self.myPrint("%s" % e)
                self.localsocket.close()
                self.remotesocket.close()
                self.myPrint(" send thread exit.")
                return

        self.localsocket.close()
        self.remotesocket.close()
        self.myPrint("#### remotesocket connect closed.")

    def myPrint(self, msg):
        logging.info("[ID: %s] %s" % (self.id, msg))


#
# 绑定本地80端口
#
def start_port_map(localPort = 80):

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('127.0.0.1', localPort))
    logging.info("127.0.0.1 Server start at %s" % str(localPort))

    counter = 0
    server.listen(50)
    while 1:
        counter += 1
        localsocket, addr = server.accept()
        logging.info('[ID: %s] Got connected from %s' % (counter, addr))
        t = portmapThread(counter, localsocket)
        t.start()


def main():
    #启动多线程，测试可用的GOOGLE地址
    t=findAliveIpThread(ip_info)
    t.start()

    #启动本地端口映射
    start_port_map()
    
main()



