from ClashLib.Simulation import GameState, GameTimeline, Event
from ClashLib.MultiplayerConection import P2P
from ClashLib.Menu import Menu
from ClashLib.Entities import Entity, Caballero, Mago, Mosquetera, Tower, TowerType
from ClashLib.utils import screen_to_grid
import pygame
import sys
import random

class Board(GameState): 
    """
    Board class that extends GameState to represent the state of the game board in Clash Royale. 
    So it will contain information about the positions of units, buildings, and other game elements.
    """
    
    def __init__(self, player_id=None):
        super().__init__()
        self.width = 18
        self.height = 32
        self.cell_size = 20
        self.entities: list[Entity] = []
        self.player_id = player_id
        self.new_entities = []
        self.towers = []
        self.obstacles = set()  # Set de coordenadas de celdas bloqueadas
        
        # Inicializar obstáculos y torres
        self.setup_obstacles()
        self.setup_towers()


    def is_my_area(self, grid_position):
        """
        Verifica si una posición en la cuadrícula pertenece al área del jugador.
        Para el jugador 1, el área es la mitad superior (filas 0-15).
        Para el jugador 2, el área es la mitad inferior (filas 16-31).
        """
        columna, fila = grid_position
        
        if self.player_id == "1":
            return 0 <= fila < 16  # Área del jugador 1 (superior)
        elif self.player_id == "2":
            return 16 <= fila < 32  # Área del jugador 2 (inferior)
        return False


    def win_condition(self):
        """
        Define the win condition for the game.
        """
        # printear los ids de las torres para debug
        print(self.player_id)
        for tower in self.towers:
            print(f"Tower ID: {tower.owner}, Life: {tower.life}")  # Debugging line
        my_towers = [tower for tower in self.towers if str(tower.owner) == str(self.player_id)]
        opponent_towers = [tower for tower in self.towers if str(tower.owner) != str(self.player_id)]

        print(f"My towers: {len(my_towers)}, Opponent towers: {len(opponent_towers)}")  # Debugging line
        
        if not my_towers:
            return "lose"
        elif not opponent_towers:
            return "win"
        return "continue"

    def setup_obstacles(self):
        """
        Configura los obstáculos del mapa: agua y torres.
        Las coordenadas son en formato (columna, fila) o (x, y) en la grid.
        """
        # Limpiar obstáculos previos
        self.obstacles.clear()
        
        # AGUA (Río) - filas 15 y 16 (2 casillas de altura)
        for fila in range(15, 17):  # filas 15, 16
            for columna in range(18):
                # Excluir puentes
                # Puente izquierdo: columnas 2-4
                # Puente derecho: columnas 13-15
                if not ((columna >= 2 and columna <= 4) or (columna >= 13 and columna <= 15)):
                    self.obstacles.add((columna, fila))
        
        # TORRES SUPERIORES (Jugador 1)
        # Torre principal superior: 4x4, filas 1-4, columnas 7-10
        for fila in range(1, 5):
            for columna in range(7, 11):
                self.obstacles.add((columna, fila))
        
        # Torre izquierda superior: 3x3, filas 5-7, columnas 2-4
        for fila in range(5, 8):
            for columna in range(2, 5):
                self.obstacles.add((columna, fila))
        
        # Torre derecha superior: 3x3, filas 5-7, columnas 13-15
        for fila in range(5, 8):
            for columna in range(13, 16):
                self.obstacles.add((columna, fila))
        
        # TORRES INFERIORES (Jugador 2)
        # Torre principal inferior: 4x4, filas 27-30, columnas 7-10
        for fila in range(27, 31):
            for columna in range(7, 11):
                self.obstacles.add((columna, fila))
        
        # Torre izquierda inferior: 3x3, filas 24-26, columnas 2-4
        for fila in range(24, 27):
            for columna in range(2, 5):
                self.obstacles.add((columna, fila))
        
        # Torre derecha inferior: 3x3, filas 24-26, columnas 13-15
        for fila in range(24, 27):
            for columna in range(13, 16):
                self.obstacles.add((columna, fila))

    def setup_towers(self):
        """
        Crea las entidades de torres en el tablero.
        """
        # Torres del jugador 1 (superior)
        torre_principal_sup = Tower(8.5, 2.5, owner="1", tower_type=TowerType.CENTRAL)
        torre_izq_sup = Tower(3, 6, owner="1", tower_type=TowerType.LATERAL)
        torre_der_sup = Tower(14, 6, owner="1", tower_type=TowerType.LATERAL)
        
        # Torres del jugador 2 (inferior)
        torre_principal_inf = Tower(8.5, 28.5, owner="2", tower_type=TowerType.CENTRAL)
        torre_izq_inf = Tower(3, 25, owner="2", tower_type=TowerType.LATERAL)
        torre_der_inf = Tower(14, 25, owner="2", tower_type=TowerType.LATERAL)
        
        # Agregar torres a las entidades
        self.entities.extend([
            torre_principal_sup, torre_izq_sup, torre_der_sup,
            torre_principal_inf, torre_izq_inf, torre_der_inf
        ])

        self.towers.extend([
            torre_principal_sup, torre_izq_sup, torre_der_sup,
            torre_principal_inf, torre_izq_inf, torre_der_inf
        ])

    def is_valid_placement(self, grid_position):
        """
        Verifica si una posición es válida para colocar una carta.
        Retorna True si es válida, False si no.
        """
        columna, fila = grid_position
        
        # Verificar límites del tablero
        if columna < 0 or columna >= self.width or fila < 0 or fila >= self.height:
            return False
        
        # Verificar si está en un obstáculo
        if (columna, fila) in self.obstacles:
            return False
        
        return True

    def add_new_entity(self, entity):
        self.new_entities.append(entity)

    def update(self, tick_time):
        # update de todos
        for entity in self.entities:
            entity.update(tick_time, self.entities)        

        # excecute de todos
        for entity in self.entities:
            entity.execute(tick_time, self.obstacles, self.add_new_entity)

        # eliminar los inactivos
        self.entities = [e for e in self.entities if e.active]
        self.towers = [t for t in self.towers if t.active]

        # añadir nuevas entidades generadas
        if self.new_entities:
            self.entities.extend(self.new_entities)
            self.new_entities = []

    def render(self, screen):
        """
        Renderiza el tablero con césped, agua, puentes y torres.
        """
        for fila in range(self.height):
            for columna in range(self.width):
                x = columna * self.cell_size
                y = fila * self.cell_size
                
                # Determinar el tipo de celda
                es_rio = 15 <= fila <= 16
                es_puente = es_rio and ((2 <= columna <= 4) or (13 <= columna <= 15))
                
                # Color base
                if es_rio and not es_puente:
                    # Agua en azul
                    color = (33, 150, 243)
                else:
                    # Césped - patrón de tablero de ajedrez
                    if (columna + fila) % 2 == 0:
                        color = (163, 197, 71)
                    else:
                        color = (174, 206, 77)
                    
                    # Variación de color para más naturalidad
                    color_variation = 2
                    random.seed(x^2 + y^2)
                    color = (
                        random.randint(max(0, color[0] - color_variation), min(255, color[0] + color_variation)),
                        random.randint(max(0, color[1] - color_variation), min(255, color[1] + color_variation)),
                        random.randint(max(0, color[2] - color_variation), min(255, color[2] + color_variation))
                    )
                
                # Dibujar celda
                pygame.draw.rect(screen, color, (x, y, self.cell_size, self.cell_size))
                
                # Dibujar borde sutil
                pygame.draw.rect(screen, (100, 100, 100), (x, y, self.cell_size, self.cell_size), 1)
        
        # Renderizar entidades
        for entity in self.entities:
            entity.render(screen, cell_size=self.cell_size)

    def position_to_grid(self, position):
        return screen_to_grid(position[0], position[1], self.cell_size)

    def create_entity_by_type(self, entity_type, position, player_id):
        float_pos = (position[0], position[1])
        if entity_type == "Caballero":
            return Caballero(float_pos[0], float_pos[1], player_id)
        elif entity_type == "Mago":
            return Mago(float_pos[0], float_pos[1], player_id)
        elif entity_type == "Mosquetera":
            return Mosquetera(float_pos[0], float_pos[1], player_id) 
        else: 
            return None

    def add_entity(self, entity_type, grid_position, player_id):
        print(f"Adding entity of type {entity_type} at grid position {grid_position}")
        entity = self.create_entity_by_type(entity_type, grid_position, player_id)
        if entity is not None:
            print(f"Entity created: {entity}")
            self.entities.append(entity)



class ClashSimulation(GameTimeline):
    """
    ClashSimulation class that extends GameTimeline to manage the timeline of events specific to Clash Royale.
    """
    def __init__(self, tick_time=1/24):
        super().__init__(tick_time)


    def process_event(self, event, game_state):
        """
        Process an event and update the game state accordingly.
        This method is intended to be overridden by subclasses to provide specific event processing logic.
        """

        print(f"Processing event: {event.event_type} at simulation time {self.simulation_time}, apparition time {event.aparition_time}")

        # debo procesar el evento si su tiempo de aparicion ya paso
        if event.event_type == "spawn_unit":
            print(f"Spawning unit with data: {event.data}")
            entity_type = event.data.get("entity_type")
            grid_position = event.data.get("grid_position")
            player_id = event.data.get("player_id")

            if entity_type is not None and grid_position is not None:
                game_state.add_entity(entity_type, grid_position, player_id)
                print(f"Spawned {entity_type} at {grid_position} for player {player_id}")
        


class Clash:
    def __init__(self, player_id):
        self.player_id = player_id
        self.width = 18
        self.height = 32
        self.tick_time = 1/25 # para evitar flotantes raros
        self.connected = False
        self.board = Board(player_id=self.player_id)
        self.simulation = ClashSimulation(tick_time=self.tick_time)
        self.menu = Menu(player_id=self.player_id)
        self.p2p = P2P(local_test=True, on_connect=self.on_connect, on_receive=self.on_receive)
        self.total_ticks = 0
        self.initial_timestamp = None

        # Pygame setup
        
        pygame.init()
        self.screen = pygame.display.set_mode(
                (self.board.width*20, 
                (self.board.height*1.25)*20)
             )
        pygame.display.set_caption("Clash Royale AR: Player " + str(self.player_id))
        self.clock = pygame.time.Clock()
        self.running = True

    def on_receive(self, data, addr):
        event = Event.from_json(data['data'])

        if event is not None:
            self.simulation.add_event(event)
            print(event.aparition_time - self.p2p.initial_timestamp)
            print(self.simulation.simulation_time)

    def on_connect(self, addr):
        print(f"Connected to peer at {addr}")
        self.connected = True
        self.menu.set_game_start_time(self.p2p.get_synced_time())
        self.total_ticks = 0
        self.initial_timestamp = self.menu.game_start_time

    def make_connection(self):
        print(f"Making connection for player {self.player_id}")
        if self.player_id == "1":
            self.p2p.start_peer_host()
        elif self.player_id == "2":
            hosts = self.p2p.get_hosts()
            if not hosts:
                print("No hosts found. Exiting.")
                sys.exit(1)
            self.p2p.connect_as_peer_client(hosts[0])

    def render(self):
        
        self.screen.fill((0, 255, 0))

        self.board.render(self.screen)
        self.menu.render(self.screen, position=(0, self.board.height*20), size=(self.board.width*20, 8*20))
        pygame.display.flip()

    def get_initial_timestamp(self):
        if self.initial_timestamp is None:
            self.initial_timestamp = self.p2p.initial_timestamp
        
        if self.initial_timestamp is None:
            print("Error: initial_timestamp is still None after assignment.")
        return self.initial_timestamp

    def handle_board_click(self, grid_pos):
            """
            Maneja el clic en el tablero.
            Verifica que la posición sea válida antes de colocar la carta.
            """
            # verificar que sea su area
            if not self.board.is_my_area(grid_pos):
                print(f"Posición fuera de área permitida: {grid_pos}. No se puede colocar carta aquí.")
                # Opcionalmente, puedes deseleccionar la carta
                self.menu.selected_card = None
                return

            # Verificar si la posición es válida
            if not self.board.is_valid_placement(grid_pos):
                print(f"Posición inválida: {grid_pos}. No se puede colocar carta aquí.")
                # Opcionalmente, puedes deseleccionar la carta
                self.menu.selected_card = None
                return
            
            # Intentar usar la carta seleccionada
            used_card = self.menu.use_selected_card()
            if used_card is not None:
                # crear evento 
                event = Event(event_type="spawn_unit", 
                                timestamp=self.p2p.get_synced_time() - self.get_initial_timestamp(),
                                delay=0.2,
                                data= {
                                "entity_type": used_card,
                                "grid_position": grid_pos,
                                "player_id": self.player_id
                                })
                
                # TODO: Crear evento de tipo "placeholder_unit" que se ponga directamente en el board y desaparesca en el aparition time.

                self.p2p.send_data(event.to_json())
                self.simulation.add_event(event)
                print(f"Carta {used_card} colocada en {grid_pos}")
            else:
                print("No hay carta seleccionada o no hay suficiente elixir")

    def handle_menu_click(self, mouse_pos):
        self.menu.handle_click(mouse_pos, (0, self.board.height*20), (self.board.width*20, 8*20))

    def handle_inputs(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                grid_pos = self.board.position_to_grid(mouse_pos)

                print(grid_pos)

                if self.menu.chords_inside_menu(mouse_pos, (0, self.board.height*20), (self.board.width*20, 8*20)):
                    self.handle_menu_click(mouse_pos)
                else:
                    self.handle_board_click(grid_pos)

    def update(self):
        # win condition
        win_condition = self.board.win_condition()
        if win_condition == "win":
            print("You win!")
            self.running = False
            pygame.quit()
            sys.exit(0)
        elif win_condition == "lose":
            print("You lose!")
            self.running = False
            pygame.quit()
            sys.exit(0)

        #print(f"Updating game state for player {self.player_id}")

        expected_total_ticks = int((self.p2p.get_synced_time() - self.menu.game_start_time) / self.tick_time)
        ticks_to_process = expected_total_ticks - self.total_ticks
        
        for _ in range(ticks_to_process):
            self.simulation.execute_tick(self.board)
            self.total_ticks += 1

        
        current_synced_time = self.p2p.get_synced_time()
        self.menu.update_elixir_synced(current_synced_time)
        
        self.clock.tick(60)
        self.render()

    def try_connection(self):
        tries = 0
        while not self.connected and tries < 5:
            self.make_connection()
            tries += 1
            if not self.connected:
                print("Retrying connection...")
                pygame.time.delay(2000) 

        if not self.connected:
            print("Failed to connect after multiple attempts. Exiting.")
            sys.exit(1)

    def run(self):
        self.try_connection()

        while True:
            self.handle_inputs()
            self.update()

