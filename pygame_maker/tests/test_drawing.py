#!/usr/bin/env python
"""
Author: Ron Lockwood-Childs

Licensed under LGPL v2.1 (see file COPYING for details)

Unit test the pygame_maker.support.drawing module.
"""

import math
import pygame
import pygame_maker.support.drawing as drawing
import pygame_maker.support.color as color
import pygame_maker.support.coordinate as coord
import pg_template


class MyGameManager(object):
    """Custom game manager for drawing unit test."""
    LINE1_INFO = {
        "start": coord.Coordinate(20, 20),
        "end":  coord.Coordinate(100, 20),
        "width": 1,
        "color": color.Color((255, 0, 0)),
        "style": "solid"
    }
    LINE2_INFO = {
        "start": coord.Coordinate(20, 100),
        "end":   coord.Coordinate(22, 100),
        "color": color.Color((255, 255, 255)),
        "width": 1,
        "style": "dotted"
    }
    LINE3_INFO = {
        "start": coord.Coordinate(22, 100),
        "end":  coord.Coordinate(22, 150),
        "width": 1,
        "color": color.Color((255, 0, 0)),
        "style": "solid"
    }
    LINE4_INFO = {
        "start": coord.Coordinate(20, 100),
        "end":   coord.Coordinate(20, 150),
        "color": color.Color((255, 255, 255)),
        "width": 1,
        "style": "solid"
    }
    LINE5_INFO = {
        "start": coord.Coordinate(20, 150),
        "end":   coord.Coordinate(22, 150),
        "color": color.Color((100, 100, 255)),
        "width": 3,
        "style": "dashed"
    }
    LINE2_MAX_LENGTH = 400
    LINE2_LENGTH_CHANGE = 0.25
    def __init__(self):
        self.current_events = []
        self.objects = []
        self.done = False
        self.screen = None
        self.line2_length = 1.0

    def setup(self, screen):
        """Handle setup callback from PygameTemplate."""
        self.screen = screen

    def collect_event(self, event):
        """Handle collect_event callback from PygameTemplate."""
        self.current_events.append(event)

    def update(self):
        """Handle PygameTemplate update callback."""
        for cev in self.current_events:
            if cev.type == pygame.KEYDOWN:
                if cev.key == pygame.K_ESCAPE:
                    self.done = True
                    break
        # done with event handling
        self.current_events = []

    def draw_objects(self):
        """Handle draw_objects callback from PygameTemplate."""
        drawing.draw_line(self.screen, self.LINE1_INFO["start"], self.LINE1_INFO["end"],
                          self.LINE1_INFO["width"], self.LINE1_INFO["color"],
                          self.LINE1_INFO["style"])
        drawing.draw_line(self.screen, self.LINE2_INFO["start"], self.LINE2_INFO["end"],
                          self.LINE2_INFO["width"], self.LINE2_INFO["color"],
                          self.LINE2_INFO["style"])
        drawing.draw_line(self.screen, self.LINE3_INFO["start"], self.LINE3_INFO["end"],
                          self.LINE3_INFO["width"], self.LINE3_INFO["color"],
                          self.LINE3_INFO["style"])
        drawing.draw_line(self.screen, self.LINE4_INFO["start"], self.LINE4_INFO["end"],
                          self.LINE4_INFO["width"], self.LINE4_INFO["color"],
                          self.LINE4_INFO["style"])
        drawing.draw_line(self.screen, self.LINE5_INFO["start"], self.LINE5_INFO["end"],
                          self.LINE5_INFO["width"], self.LINE5_INFO["color"],
                          self.LINE5_INFO["style"])
        self.line2_length += self.LINE2_LENGTH_CHANGE
        self.LINE2_INFO["end"].x = self.LINE2_INFO["start"].x + int(math.floor(self.line2_length))
        self.LINE5_INFO["end"].x = self.LINE5_INFO["start"].x + int(math.floor(self.line2_length))
        self.LINE3_INFO["start"].x = self.LINE2_INFO["end"].x
        self.LINE3_INFO["end"].x = self.LINE2_INFO["end"].x
        if self.line2_length > self.LINE2_MAX_LENGTH:
            self.line2_length = self.LINE2_INFO["start"].x + 1.0

    def draw_background(self):
        """Handle draw_background callback from PygameTemplate."""
        self.screen.fill((0, 0, 0)) # grey background color

    def final_pass(self):
        """Handle final_pass callback from PygameTemplate."""
        pass

    def is_done(self):
        """Handle is_done callback from PygameTemplate."""
        return self.done


MYMANAGER = MyGameManager()
MYGAME = pg_template.PygameTemplate((1024, 768), "Drawing Tests", MYMANAGER)
MYGAME.run()

