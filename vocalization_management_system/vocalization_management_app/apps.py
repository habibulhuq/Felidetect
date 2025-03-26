from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class VocalizationManagementAppConfig(AppConfig):
    name = 'vocalization_management_app'
    
    def ready(self):
        """
        Start the background audio processor when Django starts
        This method is called once when Django starts
        """
        # Only start the processor in the main process, not in management commands
        import sys
        if 'runserver' in sys.argv:
            logger.info("Starting background audio processor...")
            try:
                # Import here to avoid circular imports
                from .tasks import start_background_processor
                start_background_processor()
                logger.info("Background audio processor started successfully")
            except Exception as e:
                logger.error(f"Failed to start background audio processor: {str(e)}")
