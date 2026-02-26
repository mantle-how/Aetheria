#最常見的action, 定義一些常見的行為類別，例如可食用、可放入背包、可移動等，這些類別可以被具體的物件類別繼承和實現，以定義它們的行為。
class Edible:
    def eat(self, actor):
        """
        定義可食用物件的吃方法，接受一個actor參數，表示吃這個物件的實體。
        這個方法可以被具體的可食用物件類別實現，以定義吃這個物件後的效果。
        """
        pass

class Bagable:
    def bag(self, actor):
        """
        定義可放入背包物件的bag方法，接受一個actor參數，表示將這個物件放入背包的實體。
        這個方法可以被具體的可放入背包物件類別實現，以定義放入背包後的效果。
        """
        pass

class Moveable:
    def move(self, actor, direction):
        """
        定義可移動物件的move方法，接受一個actor參數，表示移動這個物件的實體，以及一個direction參數，表示移動的方向。
        這個方法可以被具體的可移動物件類別實現，以定義移動後的位置變化。
        """
        pass

class Observable:
    def observe(self, actor):
        """
        定義可觀察物件的observe方法，接受一個actor參數，表示觀察這個物件的實體。
        這個方法可以被具體的可觀察物件類別實現，以定義觀察後的效果，例如提供信息或觸發事件。
        """
        pass

class Talkable:
    def talk(self, actor):
        """
        定義可對話物件的talk方法，接受一個actor參數，表示與這個物件對話的實體。
        這個方法可以被具體的可對話物件類別實現，以定義對話後的效果，例如提供信息、觸發事件或改變關係。
        """
        pass

class Socialable:
    def socialize(self, actor):
        """
        定義可社交物件的socialize方法，接受一個actor參數，表示與這個物件社交的實體。
        這個方法可以被具體的可社交物件類別實現，以定義社交後的效果，例如建立友誼、觸發事件或改變關係。
        """
        pass

class Tradeable:
    def trade(self, actor, item):
        """
        定義可交易物件的trade方法，接受一個actor參數，表示與這個物件交易的實體，以及一個item參數，表示交易的物品。
        這個方法可以被具體的可交易物件類別實現，以定義交易後的效果，例如交換物品、觸發事件或改變關係。
        """
        pass

class Diggable:
    def dig(self, actor):
        """
        定義可挖掘物件的dig方法，接受一個actor參數，表示挖掘這個物件的實體。
        這個方法可以被具體的可挖掘物件類別實現，以定義挖掘後的效果，例如獲得資源、觸發事件或改變地形。
        """
        pass

class Researchable:
    def research(self, actor):
        """
        定義可研究物件的research方法，接受一個actor參數，表示研究這個物件的實體。
        這個方法可以被具體的可研究物件類別實現，以定義研究後的效果，例如獲得知識、觸發事件或改變能力。
        """
        pass