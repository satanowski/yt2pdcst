from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(loader=FileSystemLoader("templates"), autoescape=select_autoescape())

index = env.get_template("index.jinja")


def make_rss(context: dict, entries: list) -> str:
    context.update({"items": entries})
    return index.render(context)
