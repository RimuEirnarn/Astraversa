"""Assets loader"""

from os.path import join
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

assets = Path(str(files("astraversa").joinpath("assets"))).resolve()
resources = Path(str(files('astraversa').joinpath('resources'))).resolve()

class SchemeNotFound(Exception):
    """Scheme not found"""

class AssetsManager:
    def __init__(self) -> None:
        self._cache: dict[str, Path] = {}
        self._definitions: dict[str, Path] = {"res": Path("resources"), "assets": Path("assets"), "astra-res": resources, "astra-assets": assets}
    
    def _resolve(self, uri: str):
        if uri in self._cache:
            return self._cache[uri]
        url_data = urlsplit(uri, allow_fragments=False)
        scheme = url_data.scheme
        if not url_data.scheme in self._definitions:
            err = SchemeNotFound(f"Namespace {scheme} does not exists.")
            err.add_note(f"Hint: Use Assets.define('{scheme}', '/path/to/dir')")
            raise err
        if url_data.netloc:
            file = join(url_data.netloc, url_data.path)
        else:
            file = url_data.path.lstrip("/")
        root = self._definitions[scheme]
        converged = (root / file).resolve()
        if not converged.is_relative_to(root.resolve()):
            raise ValueError("Path traversal is not allowed")
        self._cache[uri] = converged
        return converged

    def get(self, uri: str):
        """Retrieve assets/resources"""
        return self._resolve(uri)
    
    def define(self, scheme: str, path: Path):
        """Define a new scheme"""
        if not scheme in self._definitions:
            self._definitions[scheme] = path
            return
        for key in self._definitions.copy().keys():
            if key.startswith(scheme):
                del self._definitions[key]

Assets = AssetsManager()

__all__ = ['Assets']