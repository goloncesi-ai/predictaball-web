from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .config import SimulationConfig

@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int
    x2: int
    y1: int
    y2: int

    def contains(self, x: int, y: int, margin: int = 0) -> bool:
        return (self.x1 - margin <= x <= self.x2 + margin) and (self.y1 - margin <= y <= self.y2 + margin)

def build_clusters() -> List[Cluster]:
    return [
        Cluster("Goalkeeper_Zone", 1, 1, 1, 9),
        Cluster("Back_Left", 2, 3, 1, 3),
        Cluster("Back_Right", 2, 3, 7, 9),
        Cluster("Mid_Def", 2, 3, 4, 6),
        Cluster("Mid_Att", 4, 5, 4, 6),
        Cluster("Wing_Left", 4, 5, 1, 3),
        Cluster("Wing_Right", 4, 5, 7, 9),
        Cluster("Left_Strip", 2, 5, 1, 3),
        Cluster("Mid_Strip", 2, 5, 4, 6),
        Cluster("Right_Strip", 2, 5, 7, 9),
    ]

def main_clusters() -> List[Cluster]:
    return [
        Cluster("Goalkeeper_Zone", 1, 1, 1, 9),
        Cluster("Back_Left", 2, 3, 1, 3),
        Cluster("Back_Right", 2, 3, 7, 9),
        Cluster("Mid_Def", 2, 3, 4, 6),
        Cluster("Mid_Att", 4, 5, 4, 6),
        Cluster("Wing_Left", 4, 5, 1, 3),
        Cluster("Wing_Right", 4, 5, 7, 9),
    ]

def strip_clusters() -> List[Cluster]:
    return [
        Cluster("Left_Strip", 2, 5, 1, 3),
        Cluster("Mid_Strip", 2, 5, 4, 6),
        Cluster("Right_Strip", 2, 5, 7, 9),
    ]

def mirror_cluster_x(c: Cluster, cfg: SimulationConfig) -> Cluster:
    # Mirror rectangle in X: (x1..x2) -> (mirror(x2)..mirror(x1))
    mirror = lambda x: (cfg.x_min + cfg.x_max) - x
    return Cluster(name=c.name, x1=mirror(c.x2), x2=mirror(c.x1), y1=c.y1, y2=c.y2)
