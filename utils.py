import zlib
import base64
from typing import Tuple

def compress_string(text: str) -> Tuple[str, int, int, float]:
    """
    Compress a string using zlib compression
    
    Returns:
        Tuple of (compressed_data_base64, original_size, compressed_size, compression_ratio)
    """
    original_bytes = text.encode('utf-8')
    original_size = len(original_bytes)
    
    # Compress the data
    compressed_bytes = zlib.compress(original_bytes)
    compressed_size = len(compressed_bytes)
    
    # Encode to base64 for safe transport
    compressed_data = base64.b64encode(compressed_bytes).decode('utf-8')
    
    # Calculate compression ratio
    compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
    
    return compressed_data, original_size, compressed_size, compression_ratio

def decompress_string(compressed_data: str) -> str:
    """
    Decompress a base64-encoded compressed string
    
    Args:
        compressed_data: Base64-encoded compressed string
        
    Returns:
        Original decompressed string
    """
    # Decode from base64
    compressed_bytes = base64.b64decode(compressed_data)
    
    # Decompress
    decompressed_bytes = zlib.decompress(compressed_bytes)
    decompressed_text = decompressed_bytes.decode('utf-8')
    
    return decompressed_text

def validate_csv_structure(df, required_columns):
    """
    Validate that a DataFrame has the required columns
    
    Args:
        df: pandas DataFrame
        required_columns: List of required column names
        
    Returns:
        bool: True if valid, raises exception if not
    """
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    return True
