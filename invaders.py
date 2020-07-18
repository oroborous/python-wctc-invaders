import random
import cocos
import cocos.euclid as eu
import cocos.collision_model as cm
import cocos.director as cd
import pyglet.media
from pyglet.window import key
from pyglet.image import load, ImageGrid, Animation

shoot_sfx = pyglet.media.load('sfx/shoot.wav', streaming=False)
kill_sfx = pyglet.media.load('sfx/invaderkilled.wav', streaming=False)
die_sfx = pyglet.media.load('sfx/explosion.wav', streaming=False)
ufo_sfx = pyglet.media.load('sfx/ufo_lowpitch.wav', streaming=False)


def load_animation(image):
    # 2 rows, 1 column on sprite sheet
    seq = ImageGrid(load(image), 2, 1)
    # show each image for half a second
    return Animation.from_image_sequence(seq, 0.5)


# load each animation only once at beginning of game
# number is the points each alien type is worth
TYPES = {
    '1': (load_animation('img/alien1.png'), 40),
    '2': (load_animation('img/alien2.png'), 20),
    '3': (load_animation('img/alien3.png'), 10)
}


class Actor(cocos.sprite.Sprite):
    def __init__(self, image, x, y):
        super(Actor, self).__init__(image)
        pos = eu.Vector2(x, y)
        self.position = pos
        self.cshape = cm.AARectShape(pos,
                                     self.width * 0.5,
                                     self.height * 0.5)

    def move(self, offset):
        # move the sprite
        self.position += offset
        # move the collider with it
        self.cshape.center += offset

    # will be overridden in subclasses
    def update(self, delta_time):
        pass

    # will be overridden in subclasses
    def collide(self, other):
        pass


class PlayerCannon(Actor):
    def __init__(self, x, y):
        super(PlayerCannon, self) \
            .__init__('img/cannon.png', x, y)
        self.speed = eu.Vector2(200, 0)

    def collide(self, other):
        # kill removes an object from its parent
        other.kill()
        self.kill()

    def update(self, delta_time):
        # find the movement modifier (-1, 0, or 1)
        horizontal_movement = keyboard[key.RIGHT] - keyboard[key.LEFT]

        # find half the width of the cannon sprite
        half_width = self.width * 0.5

        # ensure the center of the cannon (its anchor point) doesn't
        # move closer than half its width toward either screen edge
        if half_width <= self.x <= self.parent.width - half_width:
            self.move(self.speed * horizontal_movement * delta_time)

        # is the player firing the laser?
        is_firing = keyboard[key.SPACE]
        # don't allow double-firing
        if PlayerShoot.INSTANCE is None and is_firing:
            self.parent.add(PlayerShoot(self.x, self.y + 50))
            shoot_sfx.play()


class Alien(Actor):
    def __init__(self, img, x, y, points, column=None):
        super(Alien, self).__init__(img, x, y)
        self.points = points
        self.column = column

    def on_exit(self):
        super(Alien, self).on_exit()
        # if this alien's column is assigned...
        if self.column:
            # ... remove itself from the column
            self.column.remove(self)

    @staticmethod
    def from_type(x, y, alien_type, column):
        animation, points = TYPES[alien_type]
        return Alien(animation, x, y, points, column)


class AlienColumn:
    def __init__(self, x, y):
        alien_types = enumerate(['3', '3', '2', '2', '1'])

        # using a for loop
        self.aliens = []
        for i, alien_type in alien_types:
            self.aliens.append(Alien.from_type(x, y + i * 60, alien_type, self))

        # using a list comprehension
        # self.aliens = [Alien.from_type(x, y + i * 60, alien_type, self)
        #               for i, alien_type in alien_types]

    # remove a destroyed alien from the column
    def remove(self, alien):
        self.aliens.remove(alien)

    # should the swarm change direction?
    # current direction is 1 for right, -1 for left
    def should_turn(self, direction):
        # if no aliens in column, doesn't matter it if goes offscreen
        if len(self.aliens) == 0:
            return False
        # get first alien in column
        alien = self.aliens[0]
        # get x coord of alien and right edge of screen
        x, width = alien.x, alien.parent.width
        # test if x is within 50 pixels of either edge
        return x >= width - 50 and direction == 1 \
               or x <= 50 and direction == -1

    def shoot(self):
        # get a random number between 0 and 1
        # probability of firing is low because this method
        # will be called many times per second
        if random.random() < 0.001 and len(self.aliens) > 0:
            # get bottom alien's current position
            pos = self.aliens[0].position
            # alien missile originates 50 pixels below bottom
            # alien in column
            return Shoot(pos[0], pos[1] - 50)
        else:
            return None


class Swarm:
    def __init__(self, x, y):
        self.columns = [AlienColumn(x + i * 60, y)
                        for i in range(10)]
        self.speed = eu.Vector2(10, 0)
        self.direction = 1
        self.elapsed = 0.0
        self.period = 1.0

    # iterate the list of columns
    # pass each column (as c) to an anonymous function that
    # calls the column's should_turn method
    # if any should_turn returns True, return True
    def side_reached(self):
        return any(map(lambda c: c.should_turn(self.direction),
                       self.columns))

    # iterator to easily iterate all aliens in all columns
    def __iter__(self):
        for column in self.columns:
            for alien in column.aliens:
                yield alien

    def update(self, delta_time):
        # add elapsed time since last frame
        self.elapsed += delta_time
        # if more than 1 second has elapsed, time to move!
        while self.elapsed >= self.period:
            # reduce the elapsed time
            self.elapsed -= self.period
            # multiply speed by current direction to get +/-10 vector
            movement = self.direction * self.speed
            # if any column reports it's close to the edge
            if self.side_reached():
                # change direction
                self.direction *= -1
                # prepare to move downward instead of left/right
                movement = eu.Vector2(0, -10)
            # move all aliens in the swarm
            for alien in self:
                alien.move(movement)


class PlayerShoot(Actor):
    INSTANCE = None

    def __init__(self, x, y):
        super(PlayerShoot, self).__init__('img/laser.png', x, y)
        # players shoot up, aliens shoot down
        self.speed = eu.Vector2(0, 400)
        # store newly constructed instance in class variable
        PlayerShoot.INSTANCE = self

    def collide(self, other):
        # did the missile collide with an Alien?
        if isinstance(other, Alien):
            # tell the parent layer to update the score
            self.parent.update_score(other.points)
            other.kill()
            self.kill()

    def on_exit(self):
        super(PlayerShoot, self).on_exit()
        PlayerShoot.INSTANCE = None

    # movement based on elapsed time between frames
    def update(self, delta_time):
        self.move(self.speed * delta_time)


class Shoot(Actor):
    def __init__(self, x, y):
        super(Shoot, self).__init__('img/shoot.png', x, y)
        self.speed = eu.Vector2(0, -400)

    # movement based on elapsed time between frames
    def update(self, delta_time):
        self.move(self.speed * delta_time)


class HUD(cocos.layer.Layer):
    def __init__(self):
        super(HUD, self).__init__()
        w, h = cd.director.get_window_size()

        # create label for score
        self.score_text = cocos.text.Label('', font_size=18)
        self.score_text.position = (20, h - 40)

        # create label for lives
        self.lives_text = cocos.text.Label('', font_size=18)
        self.lives_text.position = (w - 100, h - 40)

        # add both labels to the layer
        self.add(self.score_text)
        self.add(self.lives_text)

    def update_score(self, score):
        self.score_text.element.text = 'Score: {}'.format(score)

    def update_lives(self, lives):
        self.lives_text.element.text = 'Lives: {}'.format(lives)

    def show_game_over(self, message):
        w, h = cd.director.get_window_size()

        # create a label that will be anchored on its center point
        game_over = cocos.text.Label(message,
                                     font_size=50,
                                     anchor_x='center',
                                     anchor_y='center')

        # add it to the center of the layer
        game_over.position = w * 0.5, h * 0.5
        self.add(game_over)


class GameLayer(cocos.layer.Layer):
    def __init__(self, hud):
        super(GameLayer, self).__init__()
        self.hud = hud

        # grab window width and height for frequent use
        w, h = cd.director.get_window_size()
        self.width = w
        self.height = h

        # initialize lives and score
        self.lives = 3
        self.score = 0

        # create a collision manager
        cell = 1.25 * 50
        self.collman = cm.CollisionManagerGrid(0, w, 0, h, cell, cell)

        # call methods to create cannon and update both HUD labels
        self.update_score()

        # create the player cannon
        self.create_player()
        self.create_swarm(100, 300)

        # start game loop
        self.schedule(self.update)

    # create player cannon at center-bottom of screen
    def create_player(self):
        self.player = PlayerCannon(self.width * 0.5, 50)
        self.add(self.player)
        self.hud.update_lives(self.lives)

    # when the player earns points, this method adds them to the score
    def update_score(self, points=0):
        self.score += points
        self.hud.update_score(self.score)

    # the game loop
    def update(self, delta_time):
        # clear collision manager
        self.collman.clear()
        for _, actor in self.children:
            # add all of the layer's children to collision manager
            self.collman.add(actor)
            # is object in set of known entities?
            # this is possible if an object doesn't overlap with
            # the collision grid
            if not self.collman.knows(actor):
                self.remove(actor)

        # check if the player missile hit anything
        # self.collide(PlayerShoot.INSTANCE)
        if self.collide(PlayerShoot.INSTANCE):
            kill_sfx.play()

        # test the player's cannon for collisions
        if self.collide(self.player):
            die_sfx.play()
            self.respawn_player()

        # tell each alien column to randomly (possibly) shoot
        for column in self.swarm.columns:
            # if the column did shoot, get its missile
            shoot = column.shoot()
            if shoot is not None:
                # add missile to the layer
                self.add(shoot)

        # tell everything in the layer to update itself
        # for shoots, this means move
        # for the player, perform key checks and move
        for _, actor in self.children:
            actor.update(delta_time)

        self.swarm.update(delta_time)

    # test every object for collisions against the given actor
    def collide(self, actor):
        # PlayerShoot.INSTANCE might be None, so check
        if actor is not None:
            # technically an actor can only collide with one
            # other actor in this game, but the loop makes
            # it easy to work with the collision manager's
            # iterator
            for other in self.collman.iter_colliding(actor):
                actor.collide(other)
                return True
        return False

    def respawn_player(self):
        # decrement lives
        self.lives -= 1
        # stop the game loop if out of lives
        if self.lives < 0:
            # stop the game loop by unscheduling the function
            self.unschedule(self.update)
            # tell HUD to show Game Over label
            self.hud.show_game_over('Game Over')
        else:
            # player sprite was removed from game if collided
            # so must create a new object back at starting position
            self.create_player()

    # create the swarm of aliens
    def create_swarm(self, x, y):
        self.swarm = Swarm(x, y)
        # use swarm's iterator to add all Alien objects to the layer
        for alien in self.swarm:
            self.add(alien)


if __name__ == '__main__':
    song = pyglet.media.load('sfx/level1.ogg')
    player = song.play()
    player.loop = True

    # initialize main game window
    cd.director.init(caption='WCTC Invaders', width=800, height=650)

    # create a keyboard handler
    keyboard = key.KeyStateHandler()
    cd.director.window.push_handlers(keyboard)

    # create the Scene
    main_scene = cocos.scene.Scene()

    # create the HUD and add to Scene
    # higher z numbers go on top of lower z numbers
    hud_layer = HUD()
    main_scene.add(hud_layer, z=1)

    # create the GameLayer and add to Scene
    game_layer = GameLayer(hud_layer)
    main_scene.add(game_layer, z=0)

    # tell director to run the scene
    cd.director.run(main_scene)
