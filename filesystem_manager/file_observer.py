from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
from functools import lru_cache
from pathlib import Path
import logging
#from file_database import FileDatabase
WATCHED_FOLDER = './mock_filesystem'

            
class FileSystemObserver(FileSystemEventHandler):
    def __init__(self, watched_folder):
        super().__init__()
        logger = logging.getLogger(__class__.__name__)
        logging.basicConfig(level=logging.DEBUG, encoding="utf-8")
        self.logger = logger
        self.watched_folder = watched_folder
        self.snapshot = DirectorySnapshot(self.watched_folder)
        #self.file_db = FileDatabase(name="file_db")
    
    def is_tmp_file(self, file_path) -> bool:
        file_name = Path(file_path).name
        return file_name.startswith("~")
    
    def on_any_event(self, event):
        super().on_any_event(event)
        new_snapshot = DirectorySnapshot(self.watched_folder)
        diff = DirectorySnapshotDiff(self.snapshot, new_snapshot)
        if(diff.files_created and not self.is_tmp_file(event.src_path)):
            self.logger.info("Create %s", event.src_path)
        elif(diff.files_moved and not self.is_tmp_file(event.src_path)):
            before_name, after_name = diff.files_moved[0]
            if(self.is_tmp_file(before_name)):
                self.logger.info("Modified %s", after_name)
            else:     
                self.logger.info("Rename %s to %s", before_name, after_name)
        elif(diff.files_deleted and not self.is_tmp_file(event.src_path)):
            self.logger.info("Deleted %s", event.src_path)
        elif(diff.files_modified) and not self.is_tmp_file(event.src_path):
            self.logger.info("Modified %s", event.src_path)
        
        self.snapshot = new_snapshot
    # def on_deleted(self, event):
    #     super().on_deleted(event)
    #     self.snapshot = DirectorySnapshot(self.watched_folder)
    #     self.logger.info("Deleted %s", event.src_path)
        
    # @lru_cache(maxsize=256)
    # def on_modified(self, event):
    #     super().on_modified(event)
    #     new_snapshot = DirectorySnapshot(self.watched_folder)
    #     diff = DirectorySnapshotDiff(self.snapshot, new_snapshot)
        
        # if(diff.files_created and not self.should_ignore(event)):
        #     self.logger.info("Create %s", event.src_path)
        # elif(diff.files_moved):
        #     before_name, after_name = diff.files_moved[0]
        #     self.logger.info("Rename %s to %s", before_name, after_name)
        # else:
        #     self.logger.info("Modified %s to %s", event.src_path)
        
    #     self.snapshot = new_snapshot

if __name__ == "__main__":
    file_sys_observer = FileSystemObserver(WATCHED_FOLDER)
    observer = Observer()
    observer.schedule(file_sys_observer, path=file_sys_observer.watched_folder, recursive=True)
    observer.start()
    
    try:
        while observer.is_alive():
                observer.join(1)
    finally:
        observer.stop()
        observer.join()