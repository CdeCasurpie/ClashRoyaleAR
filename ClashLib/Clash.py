from ClashLib.Simulation import GameState, GameTimeline, Event
from ClashLib.MultiplayerConection import P2P
from ClashLib.Menu import Menu
from ClashLib.Entities import Entity, Caballero, Mago, Mosquetera
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
        self.obstacles = [] # future use for pathfinding

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

        # añadir nuevas entidades generadas
        if self.new_entities:
            self.entities.extend(self.new_entities)
            self.new_entities = []

    def render(self, screen):
        for x in range(0, self.width * self.cell_size, self.cell_size):
            for y in range(0, self.height * self.cell_size, self.cell_size):
                color = (163,197,71) if (x // self.cell_size + y // self.cell_size) % 2 == 0 else (174, 206, 77)


                color_variation = 2
                random.seed(x^2+y^2)
                color = (
                    random.randint(max(0, color[0] - color_variation), min(255, color[0] + color_variation)),
                    random.randint(max(0, color[1] - color_variation), min(255, color[1] + color_variation)),
                    random.randint(max(0, color[2] - color_variation), min(255, color[2] + color_variation))
                )

                pygame.draw.rect(screen, color, (x, y, self.cell_size, self.cell_size))
        

        for entity in self.entities:
            entity.render(screen, cell_size=self.cell_size)

    def position_to_grid(self, position):
        return screen_to_grid(position[0], position[1], self.cell_size)
    


    def create_entity_by_type(self, entity_type, position):
        float_pos = (position[0], position[1])
        if entity_type == "Caballero":
            return Caballero(float_pos[0], float_pos[1], self.player_id)
        elif entity_type == "Mago":
            return Mago(float_pos[0], float_pos[1], self.player_id)
        elif entity_type == "Mosquetera":
            return Mosquetera(float_pos[0], float_pos[1], self.player_id) 
        else: 
            return None

        

    def add_entity(self, entity_type, grid_position):
        print(f"Adding entity of type {entity_type} at grid position {grid_position}")
        entity = self.create_entity_by_type(entity_type, grid_position)
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
                game_state.player_id = player_id
                game_state.add_entity(entity_type, grid_position) #añadimos la entidad al board
                print(f"Spawned {entity_type} at {grid_position} for player {player_id}")



        


class Clash:
    def __init__(self, player_id):
        self.player_id = player_id
        self.width = 18
        self.height = 32
        self.tick_time = 1/25 # para evitar flotantes raros
        self.connected = False
        self.board = Board()
        self.simulation = ClashSimulation(tick_time=self.tick_time)
        self.menu = Menu()
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
        # board clicked
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
            pass

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
            #print(self.p2p.get_synced_time())
            self.handle_inputs()
            self.update()

