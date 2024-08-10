from typing import Literal


def styling(
    text: str,
    tag: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p"] = "h2",
    text_align: Literal["left", "right", "center", "justify"] = "center",
    font_size: int = 32,
    font_family: str = "Arial",
    background_color: str = "transparent",
    color: str = "black",
) -> tuple[str, bool]:
    style = f"text-align: {text_align}; font-size: {font_size}px; font-family: {font_family}; background-color: {background_color}; color: {color};"
    styled_text = f'<{tag} style="{style}">{text}</{tag}>'
    return styled_text, True


def multi_color_styling(
    text_color_pairs: list[tuple[str, str]],
    tag: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p"] = "p",
    text_align: Literal["left", "right", "center", "justify"] = "left",
    font_size: int = 14,
    font_family: str = "Arial",
    background_color: str = "transparent",
) -> str:
    style = f"text-align: {text_align}; font-size: {font_size}px; font-family: {font_family}; background-color: {background_color};"
    styled_text = f'<{tag} style="{style}">'
    for text, color in text_color_pairs:
        styled_text += f'<span style="color: {color};">{text}</span><br>'
    styled_text = styled_text.rstrip("<br>")
    styled_text += f"</{tag}>"
    return styled_text
