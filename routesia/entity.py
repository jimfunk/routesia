"""
routesia/entity.py - Entity base
"""


class Entity:
    def __init__(self, config=None):
        self.config = config

    def apply(self):
        """
        Apply entity config.
        """
        pass
