"""输入校验：与本地账号服务（auth-server）的昵称规则对齐。

为什么单独放一个模块：
  昵称既要被 /auth/register 用，也要被 /users/me 的 PATCH 用，两处共用同一套
  规则，避免「注册能过、改昵称却报错」或反过来这种双后端行为不一致。

规则（与 auth-server/src/utils/validate.js 的 assertNicknameInput 一致）：
  1. 连续的空白（含换行/制表符）折叠成单个空格，再 trim；
  2. 长度上限 24（折叠后）；
  3. 除空白以外的控制字符（\u0000-\u0008 / \u000b-\u001f / \u007f）一律拒绝；
  4. 空串的语义是「清除自定义昵称，回退到用户名」，因此返回 ""（不是 None）。

返回值是处理后的值（可能为空串），非法输入抛 AppError(PARAM_ERROR)。
"""

from app.core.responses import AppError, PARAM_ERROR

NICKNAME_MAX = 24

# 控制字符：\x00-\x08, \x0b-\x1f, \x7f。注意 \x09(\t) \x0a(\n) \x0d(\r) 属于空白，放行。
_CTRL_RE = __import__("re").compile(r"[\u0000-\u0008\u000b-\u001f\u007f]")


def assert_nickname(raw: str | None) -> str | None:
    """校验并规范化昵称。

    - None：调用方表示「不修改」，原样返回 None；
    - 合法：返回折叠空白后的字符串（可能为空串，表示清除）；
    - 非法：抛 AppError(PARAM_ERROR)，HTTP 400。
    """
    if raw is None:
        return None
    collapsed = __import__("re").sub(r"\s+", " ", raw).strip()
    if collapsed == "":
        # 空串 = 清除昵称（回退到用户名显示）
        return ""
    if _CTRL_RE.search(collapsed):
        raise AppError(PARAM_ERROR, "昵称含不可见控制字符，请重新输入", http_status=400)
    if len(collapsed) > NICKNAME_MAX:
        raise AppError(PARAM_ERROR, f"昵称最多 {NICKNAME_MAX} 个字符", http_status=400)
    return collapsed
