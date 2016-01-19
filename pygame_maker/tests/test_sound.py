#!/usr/bin/env python

from pygame_maker.sounds.sound import *
import unittest
import tempfile
import os
import sys
import time

class TestSound(unittest.TestCase):

    def setUp(self):
        self.sound_test_file = "unittest_files/Pop.wav"
        self.valid_sound_yaml = "- yaml_sound:\n    sound_file: {}\n    sound_type: music\n    preload: False\n".format(self.sound_test_file)
        self.valid_sound_object = Sound("yaml_sound",
            sound_file=self.sound_test_file, sound_type="music",
            preload=False)

    def test_005valid_sound(self):
        sound1 = Sound("sound1")
        self.assertEqual(sound1.name, "sound1")

    def test_010sound_parameters(self):
        pygame.init()
        music1 = Sound("music1", sound_type="music")
        self.assertEqual(music1.sound_type, "music")
        sound_with_file = Sound("dontpanic",
            sound_file=self.sound_test_file)
        sound_with_file.play_sound()
        self.assertTrue(sound_with_file.is_sound_playing())
        time.sleep(2)
        self.assertFalse(sound_with_file.is_sound_playing())
        self.assertEqual(sound_with_file.sound_file, self.sound_test_file)

    def test_015missing_sound_file(self):
        missing_music1 = Sound("missing1",
            sound_type="music", sound_file="unittest/missing1.wav")
        with self.assertRaises(SoundException):
            missing_music1.setup()
        missing_sound1 = Sound("missing2",
            preload=False, sound_file="unittest/missing2.wav")
        missing_sound1.setup()
        with self.assertRaises(SoundException):
            missing_sound1.play_sound()

    def test_020sound_to_yaml(self):
        self.assertEqual(self.valid_sound_object.to_yaml(),
            self.valid_sound_yaml)

    def test_025yaml_to_sound(self):
        tmpf_info = tempfile.mkstemp(dir="/tmp")
        tmp_file = os.fdopen(tmpf_info[0], 'w')
        tmp_file.write(self.valid_sound_yaml)
        tmp_file.close()
        loaded_sound1 = None
        with open(tmpf_info[1], "r") as yaml_f:
            loaded_sound1 = Sound.load_from_yaml(yaml_f)[0]
        os.unlink(tmpf_info[1])
        self.assertEqual(self.valid_sound_object, loaded_sound1)

    def test_030to_and_from_yaml(self):
        generated_sound_yaml = self.valid_sound_object.to_yaml()
        tmpf_info = tempfile.mkstemp(dir="/tmp")
        tmp_file = os.fdopen(tmpf_info[0], 'w')
        tmp_file.write(generated_sound_yaml)
        tmp_file.close()
        loaded_sound1 = None
        with open(tmpf_info[1], "r") as yaml_f:
            loaded_sound1 = Sound.load_from_yaml(yaml_f)[0]
        os.unlink(tmpf_info[1])
        self.assertEqual(self.valid_sound_object, loaded_sound1)

# run from the tests directory to find the unittest_files subdirectory
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

unittest.main()

