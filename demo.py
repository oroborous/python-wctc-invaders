import cocos
import cocos.euclid as eu
import cocos.collision_model as cm
import cocos.director as cd
from pyglet.window import key


class Actor(cocos.sprite.Sprite):
    def __init__(self, x, y, color):
        super(Actor, self).__init__('img/ball.png',
                                    color=color)
        pos = eu.Vector2(x, y)
        self.position = pos
        self.cshape = cm.CircleShape(pos, self.width / 2)
        # player moves at 100 pixels per second
        # the pickups don't move at all
        self.speed = 100


class MainLayer(cocos.layer.Layer):
    def __init__(self):
        super(MainLayer, self).__init__()

        # add blue sprite for player's character
        self.player = Actor(320, 240, (0, 0, 255))
        self.add(self.player)

        # add four red sprites as pickups
        for pos in [(100, 100), (540, 380), (540, 100), (100, 300)]:
            self.add(Actor(pos[0], pos[1], (255, 0, 0)))

        # recommend cell size for collision grid is 1.25 * largest sprite
        cell = self.player.width * 1.25
        self.collman = cm.CollisionManagerGrid(0, 640, 0, 480, cell, cell)

        # schedule from CocosNode class calls given function
        # every frame
        # first argument this function will receive is
        # delta time in seconds (time elapsed since last frame)
        self.schedule(self.update)

    def update(self, delta_time):
        #print(delta_time)

        # clear the collision manager
        self.collman.clear()

        # add Actors to set of known entities
        # https://hackernoon.com/understanding-the-underscore-of-python-309d1a029edc
        for _, actor in self.children:
            self.collman.add(actor)

        # iterate over objects' collisions
        for other in self.collman.iter_colliding(self.player):
            self.remove(other)

        # will be +1 for right movement, -1 for left movement
        horizontal_movement = keyboard[key.RIGHT] - keyboard[key.LEFT]
        # will be +1 for up movement, -1 for down movement
        vertical_movement = keyboard[key.UP] - keyboard[key.DOWN]

        # get player's current position
        pos = self.player.position

        # calculate new x and y values based on speed, elapsed time,
        # and which key is pressed
        new_x = pos[0] + self.player.speed * horizontal_movement * delta_time
        new_y = pos[1] + self.player.speed * vertical_movement * delta_time

        # update the player sprite's position
        self.player.position = (new_x, new_y)

        # also move the player sprite's collider (they're not attached)
        self.player.cshape.center = self.player.position


if __name__ == '__main__':
    cd.director.init(caption='Cocos Demo')
    keyboard = key.KeyStateHandler()
    cd.director.window.push_handlers(keyboard)

    layer = MainLayer()
    scene = cocos.scene.Scene(layer)
    cd.director.run(scene)

