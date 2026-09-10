"""Window Frame helper"""

def is_on_frame(
    mouse_x: int | float,
    mouse_y: int | float,
    corner: int,
    vline_width: int,
    hline_height: int,
    window_width: int,
    window_height: int,
):
    """Is mouse pos in frame?"""
    cw = corner
    fw = vline_width  # frame edge thickness (scaled)
    fh = hline_height

    # Top bar (includes corners)
    if mouse_y < cw:
        return True
    # Bottom bar
    if mouse_y > window_height - cw:
        return True
    # Left strip
    if mouse_x < fw:
        return True
    # Right strip
    if mouse_x > window_width - fw:
        return True

    if fh - 1:
        return False
    return False
