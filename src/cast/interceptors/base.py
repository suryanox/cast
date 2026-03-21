from __future__ import annotations


class BaseInterceptor:
    """Base class for all cast interceptors."""

    _patched: bool = False

    def patch(self):
        if not self._patched:
            self._apply_patch()
            self._patched = True

    def unpatch(self):
        if self._patched:
            self._remove_patch()
            self._patched = False

    def _apply_patch(self):
        raise NotImplementedError

    def _remove_patch(self):
        raise NotImplementedError