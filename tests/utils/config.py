import tomllib
from pathlib import Path
from tempfile import gettempdir
from typing import TYPE_CHECKING

import discord as dc

from app.config import Config, config_var

if TYPE_CHECKING:
    from contextvars import Token

ROOT = Path(__file__).parents[2]


def config() -> Token[Config]:
    """
    Intended to be used as a context manager:

        with config():
            ...
    """
    cfg = tomllib.loads((ROOT / "config-example.toml").read_text())
    cfg["data_dir"] = gettempdir()

    bot = dc.Client(intents=dc.Intents.none())

    Config.model_config["cli_parse_args"] = False
    Config.model_config["env_prefix"] = "="  # invalid env var name char
    return config_var.set(Config(**cfg, bot=bot))
