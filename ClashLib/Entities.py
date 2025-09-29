from abc import ABC, abstractmethod
import math
from enum import Enum

# ID global
_next_entity_id = 0
def get_next_id():
    global _next_entity_id
    _next_entity_id += 1
    return _next_entity_id


# crear un enum para entity types
class EntityType(Enum):
    TROOP = 'troop'
    TOWER = 'tower'
    SPELL = 'spell'
    PROJECTILE = 'projectile'

class TowerType(Enum):
    CENTRAL = 'central'
    LATERAL = 'lateral'

class StateType(Enum):
    IDLE = 'idle'
    MOVING = 'moving'
    ATTACKING = 'attacking'

class Entity(ABC):
    """
    This class represents a generic entity in the game.
    """
    def __init__(self, cell_x, cell_y, owner, entity_type=EntityType.TROOP):
        """
        The coords are in function of the map grid, so it has min y max values:
        0 <= x < map_width
        0 <= y < map_height
        """
        self.x = cell_x + 0.5
        self.y = cell_y + 0.5
        self.owner = owner
        self.entity_id = get_next_id()  # Unique incremental ID
        self.active = True
        self.type = entity_type 

    def distance_to(self, other):
        """
        Calculate Euclidean distance to another entity.
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.hypot(dx, dy)
    

    def distance_to_point(self, point):
        """
        Calculate Euclidean distance to a point (x, y).
        """
        dx = self.x - point[0]
        dy = self.y - point[1]
        return math.hypot(dx, dy)

    def get_screen_position(self, cell_size):
        """
        Convert grid coordinates to screen coordinates.
        """
        screen_x = self.x * cell_size
        screen_y = self.y * cell_size
        return (screen_x, screen_y)
    
    def get_grid_position(self):
        """
        Get the grid cell coordinates.
        """
        return (int(self.x), int(self.y))

    @abstractmethod 
    def update(self, tick_time, entities):
        """
        Update the entity state.
        """
        pass

    def execute(self, tick_time):
        """
        Execute the entity's action.
        """
        pass

    @abstractmethod
    def render(self, screen):
        """
        Render the entity on the given screen.
        """
        pass


class Tower(Entity):
    """
    This class represents a tower in the game. It extends the Entity class
    and adds specific attributes for towers.
    """
    def __init__(self, cell_x, cell_y, owner, tower_type = TowerType.CENTRAL):
        super().__init__(cell_x, cell_y, owner, entity_type=EntityType.TOWER)
        self.tower_type = tower_type
        self.size = 4.0 if tower_type == TowerType.CENTRAL else 3.0
        self.life = 4824 if tower_type == TowerType.CENTRAL else 3052
        self.max_life = self.life
        self.hit_speed = 1 if tower_type == TowerType.CENTRAL else 0.8 # tiempo entre ataques
        self.attack_range = 7.5 + self.size/2
        self.damage = 109 if tower_type == TowerType.CENTRAL else 109
        self.cooldown = 0.0
        self.target : Troop | None = None # entidad objetivo
        self.state = StateType.IDLE

    def in_range(self, target):
        return self.distance_to(target) <= self.attack_range

    def look_for_target(self, entities):
        """
        Simple nearest-target selection: find the closest enemy entity within range.
        """

        if self.state != StateType.IDLE:
            return

        entities_copy = sorted(entities, key=lambda e: self.distance_to(e))

        for entity in entities_copy:
            if entity.owner == self.owner or not entity.active or entity.type not in [EntityType.TROOP, EntityType.TOWER]:
                continue

            if self.in_range(entity):
                self.target = entity
                break


    def attack(self, add_entity=None):
        """
        Fire a projectile at the target.
        """
        P = Projectile(self.x, self.y, self.owner, speed=5.0, target=self.target, damage=self.damage)
        if add_entity:
            add_entity(P)


    def update(self, tick_time, entities):
        if self.life <= 0:
            self.active = False
            return None
        
        # verify state
        if self.target and self.target.life > 0 and self.in_range(self.target):
            self.state = StateType.ATTACKING
        else:
            self.state = StateType.IDLE
            self.target = None

        self.look_for_target(entities)


    def execute(self, tick_time, add_entity):
        self.cooldown -= tick_time
        if self.target and self.cooldown <= 0 and self.target.life > 0:
            self.attack(add_entity=add_entity)
            self.cooldown = self.hit_speed


    def receive_damage(self, amount):
        self.life -= amount
        if self.life <= 0:
            self.active = False


class Troop(Entity, ABC):
    """
    Base class for all troops. Contains common logic for moving and attacking.
    """

    def __init__(self, cell_x, cell_y, life, owner, damage, speed, range, hit_speed, target=None):
        super().__init__(cell_x, cell_y, owner)
        self.life = life
        self.max_life = life
        self.damage = damage
        self.speed = speed # cells per second
        self.range = range
        self.hit_speed = hit_speed
        self.target = target
        self.cooldown = 0.0
        self.state = StateType.IDLE
        self.delay = 1.0

    # se debe sobreescribir para tropas como el ariete
    def look_for_target(self, entities):
        """
        Simple nearest-target selection: find the closest enemy entity.
        """
        if self.state == StateType.ATTACKING:
            return
        
        entities_copy = sorted(entities, key=lambda e: self.distance_to(e))

        for entity in entities_copy:
            if entity.owner == self.owner or not entity.active or entity.type not in [EntityType.TROOP, EntityType.TOWER]:
                continue

            self.target = entity
            break


    @abstractmethod
    def attack(self, add_entity=None):
        """
        Attack the target entity. 
        Should return a Projectile or None (if melee attack).
        """
        pass

    def in_range(self, target):
        """
        Check if target is within attack range.
        """
        return self.distance_to(target) <= self.range
    
    def get_valid_waypoints(self, obstacles, map_width = 18, map_height = 32):
        muajaja = []
        for i in range(-1, 1):
            for j in range(-1, 1):
                if i == 0 and j == 0:
                    continue
                new_x = int(self.x) + i 
                new_y = int(self.y) + j 
                if 0 <= new_x < map_width and 0 <= new_y < map_height:
                    if (new_x, new_y) not in obstacles:
                        muajaja.append((new_x + 0.5, new_y + 0.5))
        return muajaja


    def get_target_waypoint(self, obstacles):
        if not self.target:
            return
    
        valid_waypoint = self.get_valid_waypoints(obstacles)
        target_wp = None
        min_dist = float('inf')
        for wp in valid_waypoint:
            dist = self.target.distance_to_point(wp)
            if dist < min_dist:
                min_dist = dist
                target_wp = wp

        return target_wp


    def move_towards(self, obstacles, ticket_time):
        if not self.target:
            return

        target_wp = self.get_target_waypoint(obstacles)
        if not target_wp:
            return
        
        dx = target_wp[0] - self.x
        dy = target_wp[1] - self.y

        max_dist = math.hypot(dx, dy)

        try_dist = self.speed * ticket_time
        if try_dist > max_dist:
            try_dist = max_dist
    

        self.x += dx / max_dist * try_dist
        self.y += dy / max_dist * try_dist


    def update(self, tick_time, entities):
        if self.life <= 0:
            self.active = False
            return None

        if self.delay > 0:
            self.state = StateType.IDLE
            self.cooldown = 0.0
            self.delay -= tick_time
            return None

        if self.target and self.in_range(self.target) and self.target.life > 0:
            self.state = StateType.ATTACKING
        else:
            self.state = StateType.MOVING

        self.look_for_target(entities)

    def execute(self, tick_time, obstacles, add_entity):
        if self.state == StateType.ATTACKING:
            self.cooldown -= tick_time
            if self.cooldown <= 0:
                self.attack(self.target, add_entity=add_entity)
                self.cooldown = self.hit_speed

        elif self.state == StateType.MOVING:
            self.move_towards(obstacles, tick_time)
    
    def receive_damage(self, amount):
        self.life -= amount
        if self.life <= 0:
            self.active = False


class Spell(Entity):
    """
    This class represents a spell in the game. It extends the Entity class
    and adds specific attributes for spells.
    """
    def __init__(self, cell_x, cell_y, owner, duration, damage, radius):
        super().__init__(cell_x, cell_y, owner, entity_type=EntityType.SPELL)
        self.duration = duration
        self.damage = damage
        self.radius = radius

    def update(self, tick_time, entities):
        if self.duration <= 0:
            self.active = False
        else:
            self.duration -= tick_time

    def execute(self, tick_time):
        return None


class Projectile(Entity):
    """
    This class represents a projectile in the game. It extends the Entity class
    and adds specific attributes for projectiles.
    """
    def __init__(self, cell_x, cell_y, owner, speed, target, damage):
        super().__init__(cell_x, cell_y, owner, entity_type=EntityType.PROJECTILE)
        self.speed = speed # cells per second
        self.target = target 
        self.damage = damage
        self.max_duration = 5.0
        self.elapsed_time = 0.0
        self.reached_target = False
        self.target_pos = (target.x, target.y) if target else None

    def move_towards(self, tick_time):
        dx = self.target_pos[0] - self.x
        dy = self.target_pos[1] - self.y
        max_dist = math.hypot(dx, dy)

        try_dist = self.speed * tick_time
        if try_dist >= max_dist:
            self.reached_target = True
            try_dist = max_dist

        self.x += dx / max_dist * try_dist
        self.y += dy / max_dist * try_dist

    def update(self, tick_time, entities):
        self.target_pos = (self.target.x, self.target.y) if self.target else self.target_pos


    def execute(self, tick_time):
        if not self.active:
            return
        
        self.elapsed_time += tick_time
        self.move_towards(tick_time)

        dx = self.target_pos[0] - self.x
        dy = self.target_pos[1] - self.y

        if (math.hypot(dx, dy) < 0.05 or self.reached_target) and self.target and self.target.active:
            self.target.receive_damage(self.damage)
            self.active = False
        if self.elapsed_time > self.max_duration:
            self.active = False

class AreaProjectile(Projectile):
    """
    This class represents an Area Projectile in the game. It extends the Projectile class
    and adds specific attributes for Area Projectiles.
    """
    def __init__(self, cell_x, cell_y, owner, speed, target, damage, radius):
        super().__init__(cell_x=cell_x, cell_y=cell_y, owner=owner, speed=speed, target=target, damage=damage)
        self.radius = radius
        self.troops_hit : list[Troop] = []

    def update(self, tick_time, entities):
        # calcula cuanto avanza y si ya esta muy cerca dle obejtivo llena trops_hit
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.radius:
            for entity in entities:
                if entity.owner != self.owner and entity.active and entity.type in [EntityType.TROOP, EntityType.TOWER]:
                    if math.hypot(entity.x - self.x, entity.y - self.y) <= self.radius:
                        if entity not in self.troops_hit:
                            self.troops_hit.append(entity)
        

    def execute(self, tick_time):
        if not self.active or not self.target:
            return

        self.elapsed_time += tick_time

        if self.elapsed_time > self.max_duration:
            self.active = False
            return

        self.move_towards(self.target.x, self.target.y, tick_time)
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        if math.hypot(dx, dy) < 0.05:
            for entity in self.troops_hit:
                if math.hypot(entity.x - self.x, entity.y - self.y) <= self.radius:
                    entity.receive_damage(self.damage)
            self.active = False


class Mosquetera(Troop):
    def __init__(self, cell_x, cell_y, owner, target=None, projectile_speed=3.0):
        super().__init__(cell_x=cell_x, cell_y=cell_y, life=721, owner=owner, damage=217, speed=1.0, range=6, hit_speed=1.0, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target, add_entity):
        P = Projectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage)
        if add_entity:
            add_entity(P)
        return P

class Mago(Troop):
    def __init__(self, cell_x, cell_y, owner, target=None, projectile_speed=3.0):
        super().__init__(cell_x=cell_x, cell_y=cell_y, life=755, owner=owner, damage=281, speed=1.0, range=5.5, hit_speed=1.4, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target, add_entity):
        P = AreaProjectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage, radius=1.5)
        if add_entity:
            add_entity(P)
        return P

class Caballero(Troop):
    """
    This class represents a Caballero troop in the game. It extends the Troop class
    and adds specific attributes for Caballeros.
    """
    def __init__(self, cell_x, cell_y, owner, target=None):
        super().__init__(cell_x=cell_x, cell_y=cell_y, life=1766, owner=owner, damage=202, speed=1.0, range=1.0, hit_speed=1.2, target=target)

    def attack(self, target, add_entity=None):
        if target.life > 0:
            target.receive_damage(self.damage)

