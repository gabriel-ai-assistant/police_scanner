"""
Tests for bug fixes in app_transcribe.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── BUG-006: transcribe_audio must use os.getenv for DB config ───

class TestBUG006NoBardcodedCreds:
    """DB config in transcribe_audio must come from environment variables,
    not hardcoded values."""

    def test_db_config_uses_getenv(self):
        """The DB dict should use os.getenv for host, dbname, user, password."""
        # Read source as text to avoid import side effects (WhisperModel, boto3)
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        # Parse the AST to find the DB dict assignment
        tree = __import__("ast").parse(source)
        for node in __import__("ast").walk(tree):
            if isinstance(node, __import__("ast").Assign):
                for target in node.targets:
                    if isinstance(target, __import__("ast").Name) and target.id == "DB" and isinstance(node.value, __import__("ast").Dict):
                        # Check that values use os.getenv, not string literals
                        for key, val in zip(node.value.keys, node.value.values, strict=False):
                            key_str = key.value if isinstance(key, __import__("ast").Constant) else None
                            if key_str in ("host", "dbname", "user", "password"):
                                # Value should be a Call to os.getenv, not a plain Constant
                                assert not isinstance(val, __import__("ast").Constant), \
                                    f"DB['{key_str}'] is hardcoded as '{val.value}', should use os.getenv()"

    def test_db_port_uses_getenv(self):
        """DB port should also use os.getenv, not be hardcoded."""
        source_path = os.path.join(os.path.dirname(__file__), "..", "transcribe_audio.py")
        with open(source_path) as f:
            source = f.read()

        import ast as ast_mod
        tree = ast_mod.parse(source)
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Assign):
                for target in node.targets:
                    if isinstance(target, ast_mod.Name) and target.id == "DB" and isinstance(node.value, ast_mod.Dict):
                        for key, val in zip(node.value.keys, node.value.values, strict=False):
                            key_str = key.value if isinstance(key, ast_mod.Constant) else None
                            if key_str == "port":
                                assert not isinstance(val, ast_mod.Constant), \
                                    f"DB['port'] is hardcoded as '{val.value}', should use os.getenv()"
