"""Command-line parameters for Weapon Blacksmith.

LunaEngine does not ship a ParameterParser class; the official
LunaEngine-Games examples use argparse.ArgumentParser directly
(see games/Breakout/main.py). This module wraps that pattern so the
rest of the game has a single typed entry point for CLI flags.
"""

from argparse import ArgumentParser


class ParameterParser:
    """Parse the game's command-line flags.

    Usage:
        params = ParameterParser(ArgumentParser(prog="Weapon Blacksmith"))
        params.fullscreen   # bool
        params.debug        # bool
    """

    def __init__(self, argparser: ArgumentParser):
        argparser.add_argument(
            "--fullscreen",
            action="store_true",
            default=False,
            help="Launch the game in fullscreen mode.",
        )
        argparser.add_argument(
            "--debug",
            action="store_true",
            default=False,
            help="Enable LunaEngine's debug overlay and LiveInspector.",
        )

        self.argparser = argparser
        # parse_known_args tolerates extra flags injected by LunaLauncher
        # (for example --username), so the game does not crash on them.
        self.args, self.unknown = argparser.parse_known_args()

    def __getattr__(self, name):
        # Convenience: params.fullscreen instead of params.args.fullscreen.
        args = self.__dict__.get("args")
        if args is None:
            raise AttributeError(name)
        return getattr(args, name)

    def __repr__(self):
        return f"ParameterParser(fullscreen={self.fullscreen}, debug={self.debug})"