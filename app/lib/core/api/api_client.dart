import "package:dio/dio.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:flutter_secure_storage/flutter_secure_storage.dart";

/// 与后端契约对齐（server/app/core/responses.py）：
///   成功：{code:0, message, data, traceId}
///   失败：{code:1xxx/2xxx/4xxx, message, data, traceId}
class ApiException implements Exception {
  ApiException(this.code, this.message, {this.traceId});

  final int code;
  final String message;
  final String? traceId;

  static const unauthorized = 1002;
  static const quotaExceeded = 2001;
  static const guestRestricted = 4021;

  @override
  String toString() => "ApiException($code): $message";
}

class TokenStorage {
  static const _kAccess = "token.access";
  static const _kRefresh = "token.refresh";
  final _store = const FlutterSecureStorage();

  Future<String?> get access => _store.read(key: _kAccess);
  Future<String?> get refresh => _store.read(key: _kRefresh);

  Future<void> save({required String access, required String refresh}) async {
    await _store.write(key: _kAccess, value: access);
    await _store.write(key: _kRefresh, value: refresh);
  }

  Future<void> clear() async {
    await _store.delete(key: _kAccess);
    await _store.delete(key: _kRefresh);
  }
}

class ApiClient {
  ApiClient(this._tokenStorage)
      : dio = Dio(BaseOptions(
          // 打包时通过 --dart-define=API_BASE_URL=https://api.example.com/api/v1 注入
          baseUrl: const String.fromEnvironment(
            "API_BASE_URL",
            defaultValue: "http://10.0.2.2:8000/api/v1", // Android 模拟器访问宿主机
          ),
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        )) {
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _tokenStorage.access;
        if (token != null) options.headers["Authorization"] = "Bearer $token";
        handler.next(options);
      },
      onError: (e, handler) async {
        // access token 过期 → 用 refresh token 换新后重放一次（后端为旋转刷新）
        if (e.response?.statusCode == 401 && !_isRefreshCall(e)) {
          final ok = await _refresh();
          if (ok) {
            final req = e.requestOptions;
            req.headers["Authorization"] = "Bearer ${await _tokenStorage.access}";
            try {
              return handler.resolve(await dio.fetch(req));
            } on DioException catch (retryError) {
              return handler.next(retryError);
            }
          }
        }
        handler.next(e);
      },
    ));
  }

  final Dio dio;
  final TokenStorage _tokenStorage;
  bool _refreshing = false;

  bool _isRefreshCall(DioException e) => e.requestOptions.path.endsWith("/auth/refresh");

  Future<bool> _refresh() async {
    if (_refreshing) return false;
    _refreshing = true;
    try {
      final rt = await _tokenStorage.refresh;
      if (rt == null) return false;
      final resp = await dio.post<Map<String, dynamic>>(
        "/auth/refresh",
        data: {"refresh_token": rt},
        options: Options(headers: {"Authorization": null}),
      );
      final data = _unwrap(resp.data!);
      await _tokenStorage.save(
        access: data["access_token"] as String,
        refresh: data["refresh_token"] as String,
      );
      return true;
    } catch (_) {
      await _tokenStorage.clear();
      return false;
    } finally {
      _refreshing = false;
    }
  }

  dynamic _unwrap(Map<String, dynamic> body) {
    final code = body["code"] as int? ?? -1;
    if (code != 0) {
      throw ApiException(code, body["message"] as String? ?? "未知错误",
          traceId: body["traceId"] as String?);
    }
    return body["data"];
  }

  /// GET，自动解包 envelope，返回 data 字段
  Future<dynamic> get(String path, {Map<String, dynamic>? query}) async {
    try {
      final resp = await dio.get<Map<String, dynamic>>(path, queryParameters: query);
      return _unwrap(resp.data!);
    } on DioException catch (e) {
      throw _convert(e);
    }
  }

  Future<dynamic> post(String path, {Object? data}) async {
    try {
      final resp = await dio.post<Map<String, dynamic>>(path, data: data);
      return _unwrap(resp.data!);
    } on DioException catch (e) {
      throw _convert(e);
    }
  }

  Future<dynamic> patch(String path, {Object? data}) async {
    try {
      final resp = await dio.patch<Map<String, dynamic>>(path, data: data);
      return _unwrap(resp.data!);
    } on DioException catch (e) {
      throw _convert(e);
    }
  }

  ApiException _convert(DioException e) {
    final body = e.response?.data;
    if (body is Map<String, dynamic> && body.containsKey("code")) {
      return ApiException(
        body["code"] as int? ?? -1,
        body["message"] as String? ?? "请求失败",
        traceId: body["traceId"] as String?,
      );
    }
    if (e.type == DioExceptionType.connectionError ||
        e.type == DioExceptionType.connectionTimeout) {
      return ApiException(-1, "网络连接失败，请检查网络后重试");
    }
    return ApiException(e.response?.statusCode ?? -1, e.message ?? "请求失败");
  }
}

final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient(ref.watch(tokenStorageProvider)));
