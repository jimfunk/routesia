"""
routesia/entity.py - Entity base
"""


class Entity:
    def __init__(self, config=None):
        self.config = config
        self.state = {}

    def apply_config(self):
        pass
