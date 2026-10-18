import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.app import _cors_origins
from api.routers.files import _safe_upload_name
from config import SECRET_MASK, merge_config_update, redact_config
from path_security import resolve_allowed_local_file, resolve_media_reference


def _can_create_symlinks() -> bool:
    """探测当前环境能否创建符号链接（Windows 普通用户默认不行）。"""
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            target = base / "t.txt"
            target.write_text("x", encoding="utf-8")
            (base / "l.txt").symlink_to(target)
        return True
    except (OSError, NotImplementedError):
        return False


class ConfigSecurityTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "server": {"host": "127.0.0.1", "port": 8000},
            "api_providers": {
                "openai": {"api_key": "real-secret", "base_url": "https://example.com"},
                "gemini": {"api_key": ""},
                "deepseek": {"api_key": ""},
                "dashscope": {"api_key": ""},
                "ark": {"api_key": ""},
                "kling": {"access_key": "", "secret_key": ""},
            },
        }

    def test_public_config_never_contains_secret(self):
        public = redact_config(self.config)

        self.assertEqual(public["api_providers"]["openai"]["api_key"], SECRET_MASK)
        self.assertNotIn("real-secret", repr(public))

    def test_masked_secret_is_preserved_during_update(self):
        merged = merge_config_update(
            self.config,
            {
                "server": {"port": 9000},
                "api_providers": {"openai": {"api_key": SECRET_MASK}},
            },
        )

        self.assertEqual(merged["server"]["port"], 9000)
        self.assertEqual(merged["api_providers"]["openai"]["api_key"], "real-secret")

    def test_explicit_empty_secret_clears_value(self):
        merged = merge_config_update(
            self.config,
            {"api_providers": {"openai": {"api_key": ""}}},
        )

        self.assertEqual(merged["api_providers"]["openai"]["api_key"], "")


class PathSecurityTests(unittest.TestCase):
    def test_local_file_must_stay_under_allowed_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            allowed = parent / "uploads"
            allowed.mkdir()
            uploaded = allowed / "input.md"
            uploaded.write_text("ok", encoding="utf-8")
            outside = parent / "outside.md"
            outside.write_text("secret", encoding="utf-8")

            self.assertEqual(
                resolve_allowed_local_file("input.md", [str(allowed)]),
                str(uploaded.resolve()),
            )
            with self.assertRaises(ValueError):
                resolve_allowed_local_file("../outside.md", [str(allowed)])

    @unittest.skipUnless(
        _can_create_symlinks(),
        "需要创建符号链接的权限（Windows 需开发者模式或管理员）",
    )
    def test_symlink_pointing_outside_root_is_rejected(self):
        """指向允许目录之外的符号链接必须被拒绝。

        单独成例并加 skip 条件：Windows 默认不允许普通用户创建符号链接
        （WinError 1314），这属于环境限制，不应让整个测试套件报错。
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            allowed = base / "uploads"
            allowed.mkdir()
            outside = base / "outside.md"
            outside.write_text("secret", encoding="utf-8")

            link = allowed / "outside-link.md"
            link.symlink_to(outside)
            with self.assertRaises(ValueError):
                resolve_allowed_local_file(str(link), [str(allowed)])

    def test_media_reference_rejects_file_uri(self):
        with self.assertRaises(ValueError):
            resolve_media_reference("file:///tmp/private.png", ["/tmp"])

    def test_media_reference_allows_http_url(self):
        url = "https://cdn.example.com/input.png"
        self.assertEqual(resolve_media_reference(url, ["/tmp"]), url)

    def test_upload_name_drops_client_directories(self):
        safe_name = _safe_upload_name("../../private/input.pdf")

        self.assertEqual(Path(safe_name).name, safe_name)
        self.assertTrue(safe_name.endswith("_input.pdf"))


class CorsSecurityTests(unittest.TestCase):
    def test_cors_env_only_accepts_http_origins(self):
        with patch.dict(
            "os.environ",
            {
                "XYQ_CORS_ORIGINS": (
                    "https://studio.example.com/,*,file:///tmp/index.html,"
                    "https://studio.example.com/path"
                )
            },
        ):
            origins = _cors_origins()

        self.assertIn("https://studio.example.com", origins)
        self.assertNotIn("*", origins)
        self.assertNotIn("file:///tmp/index.html", origins)
        self.assertNotIn("https://studio.example.com/path", origins)


if __name__ == "__main__":
    unittest.main()
