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

from gi.repository import GLib, GObject, Gio, Gtk

from .context import HatchetShortcuts

def str_arg(s):
    return GLib.Variant("s", s)

def add_key(store, trigger, action, params=None):
    shortcut_trigger = Gtk.ShortcutTrigger.parse_string(trigger)

    reset_keymap = action != "app.next-keymap"
    def cb(widget, args):
        widget.activate_action(action, params)
        if reset_keymap:
            widget.activate_action("app.next-keymap", str_arg('base'))
        return True
    shortcut_action = Gtk.CallbackAction.new(cb)

    shortcut = Gtk.Shortcut(trigger=shortcut_trigger, action=shortcut_action)
    store.append(shortcut)

def bind_emacs_base(shortcuts):
    add_key(shortcuts.window, "<primary>x", "app.next-keymap", str_arg("secondary"))
    add_key(shortcuts.window, "<primary>s", "app.next-keymap", str_arg("special"))
    add_key(shortcuts.window, "<alt>x", "win.open-action-picker", str_arg(""))

    add_key(shortcuts.picker, "<primary>p", "picker.prev")
    add_key(shortcuts.picker, "<primary>n", "picker.next")
    add_key(shortcuts.picker, "Tab", "picker.complete")
    add_key(shortcuts.picker, "<shift>Tab", "picker.uncomplete")
    add_key(shortcuts.picker, "<alt>BackSpace", "picker.uncomplete")
    add_key(shortcuts.picker, "<primary>g", "picker.cancel")
    add_key(shortcuts.picker, "Escape", "picker.cancel")

    add_key(shortcuts.sourceview, "<primary>g", "sourceview.cancel")
    add_key(shortcuts.sourceview, "<primary>p", "sourceview.prev-line")
    add_key(shortcuts.sourceview, "<primary>n", "sourceview.next-line")
    add_key(shortcuts.sourceview, "<primary>b", "sourceview.prev-char")
    add_key(shortcuts.sourceview, "<primary>f", "sourceview.next-char")
    add_key(shortcuts.sourceview, "<alt>b", "sourceview.prev-word")
    add_key(shortcuts.sourceview, "<alt>f", "sourceview.next-word")
    add_key(shortcuts.sourceview, "<primary>a", "sourceview.beginning-of-line")
    add_key(shortcuts.sourceview, "<primary>e", "sourceview.end-of-line")
    add_key(shortcuts.sourceview, "<alt>d", "sourceview.kill-word")
    add_key(shortcuts.sourceview, "<alt>BackSpace", "sourceview.backward-kill-word")
    add_key(shortcuts.sourceview, "<primary><shift>BackSpace", "sourceview.kill-line")
    add_key(shortcuts.sourceview, "<primary>k", "sourceview.kill-line-rest")
    add_key(shortcuts.sourceview, "<primary>space", "sourceview.activate-mark-region")
    add_key(shortcuts.sourceview, "<alt>w", "sourceview.copy-region")
    add_key(shortcuts.sourceview, "<primary>w", "sourceview.kill-region")
    add_key(shortcuts.sourceview, "<primary>y", "sourceview.paste")
    add_key(shortcuts.sourceview, "<primary>slash", "sourceview.undo")
    add_key(shortcuts.sourceview, "<primary>m", "sourceview.insert-newline")
    add_key(shortcuts.sourceview, "<primary>l", "sourceview.center-view")
    add_key(shortcuts.sourceview, "<alt>v", "sourceview.scroll-up")
    add_key(shortcuts.sourceview, "<primary>v", "sourceview.scroll-down")
    add_key(shortcuts.sourceview, "<primary><alt>p", "sourceview.prev-pair")
    add_key(shortcuts.sourceview, "<primary><alt>n", "sourceview.next-pair")
    add_key(shortcuts.sourceview, "<primary><alt>space", "sourceview.mark-next-pair")

def bind_emacs_secondary(shortcuts):
    add_key(shortcuts.window, "<primary>g", "app.next-keymap", str_arg("base"))
    add_key(shortcuts.window, "<primary>f", "app.open-document", str_arg(""))
    add_key(shortcuts.window, "b", "app.switch-document", str_arg(""))
    add_key(shortcuts.window, "<primary>s", "win.save-document")

    add_key(shortcuts.sourceview, "<primary>x", "sourceview.swap-around-mark-region")

def bind_emacs_special(shortcuts):
    add_key(shortcuts.window, "<primary>g", "app.next-keymap", str_arg("base"))
    add_key(shortcuts.window, "b", "app.switch-document", str_arg(""))

    add_key(shortcuts.sourceview, "p", "sourceview.beginning-of-document")
    add_key(shortcuts.sourceview, "n", "sourceview.end-of-document")
