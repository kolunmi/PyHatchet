# main.py
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

import sys
import asyncio
import gi

from gettext import gettext as _

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Dex', '1')
gi.require_version('Foundry', '1')
gi.require_version('FoundryGtk', '1')
gi.require_version('FoundryAdw', '1')

from gi.repository import GLib, Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw, Peas
from gi.events import GLibEventLoopPolicy

from .util import run_async, item_future
from .context import HatchetContext, HatchetShortcuts
from .window import HatchetWindow
from .emacs import bind_emacs_base, bind_emacs_secondary

class HatchetApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='net.kolunmi.Hatchet',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/net/kolunmi/Hatchet')

        self.create_action('next-keymap', self.on_next_keymap_action, "s")
        self.create_action('quit', lambda *_: self.quit(), None, shortcuts=['<control>q'])
        self.create_action('about', self.on_about_action, None)
        self.create_action('preferences', self.on_preferences_action, None)
        self.create_action('open-document', self.on_open_document_action, "s", arg_hint=Gio.File)
        self.create_action('switch-document', self.on_switch_document_action, "s", arg_hint=Foundry.TextDocument)
        self.create_action('save-document', self.on_save_document_action, "s", arg_hint=Foundry.TextDocument)

        self.keymaps = {}
        self.current_keymap = "base"

        base_shortcuts = HatchetShortcuts.new_with_stores()
        bind_emacs_base(base_shortcuts)
        self.keymaps["base"] = base_shortcuts

        secondary_shortcuts = HatchetShortcuts.new_with_stores()
        bind_emacs_secondary(secondary_shortcuts)
        self.keymaps["secondary"] = secondary_shortcuts

        shortcuts = HatchetShortcuts.new_with_stores()
        shortcuts.apply(base_shortcuts)

        user_foundry = Foundry.FutureItem.new(Foundry.Context.new_for_user())
        foundrys = Gio.ListStore.new(Foundry.FutureItem)
        foundrys.append(user_foundry)

        self.context = HatchetContext(
            shortcuts=shortcuts,
            user_foundry=user_foundry,
            foundrys=foundrys,
            current_keymap=self.current_keymap,
        )

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = HatchetWindow(application=self,context=self.context)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(application_name='Hatchet',
                                application_icon='net.kolunmi.Hatchet',
                                developer_name='kol',
                                version='0.1.0',
                                # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
                                translator_credits = _('translator-credits'),
                                developers=['kol'],
                                copyright='© 2026 kol')
        about.present(self.props.active_window)

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        print('app.preferences action activated')

    def on_next_keymap_action(self, widget, params):
        keymap_id = params.get_string()
        if not keymap_id in self.keymaps:
            keymap_id = "base"
        if keymap_id == self.current_keymap:
            return
        shortcuts = self.keymaps[keymap_id]
        self.context.shortcuts.apply(shortcuts)
        self.current_keymap = keymap_id
        self.context.current_keymap = keymap_id

    def on_open_document_action(self, widget, params):
        path = params.get_string()

        # interactive mode if the string is empty
        if len(path) == 0:
            win = self.choose_window()
            if win:
                variant = GLib.Variant("s", "open-document")
                win.activate_action("win.open-action-picker", variant)
            return

        async def action(self):
            foundry = await self.context.get_foundry_for_path(path)
            text_mgr = foundry.dup_text_manager()
            try:
                document = await text_mgr.load(
                    Gio.File.new_for_path(path),
                    Foundry.Operation.new(),
                    None,
                ).to_asyncio()
                win = self.choose_window()
                if win:
                    win.open_document(document)
            except GLib.Error as err:
                self.show_error("Failed to open document", str(err))
        run_async(action(self))

    def on_switch_document_action(self, widget, params):
        path = params.get_string()

        # interactive mode if the string is empty
        if len(path) == 0:
            win = self.choose_window()
            if win:
                variant = GLib.Variant("s", "switch-document")
                win.activate_action("win.open-action-picker", variant)
            return

        self.on_open_document_action(widget, params)

    def on_save_document_action(self, widget, params):
        path = params.get_string()
        async def action(self):
            foundry = await self.context.get_foundry_for_path(path)
            text_mgr = foundry.dup_text_manager()
            try:
                document = await text_mgr.load(
                    Gio.File.new_for_path(path),
                    Foundry.Operation.new(),
                    None,
                ).to_asyncio()
                await document.save(Foundry.Operation.new()).to_asyncio()
            except GLib.Error as err:
                self.show_error("Failed to save document", str(err))
        run_async(action(self))

    def create_action(self, name, callback, params, shortcuts=None, arg_hint=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        if params:
            variant_string = GLib.VariantType(params)
        else:
            variant_string = None
        action = Gio.SimpleAction.new(name, variant_string)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)
        action._arg_hint = arg_hint

    def choose_window(self):
        win = self.get_active_window()
        if win:
            return win
        else:
            windows = self.get_windows()
            if len(windows) > 0:
                return windows[0]

    def show_error(self, heading, body):
        win = self.choose_window()
        if not win:
            return
        variant = GLib.Variant("(ss)", [heading, body])
        win.activate_action("win.show-error", variant)

def main(version):
    asyncio_policy = GLibEventLoopPolicy()
    asyncio.set_event_loop_policy(asyncio_policy)

    Dex.init()
    Gtk.init()
    Adw.init()
    FoundryGtk.gtk_init();
    FoundryAdw.adw_init();
    Foundry.init().disown()

    """The application's entry point."""
    app = HatchetApplication()
    return app.run(sys.argv)
