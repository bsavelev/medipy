##########################################################################
# MediPy - Copyright (C) Universite de Strasbourg
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

import logging
import multiprocessing
import select
import socket
import SocketServer
import time

try :
    import paramiko
except ImportError :
    logging.warning("medipy.io.dicom.SSHTunnelConnect not usable: cannot find paramiko package")

from connection_base import ConnectionBase

class SSHTunnelConnection(ConnectionBase) :
    """ DICOM network connection through a SSH tunnel.
    
        The tunnel is as follows :
        
        (localhost, local_port) <-> (remote_host, 22) <-> (remote_host, remote_port)
    """
    
    def __init__(self, remote_host, remote_port, calling_ae_title, called_ae_title, 
                 username, password, local_port=None, connect=False) :
        
        if local_port is None :
            # Let the OS pick an available port by binding to port 0
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", 0))
            self._local_port = s.getsockname()[1]
            s.close()
        else :
            self._local_port = local_port

        #Properties attributes
        self._remote_host=None
        self._remote_port=None
        self._username=None
        self._password=None
        self._connected = False
        
        self._set_remote_host(remote_host)
        self._set_remote_port(remote_port)
        self._set_password(password)
        self._set_user(username)

        ConnectionBase.__init__(self, "localhost", self._local_port, calling_ae_title, called_ae_title, connect)

    def connect(self) :
        if not self.connected:
            pipe = multiprocessing.Pipe()
            self.process = multiprocessing.Process(
                target=SSHTunnelConnection._start_tunnel, 
                args=(self._remote_host, self._remote_port, self._username, self._password, self._local_port, pipe))
            self.process.daemon = False
            self.process.start()
			
            # Wait for the child process to give some information about its success
            while(not pipe[0].poll(0.005)) :
                pass
            exception = pipe[0].recv()
            if exception :
                # Kill the child process and propagate the exception
                self._shutdown_tunnel()
                raise exception
            
            self._connected = True

    def disconnect(self):
        if self.connected:
            self._shutdown_tunnel()

    ##############
    # Properties #
    ##############
    def _get_remote_host(self):
        return self._remote_host

    def _set_remote_host(self,host):
        if self.connected:
            self.disconnect()
            self._remote_host = host
            self.connect()
        else :
            self._remote_host = host

    def _get_remote_port(self):
        return self._remote_port

    def _set_remote_port(self,port):
        if self.connected:
            self.disconnect()
            self._remote_port = port
            self.connect()
        else :
            self._remote_port = port

    def _get_user(self):
        return self._username

    def _set_user(self,user):
        if self.connected:
            self.disconnect()
            self._username = user
            self.connect()
        else :
            self._username = user

    def _get_password(self):
        return self._password

    def _set_password(self,password):
        if self.connected:
            self.disconnect()
            self._password = password
            self.connect()
        else:
            self._password = password

    def _get_connected(self):
        return self._connected

    remote_host = property(_get_remote_host,_set_remote_host)
    remote_port = property(_get_remote_port,_set_remote_port)
    user = property(_get_user,_set_user)
    password = property(_get_password,_set_password)
    connected = property(_get_connected)
    
    ############################
    # Tunnel related functions #
    ############################
    
    @staticmethod
    def _start_tunnel(remote_host, remote_port, username, password, local_port, pipe) :
        """ Start the tunnel to the remote host. This function is supposed to
            be executed in a multiprocessing.Process, so exceptions are caught
            and returned using pipe[1].send().
        """
        
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try :
            client.connect(remote_host, username=username, password=password)
        except Exception as e :
            pipe[1].send(e)
            return
        else :
            pipe[1].send(None)
        
        SSHTunnelConnection._forward_tunnel(
            local_port, remote_host, remote_port, client.get_transport())
    
    @staticmethod
    def _forward_tunnel(local_port, remote_host, remote_port, transport):
        """ Start the forwarding server. This function is taken from the
            Paramiko distribution.
        """
        
        # this is a little convoluted, but lets me configure things for the Handler
        # object.  (SocketServer doesn't give Handlers any way to access the outer
        # server normally.)
        class SubHandler(Handler):
            chain_host = remote_host
            chain_port = remote_port
            ssh_transport = transport
        
        server = SocketServer.ThreadingTCPServer(("", local_port), SubHandler)
        server.daemon_threads = True
        server.allow_reuse_address = True
        
        server.serve_forever()
    
    def _shutdown_tunnel(self):
        """ Destroy the tunnel by terminating the tunnel process.
        """
        
        while(self.process.is_alive()) :
            self.process.terminate()
            time.sleep(0.005)
        self._connected = False

class Handler(SocketServer.BaseRequestHandler):
    """ Handler forwarding the data between a TCPServer and a Paramiko channel.
    """
    
    def handle(self):
        try:
            channel = self.ssh_transport.open_channel(
                "direct-tcpip", (self.chain_host, self.chain_port),
                self.request.getpeername())
        except Exception, e:
            return
        
        if channel is None:
            return
        
        done = False
        while not done :
            rlist = select.select([self.request, channel], [], [])[0]
            if self.request in rlist:
                data = self.request.recv(1024)
                if len(data) == 0:
                    done = True
                channel.send(data)
            if channel in rlist :
                data = channel.recv(1024)
                if len(data) == 0:
                    done = True
                self.request.send(data)
        
        channel.close()
        self.request.close()
