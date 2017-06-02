#!/usr/bin/python -W all

# Author: Ron Lockwood-Childs

# Licensed under LGPL v2.1 (see file COPYING for details)

# pygame maker widgets

import re
import math
import pygame
from styles import WidgetStyle
from .. import object_type
from .. import simple_object_instance
from pygame_maker.actions import action
from pygame_maker.actions import action_sequence
import pygame_maker.support.drawing as drawing
import pygame_maker.support.coordinate as coord
import pygame_maker.support.color as color


# An object that can be substituted for a pygame Surface, for checking
# width and height (helpful when calculating a minimum widget size without
# having a surface to draw it on).
class DummySurface(pygame.Rect):
    def get_width(self):
        return self.width
    def get_height(self):
        return self.height


class WidgetInstance(simple_object_instance.SimpleObjectInstance):
    INSTANCE_SYMBOLS = {
        "visible": 0,
        "widget_id": "",
        "widget_class": "",
        "hover": False,
        "selected": False,
    }
    # WidgetInstance subclasses set this dict to add additional symbols with
    # default values
    WIDGET_INSTANCE_SUBCLASS_SYMBOLS = {
    }
    THIN_BORDER_WIDTH = 1
    MEDIUM_BORDER_WIDTH = 3
    THICK_BORDER_WIDTH = 5
    def __init__(self, kind, screen, screen_dims, id_, settings=None, **kwargs):
        simple_object_instance.SimpleObjectInstance.__init__(self, kind, screen_dims, id_, settings, **kwargs)
        self.screen = screen
        self.screen_width = self.screen_dims[0]
        self.screen_height = self.screen_dims[1]
        self.style_settings = {}
        self.style_values = {}
        self.symbols["widget_class"] = ""
        self.symbols["widget_id"] = "{}".format(self.inst_id)
        self.symbols["visible"] = self.kind.visible

        style_hash = self.get_widget_instance_style_hash()
        style_info_hash = self.game_engine.global_style_settings.get_style(**style_hash)
        print("{}".format(style_info_hash))
        style_info = WidgetStyle(style_info_hash)
        self.get_widget_settings(style_info)
        self.get_inner_setting_values(screen_dims)
        # width, height = self.get_element_dimensions()
        # self.symbols["width"] = width
        # self.symbols["height"] = height
        for subclass_sym in self.WIDGET_INSTANCE_SUBCLASS_SYMBOLS.keys():
            if subclass_sym not in self.symbols.keys():
                self.symbols[subclass_sym] = self.WIDGET_INSTANCE_SUBCLASS_SYMBOLS[subclass_sym]

    @property
    def visible(self):
        return self.symbols["visible"]

    @visible.setter
    def visible(self, is_visible):
        vis = (is_visible is True)
        self.symbols["visible"] = vis

    @property
    def widget_id(self):
        return self.symbols["widget_id"]

    @widget_id.setter
    def widget_id(self, new_id):
        self.symbols["widget_id"] = "{}".format(new_id)

    @property
    def widget_class(self):
        return self.symbols["widget_class"]

    @widget_class.setter
    def widget_class(self, new_class):
        self.symbols["widget_class"] = new_class

    @property
    def hover(self):
        return int(self.symbols["hover"])

    @hover.setter
    def hover(self, hover_on):
        self.symbols["hover"] = (hover_on == True)

    @property
    def selected(self):
        return int(self.symbols["selected"])

    @selected.setter
    def selected(self, is_selected):
        self.symbols["selected"] = (is_selected == True)

    @property
    def width(self):
        if "width" in self.symbols.keys():
            return self.symbols["width"]
        else:
            return 0

    @width.setter
    def width(self, new_width):
        int_width = int(new_width)
        self.rect.width = int_width
        self.symbols["width"] = int_width

    @property
    def height(self):
        return self.symbols["height"]

    @height.setter
    def height(self, new_height):
        int_height = int(new_height)
        self.rect.height = int_height
        self.symbols["height"] = int_height

    @property
    def parent(self):
        return self.symbols["parent"]

    def get_style_setting(self, setting_name, css_properties, parent_settings):
        self.debug("WidgetInstance.get_style_setting(setting_name={}, css_properties={}, parent_settings={})".format(setting_name, css_properties, parent_settings))
        default_setting = WidgetStyle.get_style_entry_default(setting_name)
        setting = default_setting
        if setting_name in self.symbols.keys():
            # settings passed in from object YAML or constructor override
            # default CSS
            setting = self.symbols[setting_name]
        if setting_name in css_properties.keys():
            check_setting = " ".join(css_properties[setting_name])
            # self.debug("check_setting: {}".format(check_setting))
            if check_setting != "initial":
                if (WidgetStyle.compare_value_vs_constraint(setting_name, "inherit") and
                                check_setting == "inherit" and self.parent is not None):
                    setting = parent_settings[setting_name]
                elif WidgetStyle.compare_value_vs_constraint(setting_name, check_setting):
                    setting = check_setting
        return setting

    def get_widget_settings(self, css_properties):
        self.debug("WidgetInstance.get_style_settings(css_properties={})".format(css_properties))
        parent_settings = None
        if self.parent is not None and isinstance(self.parent, WidgetInstance):
            # this could result in the parent checking its parent's
            # settings..
            parent_settings = self.parent.get_widget_settings(css_properties)
        for setting_name in WidgetStyle.STYLE_CONSTRAINTS.keys():
            # self.debug("Get widget setting {} .. ".format(setting_name))
            self.style_settings[setting_name] = self.get_style_setting(setting_name, css_properties,
                parent_settings)

    def _get_integer_setting(self, setting, max_value):
        value = 0
        # self.debug("search '{}', which is type '{}'".format(setting, type(setting).__name__))
        if not isinstance(setting, str):
            # in case the value is already a number
            return setting
        num_minfo = WidgetStyle.NUMBER_RE.search(setting)
        if num_minfo:
            value = int(setting)
        num_minfo = WidgetStyle.SIGNED_NUMBER_RE.search(setting)
        if num_minfo:
            value = int(setting)
        px_minfo = WidgetStyle.PX_RE.search(setting)
        if px_minfo:
            value = int(px_minfo.group(1))
        pc_minfo = WidgetStyle.PERCENT_RE.search(setting)
        if pc_minfo:
            perc = float(pc_minfo.group(1)) / 100.0
            if perc > 1.0:
                # WidgetStyle doesn't constrain the percentage; force
                # maximum to 100% 
                perc = 1.0
            value = int(math.floor(perc * max_value))
        return value

    def get_outer_setting_values(self, surface):
        self.debug("WidgetInstance.get_outer_setting_values(surface={})".format(surface))
        # CSS box model: calculate margin, border, and padding so the remaining
        # setting values can be calculated
        surface_width = surface.get_width()
        surface_height = surface.get_height()
        for setting_name in ("margin-left", "border-left-width", "padding-left",
                             "padding-right", "border-right-width", "margin-right"):
            style_val = self._get_integer_setting(self.style_settings[setting_name], surface_width)
            self.style_values[setting_name] = style_val
        for setting_name in ("margin-top", "border-top-width", "padding-top",
                             "padding-bottom", "border-bottom-width", "margin-bottom"):
            style_val = self._get_integer_setting(self.style_settings[setting_name], surface_height)
            self.style_values[setting_name] = style_val

    def calculate_outer_dimensions(self):
        self.debug("WidgetInstance.calculate_outer_dimensions()")
        # calculate width
        outer_width = (self.style_values["margin-left"] + self.style_values["margin-right"] +
            self.style_values["padding-left"] + self.style_values["padding-right"])
        border_left_width = 0
        if self.style_settings["border-left-style"] not in ("none", "hidden"):
            border_left_width = self.style_values["border-left-width"]
            if self.style_settings["border-left-style"] == "double":
                border_left_width = border_left_width * 2 + 1
        border_right_width = 0
        if self.style_settings["border-right-style"] not in ("none", "hidden"):
            border_right_width = self.style_values["border-right-width"]
            if self.style_settings["border-right-style"] == "double":
                border_right_width = border_right_width * 2 + 1
        outer_width += border_left_width + border_right_width
        # calculate height
        outer_height = (self.style_values["margin-top"] + self.style_values["margin-bottom"] +
            self.style_values["padding-top"] + self.style_values["padding-bottom"])
        border_top_height = 0
        if self.style_settings["border-top-style"] not in ("none", "hidden"):
            border_top_height = self.style_values["border-top-width"]
            if self.style_settings["border-top-style"] == "double":
                border_top_height = border_top_height * 2 + 1
        border_bottom_height = 0
        if self.style_settings["border-bottom-style"] not in ("none", "hidden"):
            border_bottom_height = self.style_values["border-bottom-width"]
            if self.style_settings["border-bottom-style"] == "double":
                border_bottom_height = border_bottom_height * 2 + 1
        outer_height += border_top_height + border_bottom_height
        return (outer_width, outer_height)

    def get_inner_setting_values(self, max_dimensions):
        self.debug("WidgetInstance.get_inner_setting_values(max_dimensions={})".format(max_dimensions))
        # calculate min-width, width, max-width values
        min_width_val = self._get_integer_setting(self.style_settings["min-width"], max_dimensions[0])
        if min_width_val > max_dimensions[0]:
            min_width_val = max_dimensions[0]
        self.style_values["min-width"] = min_width_val
        max_width_val = max_dimensions[0]
        if self.style_settings["max-width"] != "none":
            max_width_val = self._get_integer_setting(self.style_settings["max-width"], max_dimensions[0])
            if max_width_val > max_dimensions[0]:
                max_width_val = max_dimensions[0]
            elif max_width_val < min_width_val:
                max_width_val = min_width_val
            self.style_values["max-width"] = max_width_val
        if self.style_settings["width"] != "auto":
            width_val = self._get_integer_setting(self.style_settings["width"], max_dimensions[0])
            if width_val < min_width_val:
                width_val = min_width_val
            if width_val > max_width_val:
                width_val = max_width_val
            self.style_values["width"] = width_val
        # calculate min-height, height, max-height values
        min_height_val = self._get_integer_setting(self.style_settings["min-height"], max_dimensions[1])
        if min_height_val > max_dimensions[1]:
            min_height_val = max_dimensions[1]
        self.style_values["min-height"] = min_height_val
        max_height_val = max_dimensions[1]
        if self.style_settings["max-height"] != "none":
            max_height_val = self._get_integer_setting(self.style_settings["max-height"], max_dimensions[1])
            if max_height_val > max_dimensions[1]:
                max_height_val = max_dimensions[1]
            elif max_height_val < min_height_val:
                max_height_val = min_height_val
            self.style_values["max-height"] = max_height_val
        if self.style_settings["height"] != "auto":
            height_val = self._get_integer_setting(self.style_settings["height"], max_dimensions[1])
            if height_val < min_height_val:
                height_val = min_height_val
            if height_val > max_height_val:
                height_val = max_height_val
            self.style_values["height"] = height_val

    def get_element_dimensions(self):
        """
        Called after get_inner_setting_values() to determine the size of the
        widget's content.

        The base class will use the 'min-width' and 'min-height' properties as
        element dimensions, if the 'width' and 'height' properties are 'auto';
        otherwise, it will use the 'width' and/or 'height' properties' values.
        Subclasses should start here, and expand as needed to fit widget
        content, honoring the 'max-width' and 'max-height' properties.
        """
        self.debug("WidgetInstance.get_element_dimensions()")
        element_width = self.style_values["min-width"]
        element_height = self.style_values["min-height"]
        if self.style_settings["width"] != "auto":
            element_width = self.style_values["width"]
        if self.style_settings["height"] != "auto":
            element_height = self.style_values["height"]
        return (element_width, element_height)

    def get_color_values(self):
        self.debug("WidgetInstance.get_color_values()")
        color_property_list = ["border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
                               "background-color", "color"]
        # put Color objects into border/background color settings
        for color_property in color_property_list:
            color_name = self.style_settings[color_property]
            if isinstance(color_name, color.Color):
                self.style_values[color_property] = color_name
                continue
            default_color = str(WidgetStyle.STYLE_CONSTRAINTS[color_property]["default"])
            color_string = color_name
            if color_name != "transparent":
                minfo = WidgetStyle.WEB_COLOR_RE.match(color_name)
                if minfo:
                    if len(color_name) == 4:
                        color_string = "#0{}0{}0{}".format(*color_name[1:4])
                    elif len(color_name) == 5:
                        color_string = "#0{}0{}0{}0{}".format(*color_name[1:5])
                    elif len(color_name) == 6:
                        str_ary = [color_name[idx] for idx in range(1,4)]
                        str_ary.append(color_name[4:])
                        color_string = "#0{}0{}0{}{}".format(*str_ary)
                    elif len(color_name) == 8:
                        color_string = "{}0{}".format(color_name[:7], color_name[7])
                try:
                    self.style_values[color_property] = color.Color(color_string)
                except ValueError:
                    self.style_values[color_property] = color.Color(default_color)
            elif color_property == "color":
                # font color isn't supposed to be "transparent", so replace
                # this string with the default color
                self.style_values[color_property] = color.Color(default_color)

    def get_min_size(self):
        """
        Calculate the widget's mininum width and height, and return them in a
        tuple.

        Container widgets may call this to find out how much space it needs
        to reserve for each of its child widgets.
        The base class only returns the space surrounding the widget's
        contents: the sum of margin, border, and padding widths for each side.
        Subclasses should call this method, then determine the element's
        actual dimensions after taking min/max width and height into account.
        """
        self.debug("WidgetInstance.get_min_size()")
        # create a surface such that 1% is a minimum of 1 pixel
        dummy_surface = DummySurface(0,0,100,100)
        min_width = 1
        min_height = 1
        style_hash = self.get_widget_instance_style_hash()
        style_info = WidgetStyle(self.game_engine.global_style_settings.get_style(**style_hash))
        self.get_widget_settings(style_info)
        self.get_outer_setting_values(dummy_surface)
        min_outer_dims = self.calculate_outer_dimensions()
        if min_outer_dims[0] > min_width:
            min_width = min_outer_dims[0]
        if min_outer_dims[1] > min_height:
            min_height = min_outer_dims[1]
        return (min_width, min_height)

    def _calculate_top_outer_border_size(self):
        top_size = self.style_values["margin-top"] + self.style_values["padding-top"]
        border_top_height = 0
        if (self.style_settings["border-top-style"] not in ("none", "hidden") and
                (self.style_settings["border-top-color"] != "transparent")):
            border_top_height = self.style_values["border-top-width"]
            if self.style_settings["border-top-style"] == "double":
                border_top_height = border_top_height * 2 + 1
        top_size += border_top_height
        return top_size

    def _calculate_left_outer_border_size(self):
        left_size = self.style_values["margin-left"] + self.style_values["padding-left"]
        border_left_width = 0
        if (self.style_settings["border-left-style"] not in ("none", "hidden") and
                (self.style_settings["border-left-color"] != "transparent")):
            border_left_width = self.style_values["border-left-width"]
            if self.style_settings["border-left-style"] == "double":
                border_left_width = border_left_width * 2 + 1
        left_size += border_left_width
        return left_size

    def _draw_border_side(self, screen, side, outer_dims, element_dims, width, color, style):
        draw_rect = pygame.Rect(0,0,0,0)
        # thick lines are _centered_ on the calculated coordinates, so shift them by 1/2 their width
        thick_adj = 0
        if width > 1:
            thick_adj = int(math.floor((width-1) / 2))
        if side == "top":
            draw_rect.left = self.style_values["margin-left"]
            draw_rect.top = self.style_values["margin-top"] + thick_adj
            draw_rect.width = self.style_values["border-left-width"] + self.style_values["padding-left"] + element_dims[0] + self.style_values["padding-right"]
            if draw_rect.width <= 1:
                return
        elif side == "bottom":
            draw_rect.left = self.style_values["margin-left"]
            draw_rect.top = (self._calculate_top_outer_border_size() + element_dims[1] +
                self.style_values["padding-bottom"] + thick_adj)
            draw_rect.width = self.style_values["border-left-width"] + self.style_values["padding-left"] + element_dims[0] + self.style_values["padding-right"]
            if draw_rect.width <= 1:
                return
        elif side == "left":
            draw_rect.left = self.style_values["margin-left"] + thick_adj
            draw_rect.top = self.style_values["margin-top"]
            draw_rect.height = self.style_values["border-top-width"] + self.style_values["padding-top"] + element_dims[1] + self.style_values["padding-bottom"]
            if draw_rect.height <= 1:
                return
        elif side == "right":
            draw_rect.left = (self._calculate_left_outer_border_size() + element_dims[0] +
                self.style_values["padding-right"] + thick_adj)
            draw_rect.top = self.style_values["margin-top"]
            draw_rect.height = self.style_values["border-top-width"] + self.style_values["padding-top"] + element_dims[1] + self.style_values["padding-bottom"]
            if draw_rect.height <= 1:
                return
        start_coord = coord.Coordinate(draw_rect.left, draw_rect.top)
        end_coord = coord.Coordinate(draw_rect.right, draw_rect.bottom)
        # self.debug("Draw {} border from {} to {}, width {}, color {}, style {}".format(
        #     side, start_coord, end_coord, width, color, style))
        drawing.draw_line(screen, start_coord, end_coord, width, color, style)

    def draw_border(self, screen, outer_dims):
        self.debug("WidgetInstance.draw_border(screen={}, outer_dims={})".format(screen, outer_dims))
        element_dims = self.get_element_dimensions()
        for side in ("top", "right", "bottom", "left"):
            border_width = self.style_values["border-{}-width".format(side)]
            border_style = self.style_settings["border-{}-style".format(side)]
            border_color_style = self.style_settings["border-{}-color".format(side)]
            border_color = "transparent"
            if border_color_style != "transparent":
                border_color = self.style_values["border-{}-color".format(side)]
            else:
                continue
            if border_style in ("none", "hidden") or (border_width < 1) or border_color == "transparent":
                continue
            self._draw_border_side(screen, side, outer_dims, element_dims, border_width, border_color, border_style)

    def draw(self, screen):
        """
        Draw the widget instance to a surface using css properties.

        Always recalculate the settings, in case the style has been updated,
        or an attribute has changed that may affect the style.

        :param screen: A pygame surface upon which to draw the widget
        :type screen: :py:class:`pygame.Surface`
        """
        self.debug("{} inst {}: WidgetInstance.draw(screen={})".format(self.kind.name, self.inst_id, screen))
        if not self.visible:
            return
        style_hash = self.get_widget_instance_style_hash()
        # self.debug("Find style {} in {} ..".format(style_hash, style_info))
        style_info = WidgetStyle(self.game_engine.global_style_settings.get_style(**style_hash))
        self.get_widget_settings(style_info)
        # self.debug("Style settings: {}".format(self.style_settings))
        self.get_outer_setting_values(screen)
        outer_dims = self.calculate_outer_dimensions()
        max_inner_dims = (screen.get_width() - outer_dims[0], screen.get_height() - outer_dims[1])
        self.get_inner_setting_values(max_inner_dims)
        self.get_color_values()
        # self.debug("Style values: {}".format(self.style_values))
        self.draw_border(screen, outer_dims)

    def get_widget_instance_style_hash(self):
        """
        Collect widget instance style information for comparison with
        stylesheet settings.

        Subclasses should start here and add attribute matches (e.g. a
        checkbutton could match on "checked" attribute "on" or "off")
        """
        self.debug("WidgetInstance.get_widget_instance_style_hash()")
        props = {
            "element_type": self.kind.name,
            "element_id": self.widget_id,
        }
        if len(self.widget_class) > 0:
            props["element_class"] = self.widget_class
        if self.hover:
            props["pseudo_class"] = "hover"
        return props


class LabelWidgetInstance(WidgetInstance):
    WIDGET_INSTANCE_SUBCLASS_SYMBOLS = {
        "label": "",
        "font": "",
        "font_size": "initial",
        "font_style": "initial",
        "font_weight": "initial",
        "text_decoration": "initial",
        "text_transform": "initial",
        "text_align": "initial",
        "vertical_align": "initial",
        "color": color.Color("black")
    }
    FONT_SIZE_CATEGORIES = {
        "small": 10,
        "medium": 14,
        "large": 20
    }

    def __init__(self, kind, screen, screen_dims, id_, settings=None, **kwargs):
        super(LabelWidgetInstance, self).__init__(kind, screen, screen_dims, id_, settings, **kwargs)
        self.font_resource = None
        self.get_font_resource()
        self._font_point_size = 12

    @property
    def label(self):
        return self.symbols["label"]

    @label.setter
    def label(self, new_label):
        try:
            self.symbols["label"] = str(new_label)
        except ValueError:
            pass

    @property
    def font(self):
        return self.symbols["font"]

    @font.setter
    def font(self, new_font):
        try:
            self.symbols["font"] = str(new_font)
            self.get_font_resource()
        except ValueError:
            pass

    @property
    def font_size(self):
        return self.symbols["font_size"]

    @font_size.setter
    def font_size(self, new_size):
        self.symbols["font_size"] = new_size

    def get_font_resource(self):
        self.debug("LabelWidgetInstance.get_font_resource()")
        if (len(self.font) == 0) or self.font not in self.kind.game_engine.resources['fonts'].keys():
            # revert to a system font, if found
            if hasattr(self.kind.game_engine, 'system_font'):
                self.font_resource = self.kind.game_engine.system_font
            else:
                return None
        else:
            self.font_resource = self.kind.game_engine.resources['fonts'][self.font]

    def calc_label_size(self):
        self.debug("LabelWidgetInstance.calc_label_size()")
        if self.font_resource is None:
            return (0, 0)
        if len(self.label) == 0:
            return (0, 0)
        font_rndr = self.font_resource.get_font_renderer()
        return font_rndr.calc_render_size(self.label)

    def get_min_size(self):
        self.debug("LabelWidgetInstance.get_min_size()")
        total_width, total_height = super(LabelWidgetInstance, self).get_min_size()
        text_width, text_height = self.calc_label_size()
        total_width += text_width
        total_height += text_height
        return (total_width, total_height)

    def get_element_dimensions(self):
        self.debug("LabelWidgetInstance.get_element_dimensions()")
        element_width = self.style_values["min-width"]
        element_height = self.style_values["min-height"]
        label_width, label_height = self.calc_label_size()
        if self.style_settings["width"] != "auto":
            element_width = self.style_values["width"]
        elif label_width > element_width:
            element_width = label_width
        if self.style_settings["height"] != "auto":
            element_height = self.style_values["height"]
        elif label_height > element_height:
            element_height = label_height
        return (element_width, element_height)

    def draw_text(self, surface):
        self.debug("LabelWidgetInstance.draw_text(surface={})".format(surface))
        surf_width = surface.get_width()
        surf_height = surface.get_height()
        font_rndr = self.font_resource.get_font_renderer()
        # apply horizontal, vertical alignment
        text_width, text_height = font_rndr.calc_render_size(self.label)
        top_left = coord.Coordinate(0, 0)
        if (surf_width > text_width):
            if self.style_settings["text-align"] == "center":
                top_left.x = (surf_width / 2) - (text_width / 2)
            elif self.style_settings["text-align"] == "right":
                top_left.x = surf_width - text_width
        if (surf_height > text_height):
            if self.style_settings["vertical-align"] == "middle":
                top_left.y = (surf_height / 2) - (text_height / 2)
            elif self.style_settings["vertical-align"] == "bottom":
                top_left.y = surf_height - text_height
        font_rndr.render_text(surface, top_left, self.label, self.style_values["color"])

    def draw(self, screen):
        self.debug("LabelWidgetInstance.draw(screen={})".format(screen))
        # draw any visible borders
        super(LabelWidgetInstance, self).draw(screen)
        # create a subsurface big enough to hold the element dimensions
        label_width, label_height = self.calc_label_size()
        if (label_width > 0) and (label_height > 0):
            subsurf_width, subsurf_height = self.get_element_dimensions()
            subsurf_left = super(LabelWidgetInstance, self)._calculate_left_outer_border_size()
            subsurf_top = super(LabelWidgetInstance, self)._calculate_top_outer_border_size()
            subsurf_rect = pygame.Rect(subsurf_left, subsurf_top, subsurf_width, subsurf_height)
            subsurf = screen.subsurface(subsurf_rect)
            self.draw_text(subsurf)


class WidgetObjectTypeInvalid(Exception):
    pass


class WidgetObjectType(object_type.ObjectType):
    DEFAULT_VISIBLE = False

    # subclasses set this to their own instance type
    WIDGET_INSTANCE_TYPE = WidgetInstance

    # subclasses can add their own YAML properties by setting this class
    # variable to a list of tuples [(entry_name, entry_type), ..] where
    # entry_type is usually a standard type: str, int, or bool
    WIDGET_SUBCLASS_KW_ENTRIES = []

    @classmethod
    def gen_kwargs_from_yaml_obj(cls, obj_name, obj_yaml, game_engine):
        kwargs = super(WidgetObjectType, cls).gen_kwargs_from_yaml_obj(obj_name, obj_yaml, game_engine)
        kwargs.update({
            "visible": WidgetObjectType.DEFAULT_VISIBLE,
        })
        if "visible" in obj_yaml.keys():
            kwargs["visible"] = (obj_yaml["visible"] == True)
        for kw_entry, entry_type in self.WIDGET_SUBCLASS_KW_ENTRIES:
            if kw_entry in obj_yaml.keys():
                if isinstance(entry_type, bool):
                    kwargs[kw_entry] = (obj_yaml[kw_entry] == True)
                else:
                    # set the kwarg if the type conversion succeeds
                    try:
                        kwargs[kw_entry] = entry_type(obj_yaml[kw_entry])
                    except ValueError:
                        pass
        return kwargs

    def __init__(self, widget_name, game_engine, **kwargs):
        super(WidgetObjectType, self).__init__(widget_name, game_engine, **kwargs)
        #: Flag whether this widget type is a container for other widgets
        self.is_container = False
        self.visible = self.DEFAULT_VISIBLE
        # default draw action sequence draws the object's sprite
        self["draw"] = action_sequence.ActionSequence()
        self["draw"].append_action(action.DrawAction("draw_self"))
        if kwargs and "visible" in kwargs:
            self.visible = kwargs["visible"]

    def make_new_instance(self, screen, instance_properties=None):
        """
        Generate a new instance of the widget type in response to
            :py:meth:`~pygame_maker.actors.object_type.ObjectType.create_instance`

        :param screen: The surface the instance will be drawn upon.  The
            instance can use this surface's (often a sub-surface's) width and
            height parameters to determine child widget placement
        :type screen: :py:class:`pygame.Surface`
        :param instance_properties: A hash of settings to be applied.  See
            kwargs entry in
            :py:meth:`~pygame_maker.actors.simple_object_instance.SimpleObjectInstance.__init__`
        :type instance_properties: dict
        """
        self.debug("WidgetObjectType.make_new_instance(screen={}, instance_properties={})".format(screen, instance_properties))
        screen_dims = (screen.get_width(), screen.get_height())
        new_instance = self.WIDGET_INSTANCE_TYPE(self, screen, screen_dims, self._id, instance_properties)
        self.instance_list.append(new_instance)

    def update(self):
        """
        Update all instances of this widget type.
        """
        pass

    def draw(self, in_event):
        """Draw all visible instances."""
        self.debug("WidgetObjectType.draw(in_event={})".format(in_event))
        if len(self.instance_list) > 0:
            for inst in self.instance_list:
                # self.debug("Check inst {}".format(inst))
                if inst.parent is not None:
                    continue
                if inst.visible:
                    # self.debug("Draw visible inst {}".format(inst))
                    inst.draw(inst.screen)

class LabelWidgetObjectType(WidgetObjectType):
    WIDGET_INSTANCE_TYPE = LabelWidgetInstance

