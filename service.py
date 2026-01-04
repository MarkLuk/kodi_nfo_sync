import os
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import time
import json
from datetime import datetime, timedelta

ADDON_ID = 'service.library.nfosync'
ADDON = xbmcaddon.Addon()

class Logger:
    def log(self, msg, level=xbmc.LOGINFO):
        xbmc.log(f"[{ADDON_ID}] {msg}", level)

    def notify(self, header, message, icon=xbmcgui.NOTIFICATION_INFO, time=5000):
        if ADDON.getSettingBool('show_notifications'):
            xbmcgui.Dialog().notification(header, message, icon, time)

logger = Logger()

def get_setting_int(id):
    try:
        return int(ADDON.getSettingInt(id))
    except:
        return 0

def get_last_run(key):
    last_run_str = ADDON.getSetting(key)
    if not last_run_str:
        return 0
    try:
        return float(last_run_str)
    except:
        return 0

def set_last_run(key, timestamp):
    ADDON.setSetting(key, str(timestamp))

def json_rpc(method, params=None):
    if params is None:
        params = {}
    payload = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1
    }
    response = xbmc.executeJSONRPC(json.dumps(payload))
    return json.loads(response)

def json_rpc_batch(payloads):
    if not payloads:
        return []
    # Wrap in single list for batch request
    json_payload = json.dumps(payloads)
    response = xbmc.executeJSONRPC(json_payload)
    return json.loads(response)

class NFOSyncService(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.next_run_import = 0
        self.next_run_export = 0
        self.next_run_clean = 0
        self.update_schedule()

    def update_schedule(self):
        # Update Import Schedule
        if ADDON.getSettingBool('import_enabled'):
            interval = get_setting_int('import_interval')
            last_run = get_last_run('last_run_import')
            if last_run == 0:
                self.next_run_import = time.time() + 60
            else:
                self.next_run_import = last_run + (interval * 3600)
        else:
            self.next_run_import = 0

        # Update Export Schedule
        if ADDON.getSettingBool('export_enabled'):
            interval = get_setting_int('export_interval')
            last_run = get_last_run('last_run_export')
            if last_run == 0:
                self.next_run_export = time.time() + 60
            else:
                self.next_run_export = last_run + (interval * 3600)
        else:
            self.next_run_export = 0

        # Update Clean Schedule
        if ADDON.getSettingBool('clean_enabled') and ADDON.getSetting('clean_schedule_type') == 'On Schedule':
            interval = get_setting_int('clean_interval')
            last_run = get_last_run('last_run_clean')
            if last_run == 0:
                self.next_run_clean = time.time() + 60
            else:
                self.next_run_clean = last_run + (interval * 3600)
        else:
            self.next_run_clean = 0

        logger.log(f"Schedule updated. Import: {self.fmt_time(self.next_run_import)}, Export: {self.fmt_time(self.next_run_export)}, Clean: {self.fmt_time(self.next_run_clean)}")

    def fmt_time(self, ts):
        if ts == 0: return "Disabled/Manual"
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

    def wait_for_scan(self):
        # Wait a moment for scan to potentially start
        count = 0
        while count < 10:
            if xbmc.getCondVisibility('Library.IsScanningVideo'):
                break
            xbmc.sleep(1000)
            count += 1

        # Wait for scan to finish
        while xbmc.getCondVisibility('Library.IsScanningVideo') and not self.abortRequested():
            xbmc.sleep(1000)

    def should_refresh(self, file_path, last_run):
        # Determine NFO path
        if not file_path: return False

        # Determine base path and extension
        base, ext = os.path.splitext(file_path)
        candidates = []

        # 1. Exact match: /path/movie.mkv -> /path/movie.nfo
        candidates.append(base + '.nfo')

        # 2. Movie NFO in parent dir: /path/movie.mkv -> /path/movie.nfo
        parent_dir = os.path.dirname(file_path)

        # Handle URL separators (/) vs OS separators (\ on Windows) correctly
        if '://' in file_path:
            sep = '/'
            # Ensure no double slashes except protocol
            parent_dir = parent_dir.rstrip('/\\')
        else:
            sep = os.path.sep

        candidates.append(parent_dir + sep + 'movie.nfo')

        # 3. TV Show NFO (usually file_path is the show dir or similar)
        # Note: file_path here comes from 'file' property of GetTVShows/GetMovies
        if '://' in file_path:
             candidates.append(file_path.rstrip('/\\') + sep + 'tvshow.nfo')
        else:
             candidates.append(os.path.join(file_path, 'tvshow.nfo'))

        for nfo_path in candidates:
            if xbmcvfs.exists(nfo_path):
                try:
                    stats = xbmcvfs.Stat(nfo_path)
                    mtime = stats.st_mtime()

                    if mtime > last_run:
                        logger.log(f"DETECTED CHANGE: {nfo_path} (mtime {mtime} > last_run {last_run})")
                        return True
                except Exception as e:
                    logger.log(f"Error checking NFO {nfo_path}: {e}", xbmc.LOGWARNING)
                    pass

        return False

    def wait_while_scanning(self):
        if xbmc.getCondVisibility('Library.IsScanningVideo'):
            logger.log("Library is currently scanning. Waiting for it to finish...")
            start_wait = time.time()
            while xbmc.getCondVisibility('Library.IsScanningVideo') and not self.abortRequested():
                xbmc.sleep(1000)
                if time.time() - start_wait > 30: # Log every 30s
                    logger.log("Still waiting for library scan to finish...")
                    start_wait = time.time()
            logger.log("Library scan finished. Proceeding...")

    def acquire_lock(self):
        # Use Home Window (10000) property as a specialized, ephemeral lock
        # This is memory-only and auto-clears on Kodi restart/crash
        is_running = xbmcgui.Window(10000).getProperty('service.library.nfosync.sync_active')
        if is_running == 'true':
            return False

        xbmcgui.Window(10000).setProperty('service.library.nfosync.sync_active', 'true')
        return True

    def release_lock(self):
        xbmcgui.Window(10000).setProperty('service.library.nfosync.sync_active', 'false')

    def check_preconditions(self):
        if self.acquire_lock():
            try:
                if xbmc.Player().isPlaying():
                    logger.log("Media is playing. Postponing task.")
                    return False
                self.wait_while_scanning()
                if self.abortRequested(): return False
                return True
            except:
                self.release_lock()
                raise
        else:
            logger.log("Task ignored: Another task is already in progress.")
            return False

    def run_import(self):
        if not self.check_preconditions():
            # Postpone
            self.next_run_import = time.time() + 60
            return

        try:
            import_type_str = ADDON.getSetting('import_type')
            logger.log(f"Starting Import. Type: {import_type_str}")
            logger.notify("NFO Sync", "Starting Import", xbmcgui.NOTIFICATION_INFO)

            start_time = time.time()

            # Import (Scan New Only) is index 0 (assuming based on order or string check)
            # labelenum values="Scan New Only|Full Refresh"
            if import_type_str == "Scan New Only":
                xbmc.executebuiltin('UpdateLibrary(video)')
                logger.log("Triggered UpdateLibrary (Scan)")
                self.wait_for_scan()
            elif import_type_str == "Full Refresh":
                self.refresh_library()

            set_last_run('last_run_import', start_time)
            logger.log("Import Completed")
            logger.notify("NFO Sync", "Import Completed", xbmcgui.NOTIFICATION_INFO)

            # Check for chained Clean-up
            if ADDON.getSettingBool('clean_enabled') and ADDON.getSetting('clean_schedule_type') == 'After Import':
                logger.log("Triggering Clean-up after Import...")
                self.release_lock()
                self.run_clean()
                return

        finally:
            self.release_lock()
            self.update_schedule()

    def run_export(self):
        if not self.check_preconditions():
            self.next_run_export = time.time() + 60
            return

        try:
            logger.log("Starting Export")
            logger.notify("NFO Sync", "Starting Export", xbmcgui.NOTIFICATION_INFO)
            start_time = time.time()

            # ExportLibrary(video, true, true, true, true)
            xbmc.executebuiltin('ExportLibrary(video,true,true,true,true)')
            logger.log("Triggered ExportLibrary")

            set_last_run('last_run_export', start_time)
            logger.log("Export Triggered/Completed")
            logger.notify("NFO Sync", "Export Completed", xbmcgui.NOTIFICATION_INFO)

        finally:
            self.release_lock()
            self.update_schedule()

    def run_clean(self):
        if not self.check_preconditions():
            if ADDON.getSetting('clean_schedule_type') == 'On Schedule':
                self.next_run_clean = time.time() + 60
            return

        try:
            logger.log("Starting Clean-up")
            logger.notify("NFO Sync", "Cleaning Library", xbmcgui.NOTIFICATION_INFO)
            start_time = time.time()

            xbmc.executebuiltin('CleanLibrary(video)')
            self.wait_for_scan()

            set_last_run('last_run_clean', start_time)
            logger.log("Clean-up Completed")
            logger.notify("NFO Sync", "Clean-up Completed", xbmcgui.NOTIFICATION_INFO)

        finally:
            self.release_lock()
            self.update_schedule()

    def refresh_library(self):
        logger.log("Starting Library Refresh (JSON-RPC) - Smart Mode")

        BATCH_SIZE = 5000
        last_run = get_last_run('last_run_import')

        use_smart_sync = ADDON.getSettingBool('import_smart_sync')
        logger.log(f"Smart Sync Enabled: {use_smart_sync}")

        if use_smart_sync:
            # We are using a 2h buffer is logic from before? The code view didn't show 2h buffer calc invalidating timestamp
            # But the log message said "with 2h safety buffer".
            # Actually I should trust the code I read.
            # The previous code was: `if mtime > last_run:`
            # It didn't modify last_run. The log message just said it.
            # I will keep it simple: strict check.
            logger.log(f"Checking for NFOs modified since timestamp: {last_run}")
        else:
            logger.log("Smart Sync disabled. Forcing refresh of ALL items.")

        # Refresh Movies
        movies = json_rpc('VideoLibrary.GetMovies', {'properties': ['file']})
        if 'result' in movies and 'movies' in movies['result']:
            batch = []
            total = len(movies['result']['movies'])
            skipped = 0

            logger.log(f"Analyzing {total} movies for changes...")

            for i, movie in enumerate(movies['result']['movies']):
                if self.abortRequested(): break

                # Smart Sync Check
                if use_smart_sync and last_run > 0:
                    if not self.should_refresh(movie['file'], last_run):
                        skipped += 1
                        continue

                movie_id = movie['movieid']
                logger.log(f"Queuing refresh for: {movie['label']}")
                batch.append({
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.RefreshMovie',
                    'params': {'movieid': movie_id, 'ignorenfo': False},
                    'id': i
                })

                if len(batch) >= BATCH_SIZE:
                    logger.log(f"Sending batch of {len(batch)} movies...")
                    json_rpc_batch(batch)
                    batch = []

            if batch:
                logger.log(f"Sending remaining batch of {len(batch)} movies...")
                json_rpc_batch(batch)

            logger.log(f"=== Movies Report: Total {total}, Refreshed {total - skipped}, Skipped {skipped} ===")

        # Refresh TV Shows
        shows = json_rpc('VideoLibrary.GetTVShows', {'properties': ['file']})
        if 'result' in shows and 'tvshows' in shows['result']:
            batch = []
            total = len(shows['result']['tvshows'])
            skipped = 0

            logger.log(f"Analyzing {total} TV Shows for changes...")

            for i, show in enumerate(shows['result']['tvshows']):
                if self.abortRequested(): break

                 # Smart Sync Check
                if use_smart_sync and last_run > 0:
                    if not self.should_refresh(show['file'], last_run):
                        skipped += 1
                        continue

                tvshow_id = show['tvshowid']
                logger.log(f"Queuing refresh for: {show['label']}")
                batch.append({
                    'jsonrpc': '2.0',
                    'method': 'VideoLibrary.RefreshTVShow',
                    'params': {'tvshowid': tvshow_id, 'ignorenfo': False},
                    'id': i
                })

                if len(batch) >= BATCH_SIZE:
                    logger.log(f"Sending batch of {len(batch)} TV Shows...")
                    json_rpc_batch(batch)
                    batch = []

            if batch:
                logger.log(f"Sending remaining batch of {len(batch)} TV Shows...")
                json_rpc_batch(batch)

            logger.log(f"=== TV Shows Report: Total {total}, Refreshed {total - skipped}, Skipped {skipped} ===")

        # Allow basic scan for new items as well
        if not self.abortRequested():
            logger.log("Triggering final UpdateLibrary scan for new files...")
            xbmc.executebuiltin('UpdateLibrary(video)')
            self.wait_for_scan()

    def run(self):
        logger.log("Service Started")

        # Check and run Sync on Startup (IMPORT ONLY)
        if ADDON.getSettingBool('import_enabled') and ADDON.getSettingBool('import_on_startup'):
            logger.log("Import on Startup Enabled. Waiting 30s for system to settle...")
            if not self.waitForAbort(30):
                logger.log("Triggering Startup Import...")
                self.run_import()

        while not self.abortRequested():
            now = time.time()

            # Check Import
            if self.next_run_import > 0 and now >= self.next_run_import:
                self.run_import()
                now = time.time()

            # Check Export
            if self.next_run_export > 0 and now >= self.next_run_export:
                self.run_export()
                now = time.time()

            # Check Clean
            if self.next_run_clean > 0 and now >= self.next_run_clean:
                self.run_clean()

            # Check every 10 seconds
            if self.waitForAbort(10):
                break

if __name__ == '__main__':
    service = NFOSyncService()
    service.run()
