"""
================================================================================
                                  UTILS.PY
                    Librería completa de utilidades para videojuegos
================================================================================

Esta librería contiene todas las herramientas matemáticas y algoritmos que 
necesitas para desarrollar videojuegos, especialmente juegos de estrategia 
en tiempo real como Clash Royale.


FUNCIONES DE PATHFINDING:

heuristic_distance(pos1, pos2)
get_neighbors(position, grid_width, grid_height)
a_star(start, goal, grid_width, grid_height, obstacles)

FUNCIONES DE INTERPOLACIÓN:

lerp(a, b, t)
lerp_point(p1, p2, t)
ease_in_out(t)
ease_in_quad(t)
ease_out_quad(t)
bezier_curve(p0, p1, p2, t)
cubic_bezier(p0, p1, p2, p3, t)

FUNCIONES MATEMÁTICAS:

clamp(value, min_val, max_val)
map_range(value, in_min, in_max, out_min, out_max)
angle_between_points(p1, p2)
rotate_point(point, center, angle)
degrees_to_radians(degrees)
radians_to_degrees(radians)
normalize_angle(angle)

FUNCIONES DE COLISIONES:

point_in_circle(point, center, radius)
circle_circle_collision(center1, radius1, center2, radius2)
point_in_rect(point, rect)
line_intersection(p1, p2, p3, p4)

FUNCIONES DE PYGAME:

draw_rounded_rect(surface, color, rect, radius)
draw_arrow(surface, color, start, end, width, head_size)

CONTEXT MANAGERS:

suppress_stdout()
silent_call(func, *args, **kwargs)

UTILIDADES GENERALES:

screen_to_grid(x, y, cell_size)
grid_to_screen(grid_x, grid_y, cell_size)
format_time(seconds)
random_point_in_circle(center, radius)
smooth_step(edge0, edge1, x)

CLASES DISPONIBLES:

Point:
    - __init__(x, y)
    - __add__, __sub__, __mul__, __truediv__, __eq__
    - distance_to(other)
    - magnitude()
    - normalized()
    - dot(other)
    - to_tuple()
    - to_int_tuple()

Vector2:
    - __init__(x, y)
    - __add__, __sub__, __mul__
    - magnitude()
    - normalized()
    - dot(other)
    - cross(other)
    - angle()
    - rotate(angle)

Rectangle:
    - __init__(x, y, width, height)
    - left, right, top, bottom (properties)
    - center (property)
    - contains(point)
    - intersects(other)

AStarNode:
    - __init__(position, g_cost, h_cost, parent)


EJEMPLO DE USO:

    from utils import Point, a_star, lerp, draw_rounded_rect
    
    # Crear puntos y calcular distancias
    start = Point(0, 0)
    end = Point(10, 10)
    distance = start.distance_to(end)
    
    # Pathfinding con A*
    path = a_star((0,0), (10,10), 20, 20, obstacles={(5,5), (6,6)})
    
    # Interpolación suave
    current_pos = lerp_point(start, end, 0.5)
    
    # Dibujar elementos con esquinas redondeadas
    draw_rounded_rect(screen, (255,0,0), (10,10,100,50), 5)

================================================================================
"""

import math
import sys
import os
from contextlib import contextmanager
from typing import List, Tuple, Optional, Union
import pygame
import heapq


# =============================================================================
# CLASES BÁSICAS
# =============================================================================

class Point:
    """Clase para representar un punto en 2D"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float):
        return Point(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float):
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float):
        return Point(self.x / scalar, self.y / scalar)
    
    def __eq__(self, other):
        return abs(self.x - other.x) < 1e-6 and abs(self.y - other.y) < 1e-6
    
    def __repr__(self):
        return f"Point({self.x:.2f}, {self.y:.2f})"
    
    def distance_to(self, other) -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalized(self):
        mag = self.magnitude()
        if mag == 0:
            return Point(0, 0)
        return Point(self.x / mag, self.y / mag)
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def to_int_tuple(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))


class Vector2:
    """Alias para Point con métodos específicos de vectores"""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float):
        return self.__mul__(scalar)
    
    def __repr__(self):
        return f"Vector2({self.x:.2f}, {self.y:.2f})"
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalized(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)
    
    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y
    
    def cross(self, other) -> float:
        """Cross product en 2D (devuelve escalar)"""
        return self.x * other.y - self.y * other.x
    
    def angle(self) -> float:
        """Ángulo en radianes"""
        return math.atan2(self.y, self.x)
    
    def rotate(self, angle: float):
        """Rota el vector por un ángulo en radianes"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )


class Rectangle:
    """Clase para representar un rectángulo"""
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    @property
    def left(self) -> float:
        return self.x
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def top(self) -> float:
        return self.y
    
    @property
    def bottom(self) -> float:
        return self.y + self.height
    
    @property
    def center(self) -> Point:
        return Point(self.x + self.width/2, self.y + self.height/2)
    
    def contains(self, point: Point) -> bool:
        return (self.left <= point.x <= self.right and 
                self.top <= point.y <= self.bottom)
    
    def intersects(self, other) -> bool:
        return not (self.right < other.left or other.right < self.left or
                   self.bottom < other.top or other.bottom < self.top)


# =============================================================================
# ALGORITMOS DE PATHFINDING
# =============================================================================

class AStarNode:
    def __init__(self, position: Tuple[int, int], g_cost: float = 0, h_cost: float = 0, parent=None):
        self.position = position
        self.g_cost = g_cost  # Costo desde el inicio
        self.h_cost = h_cost  # Heurística hasta el objetivo
        self.f_cost = g_cost + h_cost  # Costo total
        self.parent = parent
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        return self.position == other.position


def heuristic_distance(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
    """Distancia Manhattan para A*"""
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


def get_neighbors(position: Tuple[int, int], grid_width: int, grid_height: int) -> List[Tuple[int, int]]:
    """Obtiene vecinos válidos de una posición en una grid"""
    x, y = position
    neighbors = []
    
    # 8 direcciones (incluye diagonales)
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    
    for dx, dy in directions:
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < grid_width and 0 <= new_y < grid_height:
            neighbors.append((new_x, new_y))
    
    return neighbors


def a_star(start: Tuple[int, int], goal: Tuple[int, int], 
          grid_width: int, grid_height: int, 
          obstacles: set = None) -> Optional[List[Tuple[int, int]]]:
    """
    Implementación del algoritmo A*
    
    Args:
        start: Posición inicial (x, y)
        goal: Posición objetivo (x, y)
        grid_width: Ancho de la grid
        grid_height: Alto de la grid
        obstacles: Set de posiciones bloqueadas
    
    Returns:
        Lista de posiciones que forman el camino, o None si no hay camino
    """
    if obstacles is None:
        obstacles = set()
    
    if start == goal:
        return [start]
    
    if goal in obstacles:
        return None
    
    open_set = []
    closed_set = set()
    
    start_node = AStarNode(start, 0, heuristic_distance(start, goal))
    heapq.heappush(open_set, start_node)
    
    while open_set:
        current_node = heapq.heappop(open_set)
        
        if current_node.position == goal:
            # Reconstruir el camino
            path = []
            while current_node:
                path.append(current_node.position)
                current_node = current_node.parent
            return path[::-1]
        
        closed_set.add(current_node.position)
        
        for neighbor_pos in get_neighbors(current_node.position, grid_width, grid_height):
            if neighbor_pos in closed_set or neighbor_pos in obstacles:
                continue
            
            # Costo de movimiento (diagonal cuesta más)
            dx = abs(neighbor_pos[0] - current_node.position[0])
            dy = abs(neighbor_pos[1] - current_node.position[1])
            move_cost = 1.414 if dx + dy == 2 else 1.0  # √2 para diagonales
            
            g_cost = current_node.g_cost + move_cost
            h_cost = heuristic_distance(neighbor_pos, goal)
            
            neighbor_node = AStarNode(neighbor_pos, g_cost, h_cost, current_node)
            
            # Verificar si ya está en open_set con menor costo
            existing_node = None
            for node in open_set:
                if node.position == neighbor_pos:
                    existing_node = node
                    break
            
            if existing_node is None or g_cost < existing_node.g_cost:
                if existing_node:
                    open_set.remove(existing_node)
                    heapq.heapify(open_set)
                heapq.heappush(open_set, neighbor_node)
    
    return None  # No se encontró camino


# =============================================================================
# INTERPOLACIONES Y ANIMACIONES
# =============================================================================

def lerp(a: float, b: float, t: float) -> float:
    """Interpolación lineal entre a y b"""
    return a + (b - a) * t


def lerp_point(p1: Point, p2: Point, t: float) -> Point:
    """Interpolación lineal entre dos puntos"""
    return Point(lerp(p1.x, p2.x, t), lerp(p1.y, p2.y, t))


def ease_in_out(t: float) -> float:
    """Función de easing suave (cubic)"""
    return t * t * (3.0 - 2.0 * t)


def ease_in_quad(t: float) -> float:
    """Easing cuadrático de entrada"""
    return t * t


def ease_out_quad(t: float) -> float:
    """Easing cuadrático de salida"""
    return 1 - (1 - t) * (1 - t)


def bezier_curve(p0: Point, p1: Point, p2: Point, t: float) -> Point:
    """Curva de Bézier cuadrática"""
    u = 1 - t
    return Point(
        u*u*p0.x + 2*u*t*p1.x + t*t*p2.x,
        u*u*p0.y + 2*u*t*p1.y + t*t*p2.y
    )


def cubic_bezier(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    """Curva de Bézier cúbica"""
    u = 1 - t
    return Point(
        u*u*u*p0.x + 3*u*u*t*p1.x + 3*u*t*t*p2.x + t*t*t*p3.x,
        u*u*u*p0.y + 3*u*u*t*p1.y + 3*u*t*t*p2.y + t*t*t*p3.y
    )


# =============================================================================
# UTILIDADES DE MATEMÁTICAS
# =============================================================================

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limita un valor entre min y max"""
    return max(min_val, min(max_val, value))


def map_range(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Mapea un valor de un rango a otro"""
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def angle_between_points(p1: Point, p2: Point) -> float:
    """Calcula el ángulo entre dos puntos en radianes"""
    return math.atan2(p2.y - p1.y, p2.x - p1.x)


def rotate_point(point: Point, center: Point, angle: float) -> Point:
    """Rota un punto alrededor de un centro"""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    
    # Trasladar al origen
    dx = point.x - center.x
    dy = point.y - center.y
    
    # Rotar
    rotated_x = dx * cos_a - dy * sin_a
    rotated_y = dx * sin_a + dy * cos_a
    
    # Trasladar de vuelta
    return Point(rotated_x + center.x, rotated_y + center.y)


def degrees_to_radians(degrees: float) -> float:
    return degrees * math.pi / 180


def radians_to_degrees(radians: float) -> float:
    return radians * 180 / math.pi


def normalize_angle(angle: float) -> float:
    """Normaliza un ángulo a [-π, π]"""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


# =============================================================================
# DETECCIÓN DE COLISIONES
# =============================================================================

def point_in_circle(point: Point, center: Point, radius: float) -> bool:
    """Verifica si un punto está dentro de un círculo"""
    return point.distance_to(center) <= radius


def circle_circle_collision(center1: Point, radius1: float, center2: Point, radius2: float) -> bool:
    """Verifica colisión entre dos círculos"""
    return center1.distance_to(center2) <= (radius1 + radius2)


def point_in_rect(point: Point, rect: Rectangle) -> bool:
    """Verifica si un punto está dentro de un rectángulo"""
    return rect.contains(point)


def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
    """Encuentra la intersección entre dos líneas"""
    x1, y1 = p1.x, p1.y
    x2, y2 = p2.x, p2.y
    x3, y3 = p3.x, p3.y
    x4, y4 = p4.x, p4.y
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None  # Líneas paralelas
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    if 0 <= t <= 1 and 0 <= u <= 1:
        return Point(x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    
    return None


# =============================================================================
# UTILIDADES DE PYGAME
# =============================================================================

def draw_rounded_rect(surface, color, rect, radius):
    """Dibuja un rectángulo con esquinas redondeadas"""
    x, y, width, height = rect
    pygame.draw.rect(surface, color, (x + radius, y, width - 2*radius, height))
    pygame.draw.rect(surface, color, (x, y + radius, width, height - 2*radius))
    pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
    pygame.draw.circle(surface, color, (x + width - radius, y + radius), radius)
    pygame.draw.circle(surface, color, (x + radius, y + height - radius), radius)
    pygame.draw.circle(surface, color, (x + width - radius, y + height - radius), radius)


def draw_arrow(surface, color, start: Point, end: Point, width: int = 2, head_size: int = 10):
    """Dibuja una flecha"""
    pygame.draw.line(surface, color, start.to_int_tuple(), end.to_int_tuple(), width)
    
    # Calcular puntas de la flecha
    angle = angle_between_points(start, end)
    head_angle1 = angle + 2.5
    head_angle2 = angle - 2.5
    
    head_point1 = Point(
        end.x - head_size * math.cos(head_angle1),
        end.y - head_size * math.sin(head_angle1)
    )
    head_point2 = Point(
        end.x - head_size * math.cos(head_angle2),
        end.y - head_size * math.sin(head_angle2)
    )
    
    pygame.draw.line(surface, color, end.to_int_tuple(), head_point1.to_int_tuple(), width)
    pygame.draw.line(surface, color, end.to_int_tuple(), head_point2.to_int_tuple(), width)


# =============================================================================
# CONTEXT MANAGERS Y UTILIDADES
# =============================================================================

@contextmanager
def suppress_stdout():
    """Context manager que suprime prints"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


def silent_call(func, *args, **kwargs):
    """Ejecuta una función silenciando su output"""
    with suppress_stdout():
        return func(*args, **kwargs)


# =============================================================================
# CONVERSIONES Y UTILIDADES GENERALES
# =============================================================================

def screen_to_grid(x: float, y: float, cell_size: int) -> Tuple[int, int]:
    """Convierte coordenadas de pantalla a grid"""
    return (int(x // cell_size), int(y // cell_size))


def grid_to_screen(grid_x: int, grid_y: int, cell_size: int) -> Tuple[int, int]:
    """Convierte coordenadas de grid a pantalla"""
    return (grid_x * cell_size, grid_y * cell_size)


def format_time(seconds: float) -> str:
    """Formatea tiempo en MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def random_point_in_circle(center: Point, radius: float) -> Point:
    """Genera un punto aleatorio dentro de un círculo"""
    import random
    angle = random.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(random.random())
    return Point(center.x + r * math.cos(angle), center.y + r * math.sin(angle))


def smooth_step(edge0: float, edge1: float, x: float) -> float:
    """Función smoothstep para transiciones suaves"""
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)