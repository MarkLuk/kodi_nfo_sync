import os
import xbmc
import xbmcaddon
import xbmcgui
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

def get_last_run():
    last_run_str = ADDON.getSetting('last_run')
    if not last_run_str:
        return 0
    try:
        return float(last_run_str)
    except:
        return 0

def set_last_run(timestamp):
    ADDON.setSetting('last_run', str(timestamp))

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
        self.next_run = 0
        self.interval = 24  # Default hours
        self.update_schedule()

    def update_schedule(self):
        self.interval = get_setting_int('sync_interval')
        last_run = get_last_run()
        if last_run == 0:
            # If never run, schedule for 1 minute from now to allow startup to settle
            self.next_run = time.time() + 60
        else:
            self.next_run = last_run + (self.interval * 3600)

        logger.log(f"Schedule updated. Interval: {self.interval}h. Next run: {datetime.fromtimestamp(self.next_run)}")

    def wait_for_scan(self):
        # Wait a moment for scan to potentially start
        count = 0
        while count < 5:
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

        # Check standard NFO naming: movie.nfo or video_name.nfo
        base, ext = os.path.splitext(file_path)
        candidates = [base + '.nfo', os.path.join(os.path.dirname(file_path), 'movie.nfo')]

        # Also handling tvshow.nfo for TV shows?
        candidates.append(os.path.join(file_path, 'tvshow.nfo'))

        for nfo_path in candidates:
            if os.path.exists(nfo_path):
                try:
                    mtime = os.path.getmtime(nfo_path)
                    # Debug log for checking timestamps
                    # logger.log(f"Checking {nfo_path}: mtime={mtime}, last_run={last_run}")
                    if mtime > last_run:
                        logger.log(f"DETECTED CHANGE: {nfo_path} (mtime {mtime} > last_run {last_run})")
                        return True
                except:
                    pass

        return False

    def run_sync(self):
        # Map labelenum strings to integers
        direction_str = ADDON.getSetting('sync_direction')
        direction = 0
        if direction_str == "Import (Scan New)":
            direction = 1
        elif direction_str == "Import (Force Refresh)":
            direction = 2

        logger.log(f"Starting Sync. Direction: {direction} ({direction_str})")
        logger.notify("NFO Sync", "Starting Sync", xbmcgui.NOTIFICATION_INFO)

        start_time = time.time()

        if direction == 0:  # Export Library
            # ExportLibrary(category, separate, overwrite, images, actorimgs)
            # We want: video, true (separate files), true (overwrite), true (images), true (actorimgs)
            xbmc.executebuiltin('ExportLibrary(video,true,true,true,true)')
            logger.log("Triggered ExportLibrary")

        elif direction == 1:  # Import (Scan)
            xbmc.executebuiltin('UpdateLibrary(video)')
            logger.log("Triggered UpdateLibrary (Scan)")
            self.wait_for_scan()

        elif direction == 2:  # Import (Force Refresh)
            self.refresh_library()

        set_last_run(start_time)
        self.update_schedule()
        logger.notify("NFO Sync", "Sync Completed", xbmcgui.NOTIFICATION_INFO)

    def refresh_library(self):
        logger.log("Starting Library Refresh (JSON-RPC) - Smart Mode")

        # Batch size 5000 to process effectively all-in-one-go
        BATCH_SIZE = 5000
        last_run = get_last_run()
        logger.log(f"Checking for NFOs modified since timestamp: {last_run}")

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
                if last_run > 0:
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
                if last_run > 0:
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

        # Allow basic scan for new items as well? Maybe not needed if ONLY refreshing.
        # But usually users want both. Let's trigger a scan at the end to catch NEW files.
        if not self.abortRequested():
            logger.log("Triggering final UpdateLibrary scan for new files...")
            xbmc.executebuiltin('UpdateLibrary(video)')
            self.wait_for_scan()

    def run(self):
        logger.log("Service Started")
        while not self.abortRequested():
            if time.time() >= self.next_run:
                self.run_sync()

            # Check every 10 seconds
            if self.waitForAbort(10):
                break

if __name__ == '__main__':
    service = NFOSyncService()
    service.run()
