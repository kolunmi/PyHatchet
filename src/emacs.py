# emacs.py
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

from gi.repository import GObject, Gio, Gtk

def add_key(store, trigger, action):
    shortcut_trigger = Gtk.ShortcutTrigger.parse_string(trigger)
    shortcut_action = Gtk.ShortcutAction.parse_string(action)
    shortcut = Gtk.Shortcut(trigger=shortcut_trigger, action=shortcut_action)
    store.append(shortcut)

def bind_emacs_window(store):
    add_key(store, '<alt>x', 'action(win.open-action-picker)')

def bind_emacs_picker(store):
    add_key(store, '<primary>p', 'action(picker.prev)')
    add_key(store, '<primary>n', 'action(picker.next)')
    add_key(store, 'Tab', 'action(picker.complete)')
    add_key(store, '<shift>Tab', 'action(picker.uncomplete)')
    add_key(store, '<alt>BackSpace', 'action(picker.uncomplete)')
    add_key(store, '<primary>g', 'action(picker.cancel)')
    add_key(store, 'Escape', 'action(picker.cancel)')

def bind_emacs_sourceview(store):
    add_key(store, '<primary>g', 'action(sourceview.cancel)')
    add_key(store, '<primary>p', 'action(sourceview.prev-line)')
    add_key(store, '<primary>n', 'action(sourceview.next-line)')
    add_key(store, '<primary>b', 'action(sourceview.prev-char)')
    add_key(store, '<primary>f', 'action(sourceview.next-char)')
    add_key(store, '<alt>b', 'action(sourceview.prev-word)')
    add_key(store, '<alt>f', 'action(sourceview.next-word)')
    add_key(store, '<primary>a', 'action(sourceview.beginning-of-line)')
    add_key(store, '<primary>e', 'action(sourceview.end-of-line)')
    add_key(store, '<alt>d', 'action(sourceview.kill-word)')
    add_key(store, '<alt>BackSpace', 'action(sourceview.backward-kill-word)')
    add_key(store, '<primary><shift>BackSpace', 'action(sourceview.kill-line)')
    add_key(store, '<primary>k', 'action(sourceview.kill-line-rest)')
    add_key(store, '<primary>space', 'action(sourceview.activate-mark-region)')
