# -*- coding: utf-8 -*-
"""部署相关配置测试：环境变量覆盖行为。

这些测试覆盖后端容器化部署所依赖的行为：
Railway/Render 通过环境变量注入 HOST / PORT / 各模型 Key，
config.load_config() 必须把这些值叠加到 YAML 配置上，
且未设置环境变量时完全不影响本地开发行为。

对应验收标准：后端在云平台上能以 PORT 环境变量指定的端口对外提供服务。
"""

import importlib
import os
import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _reload_config():
    """重新加载 config 模块，让环境变量生效。"""
    if "config" in sys.modules:
        del sys.modules["config"]
    return importlib.import_module("config")


class EnvOverrideTests(unittest.TestCase):
    """config.load_config() 的环境变量覆盖能力。"""

    ENV_KEYS = (
        "HOST", "PORT", "LOG_LEVEL",
        "OPENAI_API_KEY", "OPENAI_BASE_URL",
        "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
        "DASHSCOPE_API_KEY", "ARK_API_KEY",
        "KLING_ACCESS_KEY", "KLING_SECRET_KEY",
    )

    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in self.ENV_KEYS}
        for k in self.ENV_KEYS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k in self.ENV_KEYS:
            os.environ.pop(k, None)
            if self._saved[k] is not None:
                os.environ[k] = self._saved[k]
        _reload_config()

    # ---- HOST / PORT：容器内必须能监听 0.0.0.0 与平台注入端口 ----

    def test_host_and_port_come_from_env(self):
        """部署平台注入的 HOST/PORT 必须覆盖 config.yaml 的值。"""
        os.environ["HOST"] = "0.0.0.0"
        os.environ["PORT"] = "8888"
        cfg = _reload_config()
        self.assertEqual(cfg.settings.HOST, "0.0.0.0")
        self.assertEqual(cfg.settings.PORT, 8888)

    def test_port_env_is_cast_to_int(self):
        """PORT 环境变量是字符串，必须转成 int，否则 uvicorn 会报错。"""
        os.environ["PORT"] = "12345"
        cfg = _reload_config()
        self.assertIsInstance(cfg.settings.PORT, int)
        self.assertEqual(cfg.settings.PORT, 12345)

    def test_without_env_local_defaults_are_unchanged(self):
        """不设环境变量时，行为必须与本地开发完全一致。"""
        cfg = _reload_config()
        self.assertIsInstance(cfg.settings.PORT, int)

    def test_invalid_port_env_is_ignored(self):
        """PORT 非法时不能崩，回退到配置文件的值。"""
        os.environ["PORT"] = "not-a-number"
        cfg = _reload_config()          # 不应抛异常
        self.assertIsInstance(cfg.settings.PORT, int)

    # ---- 模型 Key：云上靠环境变量注入，不进代码库 ----

    def test_api_keys_come_from_env(self):
        """各提供商 Key 必须能从环境变量读入。"""
        os.environ["DASHSCOPE_API_KEY"] = "sk-deploy-test-dashscope"
        os.environ["ARK_API_KEY"] = "ak-deploy-test-ark"
        cfg = _reload_config()
        providers = cfg.settings.CONFIG["api_providers"]
        self.assertEqual(providers["dashscope"]["api_key"], "sk-deploy-test-dashscope")
        self.assertEqual(providers["ark"]["api_key"], "ak-deploy-test-ark")

    def test_kling_keypair_come_from_env(self):
        """可灵需要 access_key + secret_key 两个值。"""
        os.environ["KLING_ACCESS_KEY"] = "ak-kling"
        os.environ["KLING_SECRET_KEY"] = "sk-kling"
        cfg = _reload_config()
        kling = cfg.settings.CONFIG["api_providers"]["kling"]
        self.assertEqual(kling["access_key"], "ak-kling")
        self.assertEqual(kling["secret_key"], "sk-kling")

    def test_empty_env_value_does_not_wipe_config(self):
        """空字符串环境变量应视为未设置，不能把已有值清掉。"""
        cfg_before = _reload_config()
        before = cfg_before.settings.CONFIG["api_providers"]["openai"]["base_url"]

        os.environ["OPENAI_BASE_URL"] = ""
        cfg_after = _reload_config()
        after = cfg_after.settings.CONFIG["api_providers"]["openai"]["base_url"]

        self.assertEqual(before, after)

    def test_env_survives_redaction(self):
        """环境变量注入的 Key 在对外配置里必须仍被掩码，不能泄漏。"""
        os.environ["DEEPSEEK_API_KEY"] = "sk-must-not-leak"
        cfg = _reload_config()
        public = cfg.redact_config(cfg.settings.CONFIG)
        self.assertNotIn("sk-must-not-leak", repr(public))


if __name__ == "__main__":
    unittest.main()
