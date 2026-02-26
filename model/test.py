from model.action import Moveable, Edible, Researchable


class Entity:
    """
    建置最初始的Entity類別，包含基本的屬性和方法。
    這個類別可以用來表示遊戲中的各種實體，例如玩家、可交互物件、不可交互物件等。
    """
    def __init__(self, entity_id, name, x, y):
        self.entity_id = entity_id
        self.name = name
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Entity(id={self.entity_id}, name='{self.name}', x={self.x}, y={self.y})"

class InteractiveEntity(Entity,Researchable):
    """
    建置一個InteractiveEntity類別，繼承自Entity，表示可交互的實體。
    這個類別可以用來表示玩家、NPC、可交互物件等，並且可以包含一些基本的交互方法，例如觀察、對話、社交等。
    """
    def __init__(self, entity_id, name, x, y, durability):
        self.durability = durability
        super().__init__(entity_id, name, x, y)

    def research(self, actor):
        """
        定義InteractiveEntity的research方法，接受一個actor參數，表示研究這個物件的實體。
        這個方法可以被具體的可研究物件類別實現，以定義研究後的效果，例如獲得知識、觸發事件或改變能力。
        """
        print(f"{actor.name} is researching {self.name}.")



class Agent(Entity, Moveable,Edible):
    """
    建置最初始的Agent類別，包含基本的屬性和方法。
    """
    def __init__(self, entity_id, name, x, y, gender, health, years, bag):
        super().__init__(entity_id, name, x, y)
        self.gender = gender
        self.health = health
        self.years = years
        self.bag = bag

    def move(self, actor, direction):
        """
        定義Agent的移動方法，接受一個actor參數，表示移動這個物件的實體，以及一個direction參數，表示移動的方向。
        根據direction的值更新Agent的位置。
        """
        if direction == "up":
            self.y += 1
        elif direction == "down":
            self.y -= 1
        elif direction == "left":
            self.x -= 1
        elif direction == "right":
            self.x += 1