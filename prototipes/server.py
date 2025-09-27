import socket
import threading
import json
import time

HOST = '127.0.0.1'
PORT = 65432
clients = []
lanzamientos = []

def handle_client(conn, addr):
    """Maneja la comunicación con un cliente específico."""
    print(f"Conexión establecida con {addr}")
    clients.append(conn)

    try:
        while True:
            data = conn.recv(1024*5)
            if not data:
                break
            
            message = json.loads(data.decode('utf-8'))
            
            if message['action'] == 'place_entity':
                # Agregar la marca de tiempo del servidor al lanzamiento
                message['timestamp'] = time.time()
                lanzamientos.append(message)
                print(f"Nuevo lanzamiento de {addr}: {message}")
                
                # Sincroniza a ambos jugadores enviándoles la lista completa
                broadcast(lanzamientos)
    except (ConnectionResetError, ConnectionAbortedError):
        print(f"Cliente {addr} desconectado.")
    finally:
        clients.remove(conn)
        conn.close()

def broadcast(message):
    """Envía un mensaje a todos los clientes conectados."""
    json_message = json.dumps(message).encode('utf-8')
    for client in clients:
        try:
            client.sendall(json_message)
        except:
            client.close()
            if client in clients:
                clients.remove(client)

def main():
    """Función principal para iniciar el servidor."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)
    print("Servidor iniciado, esperando a 2 jugadores...")

    while len(clients) < 2:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

    print("Ambos jugadores conectados. ¡Comienza el juego!")

if __name__ == '__main__':
    main()