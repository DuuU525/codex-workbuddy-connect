"""验证 Hermes provider 插件能被发现并注册。"""
import os
import sys

HERMES = str(_devcommon.HERMES_AGENT)
PLUGIN = str(_devcommon.HERMES_PLUGIN)
sys.path.insert(0, HERMES)
sys.path.insert(0, PLUGIN)

from providers import get_provider_profile, list_providers  # noqa: E402

import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("wbai_plugin", os.path.join(PLUGIN, "__init__.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

p = get_provider_profile("workbuddy-ai")
print("name        :", p.name)
print("display     :", p.display_name)
print("aliases     :", p.aliases)
print("base_url    :", p.base_url)
print("api_mode    :", p.api_mode)
print("auth_type   :", p.auth_type)
print("env_vars    :", p.env_vars, "-> 值 =", os.environ.get("WORKBUDDY_AI_API_KEY"))
print("fallback    :", len(p.fallback_models), "个模型")
print("max_tokens  : gpt-5.6-luna ->", p.get_max_tokens("gpt-5.6-luna"),
      "| kimi-k3 ->", p.get_max_tokens("kimi-k3"))
print("hostname    :", p.get_hostname())
nets = p.fetch_models()
print("fetch_models:", len(nets or []), "个", (nets or [])[:5])
print("\n别名解析: workbuddy ->", get_provider_profile("workbuddy").name,
      "| wb-ai ->", get_provider_profile("wb-ai").name)
