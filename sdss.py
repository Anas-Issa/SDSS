import sys
import os
import threading
import socket
import time
import uuid
import struct
from datetime import datetime

ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_purple(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):
    def __init__(self, delay, broadcaster_counter, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        self.broadcaster_counter = broadcaster_counter
        self.ip = ip
        self.tcp_port = tcp_port

    def get_counter(self):
        return self.broadcaster_counter

    def set_counter(self, counter):
        self.broadcaster_counter = counter


neighbor_information = {}

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("", 0))
server.listen(10)
_, server_port = server.getsockname()

# Leave broadcaster as a global variable.
broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broadcaster.bind(("", get_broadcast_port()))


def send_broadcast_thread():
    node_uuid = get_node_uuid()
    message = str(node_uuid) + " ON " + str(server_port)
    while True:
        broadcaster.sendto(message.encode("UTF-8"), ("255.255.255.255", get_broadcast_port()))
        time.sleep(1)


def receive_broadcast_thread():
    while True:
        data, (ip, port) = broadcaster.recvfrom(4096)
        data = data.decode("UTF-8")
        unique_id = data.split(" ")[0]
        other_port = data.split(" ")[2]
        if get_node_uuid() != unique_id:
            if unique_id not in neighbor_information.keys():
                neighbor_information[unique_id] = NeighborInfo(None, 0)
                daemon_thread_builder(exchange_timestamps_thread, (unique_id, ip, other_port))
            else:
                neighbor_information[unique_id].set_counter(neighbor_information[unique_id].get_counter()+1)
                print_red(unique_id + ": " + str(neighbor_information[unique_id].get_counter()))
                if neighbor_information[unique_id].get_counter() == 10:
                    del neighbor_information[unique_id]
            print_blue(f"RECV: {data} FROM: {ip}:{port}")


def tcp_server_thread():
    while True:
        server_socket, add = server.accept()
        timestamp = int(datetime.utcnow().microsecond)
        server_socket.sendto(str(timestamp).encode("UTF-8"), add)
        server_socket.close()


def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((other_ip, int(other_tcp_port)))
    timestamp = datetime.utcnow().microsecond
    data = tcp_socket.recv(4069)
    received_timestamp = int(data.decode("UTF-8"))
    delay = abs(received_timestamp-timestamp)/1000000
    neighbor_information[other_uuid] = NeighborInfo(delay, neighbor_information[other_uuid].get_counter()+1, other_ip, other_tcp_port)
    print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")
    print_green("delay:" + str(delay) + " sec")
    tcp_socket.close()


def daemon_thread_builder(target, args=()) -> threading.Thread:
    th = threading.Thread(target=target, args=args)
    th.start()
    return th


def entrypoint():
    daemon_thread_builder(send_broadcast_thread)
    daemon_thread_builder(tcp_server_thread)
    daemon_thread_builder(receive_broadcast_thread)


def main():
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)
    entrypoint()


if __name__ == "__main__":
    main()