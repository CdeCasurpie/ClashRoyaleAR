import time
import copy
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Event:
    """Evento con timestamp que puede ser procesado por el sistema de rollback"""
    def __init__(self, timestamp: float, event_type: str, data: dict, player_id: int = None):
        self.timestamp = timestamp
        self.event_type = event_type
        self.data = data
        self.player_id = player_id
    
    def __repr__(self):
        return f"Event(t={self.timestamp:.3f}, type={self.event_type}, player={self.player_id})"

class TimeSimulationLine:
    """Timeline que mantiene eventos ordenados por timestamp"""
    def __init__(self):
        self.events: List[Event] = []
    
    def add_event(self, event: Event):
        """Agregar evento manteniendo orden cronológico"""
        inserted = False
        for i, existing_event in enumerate(self.events):
            if event.timestamp < existing_event.timestamp:
                self.events.insert(i, event)
                inserted = True
                break
        if not inserted:
            self.events.append(event)
    
    def get_events_until(self, timestamp: float) -> List[Event]:
        """Obtener todos los eventos hasta un timestamp dado"""
        events_until = []
        for event in self.events:
            if event.timestamp <= timestamp:
                events_until.append(event)
            else:
                break
        return events_until
    
    def get_events_in_range(self, start_time: float, end_time: float) -> List[Event]:
        """Obtener eventos en un rango de tiempo específico"""
        events_in_range = []
        for event in self.events:
            if start_time <= event.timestamp <= end_time:
                events_in_range.append(event)
            elif event.timestamp > end_time:
                break
        return events_in_range

class SimulationState(ABC):
    """Interfaz abstracta para cualquier estado de simulación que pueda usar rollback"""
    
    @abstractmethod
    def copy(self):
        """Crear una copia profunda del estado actual"""
        pass
    
    @abstractmethod
    def advance_step(self, timeline: TimeSimulationLine, step_duration: float):
        """Avanzar la simulación un paso, procesando eventos del timeline"""
        pass
    
    @abstractmethod
    def get_simulation_time(self) -> float:
        """Obtener el tiempo actual de la simulación"""
        pass
    
    @abstractmethod
    def set_simulation_time(self, time: float):
        """Establecer el tiempo de simulación"""
        pass

class Checkpoint:
    """Checkpoint que guarda el estado en un momento específico"""
    def __init__(self, timestamp: float, state: SimulationState):
        self.timestamp = timestamp
        self.state = state.copy()  # Copia profunda del estado

class RollbackSystem:
    """Sistema de rollback genérico que puede trabajar con cualquier SimulationState"""
    
    def __init__(self, initial_state: SimulationState, simulation_fps: int = 25, 
                 checkpoint_interval: float = 0.1, checkpoint_duration: float = 4.0):
        self.state = initial_state
        self.timeline = TimeSimulationLine()
        self.checkpoints: List[Checkpoint] = []
        
        # Configuración de tiempo
        self.simulation_fps = simulation_fps
        self.step_duration = 1.0 / simulation_fps
        self.checkpoint_interval = checkpoint_interval
        self.checkpoint_duration = checkpoint_duration
        
        # Control de tiempo
        self.real_time = 0.0
        self.start_time = time.time()
        
        # Estadísticas
        self.rollback_count = 0
        self.total_events_processed = 0
    
    def get_real_time(self) -> float:
        """Obtener el tiempo real transcurrido desde el inicio"""
        return time.time() - self.start_time
    
    def get_simulation_time(self) -> float:
        """Obtener el tiempo actual de la simulación"""
        return self.state.get_simulation_time()
    
    def add_event(self, event: Event):
        """Agregar un nuevo evento al timeline y procesar rollback si es necesario"""
        self.timeline.add_event(event)
        self.total_events_processed += 1
        
        # ¿Necesitamos rollback?
        if event.timestamp < self.get_simulation_time():
            print(f"ROLLBACK requerido: evento en t={event.timestamp:.3f}, sim_time={self.get_simulation_time():.3f}")
            self.perform_rollback(event.timestamp)
    
    def perform_rollback(self, target_timestamp: float):
        """Realizar rollback al timestamp especificado"""
        self.rollback_count += 1
        
        # Buscar el checkpoint más cercano pero anterior al target
        best_checkpoint = None
        for checkpoint in self.checkpoints:
            if checkpoint.timestamp <= target_timestamp:
                if best_checkpoint is None or checkpoint.timestamp > best_checkpoint.timestamp:
                    best_checkpoint = checkpoint
        
        if best_checkpoint:
            print(f"Restaurando desde checkpoint t={best_checkpoint.timestamp:.3f}")
            self.state = best_checkpoint.state.copy()
            print(f"Estado restaurado a t={self.get_simulation_time():.3f}")
        else:
            print("No hay checkpoint disponible, manteniendo estado actual")
    
    def update_simulation(self):
        """Actualizar la simulación para alcanzar el tiempo real"""
        self.real_time = self.get_real_time()
        current_sim_time = self.get_simulation_time()
        
        # Calcular cuántos pasos necesitamos
        time_diff = self.real_time - current_sim_time
        
        if time_diff > 0:
            # Si estamos muy atrasados, acelerar
            if time_diff > 0.1:
                steps_needed = int(time_diff / self.step_duration)
                steps_this_frame = min(10, steps_needed)  # Máximo 10 pasos por frame
            else:
                steps_this_frame = 1
            
            # Ejecutar pasos
            for _ in range(steps_this_frame):
                if self.get_simulation_time() < self.real_time:
                    self.state.advance_step(self.timeline, self.step_duration)
                    
                    # Guardar checkpoint si es necesario
                    if self.should_save_checkpoint():
                        self.save_checkpoint()
    
    def should_save_checkpoint(self) -> bool:
        """Determinar si debemos guardar un checkpoint"""
        if len(self.checkpoints) == 0:
            return True
        
        last_checkpoint_time = self.checkpoints[-1].timestamp
        current_time = self.get_simulation_time()
        
        return current_time - last_checkpoint_time >= self.checkpoint_interval
    
    def save_checkpoint(self):
        """Guardar un checkpoint del estado actual"""
        checkpoint = Checkpoint(self.get_simulation_time(), self.state)
        self.checkpoints.append(checkpoint)
        
        # Limpiar checkpoints antiguos
        current_time = self.get_simulation_time()
        self.checkpoints = [cp for cp in self.checkpoints 
                           if current_time - cp.timestamp <= self.checkpoint_duration]
        
        print(f"Checkpoint guardado en t={current_time:.3f}, total={len(self.checkpoints)}")
    
    def get_stats(self) -> dict:
        """Obtener estadísticas del sistema"""
        return {
            "real_time": self.real_time,
            "simulation_time": self.get_simulation_time(),
            "time_diff": self.real_time - self.get_simulation_time(),
            "events_in_timeline": len(self.timeline.events),
            "checkpoints": len(self.checkpoints),
            "rollback_count": self.rollback_count,
            "total_events": self.total_events_processed,
            "simulation_fps": self.simulation_fps
        }

# Ejemplo de uso: Implementación específica para Clash Royale

class ClashRoyaleBoard(SimulationState):
    """Implementación específica del board de Clash Royale"""
    
    def __init__(self):
        self.simulation_time = 0.0
        self.entities = {}  # Dict[int, Entity]
        self.next_entity_id = 0
        self.grid = [[None for _ in range(18)] for _ in range(32)]  # 32x18 grid
    
    def copy(self):
        """Crear copia profunda del board"""
        new_board = ClashRoyaleBoard()
        new_board.simulation_time = self.simulation_time
        new_board.next_entity_id = self.next_entity_id
        
        # Copiar entidades (esto necesitaría implementación específica según las entidades)
        new_board.entities = {}
        for entity_id, entity in self.entities.items():
            # Aquí iría la lógica específica de copia de entidades
            new_board.entities[entity_id] = self.copy_entity(entity)
        
        # Copiar grid
        new_board.grid = [row[:] for row in self.grid]
        
        return new_board
    
    def copy_entity(self, entity):
        """Copiar una entidad específica (implementar según tipo de entidad)"""
        # Esto se implementaría según las clases de entidades específicas
        pass
    
    def advance_step(self, timeline: TimeSimulationLine, step_duration: float):
        """Avanzar un paso de simulación"""
        next_time = self.simulation_time + step_duration
        
        # Procesar eventos hasta este momento
        events_to_process = timeline.get_events_until(next_time)
        existing_entity_ids = set(self.entities.keys())
        
        for event in events_to_process:
            if event.event_type == "place_entity":
                entity_id = event.data.get("entity_id")
                if entity_id is not None and entity_id not in existing_entity_ids:
                    # Crear y agregar entidad
                    self.create_entity_from_event(event)
                    existing_entity_ids.add(entity_id)
        
        # Actualizar entidades existentes
        self.update_entities(step_duration)
        
        # Avanzar tiempo
        self.simulation_time = next_time
    
    def create_entity_from_event(self, event: Event):
        """Crear entidad basada en un evento (implementar según necesidades)"""
        # Implementar creación de entidades específicas
        pass
    
    def update_entities(self, dt: float):
        """Actualizar todas las entidades"""
        for entity in list(self.entities.values()):
            # Aquí iría la lógica de actualización de entidades
            # entity.update(dt)
            pass
    
    def get_simulation_time(self) -> float:
        return self.simulation_time
    
    def set_simulation_time(self, time: float):
        self.simulation_time = time

class TestSimulation:
    """Ejemplo de uso del sistema de rollback"""
    
    def __init__(self):
        # Crear estado inicial
        initial_board = ClashRoyaleBoard()
        
        # Crear sistema de rollback
        self.rollback_system = RollbackSystem(
            initial_state=initial_board,
            simulation_fps=25,
            checkpoint_interval=0.1,
            checkpoint_duration=4.0
        )
    
    def create_event_with_artificial_lag(self, event_type: str, data: dict, lag_seconds: float = 0.5):
        """Crear evento con lag artificial para testing"""
        # Evento ocurre en el pasado (simulando latencia de red)
        event_timestamp = self.rollback_system.get_real_time() - lag_seconds
        
        event = Event(
            timestamp=event_timestamp,
            event_type=event_type,
            data=data,
            player_id=1
        )
        
        return event
    
    def simulate_network_event(self):
        """Simular llegada de evento de red con lag"""
        event = self.create_event_with_artificial_lag(
            "place_entity",
            {"entity_type": "esqueleto", "pos": (10, 5), "entity_id": 123},
            lag_seconds=0.3
        )
        
        self.rollback_system.add_event(event)
    
    def run_test(self):
        """Ejecutar test del sistema"""
        print("Iniciando test del sistema de rollback...")
        
        # Simular algunos frames
        for frame in range(100):
            # Actualizar simulación
            self.rollback_system.update_simulation()
            
            # Cada 30 frames, simular evento con lag
            if frame % 30 == 0:
                self.simulate_network_event()
            
            # Mostrar estadísticas cada 50 frames
            if frame % 50 == 0:
                stats = self.rollback_system.get_stats()
                print(f"Frame {frame}: Real={stats['real_time']:.3f}s, "
                      f"Sim={stats['simulation_time']:.3f}s, "
                      f"Diff={stats['time_diff']:.3f}s, "
                      f"Rollbacks={stats['rollback_count']}")
            
            # Simular 60 FPS
            time.sleep(1/60)

if __name__ == "__main__":
    # Ejecutar test
    test = TestSimulation()
    test.run_test()