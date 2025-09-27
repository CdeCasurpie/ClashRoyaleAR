from ClashLib.Simulation import GameState, GameTimeline, Event
from ClashLib.MultiplayerConection import P2P
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

import pygame
import math

class Menu:
    def set_game_start_time(self, start_time):
        """Establece cuándo empezó el juego (llamar una vez al conectarse)"""
        self.game_start_time = start_time
        self.elixir = 7

    def __init__(self):
        self.selected_card = None
        self.last_update_time = 0
        self.initial_elixir = 7
        self.max_elixir = 10
        self.maze = self.generate_maze()
        self.card_list = []
        self.card_costs = [3, 3, 5, 3]
        self.game_start_time = None
        self.generated_elixir = 0  # Elixir total generado desde el inicio
        self.elixir_used = 0  # Elixir total usado en cartas
        self.elixir_wasted = 0  # Elixir desperdiciado por estar en el máximos
        self.seconds_for_one_elixir = 1.5  # Cada 2.8 segundos se genera 1 elixir

    def update_elixir_synced(self, current_synced_time):
        """
        Calcula el elixir basándose directamente en el tiempo sincronizado
        """
        if self.last_update_time == 0:
            self.last_update_time = current_synced_time
            self.elixir = self.initial_elixir
            return

        # Tiempo transcurrido desde el inicio del juego
        time_elapsed = current_synced_time - self.game_start_time
        self.last_update_time = current_synced_time
        
        self.generated_elixir = time_elapsed / self.seconds_for_one_elixir

        self.elixir = self.initial_elixir + self.generated_elixir - self.elixir_used - self.elixir_wasted

        if self.elixir > self.max_elixir:
            self.elixir = self.max_elixir
            self.elixir_wasted = (self.initial_elixir + self.generated_elixir) - self.max_elixir - self.elixir_used

        self.elixir_wasted = max(0, self.elixir_wasted)



    def use_selected_card(self):
        """
        Usa la carta seleccionada y registra el elixir usado
        """
        if self.selected_card is not None and self.elixir >= self.card_costs[self.selected_card]:
            self.elixir_used += self.card_costs[self.selected_card]
            used_card = self.selected_card
            self.selected_card = None
            print(f"Carta {used_card} usada. Elixir usado total: {self.elixir_used}")
            return used_card
        return None
    

    def generate_maze(self):
        return []

    def draw_rounded_rect(self, surface, color, rect, radius):
        """
        Dibuja un rectángulo con esquinas redondeadas
        """
        x, y, width, height = rect
        
        # Rectángulo principal
        pygame.draw.rect(surface, color, (x + radius, y, width - 2*radius, height))
        pygame.draw.rect(surface, color, (x, y + radius, width, height - 2*radius))
        
        # Esquinas redondeadas
        pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + width - radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + radius, y + height - radius), radius)
        pygame.draw.circle(surface, color, (x + width - radius, y + height - radius), radius)

    def render_card(self, screen, position, size, card_index, is_selected=False):
        """
        Renderiza una carta individual con bordes redondeados
        """
        x, y = position
        width, height = size
        radius = 8
        
        # Color de fondo de la carta
        card_color = (65, 85, 140) if not is_selected else (85, 105, 160)
        
        # Dibujar carta con bordes redondeados
        self.draw_rounded_rect(screen, card_color, (x, y, width, height), radius)
        
        # Borde gris claro
        border_color = (140, 140, 140)
        # Simular borde redondeado dibujando múltiples rectángulos más pequeños
        for i in range(2):
            border_rect = (x - i, y - i, width + 2*i, height + 2*i)
            self.draw_rounded_rect(screen, border_color, border_rect, radius + i)
        
        # Redibujar la carta encima del borde
        self.draw_rounded_rect(screen, card_color, (x, y, width, height), radius)
        
        # Círculo de elixir en esquina superior izquierda
        elixir_radius = 18
        elixir_center = (x + elixir_radius + 5, y + elixir_radius + 5)
        
        # Color del elixir: #e771e8
        elixir_color = (231, 113, 232)
        pygame.draw.circle(screen, elixir_color, elixir_center, elixir_radius)
        pygame.draw.circle(screen, (255, 255, 255), elixir_center, elixir_radius, 3)
        
        # Número del costo de elixir
        font = pygame.font.Font(None, 28)
        cost_text = font.render(str(self.card_costs[card_index]), True, (255, 255, 255))
        cost_rect = cost_text.get_rect(center=elixir_center)
        screen.blit(cost_text, cost_rect)

    def render(self, screen, position=(0, 32*20), size=(18*20, 8*20)):
        """
        Renderiza el menú con el diseño correcto
        """
        x, y = position
        width, height = size
        
        # Fondo del menú - azul intenso
        pygame.draw.rect(screen, (20, 80, 150), (x, y, width, height))
        
        # Configuración de las cartas
        num_cards = 4
        card_margin = 8
        card_padding = 15
        
        available_width = width - (2 * card_padding)
        card_spacing = card_margin
        total_spacing = card_spacing * (num_cards - 1)
        card_width = (available_width - total_spacing) // num_cards
        card_height = height - 60  # Dejar más espacio para el elixir abajo
        
        # Renderizar las 4 cartas
        for i in range(num_cards):
            card_x = x + card_padding + i * (card_width + card_spacing)
            card_y = y + 15
            
            is_selected = (self.selected_card == i)
            self.render_card(
                screen, 
                (card_x, card_y), 
                (card_width, card_height), 
                i, 
                is_selected
            )
        
        # Contador de elixir centrado en la parte inferior
        self.render_elixir_counter(screen, x, y, width, height)

    def render_elixir_counter(self, screen, menu_x, menu_y, menu_width, menu_height):
        """
        Renderiza el contador de elixir con divisiones como en Clash Royale
        """
        # Configuración de la barra - más larga, ocupando casi todo el ancho
        bar_width = menu_width - 90  # Dejar márgenes pequeños
        bar_height = 20
        bar_x = menu_x + 60  # Margen izquierdo
        bar_y = menu_y + menu_height - bar_height - 15
        
        # Círculo de elixir a la izquierda
        circle_radius = 15
        circle_center = (bar_x - 25, bar_y + bar_height // 2)
        
        # Dibujar círculo con el número de elixir
        pygame.draw.circle(screen, (231, 113, 232), circle_center, circle_radius)  # #e771e8
        pygame.draw.circle(screen, (255, 255, 255), circle_center, circle_radius, 2)
        
        # Texto del elixir en el círculo
        font = pygame.font.Font(None, 22)
        elixir_text = font.render(f"{int(self.elixir)}", True, (255, 255, 255))
        text_rect = elixir_text.get_rect(center=circle_center)
        screen.blit(elixir_text, text_rect)
        
        # Fondo de la barra (negro)
        pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height))
        
        # Calcular el ancho de cada segmento de elixir
        segment_width = bar_width / self.max_elixir
        
        # Dibujar cada segmento de elixir
        for i in range(self.max_elixir):
            segment_x = bar_x + i * segment_width
            
            # Color del segmento
            if i < int(self.elixir):
                # Segmento lleno
                segment_color = (231, 113, 232)  # #e771e8
            elif i < self.elixir:
                # Segmento parcialmente lleno
                segment_color = (100, 79, 127)
            else:
                # Segmento vacío
                segment_color = (60, 60, 60)
            
            # Dibujar el segmento con un pequeño margen
            margin = 1
            pygame.draw.rect(screen, segment_color, 
                           (segment_x + margin, bar_y + margin, 
                            segment_width - 2*margin, bar_height - 2*margin))
        
        # Si hay elixir parcial, dibujarlo
        if self.elixir != int(self.elixir):
            partial_segment = int(self.elixir)
            if partial_segment < self.max_elixir:
                partial_progress = self.elixir - partial_segment
                partial_x = bar_x + partial_segment * segment_width
                partial_width = segment_width * partial_progress
                
                margin = 1
                pygame.draw.rect(screen, (231, 113, 232),
                               (partial_x + margin, bar_y + margin,
                                partial_width - 2*margin, bar_height - 2*margin))

    def handle_click(self, mouse_pos, menu_position, menu_size):
        """
        Maneja los clics del mouse para seleccionar cartas
        """
        x, y = menu_position
        width, height = menu_size
        
        # Verificar si el clic está en el área del menú
        if not (x <= mouse_pos[0] <= x + width and y <= mouse_pos[1] <= y + height):
            return
        
        # Calcular en qué carta se hizo clic
        num_cards = 4
        card_margin = 8
        card_padding = 15
        
        available_width = width - (2 * card_padding)
        card_spacing = card_margin
        total_spacing = card_spacing * (num_cards - 1)
        card_width = (available_width - total_spacing) // num_cards
        card_height = height - 60
        
        for i in range(num_cards):
            card_x = x + card_padding + i * (card_width + card_spacing)
            card_y = y + 15
            
            if (card_x <= mouse_pos[0] <= card_x + card_width and 
                card_y <= mouse_pos[1] <= card_y + card_height):
                # Verificar si tiene suficiente elixir
                if self.elixir >= self.card_costs[i]:
                    self.selected_card = i
                    print(f"Carta {i} seleccionada (Costo: {self.card_costs[i]})")
                else:
                    print(f"No tienes suficiente elixir para la carta {i}")
                break
    
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

