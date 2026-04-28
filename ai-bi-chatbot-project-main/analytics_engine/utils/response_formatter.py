def success_response(data, insight=None):
    return{
        "status": "success",
        "data": data,
        "insight": insight
    }

def error_response(message):
    return{
        "status": "error",
        "message": message
    }