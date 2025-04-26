import time
import pytest
import logging
from pathlib import Path
from watchdog.observers import Observer
from filesystem_manager.file_observer import FileSystemObserver


@pytest.fixture(scope="function")
def test_folder(tmp_path) -> Path:
    """create a tmp folder for testing"""
    return tmp_path


@pytest.fixture(scope="function")
def file_observer(test_folder):
    file_sys_observer = FileSystemObserver(str(test_folder))
    observer = Observer()
    observer.schedule(
        file_sys_observer, path=file_sys_observer.watched_folder, recursive=True
    )
    observer.start()
    time.sleep(1)
    yield file_sys_observer
    observer.stop()
    observer.join()


def create_file(test_folder, filename, content=""):
    """建立檔案"""
    file_path = test_folder / filename
    file_path.write_text(content, encoding="utf-8")
    time.sleep(1)  # 等待事件觸發
    return file_path


def modify_file(file_path, new_content):
    """修改檔案內容"""
    file_path.write_text(new_content, encoding="utf-8")
    time.sleep(1)


def delete_file(file_path):
    """刪除檔案"""
    file_path.unlink()
    time.sleep(1)


def rename_file(file_path, new_name):
    """重新命名檔案"""
    new_path = file_path.parent / new_name
    file_path.rename(new_path)
    time.sleep(1)
    return new_path


def test_create_txt_file(file_observer, test_folder, caplog):
    caplog.set_level(logging.INFO)
    file_path = create_file(test_folder, "test.txt")
    assert any(f"Create {file_path}" in record.message for record in caplog.records)


def test_rename_txt_file(file_observer, test_folder, caplog):
    caplog.set_level(logging.INFO)
    file_path = create_file(test_folder, "rename_me.txt")
    new_file_path = rename_file(file_path, "renamed.txt")
    assert new_file_path.exists()
    assert not file_path.exists()
    assert any(
        f"Rename {file_path} to {new_file_path}" in record.message
        for record in caplog.records
    )


def test_modify_txt_file(file_observer, test_folder, caplog):
    caplog.set_level(logging.INFO)
    file_path = create_file(test_folder, "modify.txt")
    modify_file(file_path, "New content.")
    assert file_path.read_text(encoding="utf-8") == "New content."
    assert any(f"Modified {file_path}" in record.message for record in caplog.records)


def test_delete_txt_file(file_observer, test_folder, caplog):
    caplog.set_level(logging.INFO)
    file_path = create_file(test_folder, "delete_me.txt", "Temporary file.")
    delete_file(file_path)
    assert not file_path.exists()
    assert any(f"Deleted {file_path}" in record.message for record in caplog.records)
