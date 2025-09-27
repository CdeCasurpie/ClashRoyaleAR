import pygame
import socket
import threading
import json
import time
import math
import sys
import copy
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Any
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
GRAY = (128, 128, 128)

# ===== SISTEMA DE ROLLBACK GENÉRICO =====

class Event:
    def __init__(self, timestamp: float, event_type: str, data: dict, player_id: int = None):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
        self.player_id = player_id
    
    def __repr__(self):
        return f"Event(t={self.timestamp:.3f}, type={self.event_type}, player={self.player_id})"

class TimeSimulationLine:
    def __init__(self):
        self.events: List[Event] = []
    
    def add_event(self, event: Event):
        # No permitir eventos con timestamp negativo
        if event.timestamp < 0:
            print(f"WARNING: Evento con timestamp negativo ignorado: {event.timestamp}")
            return
            
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

class SimulationState(ABC):
    @abstractmethod
    def copy(self):
        pass
    
    @abstractmethod
    def advance_step(self, timeline: TimeSimulationLine, step_duration: float):
        pass
    
    @abstractmethod
    def get_simulation_time(self) -> float:
        pass
    
    @abstractmethod
    def set_simulation_time(self, time: float):
        pass

class Checkpoint:
    def __init__(self, timestamp: float, state: SimulationState):
        self.timestamp = timestamp
        self.state = state.copy()

class RollbackSystem:
    def __init__(self, initial_state: SimulationState, simulation_fps: int = 25, 
                 checkpoint_interval: float = 0.1, checkpoint_duration: float = 4.0):
        self.state = initial_state
        self.timeline = TimeSimulationLine()
        self.checkpoints: List[Checkpoint] = []
        
        self.simulation_fps = simulation_fps
        self.step_duration = 1.0 / simulation_fps
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_duration = checkpoint_duration
        
        self.real_time = 0.0
        self.start_time = time.time()
        
        self.rollback_count = 0
        self.total_events_processed = 0
        
        # Guardar checkpoint inicial
        self.save_checkpoint()
    
    def get_real_time(self) -> float:
        return time.time() - self.start_time
    
    def get_simulation_time(self) -> float:
        return self.state.get_simulation_time()
    
    def add_event(self, event: Event):
        self.timeline.add_event(event)
        self.total_events_processed += 1
        
        if event.timestamp < self.get_simulation_time():
            print(f"ROLLBACK: evento t={event.timestamp:.3f}, sim_time={self.get_simulation_time():.3f}")
            self.perform_rollback(event.timestamp)
    
    def perform_rollback(self, target_timestamp: float):
        self.rollback_count += 1
        
        best_checkpoint = None
        for checkpoint in self.checkpoints:
            if checkpoint.timestamp <= target_timestamp:
                if best_checkpoint is None or checkpoint.timestamp > best_checkpoint.timestamp:
                    best_checkpoint = checkpoint
        
        if best_checkpoint:
            print(f"Restaurando desde checkpoint t={best_checkpoint.timestamp:.3f}")
            self.state = best_checkpoint.state.copy()
        else:
            print("No hay checkpoint disponible")
    
    def update_simulation(self):
        self.real_time = self.get_real_time()
        current_sim_time = self.get_simulation_time()
        time_diff = self.real_time - current_sim_time
        
        if time_diff > 0:
            if time_diff > 0.1:
                steps_needed = int(time_diff / self.step_duration)
                steps_this_frame = min(10, steps_needed)
            else:
                steps_this_frame = 1
            
            for _ in range(steps_this_frame):
                if self.get_simulation_time() < self.real_time:
                    self.state.advance_step(self.timeline, self.step_duration)
                    
                    if self.should_save_checkpoint():
                        self.save_checkpoint()
    
    def should_save_checkpoint(self) -> bool:
        if len(self.checkpoints) == 0:
            return True
        
        last_checkpoint_time = self.checkpoints[-1].timestamp
        current_time = self.get_simulation_time()
        return current_time - last_checkpoint_time >= self.checkpoint_interval
    
    def save_checkpoint(self):
        checkpoint = Checkpoint(self.get_simulation_time(), self.state)
        self.checkpoints.append(checkpoint)
        
        current_time = self.get_simulation_time()
        self.checkpoints = [cp for cp in self.checkpoints 
                           if current_time - cp.timestamp <= self.checkpoint_duration]
    
    def get_stats(self) -> dict:
        return {
            "real_time": self.real_time,
            "simulation_time": self.get_simulation_time(),
            "time_diff": self.real_time - self.get_simulation_time(),
            "events_in_timeline": len(self.timeline.events),
            "checkpoints": len(self.checkpoints),
            "rollback_count": self.rollback_count,
            "total_events": self.total_events_processed
        }

# ===== ENTIDADES DEL JUEGO =====

class EntityType(Enum):
    TORRE_PRINCIPAL = "torre_principal"
    TORRE_SECUNDARIA = "torre_secundaria"
    ESQUELETO = "esqueleto"

class Entity(ABC):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        self.pos = list(pos)  # [row, col] - usar lista para mutabilidad
        self.player_id = player_id
        self.entity_id = entity_id
        self.hp = 100
        self.max_hp = 100
        self.alive = True
    
    @abstractmethod
    def update(self, dt: float):
        pass
    
    @abstractmethod
    def render(self, screen, cell_width: int, cell_height: int):
        pass
    
    def copy(self):
        # Crear copia usando el mismo constructor
        new_entity = self.__class__(tuple(self.pos), self.player_id, self.entity_id)
        new_entity.hp = self.hp
        new_entity.max_hp = self.max_hp
        new_entity.alive = self.alive
        return new_entity

class Torre(Entity):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int, torre_type: str):
        super().__init__(pos, player_id, entity_id)
        self.torre_type = torre_type
        self.hp = 2000 if torre_type == "principal" else 1500
        self.max_hp = self.hp
    
    def update(self, dt: float):
        pass
    
    def render(self, screen, cell_width: int, cell_height: int):
        x = self.pos[1] * cell_width
        y = self.pos[0] * cell_height
        
        color = PURPLE if self.torre_type == "principal" else ORANGE
        pygame.draw.rect(screen, color, (x, y, cell_width, cell_height))
        
        font = pygame.font.Font(None, 24)
        symbol = "♔" if self.torre_type == "principal" else "♖"
        text = font.render(symbol, True, WHITE)
        text_rect = text.get_rect(center=(x + cell_width//2, y + cell_height//2))
        screen.blit(text, text_rect)
    
    def copy(self):
        new_torre = Torre(tuple(self.pos), self.player_id, self.entity_id, self.torre_type)
        new_torre.hp = self.hp
        new_torre.max_hp = self.max_hp
        new_torre.alive = self.alive
        return new_torre

class Tropa(Entity):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        super().__init__(pos, player_id, entity_id)
        self.speed = 0.5  # Muy lento para experimentación (0.5 cells por segundo)
        self.move_timer = 0.0

class Esqueleto(Tropa):
    def __init__(self, pos: Tuple[int, int], player_id: int, entity_id: int):
        super().__init__(pos, player_id, entity_id)
        self.hp = 67
        self.max_hp = 67
        self.damage = 67
    
    def update(self, dt: float):
        # Movimiento muy lento hacia el objetivo
        self.move_timer += dt
        move_interval = 1.0 / self.speed  # segundos por movimiento
        
        if self.move_timer >= move_interval:
            self.move_timer = 0.0
            
            # Movimiento simple hacia el lado enemigo
            if self.player_id == 1:
                # Jugador 1 va hacia abajo (filas mayores)
                if self.pos[0] < GRID_ROWS - 1:
                    self.pos[0] += 1
            else:
                # Jugador 2 va hacia arriba (filas menores)
                if self.pos[0] > 0:
                    self.pos[0] -= 1
    
    def render(self, screen, cell_width: int, cell_height: int):
        x = self.pos[1] * cell_width + cell_width // 2
        y = self.pos[0] * cell_height + cell_height // 2
        
        color = RED if self.player_id == 1 else BLUE
        pygame.draw.circle(screen, color, (x, y), min(cell_width, cell_height) // 4)
        
        # Mostrar ID de la entidad
        font = pygame.font.Font(None, 16)
        id_text = font.render(str(self.entity_id), True, WHITE)
        screen.blit(id_text, (x - 8, y + 8))
    
    def copy(self):
        new_esqueleto = Esqueleto(tuple(self.pos), self.player_id, self.entity_id)
        new_esqueleto.hp = self.hp
        new_esqueleto.max_hp = self.max_hp
        new_esqueleto.alive = self.alive
        new_esqueleto.speed = self.speed
        new_esqueleto.move_timer = self.move_timer
        return new_esqueleto

# ===== SISTEMA DE CARTAS =====

class Card:
    def __init__(self, name: str, cost: int, entity_type: EntityType, image_path: str = None):
        self.name = name
        self.cost = cost
        self.entity_type = entity_type
        self.image_path = image_path
    
    def create_entity(self, pos: Tuple[int, int], player_id: int, entity_id: int) -> Entity:
        if self.entity_type == EntityType.ESQUELETO:
            return Esqueleto(pos, player_id, entity_id)
        elif self.entity_type == EntityType.TORRE_PRINCIPAL:
            return Torre(pos, player_id, entity_id, "principal")
        elif self.entity_type == EntityType.TORRE_SECUNDARIA:
            return Torre(pos, player_id, entity_id, "secundaria")
        else:
            raise ValueError(f"Tipo de entidad no implementado: {self.entity_type}")

class Menu:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.elixir = 5  # Elixir inicial
        self.max_elixir = 10
        self.elixir_regen_rate = 1.0  # elixir per second
        self.elixir_timer = 0.0
        
        # Cartas disponibles (deck simple)
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
    
    def spend_elixir(self, amount: int) -> bool:
        if self.elixir >= amount:
            self.elixir -= amount
            return True
        return False

# ===== BOARD COMO SIMULATION STATE =====

class ClashRoyaleBoard(SimulationState):
    def __init__(self):
        self.simulation_time = 0.0
        self.entities: Dict[int, Entity] = {}
        self.next_entity_id = 0
        self.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        
        # Crear torres iniciales
        self.create_initial_towers()
    
    def create_initial_towers(self):
        # Torres para jugador 1 (superior)
        torres_p1 = [
            ((2, 8), "principal"),
            ((6, 3), "secundaria"),
            ((6, 14), "secundaria")
        ]
        
        # Torres para jugador 2 (inferior)
        torres_p2 = [
            ((29, 8), "principal"),
            ((25, 3), "secundaria"),
            ((25, 14), "secundaria")
        ]
        
        for pos, tipo in torres_p1:
            entity_id = self.get_next_entity_id()
            torre = Torre(pos, 1, entity_id, tipo)
            self.add_entity(torre)
        
        for pos, tipo in torres_p2:
            entity_id = self.get_next_entity_id()
            torre = Torre(pos, 2, entity_id, tipo)
            self.add_entity(torre)
    
    def get_next_entity_id(self) -> int:
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        return entity_id
    
    def add_entity(self, entity: Entity):
        self.entities[entity.entity_id] = entity
        row, col = entity.pos
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            self.grid[row][col] = entity.entity_id
    
    def is_valid_position(self, row: int, col: int) -> bool:
        return (0 <= row < GRID_ROWS and 0 <= col < GRID_COLS and 
                self.grid[row][col] is None)
    
    def copy(self):
        new_board = ClashRoyaleBoard()
        new_board.simulation_time = self.simulation_time
        new_board.next_entity_id = self.next_entity_id
        
        # Copiar entidades
        new_board.entities = {}
        for entity_id, entity in self.entities.items():
            new_board.entities[entity_id] = entity.copy()
        
        # Reconstruir grid
        new_board.grid = [[None for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        for entity in new_board.entities.values():
            row, col = entity.pos
            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                new_board.grid[row][col] = entity.entity_id
        
        return new_board
    
    def advance_step(self, timeline: TimeSimulationLine, step_duration: float):
        next_time = self.simulation_time + step_duration
        
        # Procesar eventos hasta este momento
        events_to_process = timeline.get_events_until(next_time)
        existing_entity_ids = set(self.entities.keys())
        
        for event in events_to_process:
            if event.event_type == "place_entity":
                entity_id = event.data.get("entity_id")
                if entity_id is not None and entity_id not in existing_entity_ids:
                    self.create_entity_from_event(event)
                    existing_entity_ids.add(entity_id)
        
        # Actualizar entidades existentes
        for entity in list(self.entities.values()):
            if entity.alive:
                # Limpiar posición anterior del grid
                old_row, old_col = entity.pos
                if (0 <= old_row < GRID_ROWS and 0 <= old_col < GRID_COLS and
                    self.grid[old_row][old_col] == entity.entity_id):
                    self.grid[old_row][old_col] = None
                
                # Actualizar entidad
                entity.update(step_duration)
                
                # Actualizar posición en grid
                new_row, new_col = entity.pos
                if 0 <= new_row < GRID_ROWS and 0 <= new_col < GRID_COLS:
                    self.grid[new_row][new_col] = entity.entity_id
        
        self.simulation_time = next_time
    
    def create_entity_from_event(self, event: Event):
        pos = tuple(event.data["pos"])
        entity_id = event.data["entity_id"]
        entity_type = event.data["entity_type"]
        player_id = event.player_id
        
        if entity_type == "esqueleto":
            entity = Esqueleto(pos, player_id, entity_id)
        elif entity_type == "torre_principal":
            entity = Torre(pos, player_id, entity_id, "principal")
        elif entity_type == "torre_secundaria":
            entity = Torre(pos, player_id, entity_id, "secundaria")
        else:
            print(f"WARNING: Tipo de entidad desconocido: {entity_type}")
            return
        
        self.add_entity(entity)
        print(f"Entidad creada: {entity_type} en {pos} para jugador {player_id}")
    
    def get_simulation_time(self) -> float:
        return self.simulation_time
    
    def set_simulation_time(self, time: float):
        self.simulation_time = time
    
    def render(self, screen):
        # Dibujar grid
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x = col * CELL_WIDTH
                y = row * CELL_HEIGHT
                
                # Fondo según zona
                if 15 <= row <= 16:  # Río
                    color = BLUE if 2 <= col <= 4 or 13 <= col <= 15 else GRAY
                else:
                    color = GREEN
                
                pygame.draw.rect(screen, color, (x, y, CELL_WIDTH, CELL_HEIGHT))
                pygame.draw.rect(screen, BLACK, (x, y, CELL_WIDTH, CELL_HEIGHT), 1)
        
        # Dibujar entidades
        for entity in self.entities.values():
            if entity.alive:
                entity.render(screen, CELL_WIDTH, CELL_HEIGHT)

# ===== RED P2P =====

class P2P:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.socket = None
        self.connected = False
        self.sync_complete = False
        
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if self.player_id == 1:
            self.socket.bind(('localhost', 12345))
            self.socket.listen(1)
            print("Jugador 1: Esperando conexión...")
            conn, addr = self.socket.accept()
            self.socket = conn
            print(f"Jugador 1: Conectado con {addr}")
        else:
            print("Jugador 2: Intentando conectar...")
            self.socket.connect(('localhost', 12345))
            print("Jugador 2: Conectado")
        
        self.connected = True
        self.synchronize_start()
    
    def synchronize_start(self):
        if self.player_id == 1:
            self.send_data({"type": "ready", "timestamp": time.time()})
            data = self.receive_data()
            if data and data.get("type") == "ready_ack":
                start_time = time.time() + 1.0
                self.send_data({"type": "start", "start_time": start_time})
                self.sync_complete = True
        else:
            data = self.receive_data()
            if data and data.get("type") == "ready":
                self.send_data({"type": "ready_ack"})
                data = self.receive_data()
                if data and data.get("type") == "start":
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

# ===== JUEGO PRINCIPAL =====

class Juego:
    def __init__(self, player_id: int):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Clash Royale - Player {player_id}")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        
        self.player_id = player_id
        self.running = True
        
        # Crear board inicial
        initial_board = ClashRoyaleBoard()
        
        # Crear sistema de rollback
        self.rollback_system = RollbackSystem(
            initial_state=initial_board,
            simulation_fps=SIMULATION_FPS,
            checkpoint_interval=0.1,
            checkpoint_duration=4.0
        )
        
        # Componentes
        self.p2p = P2P(player_id)
        self.menu = Menu(player_id)
        
        # Estado
        self.game_started = False
        self.receive_thread = None
    
    def start_network(self):
        self.p2p.connect()
        
        self.receive_thread = threading.Thread(target=self.network_listener)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        while not self.p2p.sync_complete:
            time.sleep(0.01)
        
        self.game_started = True
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
                self.rollback_system.add_event(event)
    
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
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_WIDTH
                    row = mouse_y // CELL_HEIGHT
                    
                    if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                        self.place_card((row, col))
    
    def place_card(self, coords: Tuple[int, int]):
        selected_card = self.menu.get_selected_card()
        if selected_card is None:
            print("No se puede colocar carta: sin elixir o carta inválida")
            return
        
        board = self.rollback_system.state
        row, col = coords
        
        # Validar posición ANTES de gastar elixir
        if not board.is_valid_position(row, col):
            print(f"Posición inválida: ({row}, {col})")
            return
        
        # Gastar elixir solo si la posición es válida
        if not self.menu.spend_elixir(selected_card.cost):
            print("No hay suficiente elixir")
            return
        
        # Crear evento
        event = Event(
            timestamp=self.rollback_system.get_real_time(),
            event_type="place_entity",
            data={
                "entity_type": selected_card.entity_type.value,
                "pos": coords,
                "entity_id": board.get_next_entity_id()
            },
            player_id=self.player_id
        )
        
        print(f"Colocando carta: {selected_card.name} en {coords}")
        
        # Enviar por P2P
        self.p2p.send_event(event)
        
        # Procesar localmente
        self.rollback_system.add_event(event)
    
    def update(self):
        if not self.game_started:
            return
        
        dt = 1.0 / FPS
        self.menu.update(dt)
        self.rollback_system.update_simulation()
    
    def render(self):
        self.screen.fill(BLACK)
        
        if not self.game_started:
            text = self.font.render("Esperando sincronización...", True, WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(text, text_rect)
        else:
            # Renderizar board
            self.rollback_system.state.render(self.screen)
            
            # UI
            self.render_ui()
        
        pygame.display.flip()
    
    def render_ui(self):
        # Estadísticas de tiempo
        stats = self.rollback_system.get_stats()
        time_info = [
            f"Real Time: {stats['real_time']:.3f}s",
            f"Sim Time: {stats['simulation_time']:.3f}s",
            f"Time Diff: {stats['time_diff']:.3f}s",
            f"Rollbacks: {stats['rollback_count']}",
            f"Events: {stats['events_in_timeline']}",
            f"Checkpoints: {stats['checkpoints']}"
        ]
        
        # Mostrar estadísticas en la esquina superior derecha
        for i, info in enumerate(time_info):
            text = self.font.render(info, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH - 200, 10 + i * 20))
        
        # Barra de elixir
        elixir_text = self.font.render(f"Elixir: {self.menu.elixir}/{self.menu.max_elixir}", True, WHITE)
        self.screen.blit(elixir_text, (10, 10))
        
        # Cartas disponibles
        cards_y = 50
        for i, card in enumerate(self.menu.available_cards):
            color = GREEN if i == self.menu.selected_card_index else WHITE
            if not self.menu.can_place_card(i):
                color = GRAY
            
            card_text = self.font.render(f"{i+1}. {card.name} ({card.cost})", True, color)
            self.screen.blit(card_text, (10, cards_y + i * 25))
        
        # Instrucciones
        instructions = [
            "Controles:",
            "1-4: Seleccionar carta",
            "Click: Colocar carta",
            f"Jugador: {self.player_id}",
            "",
            "Estado de red:",
            f"Conectado: {'Sí' if self.p2p.connected else 'No'}"
        ]
        
        instructions_y = SCREEN_HEIGHT - len(instructions) * 20 - 10
        for i, instruction in enumerate(instructions):
            color = WHITE if instruction else WHITE
            text = self.font.render(instruction, True, color)
            self.screen.blit(text, (10, instructions_y + i * 20))
    
    def run(self):
        try:
            # Iniciar red
            self.start_network()
            
            # Loop principal
            while self.running:
                self.handle_events()
                self.update()
                self.render()
                self.clock.tick(FPS)
                
        except KeyboardInterrupt:
            print(f"Jugador {self.player_id}: Interrupción de teclado")
        except Exception as e:
            print(f"Error en jugador {self.player_id}: {e}")
        finally:
            pygame.quit()
            if self.p2p.socket:
                self.p2p.socket.close()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['1', '2']:
        print("Uso: python juego.py [1|2]")
        print("Ejemplo:")
        print("  Terminal 1: python juego.py 1")
        print("  Terminal 2: python juego.py 2")
        sys.exit(1)
    
    player_id = int(sys.argv[1])
    print(f"Iniciando Clash Royale - Jugador {player_id}")
    
    juego = Juego(player_id)
    juego.run()

if __name__ == "__main__":
    main()