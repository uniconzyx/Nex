import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:go_router/go_router.dart";

import "../../core/api/api_client.dart";
import "../../core/theme/app_colors.dart";
import "../../widgets/cpp_cat.dart";

/// 登录 / 注册：提交 /auth/login，保存 token（后端旋转刷新），成功后回首页
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _nick = TextEditingController();
  final _pwd = TextEditingController();
  bool _busy = false;
  String? _err;

  Future<void> _submit() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final data = await ref.read(apiClientProvider).post("/auth/login", data: {
        "nickname": _nick.text.trim(),
        "password": _pwd.text,
      });
      // 后端返回 {access_token, refresh_token}，TokenStorage 已在拦截器内更新
      await ref.read(tokenStorageProvider).save(
        access: data["access_token"] as String,
        refresh: data["refresh_token"] as String,
      );
      if (mounted) context.go("/home");
    } on ApiException catch (e) {
      if (e.code == ApiException.unauthorized) {
        setState(() => _err = "账号或密码错误，再试试喵~");
      } else {
        setState(() => _err = e.message);
      }
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(leading: const BackButton(), backgroundColor: Colors.transparent, elevation: 0),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          CppCatMascot(mood: CatMood.happy, size: 96),
          const SizedBox(height: 16),
          const Text("欢迎回来 🐱", style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
          const SizedBox(height: 24),
          TextField(controller: _nick, decoration: const InputDecoration(labelText: "昵称 / 邮箱", prefixIcon: Icon(Icons.person_rounded))),
          const SizedBox(height: 12),
          TextField(controller: _pwd, obscureText: true, decoration: const InputDecoration(labelText: "密码", prefixIcon: Icon(Icons.lock_rounded))),
          if (_err != null) ...[
            const SizedBox(height: 10),
            Text(_err!, style: const TextStyle(color: AppColors.red, fontSize: 12)),
          ],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _busy ? null : _submit,
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(48)),
            child: _busy ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Text("登录"),
          ),
        ]),
      ),
    );
  }
}
