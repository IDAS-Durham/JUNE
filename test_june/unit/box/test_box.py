from june.box import Box, Boxes

def test__box_group():
    box = Box()
    assert hasattr(box, "people")

def test__boxes_group():
    boxes = Boxes([])
    assert hasattr(boxes, "members")



