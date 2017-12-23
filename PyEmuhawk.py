import os
import sys
import pathlib
import mmap
import socket
import time
import http.server
import threading


class EmuhawkException(Exception):
    pass




class Emuhawk:
    def __init__(self, emuhawk_exe=None):

        self.emuhawk_exe = None
        if emuhawk_exe is None:
            self.find_emuhawk_exe()
        else:
            self.emuhawk_exe = emuhawk_exe
        self.socket_server = SocketServer()

    def find_emuhawk_exe(self):
        """

        :return:
        """
        if os.getenv('emuhawk') is not None:
            self.emuhawk_exe = os.getenv('emuhawk')
            return self.emuhawk_exe
        else:
            possible_locations = list()
            try:
                possible_locations.append(os.path.join(pathlib.Path.home(),
                                                       r"Documents\GitHub\BizHawk\output\EmuHawk.exe"))
            except:
                possible_locations.append(os.path.join(os.path.expanduser('~'),
                                                        r"Documents\GitHub\BizHawk\output\EmuHawk.exe"))
            if os.getenv('ProgramFiles') is not None:
                possible_locations.append(
                    os.path.join(os.getenv('ProgramFiles'), r"BizHawk\output\EmuHawk.exe"))
                possible_locations.append(
                    os.path.join(os.getenv('ProgramFiles'), r"BizHawk\EmuHawk.exe"))
            possible_l = len(possible_locations)
            for i in range(possible_l):
                if possible_locations[i].startswith('C:'):
                    possible_locations.append('D:' + possible_locations[i][2:])
                else:
                    possible_locations.append('C:' + possible_locations[i][2:])
            for p in possible_locations:
                if os.path.isfile(p):
                    self.emuhawk_exe = p
                    return self.emuhawk_exe

        if self.emuhawk_exe is None:
            raise EmuhawkException('Emuhawk.exe could not be found, please set it manually '
                                   'or set `emuhawk` as a environment variable')

    def read_mmf(self, mmf_name, mmf_len):
        """

        :param mmf_name:
        :param mmf_len:
        :return:
        """
        with mmap.mmap(-1, mmf_len, mmf_name, mmap.ACCESS_READ) as f:
            return f.read()

    def wait_for_mmf(self):
        size = int(self.socket_server.listen(run_time=10))
        print(self.read_mmf('BizhawkTemp_main', size))


class SocketServer:
    def __init__(self, ip='192.168.178.39', port=9999, timeout=100, no_of_connections=10):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.no_of_connections = no_of_connections
        self.serversocket = None
        self.connection = None
        #self.create_connection()

    def create_connection(self):
        print('establishing connection')
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(self.serversocket)
        self.serversocket.settimeout(self.timeout)
        #self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket.bind((self.ip, self.port))
        self.serversocket.listen(self.no_of_connections)
        print("listening")
        self.connection, self.address = self.serversocket.accept()
        print(self.connection, self.address)
        print('connection finished')
        #self.connection.settimeout(1)

    def connect(self):
        self.connection, self.address = self.serversocket.accept()
        print(self.connection, self.address)
    def listen(self, run_time=10):

        incoming = b''
        start_time = time.time()

        while run_time < 0 or time.time() - start_time < run_time:
            try:
                buf = self.connection.recv(4096)
            except ConnectionResetError:
                buf = ''

            if len(buf) == 0:
                print('reconnect')
                self.connect()
            else:
                incoming += buf
                if buf[-1] == 130 or buf == b'\r\n':
                    self.connection.sendall(b"ack")
                    break
                print('SOCKET received')
        return incoming


class httpServerHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, response=None, connection=None):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')

        if response is not None:
            self.send_header("Content-Length", len(response))
        if connection is not None:
            self.send_header('Connection', connection)
        self.end_headers()

    def do_GET(self):
        print('GET received')
        self.protocol_version = "HTTP/1.1"
        response = b"<html><body><h1>hi!</h1></body></html>"
        self._set_headers(response=response)
        self.wfile.write(response)

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        print('POST received')
        response = b"<html><body>OK</body></html>"
        self.protocol_version = "HTTP/1.1"
        self._set_headers(response=response, connection='keep-alive')
        self.wfile.write(response)




    def log_message(self, format, *args):
        return

if __name__ == '__main__':
    print('Starting HTTP server')

    httpd = http.server.HTTPServer(('', 9876), httpServerHandler)
    #httpd.serve_forever()
    thread_http = threading.Thread(target=httpd.serve_forever)
    thread_http.start()

    print('Starting socket server')
    s = SocketServer()
    s.create_connection()
    while True:
        s.listen()
