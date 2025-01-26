class SmartGlassesException(Exception):
    """Base exception for Smart Glasses project"""
    pass

class CameraError(SmartGlassesException):
    """Raised when there are issues with camera operations"""
    pass

class AudioError(SmartGlassesException):
    """Raised when there are issues with audio operations"""
    pass

class TokenError(SmartGlassesException):
    """Raised when there are issues with authentication tokens"""
    pass

class APIError(SmartGlassesException):
    """Raised when there are issues with external API calls"""
    pass

class GestureError(SmartGlassesException):
    """Raised when there are issues with gesture detection"""
    pass