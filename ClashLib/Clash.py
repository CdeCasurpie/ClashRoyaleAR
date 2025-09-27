from ClashLib.Simulation import GameState, GameTimeline, Event
from ClashLib.MultiplayerConection import P2P
from ClashLib.Menu import Menu
import pygame
import sys
import random


class Board(GameState): 
    """
    Board class that extends GameState to represent the state of the game board in Clash Royale. 
    So it will contain information about the positions of units, buildings, and other game elements.
    """
    def __init__(self):
        super().__init__()
        self.width = 18
        self.height = 32
        self.cell_size = 20

    def update(self, tick_time):
        pass

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
        pass


class Card:
    """
    This class represents a card in the game. It will contain information about
    the card type, cost, and any other relevant data.
    """
    def __init__(self, card_type, cost_elixir):
        self.card_type = card_type
        self.cost_elixir = cost_elixir
        self.card_id = id(self)  # Unique identifier for the card instance


class ClashSimulation(GameTimeline):
    """
    ClashSimulation class that extends GameTimeline to manage the timeline of events specific to Clash Royale.
    """
    def __init__(self):
        super().__init__()

    def process_event(self, event, game_state):
        """
        Process an event and update the game state accordingly.
        This method is intended to be overridden by subclasses to provide specific event processing logic.
        """
        print(f"Processing event: {event.event_type} at time {self.simulation_time}")
        pass
    


class Clash:
    def __init__(self, player_id):
        self.player_id = player_id
        self.width = 18
        self.height = 32
        self.connected = False
        self.board = Board()
        self.simulation = ClashSimulation()
        self.menu = Menu()
        self.p2p = P2P(local_test=True, on_connect=self.on_connect)

        # Pygame setup
        
        pygame.init()
        self.screen = pygame.display.set_mode(
                (self.board.width*20, 
                (self.board.height*1.25)*20)
             )
        pygame.display.set_caption("Clash Royale AR: Player " + str(self.player_id))
        self.clock = pygame.time.Clock()
        self.running = True


    def on_connect(self, addr):
        print(f"Connected to peer at {addr}")
        self.connected = True
        self.menu.set_game_start_time(self.p2p.get_synced_time())

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

    def handle_inputs(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self.menu.handle_click(mouse_pos, (0, self.board.height*20), (self.board.width*20, 8*20))
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    used_card = self.menu.use_selected_card()
                    if used_card is not None:
                        print(f"Player {self.player_id} used card {used_card}")
                        # Aquí podrías agregar lógica para colocar la carta en el tablero

    def update(self):
        print(f"Updating game state for player {self.player_id}")
        self.simulation.execute_tick(self.board)
        
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

        print(f"Running game for player {self.player_id}")
        while True:
            print(self.p2p.get_synced_time())
            self.handle_inputs()
            self.update()

