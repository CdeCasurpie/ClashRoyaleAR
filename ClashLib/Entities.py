from abc import ABC, abstractmethod
import math

# ID global
_next_entity_id = 0
def get_next_id():
    global _next_entity_id
    _next_entity_id += 1
    return _next_entity_id

class Entity(ABC):
    """
    This class represents a generic entity in the game.
    """
    def __init__(self, x, y, owner, entity_type = 'troop'):
        self.x = x
        self.y = y
        self.owner = owner
        self.entity_id = get_next_id()  # Unique incremental ID
        self.active = True
        self.type = entity_type  # 'troop', 'tower', 'spell', 'projectile', etc.

    @abstractmethod 
    def update(self, delta_time, entities, path_finder=None):
        """
        Update the entity state.
        """
        pass

    @abstractmethod
    def execute(self, delta_time):
        """
        Execute the entity's action.
        """
        pass


class Tower(Entity):
    """
    This class represents a tower in the game. It extends the Entity class
    and adds specific attributes for towers.
    """
    def __init__(self, x, y, life, owner, tower_type):
        super().__init__(x, y, owner, entity_type='tower')
        self.tower_type = tower_type
        self.life = life
        self.attack_speed = 1.0
        self.attack_range = 5.0
        self.damage = 1
        self.cooldown = 0.0
        self.target : Troop | None = None

    def in_range(self, target):
        dx = target.x - self.x
        dy = target.y - self.y
        return math.hypot(dx, dy) <= self.attack_range

    def look_for_target(self, entities):
        """
        Simple nearest-target selection: find the closest enemy entity within range.
        """
        closest = None
        min_dist = float('inf')
        for entity in entities:
            if entity.owner == self.owner or not entity.active:
                continue

            dx = entity.x - self.x
            dy = entity.y - self.y
            dist = math.hypot(dx, dy)
            if dist <= self.attack_range and dist < min_dist:
                min_dist = dist
                closest = entity
        self.target = closest

    def attack(self, target):
        """
        Fire a projectile at the target.
        """
        return Projectile(self.x, self.y, self.owner, speed=5.0, target=target, damage=self.damage)

    def update(self, delta_time, entities, path_finder=None):
        if self.life <= 0:
            self.active = False
            return None

        if not self.target or not self.target.active or not self.in_range(self.target):
            self.look_for_target(entities)


    def execute(self, delta_time):
        self.cooldown -= delta_time
        projectile = None
        if self.target and self.cooldown <= 0 and self.target.life > 0:
            projectile = self.attack(self.target)
            self.cooldown = 1.0 / self.attack_speed

        return projectile

class Troop(Entity, ABC):
    """
    Base class for all troops. Contains common logic for moving and attacking.
    """

    def __init__(self, x, y, life, owner, damage, speed, range, attack_speed, target=None):
        super().__init__(x, y, owner)
        self.life = life
        self.damage = damage
        self.speed = speed
        self.range = range
        self.attack_speed = attack_speed
        self.target = target
        self.cooldown = 0.0
        self.state = "idle" # or "attacking" or "idle"
        self.current_path = []
        self.delay = 1.0

    # se debe sobreescribir para tropas como el ariete
    def look_for_target(self, entities):
        """
        Simple nearest-target selection: find the closest enemy entity.
        """
        closest = None
        min_dist = float('inf')
        for entity in entities:
            if entity.owner == self.owner or not entity.active or entity.type == 'projectile':
                continue
            dx = entity.x - self.x
            dy = entity.y - self.y
            dist = math.hypot(dx, dy)
            if dist < min_dist:
                min_dist = dist
                closest = entity
        self.target = closest

    @abstractmethod
    def attack(self, target):
        """
        Attack the target entity. 
        Should return a Projectile or None (if melee attack).
        """
        pass

    def in_range(self, target):
        """
        Check if target is within attack range.
        """
        dx = target.x - self.x
        dy = target.y - self.y
        return math.hypot(dx, dy) <= self.range

    def move_towards(self, target_x, target_y, delta_time, tolerance=0.05):
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > tolerance:
            self.x += dx / dist * self.speed * delta_time
            self.y += dy / dist * self.speed * delta_time

    def update(self, delta_time, entities, path_finder=None):
        self.delay -= delta_time
        if self.delay > 0:
            return None
        
        self.state = "attacking" if self.target and self.in_range(self.target) else "moving"

        if self.life <= 0:
            self.active = False
            return None

        old_target = self.target
        if (not self.target or self.target.life <= 0) and (self.state != "attacking"):
            self.look_for_target(entities)

        # si cambie de target, recalculo el path
        if old_target != self.target and self.target and path_finder:
            start = [int(self.x), int(self.y)]
            goal = [int(self.target.x), int(self.target.y)]
            self.current_path = path_finder(start, goal)

    def execute(self, delta_time):
        projectile = None
        if self.state == "attacking" and self.target and self.target.life > 0:
            self.cooldown -= delta_time
            if self.cooldown <= 0:
                projectile = self.attack(self.target)
                self.cooldown = 1.0 / self.attack_speed
        elif self.state == "moving" and self.current_path:
            next_cell = self.current_path[0]
            self.move_towards(next_cell[0] + 0.5, next_cell[1] + 0.5, delta_time)
            if math.hypot(self.x - (next_cell[0] + 0.5), self.y - (next_cell[1] + 0.5)) < 0.1:
                self.current_path.pop(0)
        return projectile
    

    def receive_damage(self, amount):
        self.life -= amount
        if self.life <= 0:
            self.active = False


class Spell(Entity):
    """
    This class represents a spell in the game. It extends the Entity class
    and adds specific attributes for spells.
    """
    def __init__(self, x, y, owner, duration, damage, radius):
        super().__init__(x, y, owner, entity_type='spell')
        self.duration = duration
        self.damage = damage
        self.radius = radius

    def update(self, delta_time, entities=None, path_finder=None):
        if self.duration <= 0:
            self.active = False
        else:
            self.duration -= delta_time

    def execute(self, delta_time):
        return None


class Projectile(Entity):
    """
    This class represents a projectile in the game. It extends the Entity class
    and adds specific attributes for projectiles.
    """
    def __init__(self, x, y, owner, speed, target, damage):
        super().__init__(x, y, owner, entity_type='projectile')
        self.speed = speed
        self.target = target
        self.damage = damage
        self.max_duration = 5.0
        self.elapsed_time = 0.0

    def move_towards(self, target_x, target_y, delta_time, tolerance=0.05):
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > tolerance:
            self.x += dx / dist * self.speed * delta_time
            self.y += dy / dist * self.speed * delta_time

    def update(self, delta_time, entities=None, path_finder=None):
        pass

    def execute(self, delta_time):
        if not self.active or not self.target:
            return
        
        self.elapsed_time += delta_time
        self.move_towards(self.target.x, self.target.y, delta_time)

        dx = self.target.x - self.x
        dy = self.target.y - self.y

        if math.hypot(dx, dy) < 0.05:
            self.target.receive_damage(self.damage)
            self.active = False
        if self.elapsed_time > self.max_duration:
            self.active = False

class AreaProjectile(Projectile):
    """
    This class represents an Area Projectile in the game. It extends the Projectile class
    and adds specific attributes for Area Projectiles.
    """
    def __init__(self, x, y, owner, speed, target, damage, radius):
        super().__init__(x, y, owner, speed, target, damage)
        self.radius = radius
        self.troops_hit : list[Troop] = []

    def update(self, delta_time, entities, path_finder=None):
        # calcula cuanto avanza y si ya esta muy cerca dle obejtivo llena trops_hit
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        dist = math.hypot(dx, dy)
        if dist < self.radius:
            for entity in entities:
                if entity.owner != self.owner and entity.active and entity.type != 'projectile':
                    if math.hypot(entity.x - self.x, entity.y - self.y) <= self.radius:
                        if entity not in self.troops_hit:
                            self.troops_hit.append(entity)
        


    def execute(self, delta_time):
        if not self.active or not self.target:
            return

        self.elapsed_time += delta_time

        if self.elapsed_time > self.max_duration:
            self.active = False
            return

        self.move_towards(self.target.x, self.target.y, delta_time)
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        if math.hypot(dx, dy) < 0.05:
            for entity in self.troops_hit:
                if math.hypot(entity.x - self.x, entity.y - self.y) <= self.radius:
                    entity.receive_damage(self.damage)
            self.active = False


class Mosquetera(Troop):
    def __init__(self, x, y, owner, target, projectile_speed=3.0):
        super().__init__(x, y, life=4, owner=owner, damage=1, speed=1.5, range=5, attack_speed=1.5, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target):
        return Projectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage)


class Mago(Troop):
    def __init__(self, x, y, owner, target, projectile_speed=3.0):
        super().__init__(x, y, life=4, owner=owner, damage=1, speed=1.0, range=5, attack_speed=1.0, target=target)
        self.projectile_speed = projectile_speed

    def attack(self, target):
        return AreaProjectile(self.x, self.y, self.owner, speed=self.projectile_speed, target=target, damage=self.damage, radius=2)


class Caballero(Troop):
    """
    This class represents a Caballero troop in the game. It extends the Troop class
    and adds specific attributes for Caballeros.
    """
    def __init__(self, x, y, owner, target):
        super().__init__(x, y, life=6, owner=owner, damage=1, speed=1.0, range=1, attack_speed=1.0, target=target)

    def attack(self, target: Troop):
        if target.life > 0:
            target.receive_damage(self.damage)
            if target.life < 0:
                target.life = 0

