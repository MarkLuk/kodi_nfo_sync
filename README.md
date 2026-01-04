# NFO Sync for Kodi

**NFO Sync** is a Kodi Program Add-on designed to keep your library in sync with your local `.nfo` files. It supports automatic exporting, importing, and cleaning of your library based on configurable schedules.

## Features

-   **Two-Way Synchronization**:
    -   **Export**: Export your Kodi library to `.nfo` files, overwriting existing files. Useful for backing up your library or syncing changes to other Kodi instances.
    -   **Import**: Import data from `.nfo` files into your Kodi library. Supports Movies, TV Shows, and Music Videos.
-   **Preserve Watched Status**: Option to preserve your current watched status (play count, resume point, last played) during an import, even if the NFO file says otherwise.
-   **Smart Sync**: When importing, the addon can check file modification times (`mtime`) to only refresh items that have changed since the last run, significantly speeding up the process.
-   **Automated Scheduling**:
    -   **Import Interval**: Run imports automatically every X hours.
    -   **Export Interval**: Run exports automatically every X hours.
    -   **Clean Interval**: Run library clean-ups automatically or immediately after an import.
-   **Startup Sync**: Option to trigger an import automatically when Kodi starts.
-   **Configuration**: All schedules and options are fully configurable via the addon settings.

## Usage / Sync Options

The addon provides three main manual operations:

1.  **Export Library**
    *   Exports the current Kodi library to `.nfo` files.
    *   **Note**: This overwrites existing `.nfo` files with the data currently in your library.

2.  **Import (Scan New)**
    *   Scans for *new* files and `.nfo` files that are not yet in the library.
    *   Does not overwrite existing library information.

3.  **Import (Force Refresh)**
    *   Imports `.nfo` files to the Kodi library.
    *   **Smart Sync**: If enabled in settings, this will only refresh items where the NFO file has changed.
    *   If Smart Sync is disabled, this will force a refresh of *all* items in the library (useful for external tools like [Tiny Media Manager](https://www.tinymediamanager.org/)).

## Configuration

Go to **Add-on Settings** to configure:

*   **General**: Enable/Disable notifications.
*   **Import**: Enable scheduling, set interval, enable "Smart Sync", and toggle "Run on Startup".
*   **Export**: Enable scheduling and set interval.
*   **Clean**: Enable scheduling or set to run "After Import".

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
