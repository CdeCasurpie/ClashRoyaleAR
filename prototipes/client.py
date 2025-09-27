import pygame
import sys
import time
import copy
from typing import List, Tuple

# ------------------------------------
# Constantes y Configuración
# ------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TARGET_FPS = 25.0
DELTA_TIME = 1.0 / TARGET_FPS
CHECKPOINT_SECONDS = 4.0 # Guardar los últimos 4 segundos de estados
GRAVITY = 98.1

# Colores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 80, 80)
BLUE = (100, 149, 237)
GREEN = (50, 205, 50)

# ------------------------------------
# Clase Evento (Proporcionada)
# ------------------------------------
class Event:
    def __init__(self, timestamp: float, event_type: str, data: dict):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
    
    def __repr__(self):
        return f"Event(t={self.timestamp:.3f}, type={self.event_type}, data={self.data})"

# ------------------------------------
# Clase Partícula (Proporcionada y extendida)
# ------------------------------------
class Particle:
    def __init__(self, mass: int, pos: Tuple[float, float]):
        self.mass = mass
        self.pos = list(pos)
        self.vel = [0.0, 5.0] # Pequeña velocidad inicial para ver la gravedad
        self.life = mass
        self.id = id(self)

    def update(self, delta_time: float):
        # Aplicar gravedad
        self.vel[1] += GRAVITY * delta_time
        
        # Actualizar posición
        self.pos[0] += self.vel[0] * delta_time
        self.pos[1] += self.vel[1] * delta_time
        
        # Simular rebote con el suelo
        if self.pos[1] > SCREEN_HEIGHT:
            self.pos[1] = SCREEN_HEIGHT
            self.vel[1] *= -0.7 # Perder algo de energía en el rebote

    def draw(self, screen):
        radius = int(self.mass / 2)
        pygame.draw.circle(screen, RED, (int(self.pos[0]), int(self.pos[1])), radius)

# ------------------------------------
# Clase SimulationState
# ------------------------------------
class SimulationState:
    def __init__(self, simulation_time: float, particles: List[Particle]):
        self.time = simulation_time
        # Es crucial hacer una copia profunda para que cada estado sea independiente
        self.particles = copy.deepcopy(particles)

    def advance_step(self, delta_time: float, events_in_step: List[Event]) -> 'SimulationState':
        """Crea y devuelve el siguiente estado de la simulación."""
        
        # 1. Crear el nuevo estado a partir del actual
        new_time = self.time + delta_time
        new_particles = copy.deepcopy(self.particles)

        # 2. Procesar eventos que ocurren en este paso de tiempo
        for event in events_in_step:
            if event.event_type == 'CREATE_PARTICLE':
                mass = event.data.get('mass', 10)
                pos = event.data.get('pos', (0, 0))
                new_particles.append(Particle(mass, pos))

        # 3. Actualizar la física de todas las partículas
        for particle in new_particles:
            particle.update(delta_time)
            
        return SimulationState(new_time, new_particles)

    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

# ------------------------------------
# Clase TimeSimulationLine
# ------------------------------------
class TimeSimulationLine:
    def __init__(self):
        self.events: List[Event] = []

    def add_event(self, event: Event):
        self.events.append(event)
        # Mantener los eventos siempre ordenados por su timestamp
        self.events.sort(key=lambda e: e.timestamp)

    def get_events_in_range(self, start_time: float, end_time: float) -> List[Event]:
        """Devuelve una lista de eventos cuyo timestamp está en el intervalo [start_time, end_time)"""
        return [e for e in self.events if start_time <= e.timestamp < end_time]

    def clear(self):
        self.events = []

# ------------------------------------
# Funciones Auxiliares de UI
# ------------------------------------
def draw_text(screen, text, font, color, position):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, position)

def draw_ui(screen, font, real_time, sim_time, delay, fps):
    # Fondo semitransparente para el UI
    ui_panel = pygame.Surface((SCREEN_WIDTH, 120))
    ui_panel.set_alpha(180)
    ui_panel.fill(BLACK)
    screen.blit(ui_panel, (0, 0))

    draw_text(screen, "Instrucciones:", font, WHITE, (10, 10))
    draw_text(screen, "  'T' - Crear partícula con retraso", font, GREEN, (10, 30))
    draw_text(screen, "  'R' - Reiniciar simulación", font, GREEN, (10, 50))
    draw_text(screen, "  '+' / '-' - Ajustar retraso del evento", font, GREEN, (10, 70))

    draw_text(screen, f"Tiempo Real: {real_time:.2f} s", font, WHITE, (400, 10))
    draw_text(screen, f"Tiempo Simulación: {sim_time:.2f} s", font, BLUE, (400, 30))
    draw_text(screen, f"Retraso de Evento ('T'): {delay:.2f} s", font, RED, (400, 50))
    draw_text(screen, f"FPS Real: {fps:.1f}", font, WHITE, (400, 70))

# ------------------------------------
# Función Principal
# ------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Simulación Determinista con Retroceso")
    font = pygame.font.Font(None, 24)
    real_time_clock = pygame.time.Clock()

    # --- Inicialización de la simulación ---
    timeline = TimeSimulationLine()
    
    # Guardamos el estado inicial para poder reiniciar con 'R'
    initial_state = SimulationState(simulation_time=0.0, particles=[])
    
    # El historial de estados guarda los checkpoints de los últimos N segundos
    state_history: List[SimulationState] = [initial_state]
    
    simulation_time = 0.0
    start_time = time.time() # Tiempo de reloj real al iniciar
    
    event_delay = 1.0 # Retraso inicial para los eventos creados por el usuario

    running = True
    while running:
        # --- Actualización del Tiempo Real ---
        real_time = time.time() - start_time
        
        # --- Manejo de Entradas del Usuario ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r: # Reiniciar simulación
                    print("--- REINICIANDO SIMULACIÓN ---")
                    timeline.clear()
                    state_history = [initial_state]
                    simulation_time = 0.0
                    start_time = time.time() # Reiniciar también el tiempo real para evitar un salto grande
                
                if event.key == pygame.K_t: # Crear un evento en el pasado
                    mouse_pos = pygame.mouse.get_pos()
                    # El timestamp es en el pasado para forzar un retroceso
                    event_timestamp = real_time - event_delay
                    
                    # Garantizar que el evento no sea más antiguo que el historial
                    if event_timestamp < state_history[0].time:
                         print(f"ADVERTENCIA: Evento demasiado antiguo (t={event_timestamp:.2f}). No se puede procesar.")
                         continue

                    print(f"Nuevo evento en t={event_timestamp:.2f}. Sim_time actual={simulation_time:.2f}")
                    new_event = Event(
                        timestamp=event_timestamp,
                        event_type='CREATE_PARTICLE',
                        data={'mass': 20, 'pos': mouse_pos}
                    )
                    timeline.add_event(new_event)

                    # ----- LÓGICA DE RETROCESO (ROLLBACK) -----
                    if new_event.timestamp < simulation_time:
                        print(f"¡RETROCESO NECESARIO! Evento en {new_event.timestamp:.2f} < SimTime {simulation_time:.2f}")
                        
                        # Buscar el checkpoint más cercano anterior al evento
                        rollback_index = -1
                        for i in range(len(state_history) - 1, -1, -1):
                            if state_history[i].time <= new_event.timestamp:
                                rollback_index = i
                                break
                        
                        if rollback_index != -1:
                            # Recortar el historial al punto de retroceso
                            state_history = state_history[:rollback_index + 1]
                            # Actualizar el tiempo de la simulación al de ese checkpoint
                            simulation_time = state_history[-1].time
                            print(f"Retrocediendo a checkpoint en t={simulation_time:.2f}")

                # Ajustar el retraso del evento
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    event_delay = min(event_delay + 0.2, CHECKPOINT_SECONDS - 0.1)
                if event.key == pygame.K_MINUS:
                    event_delay = max(0.1, event_delay - 0.2)

        # --- Bucle de Sincronización y Simulación ---
        # Este bucle se ejecuta tantas veces como sea necesario por frame para
        # que simulation_time alcance a real_time.
        while simulation_time < real_time:
            current_state = state_history[-1]
            
            # Obtener los eventos que deben procesarse en el siguiente paso
            events_this_step = timeline.get_events_in_range(simulation_time, simulation_time + DELTA_TIME)
            
            # Avanzar la simulación un paso
            new_state = current_state.advance_step(DELTA_TIME, events_this_step)
            
            # Añadir el nuevo estado al historial
            state_history.append(new_state)
            simulation_time = new_state.time

            # --- Poda del Historial (Pruning) ---
            # Eliminar los estados más antiguos si el historial excede los segundos de checkpoint
            while state_history[-1].time - state_history[0].time > CHECKPOINT_SECONDS:
                state_history.pop(0)

        # --- Renderizado ---
        screen.fill(BLACK)
        
        # Dibujar el estado más reciente de la simulación
        if state_history:
            state_history[-1].draw(screen)

        # Dibujar la interfaz de usuario
        draw_ui(screen, font, real_time, simulation_time, event_delay, real_time_clock.get_fps())
        
        pygame.display.flip()
        
        # Limitar el frame rate del bucle principal (el de renderizado)
        real_time_clock.tick(TARGET_FPS * 2) # Un poco más alto para dar margen

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()