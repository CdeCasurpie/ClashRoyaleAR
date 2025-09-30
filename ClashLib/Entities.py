from abc import ABC, abstractmethod
import math
from enum import Enum
import pygame

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
        # si las coordenadas salen de los limites del mapa, lanzamos un error

        if cell_x < 0 or cell_x >= 18 or cell_y < 0 or cell_y >= 32:
            raise ValueError("Coordinates are out of bounds.")
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

    @abstractmethod
    def execute(self, tick_time, obstacles, add_entity):
        """
        Execute the entity's action.
        """
        pass

    def render(self, screen, cell_size=20):
        """
        Render the entity on the given screen.
        """

        screen_position = self.get_screen_position(cell_size)

        radius = 10


        # si es id1 dibujar un circulo azul, si es id2 dibujar un circulo rojo
        if (self.owner == 1 or self.owner == '1'):
            pygame.draw.circle(screen, (0, 0, 255), (int(screen_position[0]), int(screen_position[1])), radius)
        elif (self.owner == 2 or self.owner == '2'):
            pygame.draw.circle(screen, (255, 0, 0), (int(screen_position[0]), int(screen_position[1])), radius)
        

        font = pygame.font.Font(None, 24)
        text = font.render(f"{self.entity_id}", True, (255, 255, 255))
        text_rect = text.get_rect(center=(int(screen_position[0]), int(screen_position[1])))
        screen.blit(text, text_rect)

        #renderizar el player id
        p_text = font.render(f"P{self.owner}", True, (255, 255, 0))
        p_text_rect = p_text.get_rect(center=(int(screen_position[0]), int(screen_position[1]) + 12))
        screen.blit(p_text, p_text_rect)






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

    def can_i_attack(self, entities):
        if self.tower_type != TowerType.CENTRAL: 
            return True

        if self.tower_type == TowerType.CENTRAL and self.life < self.max_life:
            return True

        if (self.tower_type == TowerType.CENTRAL):
            me_owner = self.owner
            for entity in entities:
                if entity.owner == me_owner and entity.type == EntityType.TOWER and entity.tower_type != TowerType.CENTRAL:
                    # entonces es mi torre y no es la central
                    if entity.life <= 0:
                        return True
        return False

    def update(self, tick_time, entities):
        if self.life <= 0:
            self.active = False
            return None

        if not self.can_i_attack(entities):
            self.state = StateType.IDLE
            self.cooldown = 0.0
            self.target = None
            return None # so never attack unless activated

        # verify state
        if self.target and self.target.life > 0 and self.in_range(self.target):
            self.state = StateType.ATTACKING
        else:
            self.state = StateType.IDLE
            self.target = None

        self.look_for_target(entities)


    def execute(self, tick_time, obstacles, add_entity):
        self.cooldown -= tick_time
        if self.target and self.cooldown <= 0 and self.target.life > 0:
            self.attack(add_entity=add_entity)
            self.cooldown = self.hit_speed


    def receive_damage(self, amount):
        self.life -= amount
        if self.life <= 0:
            self.active = False

    def render(self, screen, cell_size):
        # dibujar la torre como un circulo dependiendo de su tipo
        screen_position = self.get_screen_position(cell_size)
        radius = int(self.size * cell_size / 2)
        if self.tower_type == TowerType.CENTRAL:
            color = (0, 0, 255) if self.owner in [1, '1'] else (255, 0, 0)
        else:
            color = (0, 100, 255) if self.owner in [1, '1'] else (255, 100, 0)

        # dibuajar circulo con transparencia
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color + (200,), (radius, radius), radius)
        screen.blit(s, (int(screen_position[0]) - radius, int(screen_position[1]) - radius))

        # dibujar rey o princesa
        font = pygame.font.Font(None, 24)
        if self.tower_type == TowerType.CENTRAL:
            text = font.render("K", True, (255, 255, 255))
        else:
            text = font.render("P", True, (255, 255, 255))
        text_rect = text.get_rect(center=(int(screen_position[0]), int(screen_position[1])))
        screen.blit(text, text_rect)
        # dibujar barra de vida
        bar_width = radius * 2
        bar_height = 5
        health_percent = max(0, self.life / self.max_life)
        pygame.draw.rect(screen, (50, 50, 50), (int(screen_position[0]) - radius, int(screen_position[1]) - radius - 10, bar_width, bar_height))
        health_color = (0, 255, 0) if health_percent > 0.5 else (255, 255, 0) if health_percent > 0.25 else (255, 0, 0)
        pygame.draw.rect(screen, health_color, (int(screen_position[0]) - radius, int(screen_position[1]) - radius - 10, int(bar_width * health_percent), bar_height))

    def distance_to(self, other):
        # consider my radius
        effective_distance = super().distance_to(other) - self.size / 2
        return effective_distance


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
        if target.type == EntityType.TOWER:
            return target.distance_to(self) <= self.range

        return self.distance_to(target) <= self.range
    
    def get_valid_waypoints(self, obstacles, map_width = 18, map_height = 32):
        muajaja = []
        for i in range(-1, 2):
            for j in range(-1, 2):
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

        if self.target and (self.target.life <= 0 or not self.target.active):
            self.target = None
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

    def render(self, screen, cell_size):
        super().render(screen, cell_size)

        # dibujar una linea con una flecha hacia su target
        if self.target and self.target.active:
            start_pos = self.get_screen_position(cell_size)
            end_pos = self.target.get_screen_position(cell_size)
            pygame.draw.line(screen, (255, 255, 0), start_pos, end_pos, 2)
            # dibujar una flecha en la punta
            angle = math.atan2(end_pos[1] - start_pos[1], end_pos[0] - start_pos[0])
            arrow_size = 5
            arrow_angle = math.pi / 6
            arrow_point1 = (end_pos[0] - arrow_size * math.cos(angle - arrow_angle),
                            end_pos[1] - arrow_size * math.sin(angle - arrow_angle))
            arrow_point2 = (end_pos[0] - arrow_size * math.cos(angle + arrow_angle),
                            end_pos[1] - arrow_size * math.sin(angle + arrow_angle))
            pygame.draw.polygon(screen, (255, 255, 0), [end_pos, arrow_point1, arrow_point2])
        pass


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

    def execute(self, tick_time, obstacles, add_entity):
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

        if max_dist < 1e-6:
            return

        self.x += dx / max_dist * try_dist
        self.y += dy / max_dist * try_dist

    def update(self, tick_time, entities):
        self.target_pos = (self.target.x, self.target.y) if self.target else self.target_pos


    def execute(self, tick_time, obstacles, add_entity):
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
        
    def render(self, screen, cell_size=20):
        # dibujar una bolita pequeña negra
        screen_position = self.get_screen_position(cell_size)
        radius = 4
        pygame.draw.circle(screen, (50,50,50), (int(screen_position[0]), int(screen_position[1])), radius)

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
        

    def execute(self, tick_time, obstacles, add_entity):
        if not self.active:
            return
        
        self.elapsed_time += tick_time
        self.move_towards(tick_time)

        dx = self.target_pos[0] - self.x
        dy = self.target_pos[1] - self.y

        if (math.hypot(dx, dy) < 0.05 or self.reached_target):
            for troop in self.troops_hit:
                if troop.active:
                    troop.receive_damage(self.damage)
            self.active = False
        if self.elapsed_time > self.max_duration:
            self.active = False
    
    def render(self, screen, cell_size=20):
        # dibujar una bolita grande naranja
        screen_position = self.get_screen_position(cell_size)
        radius = 18
        pygame.draw.circle(screen, (255,165,0), (int(screen_position[0]), int(screen_position[1])), radius, 2)


class Mosquetera(Troop):
    def __init__(self, cell_x, cell_y, owner, target=None, projectile_speed=15.0):
        super().__init__(cell_x=cell_x, cell_y=cell_y, life=721, owner=owner, damage=217, speed=1.0, range=6, hit_speed=1.0, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target, add_entity):
        P = Projectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage)
        if add_entity:
            add_entity(P)
        return P
    
    def render(self, screen, cell_size):
        screen_pos = self.get_screen_position(cell_size)
        x, y = int(screen_pos[0]), int(screen_pos[1])
        
        # Color base según el jugador
        base_color = (100, 150, 255) if self.owner in [1, '1'] else (255, 100, 100)
        dark_color = (50, 100, 200) if self.owner in [1, '1'] else (200, 50, 50)
        
        # Cuerpo (vestido triangular)
        body_points = [(x, y - 8), (x - 6, y + 6), (x + 6, y + 6)]
        pygame.draw.polygon(screen, base_color, body_points)
        pygame.draw.polygon(screen, dark_color, body_points, 2)
        
        # Cabeza
        pygame.draw.circle(screen, (255, 220, 177), (x, y - 10), 4)
        pygame.draw.circle(screen, (0, 0, 0), (x, y - 10), 4, 1)
        
        # Cabello (ponytail)
        pygame.draw.circle(screen, (139, 69, 19), (x - 4, y - 11), 3)
        pygame.draw.circle(screen, (139, 69, 19), (x + 4, y - 11), 3)
        
        # Arma (mosquete)
        weapon_angle = -45 if self.owner in [1, '1'] else 45
        weapon_end_x = x + 8 * math.cos(math.radians(weapon_angle))
        weapon_end_y = y + 8 * math.sin(math.radians(weapon_angle))
        pygame.draw.line(screen, (80, 50, 30), (x + 2, y), (weapon_end_x, weapon_end_y), 3)
        
        # Barra de vida
        self._render_health_bar(screen, x, y - 18, cell_size)

    def _render_health_bar(self, screen, x, y, cell_size):
        bar_width = 20
        bar_height = 3
        health_percent = max(0, self.life / self.max_life)
        
        # Fondo de la barra
        pygame.draw.rect(screen, (50, 50, 50), (x - bar_width//2, y, bar_width, bar_height))
        # Barra de vida
        health_color = (0, 255, 0) if health_percent > 0.5 else (255, 255, 0) if health_percent > 0.25 else (255, 0, 0)
        pygame.draw.rect(screen, health_color, (x - bar_width//2, y, int(bar_width * health_percent), bar_height))


class Mago(Troop):
    def __init__(self, cell_x, cell_y, owner, target=None, projectile_speed=10.0):
        super().__init__(cell_x=cell_x, cell_y=cell_y, life=755, owner=owner, damage=281, speed=1.0, range=5.5, hit_speed=1.4, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target, add_entity):
        P = AreaProjectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage, radius=1.5)
        if add_entity:
            add_entity(P)
        return P
    
    def render(self, screen, cell_size):
        screen_pos = self.get_screen_position(cell_size)
        x, y = int(screen_pos[0]), int(screen_pos[1])
        
        # Color mágico según el jugador
        magic_color = (138, 43, 226) if self.owner in [1, '1'] else (255, 20, 147)
        robe_color = (75, 0, 130) if self.owner in [1, '1'] else (139, 0, 69)
        
        # Túnica (cuerpo)
        robe_points = [(x, y - 8), (x - 7, y + 7), (x + 7, y + 7)]
        pygame.draw.polygon(screen, robe_color, robe_points)
        pygame.draw.polygon(screen, magic_color, robe_points, 2)
        
        # Cabeza
        pygame.draw.circle(screen, (255, 220, 177), (x, y - 10), 4)
        pygame.draw.circle(screen, (0, 0, 0), (x, y - 10), 4, 1)
        
        # Sombrero puntiagudo de mago
        hat_points = [(x - 5, y - 13), (x, y - 22), (x + 5, y - 13)]
        pygame.draw.polygon(screen, robe_color, hat_points)
        pygame.draw.polygon(screen, magic_color, hat_points, 1)
        
        # Estrella mágica en el sombrero
        star_y = y - 17
        pygame.draw.circle(screen, (255, 255, 100), (x, star_y), 2)
        
        # Báculo mágico
        staff_end_y = y + 10
        pygame.draw.line(screen, (139, 90, 43), (x - 5, y - 3), (x - 5, staff_end_y), 2)
        # Orbe mágico en la punta
        pygame.draw.circle(screen, magic_color, (x - 5, y - 5), 3)
        pygame.draw.circle(screen, (255, 255, 255), (x - 5, y - 5), 3, 1)
        
        # Barra de vida
        self._render_health_bar(screen, x, y - 25, cell_size)

    def _render_health_bar(self, screen, x, y, cell_size):
        bar_width = 20
        bar_height = 3
        health_percent = max(0, self.life / self.max_life)
        
        pygame.draw.rect(screen, (50, 50, 50), (x - bar_width//2, y, bar_width, bar_height))
        health_color = (0, 255, 0) if health_percent > 0.5 else (255, 255, 0) if health_percent > 0.25 else (255, 0, 0)
        pygame.draw.rect(screen, health_color, (x - bar_width//2, y, int(bar_width * health_percent), bar_height))


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

    def render(self, screen, cell_size):
        screen_pos = self.get_screen_position(cell_size)
        x, y = int(screen_pos[0]), int(screen_pos[1])
        
        # Colores según el jugador
        armor_color = (192, 192, 192) if self.owner in [1, '1'] else (169, 169, 169)
        accent_color = (0, 100, 200) if self.owner in [1, '1'] else (200, 0, 0)
        
        # Cuerpo del caballero (rectángulo para armadura)
        pygame.draw.rect(screen, armor_color, (x - 6, y - 4, 12, 10))
        pygame.draw.rect(screen, (100, 100, 100), (x - 6, y - 4, 12, 10), 1)
        
        # Detalles de armadura (líneas)
        pygame.draw.line(screen, accent_color, (x - 4, y - 2), (x - 4, y + 4), 1)
        pygame.draw.line(screen, accent_color, (x + 4, y - 2), (x + 4, y + 4), 1)
        
        # Cabeza con casco
        pygame.draw.circle(screen, armor_color, (x, y - 9), 5)
        pygame.draw.circle(screen, (100, 100, 100), (x, y - 9), 5, 1)
        
        # Visera del casco
        pygame.draw.rect(screen, (50, 50, 50), (x - 3, y - 10, 6, 3))
        
        # Penacho en el casco
        plume_points = [(x - 1, y - 14), (x, y - 17), (x + 1, y - 14)]
        pygame.draw.polygon(screen, accent_color, plume_points)
        
        # Escudo
        shield_x = x - 8
        shield_points = [
            (shield_x, y - 3),
            (shield_x - 3, y),
            (shield_x - 3, y + 4),
            (shield_x, y + 6),
            (shield_x + 3, y + 4),
            (shield_x + 3, y)
        ]
        pygame.draw.polygon(screen, accent_color, shield_points)
        pygame.draw.polygon(screen, (255, 215, 0), shield_points, 1)
        
        # Espada
        sword_x = x + 8
        pygame.draw.line(screen, (200, 200, 200), (sword_x, y - 2), (sword_x, y + 8), 3)
        # Empuñadura
        pygame.draw.line(screen, (139, 69, 19), (sword_x - 2, y), (sword_x + 2, y), 3)
        # Pomo
        pygame.draw.circle(screen, (255, 215, 0), (sword_x, y + 9), 2)
        
        # Barra de vida
        self._render_health_bar(screen, x, y - 20, cell_size)

    def _render_health_bar(self, screen, x, y, cell_size):
        bar_width = 24
        bar_height = 4
        health_percent = max(0, self.life / self.max_life)
        
        pygame.draw.rect(screen, (50, 50, 50), (x - bar_width//2, y, bar_width, bar_height))
        health_color = (0, 255, 0) if health_percent > 0.5 else (255, 255, 0) if health_percent > 0.25 else (255, 0, 0)
        pygame.draw.rect(screen, health_color, (x - bar_width//2, y, int(bar_width * health_percent), bar_height))
