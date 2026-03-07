import tomllib


class Info:
    name: str
    version: str

    def __init__(self) -> None:
        with open("info.toml", "rb") as f:
            info = tomllib.load(f)

        for key, value in info.items():
            setattr(self, key, value)


info = Info()
