import json
from collections.abc import Mapping, Sequence

def sanitize_for_json(obj):
    """Recursively convert non-JSON-serializable objects to primitives.

    - dict-like and list-like structures are walked.
    - Objects with a `content` attribute (LangChain messages) are replaced with their `.content`.
    - Other unknown objects are converted with `str()`.
    """
    # Primitive types
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Mapping (dict-like)
    if isinstance(obj, Mapping):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}

    # Sequence (list/tuple) but not string
    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        return [sanitize_for_json(v) for v in obj]

    # LangChain-like message objects have `content`
    if hasattr(obj, "content"):
        try:
            return sanitize_for_json(getattr(obj, "content"))
        except Exception:
            return str(obj)

    # Fallback: try to json.dumps, else str()
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)
