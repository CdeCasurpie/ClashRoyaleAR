from abc import ABC, abstractmethod
import math

class Entity(ABC):
    """
    This class represents a generic entity in the game. It will contain
    information about position, health, owner, etc.
    """
    def __init__(self, x, y, owner, entity_type = 'troop'):
        self.x = x
        self.y = y
        self.owner = owner  # Could be 'player1' or 'player2'
        self.entity_id = id(self)  # Unique identifier for the entity instance
        self.active = True  # Indicates if the entity is active in the game
        self.type = entity_type  # 'troop', 'tower', 'spell', 'projectile', etc.
    @abstractmethod 
    def update(self):
        """
        Update the entity state based on the game rules.
        """
        pass
    
class Tower(Entity):
    """
    This class represents a tower in the game. It extends the Entity class
    and adds specific attributes for towers.
    """
    def __init__(self, x, y, life, owner, tower_type):
        super().__init__(x, y, owner)
        self.tower_type = tower_type  # Could be 'lateral' or 'central'
        self.life = life
        self.attack_speed = 1.0  # Attacks per second
        self.attack_range = 5.0  # Attack range in meters
        self.damage = 1  # Damage per attack
        self.cooldown = 0.0
        self.target = None

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
            if entity.owner == self.owner or not entity.active: # falta poner if entity.type == hechizo
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

    def update(self, delta_time, entities):
        """
        Update tower state: find a target, handle cooldown, and attack.
        Returns a projectile if fired, else None.
        """
        if not self.target or not self.target.active or not self.in_range(self.target):
            self.look_for_target(entities)

        self.cooldown -= delta_time
        projectile = None
        if self.target and self.cooldown <= 0:
            projectile = self.attack(self.target)
            self.cooldown = 1.0 / self.attack_speed

        if self.life <= 0:
            self.active = False

        return projectile

class Troop(Entity, ABC):
    """
    Base class for all troops. Contains common logic for moving and attacking.
    """

    def __init__(self, x, y, life, owner, damage, speed, range, attack_speed, target=None):
        super().__init__(x, y, owner)
        self.life = life  
        self.damage = damage
        self.speed = speed            # Speed in meters per second
        self.range = range            # Attack range in meters
        self.attack_speed = attack_speed  # Attacks per second
        self.target = target          # Target entity
        self.cooldown = 0

    # se debe sobreescribir para tropas como el ariete
    def look_for_target(self, entities):
        """
        Simple nearest-target selection: find the closest enemy entity.
        """
        closest = None
        min_dist = float('inf')
        for entity in entities:
            if entity.owner == self.owner or not entity.active: # falta poner if entity.type == hechizo
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

    # cambiar este metodo para que use el grafo
    def move_towards(self, target_x, target_y, delta_time):
        """
        Move the troop towards a point at self.speed.
        """
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += dx / dist * self.speed * delta_time
            self.y += dy / dist * self.speed * delta_time
    

    def update(self, delta_time, entities):
        """
        Update the troop state. 
        """
        if not self.target or self.target.life <= 0:
            self.look_for_target(entities)

        # Move or attack
        something = None
        if self.target:
            if not self.in_range(self.target):
                # move closer
                self.move_towards(self.target.x, self.target.y, delta_time)
            else:
                # in range, try attack
                self.cooldown -= delta_time
                if self.cooldown <= 0:
                    something = self.attack(self.target)
                    self.cooldown = 1.0 / self.attack_speed
                    
        if self.life <= 0:
            self.active = False  # Mark as inactive if life is 0 or below

        return something
 


class Spell(Entity):
    """
    This class represents a spell in the game. It extends the Entity class
    and adds specific attributes for spells.
    """
    def __init__(self, x, y, owner, duration, damage, radius):
        super().__init__(x, y, owner)
        self.duration = duration  # Duration of the spell effect
        self.damage = damage
        self.radius = radius  # Area of effect radius

    def update(self):
        """
        Update the spell state based on the game rules.
        """
        pass

class Projectile(Entity):
    """
    This class represents a projectile in the game. It extends the Entity class
    and adds specific attributes for projectiles.
    """
    def __init__(self, x, y, owner, speed, target, damage):
        super().__init__(x, y, owner)
        self.speed = speed  # Speed in meters per second
        self.target = target  # Target entity
        self.damage = damage  # Damage dealt by the projectile
        self.max_duration = 5.0  # Max duration in seconds
        self.elapsed_time = 0.0  # Time since projectile was created

    def move_towards(self, target_x, target_y, delta_time):
        """
        Move the projectile toward the target position.
        """
        dx = target_x - self.x
        dy = target_y - self.y
        distance = (dx**2 + dy**2)**0.5
        if distance == 0:
            return
        # Normalizamos y avanzamos
        nx, ny = dx / distance, dy / distance
        self.x += nx * self.speed * delta_time
        self.y += ny * self.speed * delta_time

    def update(self, delta_time=1.0):
        """
        Update the projectile state based on the game rules.
        """
        if not self.active or not self.target:
            return
        
        self.elapsed_time += delta_time

        # Move toward target
        self.move_towards(self.target.x, self.target.y, delta_time)

        # Check if reached target
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = (dx**2 + dy**2)**0.5

        if distance < 0.1:  # hit tolerance
            # Apply damage
            self.target.life -= self.damage
            # Deactivate projectile
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
        self.radius = radius  # Area of effect radius

    def update(self, entities, delta_time=1.0):
        """
        Update the Area Projectile state based on the game rules.
        """
        if not self.active or not self.target:
            return

        # Move toward target point (we treat target.x, target.y as center of AoE)
        self.move_towards(self.target.x, self.target.y, delta_time)

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = (dx**2 + dy**2)**0.5

        if distance < 0.1:  # reached AoE center
            # Apply damage to all entities in radius
            for entity in entities:
                edx = entity.x - self.x
                edy = entity.y - self.y
                if (edx**2 + edy**2)**0.5 <= self.radius:
                    entity.life -= self.damage
            self.active = False

class Mosquetera(Troop):
    """
    This class represents a Mosquetera troop in the game. It extends the Troop class
    and adds specific attributes for Mosqueteras.
    """
    def __init__(self, x, y, owner, target):
        super().__init__(x, y, life=4, owner=owner, damage=1, speed=1.5, range=5, target=target)
        self.attack_speed = 1.5  # Attacks per second

    def attack(self, target):
        ataque = Projectile(self.x, self.y, self.owner, speed=self.attack_speed, target=target, damage=self.damage)
        
        return ataque
    


class Mago(Troop):
    """
    This class represents a Mago troop in the game. It extends the Troop class
    and adds specific attributes for Magos.
    """
    def __init__(self, x, y, owner, target):
        super().__init__(x, y, life=4, owner=owner, damage=1, speed=1.0, range=5, target=target)
        self.attack_speed = 1.0  # Attacks per second

    def attack(self, target):
        ataque = AreaProjectile(self.x, self.y, self.owner, speed=self.attack_speed, target=target, damage=self.damage, radius=2)
        
        return ataque


class Caballero(Troop):
    """
    This class represents a Caballero troop in the game. It extends the Troop class
    and adds specific attributes for Caballeros.
    """
    def __init__(self, x, y, owner, target):
        super().__init__(x, y, life=6, owner=owner, damage=1, speed=1.0, range=1, target=target)
        self.attack_speed = 1.0  # Attacks per second

    def attack(self, target):
        if target.life > 0:
            target.life -= self.damage
            if target.life < 0:
                target.life = 0
        
