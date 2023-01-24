import json
from json import JSONDecodeError


def response(success: bool = True, message: str or None = None, *, data: list or None = None) -> json or str:
    var: dict = {
        'success': success,
        'message': message,
        'data': data
    }
    try:
        return json.dumps(var)
    except JSONDecodeError:
        return f'Response could not be serialized'
