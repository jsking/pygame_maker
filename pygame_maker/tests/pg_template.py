#!/usr/bin/python
"""
Author: Ron Lockwood-Childs

Licensed under LGPL v2.1 (see file COPYING for details)

Template for simple pygame applications.
"""

import pygame

class PygameTemplate(object):
    """
    Template for pygame applications.  Calls methods from a supplied game
    manager instance.
    """
    # define common colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)

    # every game_manager is an object that must support calls to:
    #  setup(screen)
    #  collect_event(event)
    #  update()
    #  draw_background()
    #  draw_objects()
    #  final_pass()
    #  is_done()
    def __init__(self, size_tuple, caption, game_manager, frame_rate=30):

        self.size = size_tuple
        self.caption = caption
        self.game_manager = game_manager
        self.frame_rate = frame_rate
        self.screen = None
        self.clock = None
        self.done = False

        # manage speed of screen updates

    def run(self):
        """
        Create the main screen surface, call the game manager's setup method,
        then enter the main loop, which calls the game manager's remaining
        methods.

        Maintains the given frame rate using a pygame.time.Clock() instance.
        """
        pygame.init()
        self.screen = pygame.display.set_mode(self.size)
        self.game_manager.setup(self.screen)
        pygame.display.set_caption(self.caption)
        self.clock = pygame.time.Clock()

        # --- Main Loop ---
        while not self.done:
            for event in pygame.event.get():
                self.game_manager.collect_event(event)

            # --- Game Logic ---
            self.game_manager.update()

            #self.screen.fill(self.WHITE)
            # --- Drawing ---
            self.game_manager.draw_background()
            self.game_manager.draw_objects()

            # update screen
            self.game_manager.final_pass()
            pygame.display.flip()

            # find out whether the game manager is done
            self.done = self.game_manager.is_done()

            # limit frame rate
            self.clock.tick(self.frame_rate)

        # close window & quit
        pygame.quit()

if __name__ == "__main__":
    class MyGameManager(object):
        """A custom game manager for unit test purposes."""
        LEFT_MARGIN = 10
        TOP_MARGIN = 8
        LINE_HEIGHT = 18
        TEXT_COLOR = (128, 0, 128)
        TEXT_BACKG = (255, 255, 255)
        def __init__(self):
            self.current_events = []
            self.objects = []
            self.font = None
            self.done = False
            self.screen = None
        def setup(self, screen):
            """Handle the setup callback from PygameTemplate."""
            self.screen = screen
            self.font = pygame.font.Font(None, 16)
        def collect_event(self, event):
            """Handle the collect_event callback from PygameTemplate."""
            self.current_events.append(event)
        def create_text(self, a_key):
            """Create text objects in response to key presses."""
            text = "You pressed '{}'".format(pygame.key.name(a_key))
            if len(self.objects) > 25:
                # too many text lines, remove oldest object
                self.objects = self.objects[1:]
            self.objects.append(("text", self.font.render(text, 1, self.TEXT_COLOR,
                                                          self.TEXT_BACKG)))
        def update(self):
            """Handle the update callback from PygameTemplate."""
            for cev in self.current_events:
                if cev.type == pygame.KEYDOWN:
                    if cev.key == pygame.K_ESCAPE:
                        self.done = True
                        break
                    else:
                        # create a new text object
                        self.create_text(cev.key)
            # done with event handling
            self.current_events = []

        def draw_text(self, textobj, line):
            """Draw text objects to the screen."""
            ypos = self.TOP_MARGIN + line*self.LINE_HEIGHT
            textpos = (self.LEFT_MARGIN, ypos)
            self.screen.blit(textobj[1], textpos)

        def draw_objects(self):
            """Handle the draw_objects callback from PygameTemplate."""
            for line, obj in enumerate(self.objects):
                self.draw_text(obj, line)

        def final_pass(self):
            """Handle the final_pass callback from PygameTemplate."""
            pass

        def draw_background(self):
            """Handle the draw_background callback from PygameTemplate."""
            self.screen.fill(PygameTemplate.BLACK)

        def is_done(self):
            """Handle the is_done callback from PygameTemplate."""
            return self.done

    MYMANAGER = MyGameManager()
    MYGAME = PygameTemplate((700, 500), "My Game", MYMANAGER)
    MYGAME.run()

