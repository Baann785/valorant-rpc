import ast
import unittest
from pathlib import Path


class RuntimeAssetTests(unittest.TestCase):
    def test_runtime_does_not_reference_old_local_asset_keys(self):
        old_prefixes = ("agent_", "rank_", "splash_", "mode_", "game_icon")

        for path in Path("src").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertFalse(
                        node.value.startswith(old_prefixes),
                        f"{path} still references old local Discord asset key {node.value!r}",
                    )
