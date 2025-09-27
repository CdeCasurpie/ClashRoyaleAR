import pygame
import socket
import threading
import json
import time
import math
import sys
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from enum import Enum

# Configuración
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 1152
FPS = 60
SIMULATION_FPS = 25
GRID_ROWS = 32
GRID_COLS = 18
CELL_WIDTH = SCREEN_WIDTH // GRID_COLS
CELL_HEIGHT = SCREEN_HEIGHT // GRID_ROWS

# Colores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (100, 255, 100)
BLUE = (100, 100, 255)
RED = (255, 100, 100)
PURPLE = (156, 39, 176)
ORANGE = (255, 152, 0)

class EntityType(Enum):
    TORRE = "torre"
    ESQUELETO = "esqueleto"

class Event:
    def __init__(self, timestamp: float, event_type: str, data: dict, player_id: int):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
        self.player_id = player_id

class Entity(ABC):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        self.pos = pos  # (row, col)
        self.player_id = player_id
        self.entity_id = entity_id
        self.hp = 100
        self.max_hp = 100
    
    @abstractmethod
    def update(self, dt: float):
        pass
    
    @abstractmethod
    def render(self, screen, cell_width: int, cell_height: int):
        pass

class Torre(Entity):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int, torre_type: str):
        super().__init__(pos, player_id, entity_id)
        self.torre_type = torre_type  # "principal", "izquierda", "derecha"
        self.hp = 2000 if torre_type == "principal" else 1500
        self.max_hp = self.hp
    
    def update(self, dt: float):
        pass
    
    def render(self, screen, cell_width: int, cell_height: int):
        x = self.pos[1] * cell_width
        y = self.pos[0] * cell_height
        
        # Color según jugador
        color = PURPLE if self.torre_type == "principal" else ORANGE
        pygame.draw.rect(screen, color, (x, y, cell_width, cell_height))
        
        # Símbolo
        font = pygame.font.Font(None, 24)
        symbol = "♔" if self.torre_type == "principal" else "♖"
        text = font.render(symbol, True, WHITE)
        text_rect = text.get_rect(center=(x + cell_width//2, y + cell_height//2))
        screen.blit(text, text_rect)

class Tropa(Entity):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        super().__init__(pos, player_id, entity_id)
        self.target_pos = None
        self.speed = 1.0  # cells per second

class Esqueleto(Tropa):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        super().__init__(pos, player_id, entity_id)
        self.hp = 67
        self.max_hp = 67
        self.damage = 67
    
    def update(self, dt: float):
        # Por ahora, movimiento simple hacia el río
        if self.player_id == 1:
            # Jugador 1 va hacia abajo
            target_row = GRID_ROWS - 1
        else:
            # Jugador 2 va hacia arriba
            target_row = 0
        
        if self.pos[0] != target_row:
            self.pos = (self.pos[0] + (1 if self.player_id == 1 else -1), self.pos[1])
    
    def render(self, screen, cell_width: int, cell_height: int):
        x = self.pos[1] * cell_width + cell_width // 2
        y = self.pos[0] * cell_height + cell_height // 2
        
        color = RED if self.player_id == 1 else BLUE
        pygame.draw.circle(screen, color, (x, y), min(cell_width, cell_height) // 4)

class Card:
    def __init__(self, name: str, cost: int, entity_type: EntityType, image_path: str = None):
        self.name = name
        self.cost = cost
        self.entity_type = entity_type
        self.image_path = image_path
    
    def create_entity(self, pos: Tuple[int, int], player_id: int, entity_id: int) -> Entity:
        if self.entity_type == EntityType.ESQUELETO:
            return Esqueleto(pos, player_id, entity_id)
        elif self.entity_type == EntityType.TORRE:
            return Torre(pos, player_id, entity_id, "principal")
        else:
            raise ValueError(f"Tipo de entidad no implementado: {self.entity_type}")

class Menu:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.elixir = 10  # Elixir inicial
        self.max_elixir = 10
        self.elixir_regen_rate = 1.0  # elixir per second
        self.elixir_timer = 0.0
        
        # Cartas disponibles
        self.available_cards = [
            Card("Esqueleto", 1, EntityType.ESQUELETO),
            Card("Esqueleto", 1, EntityType.ESQUELETO),
            Card("Esqueleto", 1, EntityType.ESQUELETO),
            Card("Esqueleto", 1, EntityType.ESQUELETO)
        ]
        
        self.selected_card_index = 0
    
    def update(self, dt: float):
        # Regenerar elixir
        self.elixir_timer += dt
        if self.elixir_timer >= 1.0 / self.elixir_regen_rate:
            if self.elixir < self.max_elixir:
                self.elixir += 1
            self.elixir_timer = 0.0
    
    def select_card(self, index: int):
        if 0 <= index < len(self.available_cards):
            self.selected_card_index = index
    
    def can_place_card(self, card_index: int = None) -> bool:
        if card_index is None:
            card_index = self.selected_card_index
        
        if card_index < 0 or card_index >= len(self.available_cards):
            return False
        
        card = self.available_cards[card_index]
        return self.elixir >= card.cost
    
    def get_selected_card(self) -> Optional[Card]:
        if self.can_place_card():
            return self.available_cards[self.selected_card_index]
        return None
    
    def spend_elixir(self, amount: int):
        self.elixir = max(0, self.elixir - amount)

class Board:
    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.next_entity_id = 0
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
    
    def add_entity(self, entity: Entity):
        self.entities[entity.entity_id] = entity
        row, col = entity.pos
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            self.grid[row][col] = entity.entity_id
    
    def remove_entity(self, entity_id: int):
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            row, col = entity.pos
            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                self.grid[row][col] = None
            del self.entities[entity_id]
    
    def get_next_entity_id(self) -> int:
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        return entity_id
    
    def is_valid_position(self, row: int, col: int) -> bool:
        return (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS and 
                self.grid[row][col] is None)
    
    def update(self, dt: float):
        for entity in list(self.entities.values()):
            entity.update(dt)
    
    def render(self, screen):
        # Dibujar grid
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = col * CELL_WIDTH
                y = row * CELL_HEIGHT
                
                # Fondo verde claro
                pygame.draw.rect(screen, GREEN, (x, y, CELL_WIDTH, CELL_HEIGHT))
                
                # Bordes
                pygame.draw.rect(screen, BLACK, (x, y, CELL_WIDTH, CELL_HEIGHT), 1)
        
        # Dibujar entidades
        for entity in self.entities.values():
            entity.render(screen, CELL_WIDTH, CELL_HEIGHT)

class TimeSimulationLine:
    def __init__(self):
        self.events: List[Event] = []
    
    def add_event(self, event: Event):
        # Insertar manteniendo orden por timestamp
        inserted = False
        for i, existing_event in enumerate(self.events):
            if event.timestamp < existing_event.timestamp:
                self.events.insert(i, event)
                inserted = True
                break
        if not inserted:
            self.events.append(event)
    
    def get_events_until(self, timestamp: float) -> List[Event]:
        events_until = []
        for event in self.events:
            if event.timestamp <= timestamp:
                events_until.append(event)
            else:
                break
        return events_until

class Checkpoint:
    def __init__(self, timestamp: float, board_state: Board):
        self.timestamp = timestamp
        # Crear copia profunda del estado del board
        self.entities = {}
        for entity_id, entity in board_state.entities.items():
            # Crear copia de la entidad
            if isinstance(entity, Torre):
                new_entity = Torre(entity.pos, entity.player_id, entity.entity_id, entity.torre_type)
            elif isinstance(entity, Esqueleto):
                new_entity = Esqueleto(entity.pos, entity.player_id, entity.entity_id)
            else:
                continue
            
            new_entity.hp = entity.hp
            self.entities[entity_id] = new_entity

class Sync:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.simulation_time = 0.0
        self.timeline = TimeSimulationLine()
        self.checkpoints: List[Checkpoint] = []
        self.step_duration = 1.0 / SIMULATION_FPS
        self.board = Board()
        
        # Crear torres iniciales como eventos en t=0
        self.create_initial_towers()
    
    def create_initial_towers(self):
        # Torres para jugador 1 (superior)
        torres_p1 = [
            ((2, 8), "principal"),   # Torre principal superior
            ((6, 3), "izquierda"),   # Torre izquierda superior
            ((6, 14), "derecha")     # Torre derecha superior
        ]
        
        # Torres para jugador 2 (inferior)
        torres_p2 = [
            ((29, 8), "principal"),  # Torre principal inferior
            ((25, 3), "izquierda"),  # Torre izquierda inferior
            ((25, 14), "derecha")    # Torre derecha inferior
        ]
        
        for pos, tipo in torres_p1:
            event = Event(0.0, "place_entity", {
                "entity_type": "torre",
                "pos": pos,
                "torre_type": tipo,
                "entity_id": self.board.get_next_entity_id()
            }, player_id=1)
            self.timeline.add_event(event)
        
        for pos, tipo in torres_p2:
            event = Event(0.0, "place_entity", {
                "entity_type": "torre",
                "pos": pos,
                "torre_type": tipo,
                "entity_id": self.board.get_next_entity_id()
            }, player_id=2)
            self.timeline.add_event(event)
    
    def new_event(self, coords: Tuple[int, int], card: Card) -> Optional[Event]:
        row, col = coords
        if not self.board.is_valid_position(row, col):
            return None
        
        event = Event(
            timestamp=self.simulation_time,
            event_type="place_entity",
            data={
                "entity_type": card.entity_type.value,
                "pos": (row, col),
                "entity_id": self.board.get_next_entity_id()
            },
            player_id=self.player_id
        )
        return event
    
    def process_new_event(self, event: Event):
        self.timeline.add_event(event)
        
        # Verificar si necesitamos rollback
        if event.timestamp < self.simulation_time:
            print(f"ROLLBACK necesario: evento en {event.timestamp:.3f}, sim_time: {self.simulation_time:.3f}")
            self.restore_from_checkpoint(event.timestamp)
    
    def restore_from_checkpoint(self, timestamp: float) -> bool:
        best_checkpoint = None
        for checkpoint in self.checkpoints:
            if checkpoint.timestamp <= timestamp:
                if best_checkpoint is None or checkpoint.timestamp > best_checkpoint.timestamp:
                    best_checkpoint = checkpoint
        
        if best_checkpoint:
            self.simulation_time = best_checkpoint.timestamp
            self.board.entities = best_checkpoint.entities.copy()
            
            # Reconstruir grid
            self.board.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
            for entity in self.board.entities.values():
                row, col = entity.pos
                if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                    self.board.grid[row][col] = entity.entity_id
            
            return True
        return False
    
    def advance_step(self):
        next_time = self.simulation_time + self.step_duration
        
        # Procesar eventos hasta este punto
        events_until_now = self.timeline.get_events_until(next_time)
        processed_entities = set(self.board.entities.keys())
        
        for event in events_until_now:
            if event.event_type == "place_entity":
                entity_id = event.data["entity_id"]
                if entity_id not in processed_entities:
                    # Crear entidad
                    pos = tuple(event.data["pos"])
                    entity_type = event.data["entity_type"]
                    
                    if entity_type == "torre":
                        entity = Torre(pos, event.player_id, entity_id, event.data["torre_type"])
                    elif entity_type == "esqueleto":
                        entity = Esqueleto(pos, event.player_id, entity_id)
                    else:
                        continue
                    
                    self.board.add_entity(entity)
                    processed_entities.add(entity_id)
        
        # Actualizar entidades
        self.board.update(self.step_duration)
        self.simulation_time = next_time
    
    def save_checkpoint(self):
        checkpoint = Checkpoint(self.simulation_time, self.board)
        self.checkpoints.append(checkpoint)
        
        # Eliminar checkpoints antiguos
        self.checkpoints = [cp for cp in self.checkpoints 
                           if self.simulation_time - cp.timestamp <= 4.0]

class P2P:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.socket = None
        self.connected = False
        self.other_player_ready = False
        self.sync_complete = False
        
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if self.player_id == 1:
            # Jugador 1 actúa como servidor
            self.socket.bind(('localhost', 12345))
            self.socket.listen(1)
            print("Jugador 1: Esperando conexión...")
            conn, addr = self.socket.accept()
            self.socket = conn
            print(f"Jugador 1: Conectado con {addr}")
        else:
            # Jugador 2 actúa como cliente
            print("Jugador 2: Intentando conectar...")
            self.socket.connect(('localhost', 12345))
            print("Jugador 2: Conectado")
        
        self.connected = True
        
        # Sincronización inicial
        self.synchronize_start()
    
    def synchronize_start(self):
        if self.player_id == 1:
            # Enviar señal de ready
            self.send_data({"type": "ready", "timestamp": time.time()})
            # Esperar confirmación
            data = self.receive_data()
            if data and data.get("type") == "ready_ack":
                # Enviar start simultáneo
                start_time = time.time() + 1.0  # 1 segundo en el futuro
                self.send_data({"type": "start", "start_time": start_time})
                self.sync_complete = True
        else:
            # Esperar ready del jugador 1
            data = self.receive_data()
            if data and data.get("type") == "ready":
                # Enviar confirmación
                self.send_data({"type": "ready_ack"})
                # Esperar start
                data = self.receive_data()
                if data and data.get("type") == "start":
                    # Sincronizar al tiempo especificado
                    while time.time() < data["start_time"]:
                        pass
                    self.sync_complete = True
    
    def send_event(self, event: Event):
        if self.connected:
            data = {
                "type": "game_event",
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "data": event.data,
                "player_id": event.player_id
            }
            self.send_data(data)
    
    def send_data(self, data: dict):
        try:
            json_data = json.dumps(data).encode('utf-8')
            self.socket.sendall(len(json_data).to_bytes(4, 'big'))
            self.socket.sendall(json_data)
        except:
            self.connected = False
    
    def receive_data(self) -> Optional[dict]:
        try:
            length_bytes = self.socket.recv(4)
            if not length_bytes:
                return None
            
            length = int.from_bytes(length_bytes, 'big')
            data = b''
            while len(data) < length:
                chunk = self.socket.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            
            return json.loads(data.decode('utf-8'))
        except:
            return None

class Juego:
    def __init__(self, player_id: int):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Clash Royale - Player {player_id}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        
        self.player_id = player_id
        self.running = True
        
        # Componentes
        self.p2p = P2P(player_id)
        self.sync = Sync(player_id)
        self.menu = Menu(player_id)
        
        # Estado
        self.game_started = False
        self.start_time = None
        
        # Thread para recibir eventos
        self.receive_thread = None
    
    def start_network(self):
        self.p2p.connect()
        
        # Iniciar thread para recibir eventos
        self.receive_thread = threading.Thread(target=self.network_listener)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        # Esperar sincronización
        while not self.p2p.sync_complete:
            time.sleep(0.01)
        
        self.game_started = True
        self.start_time = time.time()
        print(f"Jugador {self.player_id}: Juego iniciado!")
    
    def network_listener(self):
        while self.running and self.p2p.connected:
            data = self.p2p.receive_data()
            if data and data.get("type") == "game_event":
                event = Event(
                    data["timestamp"],
                    data["event_type"],
                    data["data"],
                    data["player_id"]
                )
                self.sync.process_new_event(event)
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.menu.select_card(0)
                elif event.key == pygame.K_2:
                    self.menu.select_card(1)
                elif event.key == pygame.K_3:
                    self.menu.select_card(2)
                elif event.key == pygame.K_4:
                    self.menu.select_card(3)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and self.game_started:
                    # Convertir coordenadas de mouse a grid
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_WIDTH
                    row = mouse_y // CELL_HEIGHT
                    
                    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                        self.place_card((row, col))
    
    def select_card(self, index: int):
        self.menu.select_card(index)
    
    def place_card(self, coords: Tuple[int, int]):
        selected_card = self.menu.get_selected_card()
        if selected_card is None:
            return  # No hay suficiente elixir o carta no válida
        
        # Crear evento
        new_event = self.sync.new_event(coords, selected_card)
        if new_event is None:
            return  # Posición no válida
        
        # Gastar elixir
        self.menu.spend_elixir(selected_card.cost)
        
        # Enviar por P2P
        self.p2p.send_event(new_event)
        
        # Procesar localmente
        self.sync.process_new_event(new_event)
    
    def update(self):
        if not self.game_started:
            return
        
        dt = 1.0 / FPS
        current_time = time.time() - self.start_time
        
        # Actualizar menu
        self.menu.update(dt)
        
        # Actualizar simulación
        time_diff = current_time - self.sync.simulation_time
        if time_diff > 0:
            steps_needed = int(time_diff / self.sync.step_duration)
            steps_this_frame = min(5, steps_needed)
            
            for _ in range(steps_this_frame):
                if self.sync.simulation_time < current_time:
                    self.sync.advance_step()
                    
                    # Guardar checkpoint periódicamente
                    if (len(self.sync.checkpoints) == 0 or 
                        self.sync.simulation_time - self.sync.checkpoints[-1].timestamp >= 0.2):
                        self.sync.save_checkpoint()
    
    def render(self):
        self.screen.fill(BLACK)
        
        if not self.game_started:
            # Pantalla de espera
            text = self.font.render("Esperando sincronización...", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
        else:
            # Renderizar board
            self.sync.board.render(self.screen)
            
            # UI del menú
            self.render_ui()
        
        pygame.display.flip()
    
    def render_ui(self):
        # Barra de elixir
        elixir_text = self.font.render(f"Elixir: {self.menu.elixir}/{self.menu.max_elixir}", True, WHITE)
        self.screen.blit(elixir_text, (10, 10))
        
        # Cartas (simplificado)
        y_offset = 50
        for i, card in enumerate(self.menu.available_cards):
            color = GREEN if i == self.menu.selected_card_index else WHITE
            card_text = self.font.render(f"{i+1}. {card.name} ({card.cost})", True, color)
            self.screen.blit(card_text, (10, y_offset + i * 30))
        
        # Instrucciones
        instructions = [
            "1-4: Seleccionar carta",
            "Click: Colocar carta",
            f"Jugador: {self.player_id}"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font.render(instruction, True, WHITE)
            self.screen.blit(text, (10, SCREEN_HEIGHT - 100 + i * 25))
    
    def run(self):
        # Iniciar red
        self.start_network()
        
        # Loop principal
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()
        if self.p2p.socket:
            self.p2p.socket.close()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['1', '2']:
        print("Uso: python juego.py [1|2]")
        sys.exit(1)
    
    player_id = int(sys.argv[1])
    juego = Juego(player_id)
    juego.run()

if __name__ == "__main__":
    main()