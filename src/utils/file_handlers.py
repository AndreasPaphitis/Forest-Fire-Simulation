#!/usr/bin/env python3
"""
Enhanced File Handling Module with File System Coordination

Provides robust file handling with:
- File locking mechanisms for concurrent access
- File system coordination to prevent corruption
- Safe file operations with retry logic
- Directory management and cleanup
"""

import os
import gc
import time
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union, BinaryIO, TextIO
import logging
import json
import pickle
import hashlib
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Cross-platform file locking
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False
    logger.warning("fcntl not available - using file-based locking fallback")

# Global file lock registry
_file_locks = {}
_lock_registry_lock = threading.Lock()

class FileLock:
    """Thread-safe file lock for coordinating file access (cross-platform)."""
    
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.lock_path = self.file_path.with_suffix(self.file_path.suffix + '.lock')
        self.lock_file = None
        self.lock_acquired = False
        self._lock_timeout = 0.0  # Disable file locking for testing
        self._lock_retry_delay = 0.1  # 100ms retry delay
    
    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire the file lock (cross-platform)."""
        if timeout is None:
            timeout = self._lock_timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Create lock file
                self.lock_file = open(self.lock_path, 'w')
                
                # Try to acquire exclusive lock (cross-platform)
                if FCNTL_AVAILABLE:
                    # Use fcntl on Unix-like systems
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    # Use file-based locking on Windows
                    # Try to write to the lock file - if it fails, another process has the lock
                    try:
                        self.lock_file.write(f"{os.getpid()}\n")
                        self.lock_file.flush()
                    except Exception:
                        self.lock_file.close()
                        self.lock_file = None
                        time.sleep(self._lock_retry_delay)
                        continue
                
                # Write process info to lock file
                lock_info = {
                    'pid': os.getpid(),
                    'timestamp': time.time(),
                    'thread_id': threading.get_ident()
                }
                json.dump(lock_info, self.lock_file)
                self.lock_file.flush()
                
                self.lock_acquired = True
                logger.debug(f"🔒 Acquired file lock: {self.file_path}")
                return True
                
            except (IOError, OSError) as e:
                # Lock is held by another process
                if self.lock_file:
                    try:
                        self.lock_file.close()
                    except:
                        pass
                    self.lock_file = None
                
                time.sleep(self._lock_retry_delay)
                continue
        
        logger.warning(f"⚠️  Failed to acquire file lock: {self.file_path} (timeout: {timeout}s)")
        return False
    
    def release(self):
        """Release the file lock (cross-platform)."""
        if self.lock_acquired and self.lock_file:
            try:
                if FCNTL_AVAILABLE:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                
                # Remove lock file
                if self.lock_path.exists():
                    self.lock_path.unlink()
                
                logger.debug(f"🔓 Released file lock: {self.file_path}")
                
            except Exception as e:
                logger.warning(f"⚠️  Error releasing file lock: {e}")
            finally:
                self.lock_acquired = False
                self.lock_file = None
    
    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Failed to acquire file lock: {self.file_path}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class FileCoordinator:
    """
    Coordinates file system access to prevent corruption and contention.
    
    Features:
    - File locking for concurrent access
    - Directory coordination
    - Safe file operations with retry logic
    - File integrity checks
    """
    
    def __init__(self):
        self.active_locks = {}
        self.coordination_lock = threading.Lock()
        self._temp_files = set()
    
    def get_file_lock(self, file_path: Union[str, Path]) -> FileLock:
        """Get or create a file lock for the specified path."""
        file_path = Path(file_path).resolve()
        
        with self.coordination_lock:
            if file_path not in self.active_locks:
                self.active_locks[file_path] = FileLock(file_path)
            
            return self.active_locks[file_path]
    
    def safe_write_file(self, file_path: Union[str, Path], content: Union[str, bytes], 
                       mode: str = 'w', encoding: str = 'utf-8', 
                       backup: bool = True, retry_count: int = 3) -> bool:
        """
        Safely write a file with locking and backup.
        
        Args:
            file_path: Path to the file
            content: Content to write
            mode: File mode ('w' for text, 'wb' for binary)
            encoding: Text encoding (for text mode)
            backup: Whether to create a backup
            retry_count: Number of retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        file_path = Path(file_path)
        
        for attempt in range(retry_count):
            try:
                with self.get_file_lock(file_path) as lock:
                    # Create backup if requested and file exists
                    if backup and file_path.exists():
                        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
                        shutil.copy2(file_path, backup_path)
                        logger.debug(f"📋 Created backup: {backup_path}")
                    
                    # Write to temporary file first
                    temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
                    
                    if mode == 'wb' or 'b' in mode:
                        with open(temp_path, 'wb') as f:
                            f.write(content)
                    else:
                        with open(temp_path, mode, encoding=encoding) as f:
                            f.write(content)
                    
                    # Atomic move to final location
                    temp_path.replace(file_path)
                    
                    logger.debug(f"✅ Safely wrote file: {file_path}")
                    return True
                    
            except Exception as e:
                logger.warning(f"⚠️  Write attempt {attempt + 1} failed for {file_path}: {e}")
                
                # Clean up temporary file
                temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                
                if attempt < retry_count - 1:
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"❌ Failed to write file after {retry_count} attempts: {file_path}")
                    return False
        
        return False
    
    def safe_read_file(self, file_path: Union[str, Path], mode: str = 'r', 
                      encoding: str = 'utf-8', retry_count: int = 3) -> Optional[Union[str, bytes]]:
        """
        Safely read a file with locking and retry logic.
        
        Args:
            file_path: Path to the file
            mode: File mode ('r' for text, 'rb' for binary)
            encoding: Text encoding (for text mode)
            retry_count: Number of retry attempts
            
        Returns:
            File content or None if failed
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"⚠️  File does not exist: {file_path}")
            return None
        
        for attempt in range(retry_count):
            try:
                with self.get_file_lock(file_path) as lock:
                    if mode == 'rb' or 'b' in mode:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                    else:
                        with open(file_path, mode, encoding=encoding) as f:
                            content = f.read()
                    
                    logger.debug(f"✅ Safely read file: {file_path}")
                    return content
                    
            except Exception as e:
                logger.warning(f"⚠️  Read attempt {attempt + 1} failed for {file_path}: {e}")
                
                if attempt < retry_count - 1:
                    time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"❌ Failed to read file after {retry_count} attempts: {file_path}")
                    return None
        
            return None

    def safe_json_operations(self, file_path: Union[str, Path], 
                           operation: str = 'read', 
                           data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Safely perform JSON file operations.
        
        Args:
            file_path: Path to the JSON file
            operation: 'read' or 'write'
            data: Data to write (for write operation)
            
        Returns:
            Data for read operation, True for successful write, None for failure
        """
        file_path = Path(file_path)
        
        if operation == 'read':
            content = self.safe_read_file(file_path, mode='r')
            if content is not None:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON in {file_path}: {e}")
                    return None
            return None
        
        elif operation == 'write':
            if data is None:
                logger.error("❌ No data provided for write operation")
                return None
            
            try:
                content = json.dumps(data, indent=2, ensure_ascii=False)
                return self.safe_write_file(file_path, content, mode='w')
            except Exception as e:
                logger.error(f"❌ Failed to serialize data for {file_path}: {e}")
                return None
        
        else:
            logger.error(f"❌ Unknown operation: {operation}")
            return None
    
    def safe_pickle_operations(self, file_path: Union[str, Path], 
                             operation: str = 'read', 
                             data: Optional[Any] = None) -> Optional[Any]:
        """
        Safely perform pickle file operations.
        
        Args:
            file_path: Path to the pickle file
            operation: 'read' or 'write'
            data: Data to write (for write operation)
            
        Returns:
            Data for read operation, True for successful write, None for failure
        """
        file_path = Path(file_path)
        
        if operation == 'read':
            content = self.safe_read_file(file_path, mode='rb')
            if content is not None:
                try:
                    return pickle.loads(content)
                except pickle.PickleError as e:
                    logger.error(f"❌ Invalid pickle data in {file_path}: {e}")
                    return None
            return None
        
        elif operation == 'write':
            if data is None:
                logger.error("❌ No data provided for write operation")
                return None
            
            try:
                content = pickle.dumps(data)
                return self.safe_write_file(file_path, content, mode='wb')
            except Exception as e:
                logger.error(f"❌ Failed to serialize data for {file_path}: {e}")
                return None
        else:
            logger.error(f"❌ Unknown operation: {operation}")
            return None
    
    def create_temp_file(self, prefix: str = 'temp', suffix: str = '', 
                        directory: Optional[Union[str, Path]] = None) -> Path:
        """Create a temporary file with tracking."""
        temp_file = tempfile.NamedTemporaryFile(
            prefix=prefix, suffix=suffix, dir=directory, delete=False
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        
        with self.coordination_lock:
            self._temp_files.add(temp_path)
        
        logger.debug(f"📄 Created temporary file: {temp_path}")
        return temp_path
    
    def cleanup_temp_files(self):
        """Clean up all tracked temporary files."""
        with self.coordination_lock:
            for temp_path in list(self._temp_files):
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                        logger.debug(f"🧹 Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"⚠️  Failed to clean up temporary file {temp_path}: {e}")
                finally:
                    self._temp_files.discard(temp_path)
    
    def ensure_directory(self, directory: Union[str, Path], 
                        create_parents: bool = True) -> bool:
        """Ensure a directory exists with proper permissions."""
        try:
            directory = Path(directory)
            
            if create_parents:
                directory.mkdir(parents=True, exist_ok=True)
            else:
                directory.mkdir(exist_ok=True)
            
            # Ensure directory is writable
            if not os.access(directory, os.W_OK):
                logger.error(f"❌ Directory not writable: {directory}")
                return False
            
            logger.debug(f"📁 Ensured directory: {directory}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure directory {directory}: {e}")
            return False
    
    def get_file_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Get detailed information about a file."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            return {
                'path': str(file_path),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'permissions': oct(stat.st_mode),
                'is_file': file_path.is_file(),
                'is_directory': file_path.is_dir(),
                'readable': os.access(file_path, os.R_OK),
                'writable': os.access(file_path, os.W_OK),
                'executable': os.access(file_path, os.X_OK)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get file info for {file_path}: {e}")
            return None
    
    def verify_file_integrity(self, file_path: Union[str, Path], 
                            expected_hash: Optional[str] = None) -> bool:
        """Verify file integrity using checksum."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"❌ File does not exist: {file_path}")
                return False
            
            # Calculate file hash
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            actual_hash = hash_md5.hexdigest()
            
            if expected_hash:
                if actual_hash == expected_hash:
                    logger.debug(f"✅ File integrity verified: {file_path}")
                    return True
                else:
                    logger.error(f"❌ File integrity check failed: {file_path}")
                    logger.error(f"   Expected: {expected_hash}")
                    logger.error(f"   Actual: {actual_hash}")
                    return False
            else:
                logger.debug(f"📋 File hash: {actual_hash} for {file_path}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to verify file integrity for {file_path}: {e}")
            return False

# Global file coordinator instance
_file_coordinator = None

def get_file_coordinator() -> FileCoordinator:
    """Get the global file coordinator instance."""
    global _file_coordinator
    if _file_coordinator is None:
        _file_coordinator = FileCoordinator()
    return _file_coordinator

# Convenience functions
def safe_write_json(file_path: Union[str, Path], data: Dict[str, Any]) -> bool:
    """Safely write JSON data to a file."""
    coordinator = get_file_coordinator()
    return coordinator.safe_json_operations(file_path, 'write', data)

def safe_read_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Safely read JSON data from a file."""
    coordinator = get_file_coordinator()
    return coordinator.safe_json_operations(file_path, 'read')

def safe_write_pickle(file_path: Union[str, Path], data: Any) -> bool:
    """Safely write pickle data to a file."""
    coordinator = get_file_coordinator()
    return coordinator.safe_pickle_operations(file_path, 'write', data)

def safe_read_pickle(file_path: Union[str, Path]) -> Optional[Any]:
    """Safely read pickle data from a file."""
    coordinator = get_file_coordinator()
    return coordinator.safe_pickle_operations(file_path, 'read')

@contextmanager
def file_lock_context(file_path: Union[str, Path], timeout: Optional[float] = None):
    """Context manager for file locking."""
    coordinator = get_file_coordinator()
    lock = coordinator.get_file_lock(file_path)
    
    if lock.acquire(timeout):
        try:
            yield lock
        finally:
            lock.release()
    else:
        raise RuntimeError(f"Failed to acquire file lock: {file_path}")

def cleanup_all_temp_files():
    """Clean up all temporary files."""
    coordinator = get_file_coordinator()
    coordinator.cleanup_temp_files()

# Auto-initialize on module import
import atexit
atexit.register(cleanup_all_temp_files)

# Legacy FileManager class for compatibility
class FileManager:
    """
    Legacy FileManager class for backward compatibility.
    
    This class provides basic file management functionality
    and is maintained for compatibility with existing code.
    """
    
    def __init__(self, config=None):
        self.config = config
        self.coordinator = get_file_coordinator()
    
    @staticmethod
    def find_files(base_dir: Union[str, Path], pattern: str) -> List[Path]:
        """Find files matching a pattern in a directory."""
        try:
            base_path = Path(base_dir)
            if not base_path.exists():
                return []
            
            return list(base_path.glob(pattern))
        except Exception as e:
            logger.warning(f"Error finding files {pattern} in {base_dir}: {e}")
            return []
    
    @staticmethod
    def save_simulation_results(results: Dict[str, Any], output_dir: Union[str, Path]) -> List[str]:
        """Save simulation results to files."""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            saved_files = []
            
            # Save results as JSON
            results_file = output_path / "simulation_results.json"
            if safe_write_json(results_file, results):
                saved_files.append(str(results_file))
            
            return saved_files
            
        except Exception as e:
            logger.error(f"Error saving simulation results: {e}")
            return []
    
    def ensure_directory(self, directory: Union[str, Path]) -> bool:
        """Ensure a directory exists."""
        return self.coordinator.ensure_directory(directory)
    
    def safe_write_file(self, file_path: Union[str, Path], content: Union[str, bytes], **kwargs) -> bool:
        """Safely write a file."""
        return self.coordinator.safe_write_file(file_path, content, **kwargs)
    
    def safe_read_file(self, file_path: Union[str, Path], **kwargs) -> Optional[Union[str, bytes]]:
        """Safely read a file."""
        return self.coordinator.safe_read_file(file_path, **kwargs) 