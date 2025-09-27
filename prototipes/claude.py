import pygame
import time
import math
import copy
from typing import List, Tuple, Optional

# Inicializar Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
SIMULATION_FPS = 25
CHECKPOINT_DURATION = 4.0  # segundos
GRAVITY_CONSTANT = 100.0
MIN_DISTANCE = 30.0  # distancia mínima para atracción

# Colores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 100, 100)
BLUE = (100, 100, 255)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 100)

class Event:
    def __init__(self, timestamp: float, event_type: str, data: dict):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
    
    def __repr__(self):
        return f"Event(t={self.timestamp:.3f}, type={self.event_type}, data={self.data})"

class Particle:
    _next_id = 0  # Contador global para IDs únicos
    
    def __init__(self, mass: int, pos: Tuple[float, float], particle_id: int = None):
        self.mass = mass
        self.pos = list(pos)
        self.vel = [0.0, 0.0]
        self.life = mass
        
        # Asignar ID único y determinista
        if particle_id is not None:
            self.id = particle_id
        else:
            self.id = Particle._next_id
            Particle._next_id += 1
        
    def copy(self):
        new_particle = Particle(self.mass, tuple(self.pos), self.id)
        new_particle.vel = self.vel.copy()
        new_particle.life = self.life
        return new_particle

class TimeSimulationLine:
    def __init__(self):
        self.events = []  # Lista ordenada de eventos por timestamp
    
    def add_event(self, event: Event):
        # Insertar evento manteniendo orden por timestamp
        inserted = False
        for i, existing_event in enumerate(self.events):
            if event.timestamp < existing_event.timestamp:
                self.events.insert(i, event)
                inserted = True
                break
        if not inserted:
            self.events.append(event)
    
    def get_events_until(self, timestamp: float) -> List[Event]:
        """Obtener todos los eventos hasta cierto timestamp"""
        events_until = []
        for event in self.events:
            if event.timestamp <= timestamp:
                events_until.append(event)
            else:
                break
        return events_until
    
    def get_events_in_range(self, start_time: float, end_time: float) -> List[Event]:
        """Obtener eventos en un rango de tiempo"""
        events_in_range = []
        for event in self.events:
            if start_time <= event.timestamp <= end_time:
                events_in_range.append(event)
            elif event.timestamp > end_time:
                break
        return events_in_range

class Checkpoint:
    def __init__(self, timestamp: float, particles: List[Particle]):
        self.timestamp = timestamp
        self.particles = [p.copy() for p in particles]

class SimulationState:
    def __init__(self):
        self.particles = []
        self.simulation_time = 0.0
        self.checkpoints = []
        self.step_duration = 1.0 / SIMULATION_FPS
        
    def copy(self):
        new_state = SimulationState()
        new_state.particles = [p.copy() for p in self.particles]
        new_state.simulation_time = self.simulation_time
        new_state.step_duration = self.step_duration
        return new_state
    
    def add_particle(self, mass: int, pos: Tuple[float, float], particle_id: int = None):
        particle = Particle(mass, pos, particle_id)
        self.particles.append(particle)
    
    def calculate_forces(self, particle1: Particle, particle2: Particle) -> Tuple[float, float]:
        """Calcular fuerza gravitacional entre dos partículas"""
        dx = particle2.pos[0] - particle1.pos[0]
        dy = particle2.pos[1] - particle1.pos[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Si están muy cerca, no hay atracción
        if distance < MIN_DISTANCE:
            return 0.0, 0.0
        
        # Fuerza gravitacional
        force_magnitude = GRAVITY_CONSTANT * particle1.mass * particle2.mass / (distance * distance)
        
        # Componentes de la fuerza
        force_x = force_magnitude * dx / distance
        force_y = force_magnitude * dy / distance
        
        return force_x, force_y
    
    def advance_step(self, timeline: TimeSimulationLine):
        """Avanzar un paso de simulación"""
        next_time = self.simulation_time + self.step_duration
        
        # DEBUG: Mostrar qué eventos deberíamos procesar
        all_events_until_now = timeline.get_events_until(next_time)
        events_that_should_exist = [ev for ev in all_events_until_now if ev.timestamp <= next_time]
        
        # Procesar TODOS los eventos que deberían existir hasta este punto
        existing_particle_ids = {p.id for p in self.particles}
        
        for event in events_that_should_exist:
            if event.event_type == "spawn_particle":
                particle_id = event.data.get("id")
                # Solo crear la partícula si no existe ya
                if particle_id is not None and particle_id not in existing_particle_ids:
                    self.add_particle(event.data["mass"], event.data["pos"], particle_id)
                    existing_particle_ids.add(particle_id)
        
        # Aplicar fuerzas entre partículas
        forces = {}
        for i, p1 in enumerate(self.particles):
            forces[p1.id] = [0.0, 0.0]
            for j, p2 in enumerate(self.particles):
                if i != j:
                    fx, fy = self.calculate_forces(p1, p2)
                    forces[p1.id][0] += fx
                    forces[p1.id][1] += fy
        
        # Actualizar velocidades y posiciones
        for particle in self.particles:
            if particle.id in forces:
                # F = ma, entonces a = F/m
                ax = forces[particle.id][0] / particle.mass
                ay = forces[particle.id][1] / particle.mass
                
                # Actualizar velocidad
                particle.vel[0] += ax * self.step_duration
                particle.vel[1] += ay * self.step_duration
                
                # Actualizar posición
                particle.pos[0] += particle.vel[0] * self.step_duration
                particle.pos[1] += particle.vel[1] * self.step_duration
                
                # Mantener partículas en pantalla (rebote)
                if particle.pos[0] < 0 or particle.pos[0] > SCREEN_WIDTH:
                    particle.vel[0] *= -0.8  # Amortiguamiento en rebote
                    particle.pos[0] = max(0, min(SCREEN_WIDTH, particle.pos[0]))
                
                if particle.pos[1] < 0 or particle.pos[1] > SCREEN_HEIGHT:
                    particle.vel[1] *= -0.8
                    particle.pos[1] = max(0, min(SCREEN_HEIGHT, particle.pos[1]))
        
        self.simulation_time = next_time
    
    def save_checkpoint(self):
        """Guardar checkpoint del estado actual"""
        checkpoint = Checkpoint(self.simulation_time, self.particles)
        self.checkpoints.append(checkpoint)
        
        # Eliminar checkpoints antiguos (más de 4 segundos)
        self.checkpoints = [cp for cp in self.checkpoints 
                          if self.simulation_time - cp.timestamp <= CHECKPOINT_DURATION]
    
    def restore_from_checkpoint(self, timestamp: float) -> bool:
        """Restaurar desde el checkpoint más cercano anterior al timestamp"""
        best_checkpoint = None
        for checkpoint in self.checkpoints:
            if checkpoint.timestamp <= timestamp:
                if best_checkpoint is None or checkpoint.timestamp > best_checkpoint.timestamp:
                    best_checkpoint = checkpoint
        
        if best_checkpoint:
            self.simulation_time = best_checkpoint.timestamp
            self.particles = [p.copy() for p in best_checkpoint.particles]
            return True
        return False
    
    def reset_to_initial(self):
        """Resetear al estado inicial"""
        self.particles = []
        self.simulation_time = 0.0

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Rollback Netcode Simulation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        
        # Tiempos
        self.real_time = 0.0
        self.start_time = time.time()
        
        # Estado de simulación
        self.simulation_state = SimulationState()
        self.initial_state = self.simulation_state.copy()
        self.timeline = TimeSimulationLine()
        
        # Control de lag artificial
        self.lag_offset = 0.5  # segundos de lag simulado
        
        # Velocidad de simulación
        self.simulation_speed = 1.0 
        
        # ID único para eventos
        self.next_event_id = 0
        
        self.running = True
    
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    # Crear partícula con lag artificial
                    spawn_time = self.real_time - self.lag_offset
                    spawn_event = Event(
                        timestamp=spawn_time,
                        event_type="spawn_particle",
                        data={
                            "mass": 20,
                            "pos": mouse_pos,
                            "id": self.next_event_id
                        }
                    )
                    self.next_event_id += 1
                    self.process_new_event(spawn_event)
                
                elif event.key == pygame.K_r:
                    # Reiniciar simulación (replay)
                    self.simulation_state.reset_to_initial()
                    # Resetear el contador de IDs también
                    Particle._next_id = 0
                
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Aumentar lag
                    self.lag_offset = min(3.0, self.lag_offset + 0.1)
                
                elif event.key == pygame.K_MINUS:
                    # Disminuir lag
                    self.lag_offset = max(0.0, self.lag_offset - 0.1)
    
    def process_new_event(self, event: Event):
        """Procesar un nuevo evento que puede requerir rollback"""
        self.timeline.add_event(event)
        
        # ¿Necesitamos rollback?
        if event.timestamp < self.simulation_state.simulation_time:
            print(f"ROLLBACK necesario: evento en {event.timestamp:.3f}, sim_time: {self.simulation_state.simulation_time:.3f}")
            
            # Intentar restaurar desde checkpoint
            if self.simulation_state.restore_from_checkpoint(event.timestamp):
                print(f"Restaurado a checkpoint: {self.simulation_state.simulation_time:.3f}")
                print(f"Eventos totales en timeline: {len(self.timeline.events)}")
                
                # Mostrar todos los eventos que deberían procesarse
                events_to_process = self.timeline.get_events_until(self.real_time)
                print(f"Eventos que deben procesarse: {len(events_to_process)}")
                for ev in events_to_process:
                    if ev.timestamp >= self.simulation_state.simulation_time:
                        print(f"  - Evento ID {ev.data.get('id')} en t={ev.timestamp:.3f}")
            else:
                print("No hay checkpoint disponible, reiniciando")
                self.simulation_state.reset_to_initial()
    
    def update_simulation(self):
        """Actualizar la simulación hacia el real_time"""
        # Determinar cuántos pasos necesitamos avanzar
        time_diff = self.real_time - self.simulation_state.simulation_time
        
        if time_diff > 0:
            # Si estamos atrasados, acelerar
            if time_diff > 0.1:  # Si estamos muy atrasados
                steps_needed = int(time_diff / self.simulation_state.step_duration)
                steps_this_frame = min(10, steps_needed)  # Máximo 10 pasos por frame
            else:
                steps_this_frame = 1
            
            for _ in range(steps_this_frame):
                if self.simulation_state.simulation_time < self.real_time:
                    self.simulation_state.advance_step(self.timeline)
                    
                    # Guardar checkpoint cada pocos pasos
                    if len(self.simulation_state.checkpoints) == 0 or \
                       self.simulation_state.simulation_time - self.simulation_state.checkpoints[-1].timestamp >= 0.1:
                        self.simulation_state.save_checkpoint()
    
    def render(self):
        self.screen.fill(BLACK)
        
        # Dibujar partículas
        colors = [RED, BLUE, GREEN, YELLOW]
        for i, particle in enumerate(self.simulation_state.particles):
            color = colors[i % len(colors)]
            radius = max(5, particle.mass // 4)
            pygame.draw.circle(
                self.screen, 
                color, 
                (int(particle.pos[0]), int(particle.pos[1])), 
                radius
            )
            
            # Dibujar ID de partícula (usar el ID real, no el índice)
            id_text = self.font.render(f"{particle.id}", True, WHITE)
            self.screen.blit(id_text, (particle.pos[0] + radius + 2, particle.pos[1] - 10))
        
        # Información en pantalla
        info_texts = [
            f"Real Time: {self.real_time:.2f}s",
            f"Simulation Time: {self.simulation_state.simulation_time:.2f}s",
            f"Lag Offset: {self.lag_offset:.2f}s",
            f"Particles: {len(self.simulation_state.particles)}",
            f"Events in Timeline: {len(self.timeline.events)}",
            f"Checkpoints: {len(self.simulation_state.checkpoints)}",
            "",
            "Particle IDs:",
            f"  {[p.id for p in self.simulation_state.particles]}",
            "",
            "Event IDs in Timeline:",
            f"  {[ev.data.get('id', '?') for ev in self.timeline.events]}",
            "",
            "Controls:",
            "T - Spawn particle (with artificial lag)",
            "R - Reset simulation (replay mode)",
            "+ - Increase lag offset",
            "- - Decrease lag offset",
            "",
            "Physics: Particles attract each other",
            "Rollback occurs when events arrive late"
        ]
        
        y_offset = 10
        for text in info_texts:
            if text:
                rendered = self.font.render(text, True, WHITE)
                self.screen.blit(rendered, (10, y_offset))
            y_offset += 25
        
        pygame.display.flip()
    
    def run(self):
        while self.running:
            # Actualizar real_time
            self.real_time = time.time() - self.start_time
            
            self.handle_events()
            self.update_simulation()
            self.render()
            
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()