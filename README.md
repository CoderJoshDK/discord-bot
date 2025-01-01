# Ghostty Discord Bot

The Ghostty Discord Bot, humorlessly named "Ghostty Bot."

## Development

The Nix environment is the only supported development environment. You can
develop this without Nix, of course, but I'm not going to help you figure it
out.

### Discord Bot

You will have to [set up a Discord bot][discord-docs] and get a Discord
bot token. The instructions for that are out of scope for this README.
The Discord bot will require the following privileges:

- Manage Roles
- Members Privileged Intents

### Nix

Once your environment is set up, create a `.env` file based on `.env.example`
and run the app:

```console
$ python -m app
...
```

After you've made your changes, run the linter and formatter:

```console
ruff check
ruff format
```

### Non-Nix

This bot runs on Python 3.12+ and is managed with uv. To get started:

1. [Install uv][uv-docs].
2. Create a `.env` file based on `.env.example`.
3. Install the project and run the bot:

   ```console
   $ uv run python -m app
   ...
   ```

4. After you've made your changes, run the linter and formatter:

   ```console
   uv run ruff check
   uv run ruff format
   ```

[discord-docs]: https://discord.com/developers/applications
[uv-docs]: https://docs.astral.sh/uv
