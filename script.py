import xbmc
import xbmcgui
from service import NFOSyncService, logger

if __name__ == '__main__':
    options = ['Import (from NFOs)', 'Export (to NFOs)', 'Clean Library']
    ret = xbmcgui.Dialog().select('NFO Sync Manual Trigger', options)

    if ret >= 0:
        service = NFOSyncService()
        if ret == 0:
            logger.log("Manual Trigger: Import")
            service.run_import()
        elif ret == 1:
            logger.log("Manual Trigger: Export")
            service.run_export()
        elif ret == 2:
            logger.log("Manual Trigger: Clean")
            service.run_clean()
