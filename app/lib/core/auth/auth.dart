import "package:flutter_riverpod/flutter_riverpod.dart";

import "../api/api_client.dart";
import "../models/models.dart";

/// 认证状态：unknown(启动中) / guest(游客，可浏览 3 章) / authed
enum AuthStatus { unknown, guest, authed }

class AuthState {
  const AuthState({this.status = AuthStatus.unknown, this.user});
  final AuthStatus status;
  final User? user;

  AuthState copyWith({AuthStatus? status, User? user}) =>
      AuthState(status: status ?? this.status, user: user ?? this.user);
}

class AuthNotifier extends Notifier<AuthState> {
  ApiClient get _api => ref.read(apiClientProvider);
  TokenStorage get _tokens => ref.read(tokenStorageProvider);

  @override
  AuthState build() {
    Future.microtask(bootstrap);
    return const AuthState();
  }

  /// 冷启动：有 token 则拉取用户信息，否则落游客态
  Future<void> bootstrap() async {
    if (await _tokens.access == null) {
      state = state.copyWith(status: AuthStatus.guest);
      return;
    }
    try {
      final data = await _api.get("/users/me");
      state = AuthState(status: AuthStatus.authed, user: User.fromJson(data as Map<String, dynamic>));
    } on ApiException {
      state = state.copyWith(status: AuthStatus.guest);
    }
  }

  Future<void> login(String email, String password) async {
    final data = await _api.post("/auth/login", data: {"email": email, "password": password});
    await _tokens.save(
      access: data["access_token"] as String,
      refresh: data["refresh_token"] as String,
    );
    await bootstrap();
  }

  Future<void> register(String email, String password, String nickname) async {
    final data = await _api.post("/auth/register",
        data: {"email": email, "password": password, "nickname": nickname});
    await _tokens.save(
      access: data["access_token"] as String,
      refresh: data["refresh_token"] as String,
    );
    await bootstrap();
  }

  Future<void> logout() async {
    await _tokens.clear();
    state = const AuthState(status: AuthStatus.guest);
  }
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
