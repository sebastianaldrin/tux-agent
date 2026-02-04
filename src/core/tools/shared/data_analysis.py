"""
Data Analysis Tools
JSON analysis, hash calculation, encoding/decoding, compression
"""
import logging
import json
import hashlib
import base64
import gzip
import zipfile
from typing import Dict, Any
from pathlib import Path

from ..base import resolve_path, DEFAULT_WORKSPACE

logger = logging.getLogger(__name__)


def json_analyzer(json_data: str) -> Dict[str, Any]:
    """Analyze and format JSON data"""
    try:
        if not json_data:
            return {'success': False, 'output': "❌ JSON data required"}
        
        # Parse JSON
        parsed = json.loads(json_data)
        
        # Format and analyze
        formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
        
        # Count elements
        def count_elements(obj, path=""):
            count = 0
            if isinstance(obj, dict):
                count += len(obj)
                for key, value in obj.items():
                    count += count_elements(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                count += len(obj)
                for i, item in enumerate(obj):
                    count += count_elements(item, f"{path}[{i}]" if path else f"[{i}]")
            return count
        
        total_elements = count_elements(parsed)
        
        output = f"📊 JSON Analysis:\n"
        output += f"• Total elements: {total_elements}\n"
        output += f"• Root type: {type(parsed).__name__}\n"
        output += f"• Size: {len(json_data)} characters\n\n"
        output += f"Formatted JSON:\n{formatted[:1000]}{'...' if len(formatted) > 1000 else ''}"
        
        return {
            'success': True,
            'output': output,
            'total_elements': total_elements,
            'root_type': type(parsed).__name__,
            'formatted': formatted
        }
        
    except json.JSONDecodeError as e:
        return {'success': False, 'output': f"❌ Invalid JSON: {str(e)} - check JSON syntax"}
    except Exception as e:
        return {'success': False, 'output': f"❌ JSON analysis failed: {str(e)} - unable to process JSON data"}


def hash_calculator(text: str, algorithm: str = "md5") -> Dict[str, Any]:
    """Calculate hashes of text"""
    try:
        if not text:
            return {'success': False, 'output': "❌ Text required"}
        
        algorithm = algorithm.lower()
        
        # Supported algorithms
        if algorithm == "md5":
            hash_obj = hashlib.md5()
        elif algorithm == "sha1":
            hash_obj = hashlib.sha1()
        elif algorithm == "sha256":
            hash_obj = hashlib.sha256()
        elif algorithm == "sha512":
            hash_obj = hashlib.sha512()
        else:
            return {'success': False, 'output': f"❌ Unsupported algorithm '{algorithm}' - use md5, sha1, sha256, or sha512"}
        
        # Calculate hash
        hash_obj.update(text.encode('utf-8'))
        hash_value = hash_obj.hexdigest()
        
        output = f"🔢 Hash Calculation:\n"
        output += f"• Algorithm: {algorithm.upper()}\n"
        output += f"• Input length: {len(text)} characters\n"
        output += f"• Hash: {hash_value}"
        
        return {
            'success': True,
            'output': output,
            'algorithm': algorithm,
            'hash': hash_value,
            'input_length': len(text)
        }
        
    except Exception as e:
        return {'success': False, 'output': f"❌ Hash calculation failed: {str(e)} - unable to calculate hash"}


def base64_encode(text: str, decode: str = "false") -> Dict[str, Any]:
    """Encode/decode base64"""
    try:
        if not text:
            return {'success': False, 'output': "❌ Text required"}
        
        is_decode = decode.lower() in ['true', '1', 'yes', 'decode']
        
        if is_decode:
            # Decode base64
            try:
                decoded_bytes = base64.b64decode(text)
                decoded_text = decoded_bytes.decode('utf-8')
                
                output = f"🔓 Base64 Decode:\n"
                output += f"• Input: {text[:100]}{'...' if len(text) > 100 else ''}\n"
                output += f"• Decoded: {decoded_text}"
                
                return {
                    'success': True,
                    'output': output,
                    'operation': 'decode',
                    'result': decoded_text
                }
                
            except Exception as e:
                return {'success': False, 'output': f"❌ Base64 decode failed: invalid base64 input - {str(e)}"}
        else:
            # Encode base64
            encoded_bytes = base64.b64encode(text.encode('utf-8'))
            encoded_text = encoded_bytes.decode('utf-8')
            
            output = f"🔒 Base64 Encode:\n"
            output += f"• Input: {text[:100]}{'...' if len(text) > 100 else ''}\n"
            output += f"• Encoded: {encoded_text}"
            
            return {
                'success': True,
                'output': output,
                'operation': 'encode',
                'result': encoded_text
            }
            
    except Exception as e:
        return {'success': False, 'output': f"❌ Base64 operation failed: {str(e)} - unable to process text"}


def compress_file(file_path: str, method: str = "gzip", workspace: Path = DEFAULT_WORKSPACE) -> Dict[str, Any]:
    """Compress files"""
    try:
        if not file_path:
            return {'success': False, 'output': "❌ File path required"}
        
        # Secure file path
        resolved_path = resolve_path(file_path, workspace)
        if not resolved_path.exists():
            return {'success': False, 'output': f"❌ File not found: {file_path}"}
        
        method = method.lower()
        
        if method == "gzip":
            output_path = resolved_path.with_suffix(resolved_path.suffix + '.gz')
            
            with open(resolved_path, 'rb') as f_in:
                with gzip.open(output_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            original_size = resolved_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            output = f"🗁️ File Compression (gzip):\n"
            output += f"• Original: {file_path} ({original_size} bytes)\n"
            output += f"• Compressed: {output_path.name} ({compressed_size} bytes)\n"
            output += f"• Compression ratio: {ratio:.1f}%"
            
            return {
                'success': True,
                'output': output,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': ratio,
                'output_file': str(output_path)
            }
        
        elif method == "zip":
            output_path = resolved_path.with_suffix('.zip')
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(resolved_path, resolved_path.name)
            
            original_size = resolved_path.stat().st_size
            compressed_size = output_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            output = f"🗁️ File Compression (zip):\n"
            output += f"• Original: {file_path} ({original_size} bytes)\n"
            output += f"• Compressed: {output_path.name} ({compressed_size} bytes)\n"
            output += f"• Compression ratio: {ratio:.1f}%"
            
            return {
                'success': True,
                'output': output,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': ratio,
                'output_file': str(output_path)
            }
        
        else:
            return {'success': False, 'output': f"❌ Unsupported compression method '{method}' - use 'gzip' or 'zip'"}
            
    except PermissionError:
        return {'success': False, 'output': f"❌ Permission denied compressing '{file_path}' - insufficient privileges"}
    except Exception as e:
        return {'success': False, 'output': f"❌ Compression failed for '{file_path}': {str(e)} - unable to compress file"}
