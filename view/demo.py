import tkinter as tk
import random

from model.test import Entity, Agent, InteractiveEntity
from view.topdown import TopDownVisualizer


def make_demo_entities():
    entities = []
    # Agents
    entities.append(Agent(1, "Alice", 0, 0, 'F', 100, 30, []))
    entities.append(Agent(2, "Bob", -20, 10, 'M', 100, 28, []))
    entities.append(Agent(3, "Eve", 50, -30, 'F', 90, 25, []))
    # Interactive entities
    entities.append(InteractiveEntity(10, "Chest", 15, 5, durability=10))
    entities.append(InteractiveEntity(11, "Research Node", -40, 20, durability=5))
    entities.append(InteractiveEntity(12, "Door", 30, 40, durability=100))
    # Generic entities
    entities.append(Entity(20, "Rock", -5, -10))
    entities.append(Entity(21, "Tree", 20, 15))
    return entities


if __name__ == '__main__':
    entities = make_demo_entities()
    viz = TopDownVisualizer(width=800, height=600)
    viz.show(entities)
