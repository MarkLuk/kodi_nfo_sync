import xbmc
import xbmcgui
from service import NFOSyncService, logger

if __name__ == '__main__':
    logger.log("Manual Run Triggered via Script")

    # Just run, no dialog
    if xbmcgui.Dialog().yesno("NFO Sync", "Run Manual Sync now?"):
        service = NFOSyncService()
        service.run_sync()
