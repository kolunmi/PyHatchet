# window.py
#
# Copyright 2026 kol
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio

from gi.repository import GLib, GObject, Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw
from .util import run_async, item_future
from .context import HatchetContext
from .picker import HatchetPicker
from .sourceview import HatchetSourceView

@Gtk.Template(resource_path='/net/kolunmi/Hatchet/window.ui')
class HatchetWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'HatchetWindow'

    context = GObject.Property(type=HatchetContext, default=None, flags=GObject.ParamFlags.READWRITE)

    overlay = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        action_group = Gio.SimpleActionGroup.new()
        self.create_action(action_group, "open-action-picker", self.action_open_action_picker, None)
        self.insert_action_group("win", action_group)

        shortcut_controller = Gtk.ShortcutController.new_for_model(self.context.window_shortcuts_model)
        self.add_controller(shortcut_controller)

        self.sourceview = HatchetSourceView(context=self.context)
        self.overlay.set_child(self.sourceview)

        self.picker = None

    def action_open_action_picker(self, action_name, params):
        if self.picker:
            return
        picker = HatchetPicker(context=self.context)
        picker.halign = Gtk.Align.FILL
        picker.valign = Gtk.Align.END
        picker.connect("selection-made", self.picker_selection_made_cb)
        self.overlay.add_overlay(picker)
        self.picker = picker

    def picker_selection_made_cb(self, ret_object, picker):
        if not self.picker:
            return
        self.overlay.remove_overlay(self.picker)
        self.picker = None

    def create_action(self, group, name, callback, params):
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        group.add_action(action)

    def open_document(self, document):
        self.sourceview.open_document(document)
        self.sourceview.grab_focus()
