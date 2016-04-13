#!/usr/bin/python -Wall

# Author: Ron Lockwood-Childs

# Licensed under LGPL v2.1 (see file COPYING for details)

# pygame maker object instance class

import pygame
import math
import random
import numpy as np
import simple_object_instance


def get_vector_xy_from_speed_direction(speed, direction):
    """
    Return an x,y vector representing the given speed and angle of motion.

    :param speed: The speed component of the velocity.
    :type speed: float
    :param direction: The direction component of the velocity.
    :type direction: float
    :return: A tuple (x, y) representing the velocity
    :rtype: (float, float)
    """
    xval = speed * math.sin(direction / 180.0 * math.pi)
    yval = speed * -1 * math.cos(direction / 180.0 * math.pi)
    xy = (xval, yval)
    return np.array(xy)


def get_speed_direction_from_xy(x, y):
    """
    Return speed and direction of motion, given an x,y vector starting from 0,0

    :param x: X component of the velocity.
    :type x: float
    :param y: Y component of the velocity.
    :type y: float
    :return: A tuple (speed, direction) representing the velocity
    :rtype: (float, float)
    """
    speed = math.sqrt(x * x + y * y)
    direction = direction_from_a_to_b(np.zeros(2), (x, y))
    spdir = (speed, direction)
    return spdir


def get_radius_angle_from_xy(x, y):
    """
    Return polar coordinates from an x, y coordinate.  This is the same
    operation as converting a velocity represented as x, y into speed,
    direction.

    :param x: X coordinate
    :param y: Y coordinate
    :return: A tuple (radius, angle) representing the polar coordinate
    :rtype: (float, float)
    """
    return get_speed_direction_from_xy(x, y)


def direction_from_a_to_b(pointa, pointb):
    """
    Calculate the direction in degrees for the line connecting points a and b.

    :param pointa: A 2-element list representing the coordinate in x, y order
    :type pointa: [float, float]
    :param pointb: A 2-element list representing the coordinate in x, y order
    :type pointb: [float, float]
    :return: The angle to pointb, using pointa as the origin.
    :rtype: float
    """
    normal_vector = np.array(pointb[:2]) - np.array(pointa[:2])
    return (math.atan2(normal_vector[1], normal_vector[0]) * 180) / math.pi


class ObjectInstance(simple_object_instance.SimpleObjectInstance,
                     pygame.sprite.DirtySprite):
    """
    Fits the purpose of pygame's Sprite class.

    Represent an instance of an ObjectType.

    An instance has:

    * position
    * speed
    * direction of motion
    * gravity
    * gravity direction
    * friction

    An instance does:

    * respond to events
    * produce collision events
    * draw itself

    As a :py:class:`pygame.sprite.DirtySprite` subclass, instances support
    dirty, blendmode, source_rect, visible, and layer attributes.

    As a subclass of LoggingObject, instances support debug(), info(),
    warning(), error(), and critical() methods.
    """
    INSTANCE_SYMBOLS = {
            "speed": 0.0,
            "direction": 0.0,
            "gravity": 0.0,
            "gravity_direction": 0.0,
            "friction": 0.0,
            "hspeed": 0.0,
            "vspeed": 0.0,
    }

    def __init__(self, kind, screen_dims, id_, settings=None, **kwargs):
        """
        Initialize an ObjectInstance.

        :param kind: The object type of this new instance
        :type kind: :py:class:`~pygame_maker.actors.object_type.ObjectType`
        :param screen_dims: Width, height of the surface this instance will be
            drawn to.  Allows boundary collisions to be detected.
        :type screen_dims: [int, int]
        :param id\_: A unique integer ID for this instance
        :type id\_: int
        :param settings: Used along with kwargs for settings attributes
            (allows attributes to be set that have a '.' character, which
            cannot be set in kwargs).  Known attributes are the same as for
            kwargs.
        :type settings: None or dict
        :param kwargs:
            Supply alternatives to instance attributes

            * position (list of float or pygame.Rect): Upper left XY coordinate.
              If not integers, each will be rounded to the next highest
              integer [(0,0)]
            * speed (float): How many pixels (or fraction thereof) the object
              moves in each update [0.0]
            * direction (float): 0-359 degrees for direction of motion [0.0]
            * gravity (float): Strength of gravity toward gravity_direction in
              pixels/sec^2 [0.0]
            * gravity_direction (float): 0-359 degrees for direction of gravity
              vector [0.0]
            * friction (float): Strength of friction vs direction of motion in
              pixels/sec [0.0]

        """
        # Flag when methods shouldn't automatically update speed, direction
        self._delay_motion_updates = False
        # call the superclasses' __init__
        simple_object_instance.SimpleObjectInstance.__init__(self, kind, screen_dims, id_, settings, **kwargs)
        pygame.sprite.DirtySprite.__init__(self)
        # set up the Sprite/DirtySprite expected parameters
        # default visibility comes from this instance's type
        self.dirty = 0
        self._visible = False
        self.visible = kind.visible
        self.source_rect = pygame.Rect(0, 0, 0, 0)
        # copy this instance's image and Rect from the sprite resource
        #: Keep a reference to the ObjectSprite's image
        self.image = kind.get_image()
        if self.image:
            image_rect = self.image.get_rect()
            self.rect.width = image_rect.width
            self.rect.height = image_rect.height
            self.mask = self.kind.mask
            if self.kind.radius:
                # disk collision type; get the predefined radius for collisions
                self.radius = self.kind.radius
            self.source_rect = pygame.Rect(self.kind.bounding_box_rect)
        self.blendmode = 0
        # use the instance type's 'depth' parameter as the layer for this
        #  instance
        self.layer = kind.depth

        self.start_position = (self.position.x, self.position.y)
        self.action_name_to_method_map.update({
            'set_velocity_compass': self.set_velocity_compass,
            'move_toward_point': self.move_toward_point,
            'set_horizontal_speed': self.set_horizontal_speed,
            'set_vertical_speed': self.set_vertical_speed,
        })
        # print("{}".format(self))

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, is_visible):
        vis = (is_visible is True)
        if vis:
            self.dirty = 2
        else:
            self.dirty = 0
        self._visible = vis

    def _change_motion_x_y(self):
        # Keep track of horizontal and vertical components of velocity.

        # Motion is represented as x and y adjustments that are made every
        # update when using the speed/direction model (as opposed to
        # manually changing the position).  Caching these values reduces the
        # number of times math functions will be called for object instances
        # with constant velocity.
        self.debug("_change_motion_x_y():")
        xadj, yadj = get_vector_xy_from_speed_direction(self.symbols['speed'],
                                                        self.symbols['direction'])
        # print("new inst {} xyadj {}, {}".format(self.inst_id, xadj, yadj))
        self.symbols['hspeed'] = xadj
        self.symbols['vspeed'] = yadj

    @property
    def direction(self):
        """Direction of motion in degrees, between 0.0 and 360.0"""
        return self.symbols['direction']

    @direction.setter
    def direction(self, value):
        new_value = value
        if new_value >= 360.0:
            new_value %= 360.0
        if new_value <= -360.0:
            new_value %= 360.0
        if (new_value > -360.0) and (new_value < 0.0):
            new_value = (360.0 + new_value)
        self.symbols['direction'] = new_value
        if not self._delay_motion_updates:
            self._change_motion_x_y()

    @property
    def speed(self):
        """Speed of motion in pixels (or fractions) per frame"""
        return self.symbols['speed']

    @speed.setter
    def speed(self, value):
        self.symbols['speed'] = value
        if not self._delay_motion_updates:
            self._change_motion_x_y()

    @property
    def friction(self):
        """Magnitude of friction applied against motion each frame"""
        return self.symbols['friction']

    @friction.setter
    def friction(self, value):
        self.symbols['friction'] = float(value)

    @property
    def gravity(self):
        """Magnitude of gravity applied each frame"""
        return self.symbols['gravity']

    @gravity.setter
    def gravity(self, value):
        self.symbols['gravity'] = float(value)

    @property
    def gravity_direction(self):
        """Direction gravity pulls the instance in degrees"""
        return self.symbols['gravity_direction']

    @gravity_direction.setter
    def gravity_direction(self, value):
        new_value = value
        if new_value >= 360.0:
            new_value %= 360.0
        if new_value <= -360.0:
            new_value %= 360.0
        if (new_value > -360.0) and (new_value < 0.0):
            new_value = (360.0 + new_value)
        self.symbols['gravity_direction'] = new_value

    @property
    def hspeed(self):
        """Horizontal speed"""
        return self.symbols['hspeed']

    @hspeed.setter
    def hspeed(self, value):
        # skip setting motion x,y and hspeed, vspeed
        self._delay_motion_updates = True
        self.speed, self.direction = get_speed_direction_from_xy(value,
                                                                 self.vspeed)
        self._delay_motion_updates = False
        self.symbols['hspeed'] = value

    @property
    def vspeed(self):
        """Vertical speed"""
        return self.symbols['vspeed']

    @vspeed.setter
    def vspeed(self, value):
        # skip setting motion x,y and hspeed, vspeed
        self._delay_motion_updates = True
        self.speed, self.direction = get_speed_direction_from_xy(self.hspeed,
                                                                 value)
        self._delay_motion_updates = False
        self.symbols['vspeed'] = value

    def get_center_point(self):
        """
        Return the approximate center pixel coordinate of the object.

        :return: A 2-element tuple x, y of the approximate position of the
            object's center point.
        :rtype: (int, int)
        """
        self.debug("get_center_point():")
        center_xy = (self.rect.x + self.rect.width / 2.0,
                     self.rect.y + self.rect.height / 2.0)
        return center_xy

    def update(self):
        """
        Move the instance from its current position.

        Calculate the new position using current speed and direction.  Queue
        events for boundary collisions or outside-of-room positions.  Make
        friction and/or gravity changes to speed and/or direction for the next
        update().
        """
        self.debug("update():")
        event_queued = None
        if self.speed > 0.0:
            self.position[0] += self.symbols['hspeed']
            self.position[1] += self.symbols['vspeed']
            self.rect.x = int(math.floor(self.position[0] + 0.5))
            self.rect.y = int(math.floor(self.position[1] + 0.5))
            # check for boundary collisions
            # allow boundary collisions for objects completely outside
            #  the other dimension's boundaries to be ignored; this
            #  makes intersect_boundary and outside_room mutually exclusive
            in_x_bounds = (((self.rect.x + self.rect.width) >= 0) and
                           (self.rect.x <= self.screen_dims[0]))
            in_y_bounds = (((self.rect.y + self.rect.height) >= 0) and
                           (self.rect.y <= self.screen_dims[1]))
            if ((self.rect.x <= 0 <= (self.rect.x + self.rect.width)) or
                (self.rect.x <= self.screen_dims[0] <=
                 (self.rect.x + self.rect.width)) and in_y_bounds):
                # queue and handle boundary collision event (async)
                event_queued = self.kind.EVENT_NAME_OBJECT_HASH["intersect_boundary"]("intersect_boundary",
                                                                                      {"type": self.kind,
                                                                                       "instance": self})
                # print("inst {} hit x bound".format(self.inst_id))
            if ((self.rect.y <= 0 <= (self.rect.y + self.rect.height)) or
                (self.rect.y <= self.screen_dims[1] <=
                 (self.rect.y + self.rect.width)) and in_x_bounds):
                # queue and handle boundary collision event (async)
                if not event_queued:
                    event_queued = self.kind.EVENT_NAME_OBJECT_HASH["intersect_boundary"]("intersect_boundary",
                                                                                          {"type": self.kind,
                                                                                           "instance": self})
                    # print("inst {} hit y bound".format(self.inst_id))
            # check for outside room
            if ((self.rect.x > self.screen_dims[0]) or
                    ((self.rect.x + self.rect.width) < 0)):
                event_queued = self.kind.EVENT_NAME_OBJECT_HASH["outside_room"]("outside_room",
                                                                                {"type": self.kind,
                                                                                 "instance": self})
            if ((self.rect.y > self.screen_dims[1]) or
                    ((self.rect.y + self.rect.height) < 0)):
                if not event_queued:
                    event_queued = self.kind.EVENT_NAME_OBJECT_HASH["outside_room"]("outside_room",
                                                                                    {"type": self.kind,
                                                                                     "instance": self})
            self.debug("  {} inst {} new position: {} ({})".format(self.kind.name,
                                                                   self.inst_id, self.position, self.rect))
        # apply forces for next update
        self._apply_gravity()
        self._apply_friction()
        # transmit outside_room or intersect_boundary event last
        if event_queued:
            self.game_engine.event_engine.queue_event(event_queued)
            self.debug("  {} inst {} transmitting {} event".format(self.kind.name,
                                                                   self.inst_id, event_queued))
            self.game_engine.event_engine.transmit_event(event_queued.name)

    def _apply_gravity(self):
        # Adjust speed and direction using value and direction of gravity.
        self.debug("_apply_gravity():")

    def _apply_friction(self):
        # Adjust speed based on friction value.
        self.debug("_apply_friction():")
        if (self.friction > 0.0) and (self.speed > 0.0):
            new_speed = self.speed - self.friction
            if new_speed < 0.0:
                new_speed = 0.0
            self.speed = new_speed

    def aim_toward_point(self, pointxy):
        """
        Change the direction of motion toward a given point.

        :param pointxy: A 2-element list of the x, y coordinate
        :type pointxy: array-like
        """
        self.debug("aim_toward_point():")
        self.direction = direction_from_a_to_b(self.get_center_point(), pointxy)

    def set_velocity_compass(self, action):
        """
        Handle the set_velocity_compass action.

        Possible directions:

        * NONE: don't set the direction, just the speed
        * '|' separated list of possible directions to be chosen at
          random: UP, UPLEFT, UPRIGHT, RIGHT, DOWN, DOWNLEFT, DOWNRIGHT, LEFT
          (see :py:attr:`~pygame_maker.actions.action.Action.COMPASS_DIRECTIONS`)

        :param action: The Action instance that triggered this method
        :type action: :py:class:`~pygame_maker.actions.action.Action`
        """
        self.debug("set_velocity_compass(action={}):".format(action))
        # convert compass direction into degrees
        new_params = dict(action.action_data)
        new_params["direction"] = 0.0
        if new_params["compass_directions"] != "NONE":
            dirs = new_params['compass_directions'].split('|')
            dir_count = len(dirs)
            new_dir = 0
            if dir_count > 1:
                new_dir = random.randint(0, dir_count - 1)
            if dirs[new_dir] in action.COMPASS_DIRECTIONS:
                # convert direction name to degrees
                new_params["direction"] = action.COMPASS_DIRECTION_DEGREES[dirs[new_dir]]
            elif dirs[new_dir] == "STOP":
                # if stop was selected, set speed to zero
                new_params['speed'] = 0
        del(new_params["compass_directions"])
        _apply_kwargs(new_params)

    def move_toward_point(self, action):
        """
        Handle the move_toward_point action.

        :param action: The Action instance that triggered this method
        :type action: :py:class:`~pygame_maker.actions.action.Action`
        """
        self.debug("move_toward_point(action={}):".format(action))
        if "destination" in action.action_data:
            self._delay_motion_updates = True
            # change direction
            self.aim_toward_point(action.action_data["destination"])
            # apply speed parameter
            self._apply_kwargs({"speed": action.action_data['speed']})
            self._delay_motion_updates = False
            self._change_motion_x_y()

    def set_horizontal_speed(self, action):
        """
        Handle the set_horizontal_speed action.

        :param action: The Action instance that triggered this method
        :type action: :py:class:`~pygame_maker.actions.action.Action`
        """
        self.debug("set_horizontal_speed(action={}):".format(action))
        relative = False
        if "relative" in action.action_data:
            relative = action.action_data["relative"]
        compass_name = action.action_data["horizontal_direction"]
        if compass_name in ["LEFT", "RIGHT"]:
            speed = action.action_data["horizontal_speed"]
            direction = action.COMPASS_DIRECTION_DEGREES[compass_name]
            # horiz_vec has only x direction
            horiz_vec = get_vector_xy_from_speed_direction(speed, direction)
            new_hspeed = horiz_vec[0]
            if relative:
                new_hspeed += self.hspeed
            self.hspeed = new_hspeed

    def set_vertical_speed(self, action):
        """
        Handle the set_vertical_speed action.

        :param action: The Action instance that triggered this method
        :type action: :py:class:`~pygame_maker.actions.action.Action`
        """
        self.debug("set_vertical_speed(action={}):".format(action))
        relative = False
        if "relative" in action.action_data:
            relative = action.action_data["relative"]
        compass_name = action.action_data["vertical_direction"]
        if compass_name in ["UP", "DOWN"]:
            speed = action.action_data["vertical_speed"]
            direction = action.COMPASS_DIRECTION_DEGREES[compass_name]
            # vert_vec has only y direction
            vert_vec = get_vector_xy_from_speed_direction(speed, direction)
            new_vspeed = vert_vec[1]
            if relative:
                new_vspeed += self.vspeed
            self.vspeed = new_vspeed

    def execute_action(self, action, event):
        """
        Perform an action in an action sequence, in response to an event.

        :param action: The Action instance that triggered this method
        :type action: :py:class:`~pygame_maker.actions.action.Action`
        :param event: The Event instance that triggered this method
        :type event: :py:class:`~pygame_maker.events.event.Event`
        """
        # Apply any setting names that match property names found in the
        #  action_data.  For some actions, this is enough.
        # common exceptions:
        #  apply_to: assumed to have directed the action to this instance
        #  relative: add to instead of replace property settings
        action_params, handled_action = simple_object_instance.SimpleObjectInstance.execute_action(self, action, event)
        # check for expressions that need to be executed
        if not handled_action:
            if action.name == "jump_to_start":
                self.position = self.start_position
            elif action.name == "reverse_horizontal_speed":
                # old_dir = self.direction
                self.direction = -self.direction
                # self.debug("Reverse hdir {} to {}".format(old_dir, self.direction))
            elif action.name == "reverse_vertical_speed":
                # old_dir = self.direction
                self.direction = 180.0 - self.direction
                # self.debug("Reverse vdir {} to {}".format(old_dir, self.direction))
            elif action.name == "destroy_object":
                # Queue the destroy event for this instance and run it, then schedule
                #  ourselves for removal from our parent object.
                self.game_engine.event_engine.queue_event(
                    self.kind.EVENT_NAME_OBJECT_HASH["destroy"]("destroy", {"type": self.kind, "instance": self})
                )
                self.game_engine.event_engine.transmit_event("destroy")
                self.kind.add_instance_to_delete_list(self)
            elif action.name == "bounce_off_collider":
                # self.debug("bounce event: {}".format(event))
                if ((action_params['precision'] == 'imprecise') or ('normal' not in
                                                                    event.event_params.keys())):
                    self.direction = 180.0 + self.direction
                else:
                    norm = np.array(event['normal'])
                    # print("Check normal {}".format(norm))
                    if abs(norm[0]) == abs(norm[1]):
                        self.direction = 180.0 + self.direction
                    elif abs(norm[0]) > abs(norm[1]):
                        # X component is greater; reverse X
                        self.direction = -self.direction
                    else:
                        # Y component is greater; reverse Y
                        self.direction = 180.0 - self.direction
            else:
                self.debug("  {} inst {} execute_action {} fell through..".format(self.kind.name,
                                                                                  self.inst_id,
                                                                                  action.name))
        self._apply_kwargs(action_params)

    def __repr__(self):
        return "<{} {:03d} @ {} dir {} speed {}>".format(type(self).__name__,
                                                         self.inst_id, self.position, self.direction, self.speed)
