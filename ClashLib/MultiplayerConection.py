import time
import threading
import socket
import json

class P2P:
    def __init__(self, on_receive=None, on_connect=None, port=10224, local_test=False):
        """
        
        Initializes the P2P connection with optional parameters for receiving data,
        port number, and local testing mode.
        on_receive (function): A lambda function to handle received data.
        port (int): The port number for the connection.
        local_test (bool): If True, runs in local test mode (same machine).

        on_receive should be a function that takes two parameters:
            - data (dict): The received data as a dictionary.
            - addr (tuple): The address of the sender as a (ip, port) tuple
        """
        self.initial_timestamp = None
        self.connected_players = []
        self.max_players = 2 # me and the peer
        self.PORT = port
        self.local_test = local_test
        self.HOST = '127.0.0.1' if local_test else self.get_local_ip()
        self.stop_broadcast = threading.Event()
        self.stop_listening = threading.Event()
        self.time_offset = 0
        self.on_receive = on_receive
        self.on_connect = on_connect
        self.is_host = False
        self.peer_address = None
        self.game_socket = None
        
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
        finally:
            s.close()

    def broadcast_host(self, interval=1.0):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not self.local_test:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            target = ('<broadcast>', self.PORT)
        else:
            target = ('127.0.0.1', self.PORT + 1)
        message = json.dumps({"host_ip": self.HOST}).encode('utf-8')
        while not self.stop_broadcast.is_set():
            sock.sendto(message, target)
            time.sleep(interval)
        sock.close()

    def start_peer_host(self):
        self.stop_peer_host()
        
        time.sleep(0.5) # wait until previous threads close
        
        self.is_host = True
        self.stop_broadcast.clear()
        self.stop_listening.clear()
        threading.Thread(target=self.broadcast_host, daemon=True).start()
        threading.Thread(target=self.listen_for_clients, daemon=True).start()
        print(f"Broadcasting host IP {self.HOST} on port {self.PORT}")

    def stop_peer_host(self):
        self.stop_broadcast.set()
        self.stop_listening.set()
        if self.game_socket:
            self.game_socket.close()
        print("Stopped broadcasting host IP")

    def listen_for_clients(self):
        """
        Listen for incoming connection requests from clients.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.HOST, self.PORT))
        sock.settimeout(1.0)  # Timeout para poder verificar stop_broadcast
        
        while not self.stop_broadcast.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                if msg.get("request") == "connect":
                    host_time = time.time()
                    response = json.dumps({"status": "connected", "host_time": host_time}).encode('utf-8')
                    sock.sendto(response, addr)
                    if addr not in self.connected_players:
                        self.connected_players.append(addr)
                        self.peer_address = addr
                        if self.on_connect:
                            self.on_connect(addr)
                            self.initial_timestamp = time.time()
                        print(f"Client connected: {addr}")
                        self.stop_broadcast.set()  # Dejar de aceptar más conexiones
                        # Iniciar escucha de eventos de juego
                        self.start_game_communication()
            except socket.timeout:
                continue
            except:
                continue
        sock.close()

    def connect_as_peer_client(self, host):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.local_test:
            sock.bind(('', self.PORT + 1))
        sock.settimeout(5)
        try:
            t1 = time.time()
            message = json.dumps({"request": "connect"}).encode('utf-8')
            sock.sendto(message, (host, self.PORT))
            data, addr = sock.recvfrom(1024)
            t3 = time.time()
            response = json.loads(data.decode('utf-8'))
            if response.get("status") == "connected":
                host_time = response["host_time"]
                rtt = t3 - t1
                self.time_offset = host_time - (t1 + rtt / 2)
                self.peer_address = (host, self.PORT)
                if self.on_connect:
                    self.on_connect(addr)
                    self.initial_timestamp = time.time()
                print(f"Connected to host {host}, time offset: {self.time_offset:.4f}s")
                # Iniciar escucha de eventos de juego
                self.start_game_communication()
                return True
            return False
        except socket.timeout:
            print("Connection timed out")
            return False
        finally:
            sock.close()

    def start_game_communication(self):
        """Inicia la comunicación bidireccional para el juego"""
        self.stop_listening.clear()
        # Crear socket para comunicación de juego
        if self.is_host:
            game_port = self.PORT + 10  # Puerto diferente para datos de juego
        else:
            game_port = self.PORT + 11  # Puerto diferente para cliente
            
        self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.game_socket.bind((self.HOST, game_port))
        
        # Iniciar thread para escuchar eventos
        threading.Thread(target=self.listen_for_events, daemon=True).start()
        print("Game communication started")

    def listen_for_events(self):
        """Escucha constantemente los eventos del otro jugador"""
        if not self.game_socket:
            return
            
        self.game_socket.settimeout(0.1)  # Timeout corto para respuesta rápida
        
        while not self.stop_listening.is_set():
            try:
                data, addr = self.game_socket.recvfrom(1024)
                try:
                    game_data = json.loads(data.decode('utf-8'))
                    # Ejecutar la función lambda on_receive si está definida
                    if self.on_receive:
                        self.on_receive(game_data, addr)
                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {data}")
                except Exception as e:
                    print(f"Error processing received data: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if not self.stop_listening.is_set():
                    print(f"Error listening for events: {e}")
                break
                
        if self.game_socket:
            self.game_socket.close()

    def send_data(self, data):
        """Envía datos al otro jugador"""
        if not self.peer_address or not self.game_socket:
            print("No peer connected to send data")
            return False
            
        try:
            # Determinar puerto de destino
            if self.is_host:
                target_port = self.PORT + 11  # Cliente escucha en este puerto
                target_addr = (self.peer_address[0], target_port)
            else:
                target_port = self.PORT + 10  # Host escucha en este puerto
                target_addr = (self.peer_address[0], target_port)
            
            # Agregar timestamp para sincronización
            data_with_time = {
                "data": data,
                "timestamp": self.get_synced_time()
            }
            
            message = json.dumps(data_with_time).encode('utf-8')
            self.game_socket.sendto(message, target_addr)
            return True
            
        except Exception as e:
            print(f"Error sending data: {e}")
            return False

    def get_synced_time(self):
        return time.time() + self.time_offset

    def get_hosts(self, timeout=5):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if not self.local_test:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', self.PORT if not self.local_test else self.PORT + 1))
        sock.settimeout(timeout)
        hosts = set()
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                msg = json.loads(data.decode('utf-8'))
                host_ip = msg.get("host_ip")
                if host_ip:
                    hosts.add(host_ip)
            except:
                continue
        sock.close()
        return list(hosts)
    
    def disconnect(self):
        """Desconecta y limpia recursos"""
        self.stop_peer_host()
        print("Disconnected from P2P network")

    def start_as_host(self):
        self.start_peer_host()
        try:
            while True:
                print(f"Synced time (host): {self.get_synced_time():.2f} | Connected players: {len(self.connected_players)}")
                time.sleep(1)
        except KeyboardInterrupt:
            self.disconnect()

    def start_as_client(self):
        hosts = self.get_hosts()
        if not hosts:
            print("No hosts found")
            return
        host = hosts[0]
        if self.connect_as_peer_client(host):
            try:
                while True:
                    print(f"Synced time (client): {self.get_synced_time():.2f}")
                    time.sleep(1)
            except KeyboardInterrupt:
                self.disconnect()
        else:
            print("Failed to connect to host")








# EJEMPLO DE USO DE ESTA HERMOSA ESTRUCTURA P2P


# Ejemplo de uso con función lambda
def example_on_receive(data, addr):
    """Ejemplo de función para manejar datos recibidos"""
    print(f"Received from {addr}: {data}")
    if 'data' in data:
        game_data = data['data']
        timestamp = data.get('timestamp', 0)
        print(f"Game data: {game_data}, Timestamp: {timestamp:.2f}")

def example_on_connect(addr):
    print(f"Connected to peer at {addr}")


if __name__ == "__main__":
    mode = input("Run as host (h) or client (c)? ").lower()
    local_test = input("Test on same machine? (y/n): ").lower() == 'y'
    
    # Crear P2P con función lambda para manejar datos recibidos
    p2p = P2P(on_receive=lambda data, addr: example_on_receive(data, addr), local_test=local_test, on_connect=example_on_connect)

    if mode == "h":
        print("Starting as host...")
        p2p.start_peer_host()
        try:
            while True:
                # Ejemplo: enviar datos cada 3 segundos
                time.sleep(3)
                if p2p.connected_players:
                    test_data = {
                        "player_position": {"x": 100, "y": 200},
                        "action": "move",
                        "player_id": "host"
                    }
                    p2p.send_data(test_data)
                    print("Sent test data to client")
                print(f"Synced time (host): {p2p.get_synced_time():.2f} | Connected: {len(p2p.connected_players)}")
        except KeyboardInterrupt:
            p2p.disconnect()
            
    elif mode == "c":
        print("Starting as client...")
        hosts = p2p.get_hosts()
        if not hosts:
            print("No hosts found")
        else:
            host = hosts[0]
            if p2p.connect_as_peer_client(host):
                try:
                    while True:
                        # Ejemplo: enviar datos cada 4 segundos
                        time.sleep(4)
                        test_data = {
                            "player_position": {"x": 50, "y": 150},
                            "action": "jump",
                            "player_id": "client"
                        }
                        p2p.send_data(test_data)
                        print("Sent test data to host")
                        print(f"Synced time (client): {p2p.get_synced_time():.2f}")
                except KeyboardInterrupt:
                    p2p.disconnect()
            else:
                print("Failed to connect to host")
    else:
        print("Invalid option")