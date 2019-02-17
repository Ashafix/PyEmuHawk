import os
import sys
import pathlib
import mmap
import socket
import time
import http.server
import threading
import argparse


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
        Tries to find the location of EmuHawk.exe
        :return: string, pull path of EmuHawk.exe
        """
        if os.getenv('emuhawk') is not None:
            self.emuhawk_exe = os.getenv('emuhawk')
            return self.emuhawk_exe

        possible_locations = []
        try:
            possible_locations.append(os.path.join(pathlib.Path.home(),
                                                   r'Documents\GitHub\BizHawk\output\EmuHawk.exe'))
        except:
            possible_locations.append(os.path.join(os.path.expanduser('~'),
                                                   r'Documents\GitHub\BizHawk\output\EmuHawk.exe'))
        if os.getenv('ProgramFiles') is not None:
            possible_locations.append(
                os.path.join(os.getenv('ProgramFiles'), r'BizHawk\output\EmuHawk.exe'))
            possible_locations.append(
                os.path.join(os.getenv('ProgramFiles'), r'BizHawk\EmuHawk.exe'))
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
        Reads a Memory Mapped File with the specified name and length
        :param mmf_name: string, the path of the Memory Mapped File
        :param mmf_len: int, the length of the file content
        :return: the content of the file
        """
        with mmap.mmap(-1, mmf_len, mmf_name, mmap.ACCESS_READ) as f:
            return f.read()


class SocketServer:
    """
    A simple socket server implementation
    """
    def __init__(self, ip=None, port=9990, timeout=None, no_of_connections=10, verbose=True, logger=sys.stdout):
        
        # try to autodetect local IP address
        if ip is None:
            self.ip = socket.gethostbyname(socket.gethostname())
        else:
            self.ip = ip
        self.port = port
        self.timeout = timeout
        self.no_of_connections = no_of_connections
        self.serversocket = None
        self.connection = None
        self.address = None
        self.logger = logger
        self.verbose = verbose

    def __print(self, message):
        if self.verbose:
            self.logger.write(message)

    def create_connection(self):
        self.__print('establishing connection\n')
        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.settimeout(self.timeout)
        self.serversocket.bind((self.ip, self.port))
        self.serversocket.listen(self.no_of_connections)
        self.__print('waiting for connection\n')
        self.connection, self.address = self.serversocket.accept()
        self.__print('{}, {}'.format(self.connection, self.address))
        self.__print('connection finished\n')

    def connect(self):
        self.connection, self.address = self.serversocket.accept()
        self.__print('{};{}\n'.format(self.connection, self.address))

    def listen(self, run_time=10):

        incoming = b''
        start_time = time.time()

        while run_time < 0 or time.time() - start_time < run_time:
            try:
                buf = self.connection.recv(4096)
            except ConnectionResetError:
                buf = ''

            if len(buf) == 0:
                self.__print('reconnect\n')
                self.connect()
            else:
                self.__print('SOCKET received\n')
                incoming += buf
                if buf[-1] == 130 or buf == b'\r\n':
                    self.connection.sendall(b'ack')
                    break
               
        return incoming


class HttpServerHandler(http.server.BaseHTTPRequestHandler):
    """
    A simple HTTP server capable of handling GET and POST requests
    """
    def _set_headers(self, response=None, connection=None):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')

        if response is not None:
            self.send_header('Content-Length', len(response))
        if connection is not None:
            self.send_header('Connection', connection)
        self.end_headers()

    def do_GET(self):
        sys.stdout.write('GET received\n')
        self.protocol_version = 'HTTP/1.1'
        response = b'<html><body><h1>hi!</h1></body></html>'
        self._set_headers(response=response)
        self.wfile.write(response)

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        sys.stdout.write('POST received\n')
        response = b'<html><body>OK</body></html>'
        self.protocol_version = 'HTTP/1.1'
        self._set_headers(response=response, connection='keep-alive')
        self.wfile.write(response)

    def log_message(self, format, *args):
        return


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--http_port', help='The port of the HTTP server, default:9876', type=int, default=9876)
    parser.add_argument('--socket_port', help='The port of the socket server, default:9990', type=int, default=9990)
    args = parser.parse_args(args)

    print('Starting HTTP server')
    httpd = http.server.HTTPServer(('', args.http_port), HttpServerHandler)
    print('Running HTTP server at: {}:{}'.format(httpd.server_address[0], httpd.server_address[1]))
    if httpd.server_address[0] == '0.0.0.0':
        print('HTTP server address is {}, probably you can use localhost or {} as its IP address'.format(httpd.server_address[0],
                                                                                                         socket.gethostbyname(
                                                                                                             socket.gethostname())
                                                                                                         ))
        http_address = 'http://{}:{}'.format(socket.gethostbyname(socket.gethostname()), httpd.server_address[1])
    else:
        http_address = 'http://{}:{}'.format(httpd.server_address[0], httpd.server_address[1])

    print('Starting socket server')
    thread_http = threading.Thread(target=httpd.serve_forever)
    thread_http.start()

    s = SocketServer(port=args.socket_port)
    print('Socket server running at {}:{}'.format(s.ip, s.port))
    print('{sep}Settings for Emuhawk:'.format(sep=os.linesep))
    print('--socket_ip={ip} --socket_port={port} --url_get={http}/get --url_post={http}/post{sep}'.format(ip=s.ip,
                                                                                                          port=s.port,
                                                                                                          http=http_address,
                                                                                                          sep=os.linesep))

    s.create_connection()
    while True:
        s.listen()


if __name__ == '__main__':
    main(sys.argv[1:])
