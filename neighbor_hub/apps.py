from django.apps import AppConfig


class NeighborHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'neighbor_hub'
    # verbose_name = 'NeighborHub'
    def ready(self):
        import neighbor_hub.signals