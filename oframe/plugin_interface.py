class OPlugin:
    """Base class for all O-Frame plugins."""

    def __init__(self, core=None):
        self.core = core

    def run(self, *args, **kwargs):
        """Execute the plugin's main logic."""
        raise NotImplementedError("Plugins must implement the run method")
