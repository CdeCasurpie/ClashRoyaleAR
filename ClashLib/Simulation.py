from abc import ABC, abstractmethod


class Event:
    """
    This class represents an event that occurs in the game. It will contain
    information about the type of event, the time it occurred, and any other
    relevant data.
    """
    def __init__(self, event_type, timestamp, delay=2): 
        """
        Un evento representa una acción. Por cuestiones de sincronizacion se le asigna un delay
        para que no se ejecute inmediatamente. Es decir un evento ocurre en su timestamp + delay. Delay
        es por defecto 2 s.
        """
        self.event_type = event_type
        self.timestamp = timestamp
        self.delay = delay
        self.aparition_time = timestamp + delay


class GameState(ABC):
    """
    This class represents the state of the game at any given time. It will contain
    information about players, units, resources, etc.

    This class is abstract and should be extended by specific game implementations.
    """
    def __init__(self):
        pass

    @abstractmethod
    def update(self, tick_time):
        """
        Update the game state based on the rules of the game.
        """
        pass

class GameTimeline(ABC):
    """
    This class represents the timeline of events in the game. So it will contain 
    the simulation time and the events that had occurred in the game.
    Attributes:
        simulation_time (int): The current time in the simulation.
        events (list): A list of events that have occurred in the game.
        tick_time (float): The time unit for each step in the simulation (e.g., 1/24 for 24 FPS).
    """
    def __init__(self, tick_time=1/24):
        self.simulation_time = 0
        self.tick_time = tick_time
        self.events = []

    def get_events_in_range(self, start_time, end_time):
        return [event for event in self.events if start_time <= event.aparition_time <= end_time]

    def add_event(self, event):
        self.events.append(event)
        self.events.sort(key=lambda e: e.aparition_time)

    def execute_tick(self, game_state):
        """
        Execute a single tick of the simulation, updating the game state and processing events.
        """
        game_state.update(self.tick_time)

        current_events = self.get_events_in_range(self.simulation_time, self.simulation_time + self.tick_time)
        for event in current_events:
            self.process_event(event, game_state)

        self.simulation_time += self.tick_time

    
    @abstractmethod
    def process_event(self, event, game_state):
        """
        Process an event and update the game state accordingly.
        This method is intended to be overridden by subclasses to provide specific event processing logic.
        """
        pass
