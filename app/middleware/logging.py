import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from ..core.logging import get_logger, request_id_var


# TODO: What other logging features to add, ignore routers, query params, etc.
class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request_id_var.set(request_id)

        client_host = request.client.host if request.client else "unknown"
        self.logger.info(
            "%s %s | client: %s", request.method, request.url.path, client_host
        )

        try:
            response = await call_next(request)
            return response

        except Exception as e:
            self.logger.exception(
                "%s %s | error: %s", request.method, request.url.path, str(e)
            )
            raise


# Just a note for other features to add, delete at some point.
# class LoggingMiddleware(BaseHTTPMiddleware):
#     """
#     Middleware that logs all HTTP requests and responses.
#     """
#
#     def __init__(self, app):
#         super().__init__(app)
#         self.logger = get_logger(__name__)
#         self.skip_paths = {"/health", "/"}
#
#     async def dispatch(self, request: Request, call_next):
#         # Generate and set request ID
#         request_id = str(uuid.uuid4())[:8]
#         request_id_var.set(request_id)
#
#         # Skip logging for certain endpoints
#         if request.url.path in self.skip_paths:
#             response = await call_next(request)
#             response.headers["X-Request-ID"] = request_id
#             return response
#
#         # Log incoming request
#         client_host = request.client.host if request.client else "unknown"
#         self.logger.info(
#             f"→ {request.method} {request.url.path} | "
#             f"client: {client_host}"
#         )
#
#         # Start timing
#         start_time = time.time()
#
#         # Process request
#         try:
#             response = await call_next(request)
#             duration = time.time() - start_time
#
#             # Log response with appropriate level
#             if response.status_code >= 500:
#                 self.logger.error(
#                     f"← {request.method} {request.url.path} | "
#                     f"status: {response.status_code} | "
#                     f"duration: {duration:.3f}s"
#                 )
#             elif response.status_code >= 400:
#                 self.logger.warning(
#                     f"← {request.method} {request.url.path} | "
#                     f"status: {response.status_code} | "
#                     f"duration: {duration:.3f}s"
#                 )
#             else:
#                 self.logger.info(
#                     f"← {request.method} {request.url.path} | "
#                     f"status: {response.status_code} | "
#                     f"duration: {duration:.3f}s"
#                 )
#
#             # Add request ID to headers
#             response.headers["X-Request-ID"] = request_id
#
#             return response
#
#         except Exception as e:
#             duration = time.time() - start_time
#             self.logger.exception(
#                 f"✗ {request.method} {request.url.path} | "
#                 f"error: {str(e)} | "
#                 f"duration: {duration:.3f}s"
#             )
#             raise
