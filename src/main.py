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

from gi.repository import Gio, Gtk, Adw, Dex, Foundry, FoundryGtk, FoundryAdw, Peas
from gi.events import GLibEventLoopPolicy

from .util import run_async, item_future
from .context import HatchetContext
from .window import HatchetWindow

class HatchetApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='net.kolunmi.Hatchet',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/net/kolunmi/Hatchet')

        self.create_action('quit', lambda *_: self.quit(), ['<control>q'])
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)

        self.context = HatchetContext(
            foundry=Foundry.FutureItem.new(Foundry.Context.new_for_user()),
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

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


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
