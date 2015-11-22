#!/usr/bin/python -Wall

# Author: Ron Lockwood-Childs

# Licensed under LGPL v2.1 (see file COPYING for details)

# bring all the things together

import os
import yaml
import pygame
import logging
import logging.config
from pygame_maker.support import logging_object
from pygame_maker.actors import object_sprite
from pygame_maker.sounds import sound
from pygame_maker.actors import object_type
from pygame_maker.scenes import background
from pygame_maker.scenes import room
from pygame_maker.events import event
from pygame_maker.events import event_engine
from pygame_maker.logic import language_engine

class GameEngineException(Exception):
    pass

class GameEngine(logging_object.LoggingObject):
    MOUSE_EVENT_TABLE=[
        {"instance_event_name": "mouse_nobutton",
         "global_event_name": "mouse_global_nobutton"},
        {"instance_event_name": "mouse_button_left",
         "global_event_name": "mouse_global_button_left",
         "instance_pressed_name": "mouse_left_pressed",
         "global_pressed_name": "mouse_global_left_pressed",
         "instance_released_name": "mouse_left_released",
         "global_released_name": "mouse_global_left_released"},
        {"instance_event_name": "mouse_button_middle",
         "global_event_name": "mouse_global_button_middle",
         "instance_pressed_name": "mouse_middle_pressed",
         "global_pressed_name": "mouse_global_middle_pressed",
         "instance_released_name": "mouse_middle_released",
         "global_released_name": "mouse_global_middle_released"},
        {"instance_event_name": "mouse_button_right",
         "global_event_name": "mouse_global_button_right",
         "instance_pressed_name": "mouse_right_pressed",
         "global_pressed_name": "mouse_global_right_pressed",
         "instance_released_name": "mouse_right_released",
         "global_released_name": "mouse_global_right_released"},
        {"instance_event_name": "mouse_wheelup",
         "global_event_name": "mouse_global_wheelup"},
        {"instance_event_name": "mouse_wheeldown",
         "global_event_name": "mouse_global_wheeldown"},
        {"instance_event_name": "mouse_button_6",
         "global_event_name": "mouse_global_button_6"},
        {"instance_event_name": "mouse_button_7",
         "global_event_name": "mouse_global_button_7"},
        {"instance_event_name": "mouse_button_8",
         "global_event_name": "mouse_global_button_8"},
    ]
    # directories where game resources are expected to reside. The path names
    #  must match the resource key names
    RESOURCE_TABLE=[
        ('sprites', object_sprite.ObjectSprite),
        ('sounds', sound.Sound),
        ('objects', object_type.ObjectType),
        ('backgrounds', background.Background),
        ('rooms', room.Room),
    ]
    DEFAULT_GAME_SETTINGS={
        "game_name": "PyGameMaker Game",
        "screen_dimensions": (640,480),
        "frames_per_second": 60,
        "logging_config": {
          "version": 1,
          "formatters": {
            "normal": {
              "format": '%(name)s [%(levelname)s]:%(message)s'
            },
            "timestamped": {
              "format": '%(asctime)s - %(name)s [%(levelname)s]:%(message)s'
            }
          },
          "handlers": {
            "console": {
              "class": 'logging.StreamHandler',
              "level": 'WARNING',
              "formatter": "normal",
              "stream": "ext://sys.stdout",
            },
            "file": {
              "class": 'logging.FileHandler',
              "level": 'DEBUG',
              "formatter": "timestamped",
              "filename": "pygame_maker_game_engine.log",
              "mode": "w"
            }
          },
          "loggers": {
            "GameEngine": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "CodeBlock": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "LanguageEngine": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "EventEngine": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "ObjectType": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "ObjectInstance": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
            "Room": {
              "level": "INFO",
              "handlers": ["console", "file"]
            },
          },
        },
    }
    GAME_SETTINGS_FILE="game_settings.yaml"
    GAME_ENGINE_ACTIONS=[
        "play_sound",
        "create_object",
        "create_object_with_velocity"
    ]

    def __init__(self):
        self.event_engine = event_engine.EventEngine()
        self.language_engine = language_engine.LanguageEngine()
        self.symbols = language_engine.SymbolTable()
        self.resources = {
            'sprites': {},
            'sounds': {},
            'backgrounds': {},
            'objects': {},
            'rooms': []
        }
        self.game_settings = dict(self.DEFAULT_GAME_SETTINGS)
        self.last_key_down = None
        self.screen = None
        self.draw_surface = None
        self.done = False
        self.mouse_pos = [0,0]
        self.action_blocks = {}
        self.current_events = []
        self.new_object_queue = []
        self.room_index = 0

        self.load_game_settings()

        if 'logging_config' in self.game_settings.keys():
            logging.config.dictConfig(self.game_settings['logging_config'])
        else:
            logging.setLevel(logging.WARNING)

        super(GameEngine, self).__init__(type(self).__name__)

        self.info("Loading game resources..")
        with logging_object.Indented(self):
            self.load_game_resources()

        if len(self.resources['rooms']) == 0:
            raise(GameEngineException("No game room resource found"))

    def load_game_settings(self):
        """
            load_game_settings():
            Collect the settings for the game itself
        """
        if os.path.exists(self.GAME_SETTINGS_FILE):
            with open(self.GAME_SETTINGS_FILE, "r") as yaml_f:
                yaml_info = yaml.load(yaml_f)
                if yaml_info:
                    for yaml_key in yaml_info.keys():
                        if yaml_key in self.game_settings:
                            self.game_settings[yaml_key] = yaml_info[yaml_key]

    def load_game_resources(self):
        """
            load_game_resources():
            Bring in resource YAML files from their expected directories:
            sprites, backgrounds, sounds, objects, and rooms
        """
        topdir = os.getcwd()
        for res_path, res_type in self.RESOURCE_TABLE:
            self.info("Loading {}..".format(res_path))
            if (not os.path.exists(res_path)):
                continue
            # resource directories are expected to contain YAML descriptions
            #  for each of their respective resource types. Sprites and sounds
            #  may also contain image or sound files, respectively, so filter
            #  out files with other extensions
            res_files = os.listdir(res_path)
            res_yaml_files = []
            for rf in res_files:
                if rf.endswith('.yaml') or rf.endswith('.yml'):
                    res_yaml_files.append(rf)
            # need to chdir, since the filenames found in YAML resource
            #  files are assumed to be relative to the YAML resource's path
            os.chdir(res_path)
            with logging_object.Indented(self):
                for res_file in res_yaml_files:
                    self.info("Import {}".format(res_file))
                    new_resources = res_type.load_from_yaml(res_file, self)
                    if res_path != "rooms":
                        with logging_object.Indented(self):
                            for res in new_resources:
                                # if multiple resources have the same name, the
                                # last one read in will override the others
                                self.debug("{}".format(res))
                                self.resources[res_path][res.name] = res
                    else:
                        # rooms are meant to stay in order
                        self.resources[res_path] = new_resources
            os.chdir(topdir)

    def execute_action(self, action, event):
        """
            execute_action():
            Perform an action that is not specific to existing objects.
            Parameters:
             action (Action): The action instance to be executed.
             event (Event): The event that triggered the action.
        """
        # filter the action parameters
        action_params = {}
        for param in action.action_data.keys():
            if param == 'apply_to':
                continue
            action_params[param] = action.get_parameter_expression_result(
                param, self.symbols, self.language_engine)

        #print("Engine received action: {}".format(action))
        self.debug("Handle action '{}'".format(action.name))
        self.bump_indent_level()
        if action.name == "play_sound":
            if ((len(action_params['sound']) > 0) and
                (action_params['sound'] in self.resources['sounds'].keys())):
                self.debug("Playing sound '{}'".format(action_params['sound']))
                self.resources['sounds'][action_params['sound']].play_sound()
            else:
                self.debug("Sound '{}' not played".format(action_params['sound']))
        elif action.name in ["create_object", "create_object_with_velocity"]:
            if (self.screen and (len(action_params['object']) > 0) and
                (action_params['object'] in self.resources['objects'].keys())):
                self.info("Creating object '{}'".format(action_params['object']))
                self.new_object_queue.append(
                    (self.resources['objects'][action_params['object']],
                        action_params)
                )
            else:
                self.debug("Object '{}' not created".format(action_params['object']))
        else:
            self.debug("No handler for action '{}'".format(action.name))
        self.drop_indent_level()

    def send_key_event(self, key_event):
        """
            send_key_event():
            Called with a keyboard event from pygame, or None if no key events
             were collected this frame. Pygame key codes will be translated
             into KeyEvents with _keyup or _keydn appended to the
             name based on the pygame event received. If no keyboard event was
             received during the frame, fire off the kb_no_key event.
            Parameters:
             key_event (pygame.event): The pygame keyboard event, or None to
              signal that no button event occurred during the frame.
        """
        pk_map = event.KeyEvent.PYGAME_KEY_TO_KEY_EVENT_MAP
        key_event_init_name = None
        key_event_name = None
        if not key_event:
            key_event_init_name = "kb_no_key"
            key_event_name = key_event_init_name
        elif key_event.key in pk_map:
            key_event_name = str(pk_map[key_event.key])
            if key_event.type == pygame.KEYDOWN:
                key_event_init_name = "{}_keydn".format(pk_map[key_event.key])
            elif key_event.type == pygame.KEYUP:
                key_event_init_name = "{}_keyup".format(pk_map[key_event.key])
        ev = event.KeyEvent(key_event_init_name)
        #print("queue event: {}".format(ev))
        self.event_engine.queue_event(ev)
        #print("xmit event: {}".format(key_event_name))
        self.event_engine.transmit_event(key_event_name)
        self.debug("Event '{}' queued and transmitted".format(key_event_init_name))

    def send_mouse_event(self, mouse_event):
        """
            send_mouse_event():
            Called with a mouse event collected from pygame, or None if no
             mouse button events were collected this frame. Motion events will
             simply capture the x, y of the mouse cursor. Button events will
             trigger MouseEvents of the appropriate global and
             instance press or release types. If no button event was received,
             fire off the nobutton global and instance events.
            Parameters:
             mouse_event (pygame.event): The pygame mouse event, or None to
              signal that no button event occurred during the frame.
        """
        if mouse_event:
            self.mouse_pos[0] = mouse_event.pos[0]
            self.mouse_pos[1] = mouse_event.pos[1]
            self.language_engine.global_symbol_table.setConstant('mouse.x',
                self.mouse_pos[0])
            self.language_engine.global_symbol_table.setConstant('mouse.y',
                self.mouse_pos[1])
            if mouse_event.type == pygame.MOUSEMOTION:
                return
        event_names = []
        if mouse_event:
            mouse_button = mouse_event.button
            if len(self.MOUSE_EVENT_TABLE) > mouse_button:
                ev_table_entry = self.MOUSE_EVENT_TABLE[mouse_button]
                #print("select mouse entries {}".format(ev_table_entry))
                # queue the instance version of the event (each object type
                #  listening for this kind of event only passes it on
                #  to instances that intersect with the mouse position)
                self.event_engine.queue_event(
                    event.MouseEvent(
                        ev_table_entry["instance_event_name"],
                        {"position": mouse_event.pos}
                    )
                )
                event_names.append(ev_table_entry["instance_event_name"])
                #print("queue {}".format(event_names[-1]))
                self.event_engine.queue_event(
                    event.MouseEvent(
                        ev_table_entry["global_event_name"],
                        {"position": mouse_event.pos}
                    )
                )
                event_names.append(ev_table_entry["global_event_name"])
                #print("queue {}".format(event_names[-1]))
                # press/release events exist only for a subset
                if mouse_event.type == pygame.MOUSEBUTTONDOWN:
                    if 'instance_pressed_name' in ev_table_entry:
                        self.event_engine.queue_event(
                            event.MouseEvent(
                                ev_table_entry["instance_pressed_name"],
                                {"position": mouse_event.pos}
                            )
                        )
                        event_names.append(ev_table_entry["instance_pressed_name"])
                        #print("queue {}".format(event_names[-1]))
                        self.event_engine.queue_event(
                            event.MouseEvent(
                                ev_table_entry["global_pressed_name"],
                                {"position": mouse_event.pos}
                            )
                        )
                        event_names.append(ev_table_entry["global_pressed_name"])
                        #print("queue {}".format(event_names[-1]))
                if mouse_event.type == pygame.MOUSEBUTTONUP:
                    if 'instance_released_name' in ev_table_entry:
                        self.event_engine.queue_event(
                            event.MouseEvent(
                                ev_table_entry["instance_released_name"],
                                {"position": mouse_event.pos}
                            )
                        )
                        event_names.append(ev_table_entry["instance_released_name"])
                        #print("queue {}".format(event_names[-1]))
                        self.event_engine.queue_event(
                            event.MouseEvent(
                                ev_table_entry["global_released_name"],
                                {"position": mouse_event.pos}
                            )
                        )
                        event_names.append(ev_table_entry["global_released_name"])
                        #print("queue {}".format(event_names[-1]))
        else:
            self.event_engine.queue_event(
                event.MouseEvent("mouse_nobutton",
                    {"position": self.mouse_pos})
            )
            event_names.append("mouse_nobutton")
            self.event_engine.queue_event(
                event.MouseEvent("mouse_global_nobutton",
                    {"position": self.mouse_pos})
            )
            event_names.append("mouse_global_nobutton")
        # transmit all queued event types
        for ev_name in event_names:
            self.event_engine.transmit_event(ev_name)
            if not ev_name in ['mouse_nobutton', 'mouse_global_nobutton']:
                self.debug("Event '{}' queued and transmitted".format(ev_name))

    def setup(self, screen):
        """
            setup():
            Called by the pygame template when pygame has been initialized.
             This is a good place to put any initialization that needs pygame
             to be set up already -- e.g. loading images and audio.
            Parameters:
             screen (pygame.Surface): The full pygame display surface itself.
              This is passed to objects so they know where the screen boundaries
              are, for transmitting boundary collision events.
        """
        self.info("Setup:")
        with logging_object.Indented(self):
            self.screen = screen
            self.symbols.setConstant('screen_width', screen.get_width())
            self.symbols.setConstant('screen_height', screen.get_height())
            self.info("Pre-load game resources..")
            with logging_object.Indented(self):
                self.setup_game_resources()
            self.info("Load first room..")
            with logging_object.Indented(self):
                self.load_room(0)

    def setup_game_resources(self):
        topdir = os.getcwd()
        if os.path.exists('sprites'):
            os.chdir('sprites')
            self.info("Preloading sprite images..")
            with logging_object.Indented(self):
                for spr in self.resources['sprites'].keys():
                    self.info("{}".format(spr))
                    self.resources['sprites'][spr].setup()
        sound_dir = os.path.join(topdir, 'sounds')
        if os.path.exists(sound_dir):
            os.chdir(sound_dir)
            self.info("Preloading sound files..")
            with logging_object.Indented(self):
                for snd in self.resources['sounds'].keys():
                    self.info("{}".format(snd))
                    self.resources['sounds'][snd].setup()
        background_dir = os.path.join(topdir, 'background')
        if os.path.exists(background_dir):
            os.chdir(background_dir)
            self.info("Preloading background images..")
            with logging_object.Indented(self):
                for bkg in self.resources['backgrounds'].keys():
                    self.info("{}".format(bkg))
                    self.resources['background'][bkg].setup()
        os.chdir(topdir)

    def load_room(self, room_n):
        """
            load_room():
            Initialize the given room number: create objects, run its init block
             (if any).
            Parameters:
             room_n (int): The number of the room to load (starting from 0)
        """
        self.info("Loading room {} ('{}')..".format(room_n,
            self.resources['rooms'][room_n].name))
        self.room_index = room_n
        room_width = self.resources['rooms'][room_n].width
        room_height = self.resources['rooms'][room_n].height
        # Create a new surface the same size as the room. This can differ from
        #  the screen dimensions. Also, for HWSURFACE displays, this allows the
        #  draw surface to be subsurface()'d, according to pygame documentation.
        self.draw_surface = pygame.Surface( (room_width, room_height) )
        self.resources['rooms'][room_n].draw_room_background(self.draw_surface)
        self.resources['rooms'][room_n].load_room(self.draw_surface)
        self.symbols.setConstant('room_width', room_width)
        self.symbols.setConstant('room_height', room_height)
        self.info("Room {} loaded.".format(room_n))

    def collect_event(self, event):
        """
            collect_event():
            The pygame event queue will lose events unless they are handled.
            This method is called by the pygame template to move the events
            out of pygame and into an instance list.
        """
        self.current_events.append(event)

    def update(self):
        """
            update():
            Called by the pygame template to update object positions. This is
             also a good time to check for any keyboard or mouse events, and to
             check for and send collision events.
        """
        # keep track of whether any mouse button or key events have been
        #  received this frame
        key_pressed = False
        mouse_button = False
        # create any new objects that were queued by create_object* events
        for new_obj, params in self.new_object_queue:
            new_obj.create_instance(self.draw_surface, params)
        # clear the queue for next frame
        self.new_object_queue = []
        # begin_step happens before other events
        ev = event.StepEvent('begin_step')
        self.event_engine.queue_event(ev)
        self.event_engine.transmit_event(ev.name)
        for ev in self.current_events:
            if ev.type == pygame.QUIT:
                self.done = True
                break
            elif ev.type in (pygame.KEYDOWN, pygame.KEYUP):
                key_pressed = True
                if (ev.key == pygame.K_ESCAPE):
                    self.done = True
                    break
                else:
                    self.send_key_event(ev)
            elif ev.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION]:
                self.send_mouse_event(ev)
                if ev.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP]:
                    mouse_button = True
        if not key_pressed:
            # no key events, so send the kb_no_key event
            self.send_key_event(None)
        if not mouse_button:
            # no mouse button events, so send the nobutton events
            self.send_mouse_event(None)
        # done with event handling
        self.current_events = []
        # normal_step happens before updating object instance positions
        ev = event.StepEvent('normal_step')
        self.event_engine.queue_event(ev)
        self.event_engine.transmit_event(ev.name)
        # perform position updates on all objects
        for obj_name in self.resources['objects'].keys():
            self.resources['objects'][obj_name].update()
        # check for object instance collisions
        obj_types = self.resources['objects'].values()
        collision_types = []
        for obj_name in self.resources['objects'].keys():
            collision_types += self.resources['objects'][obj_name].collision_check(obj_types)
        if len(collision_types) > 0:
            for coll_type in collision_types:
                self.event_engine.transmit_event(coll_type)

    def draw_objects(self):
        """
            draw_objects():
            Called by the pygame template to draw the foreground items.
        """
        # end_step happens just before drawing object instances
        ev = event.StepEvent('end_step')
        self.event_engine.queue_event(ev)
        self.event_engine.transmit_event(ev.name)
        for obj_name in self.resources['objects'].keys():
            self.info("Draw {} on surface {}".format(obj_name,
                self.draw_surface))
            self.resources['objects'][obj_name].draw(self.draw_surface)

    def draw_background(self):
        """
            draw_background():
            Called by the pygame template to draw the background.
        """
        if (self.room_index < len(self.resources['rooms'])):
            self.resources['rooms'][self.room_index].draw_room_background(self.draw_surface)

    def final_pass(self):
        # copy the room's pixels onto the display
        self.screen.blit(self.draw_surface, (0,0))

    def is_done(self):
        return self.done

    def run(self):
        pygame.init()
        self.screen = pygame.display.set_mode(self.game_settings['screen_dimensions'])
        self.setup(self.screen)
        pygame.display.set_caption(self.game_settings['game_name'])
        self.clock = pygame.time.Clock()

        # --- Main Loop ---
        while not self.done:
            for event in pygame.event.get():
                self.collect_event(event)
        
            # --- Game Logic ---
            self.update()
        
            #self.screen.fill(self.WHITE)
            # --- Drawing ---
            self.draw_background()
            self.draw_objects()
        
            # update screen
            self.final_pass()
            pygame.display.flip()
        
            # limit frame rate
            self.clock.tick(self.game_settings['frames_per_second'])

        # close window & quit
        pygame.quit()

if __name__ == "__main__":
    game_engine = GameEngine()
    game_engine.run()

