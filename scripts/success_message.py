import rich.console

# Generated using https://patorjk.com/software/taag/#p=display&f=Bloody&t=nice
SUCCESS_MESSAGE = """
  ███▄    █  ██▓ ▄████▄  ▓█████
  ██ ▀█   █ ▓██▒▒██▀ ▀█  ▓█   ▀
 ▓██  ▀█ ██▒▒██▒▒▓█    ▄ ▒███
 ▓██▒  ▐▌██▒░██░▒▓▓▄ ▄██▒▒▓█  ▄
 ▒██░   ▓██░░██░▒ ▓███▀ ░░▒████▒
 ░ ▒░   ▒ ▒ ░▓  ░ ░▒ ▒  ░░░ ▒░ ░
 ░ ░░   ░ ▒░ ▒ ░  ░  ▒    ░ ░  ░
    ░   ░ ░  ▒ ░░           ░
          ░  ░  ░ ░         ░  ░
                ░
"""


def main():
    """Print a reassuring message to cheer up the developer."""
    console = rich.console.Console(highlight=False)
    for idx, line in enumerate(SUCCESS_MESSAGE.splitlines()):
        colour = min(45 + idx, 51)  # A green-cyan gradient
        console.print(line, style=f"color({colour})")
    print()


if __name__ == "__main__":
    main()
