import "dart:convert";

import "package:hive_flutter/hive_flutter.dart";

/// 离线缓存（P0-9）：章节/练习/导图落 Hive，网络失败时兜底展示。
/// 策略：网络优先 + 成功即写缓存；网络异常时读缓存（带 24h 新鲜度标记）。
class LocalCache {
  static const _boxName = "cppmind_cache";
  static const _freshTtl = Duration(hours: 24);

  static Future<void> init() async {
    await Hive.initFlutter();
    await Hive.openBox<String>(_boxName);
  }

  static Box<String> get _box => Hive.box<String>(_boxName);

  static Future<void> write(String key, Object data) async {
    await _box.put(key, jsonEncode({"ts": DateTime.now().millisecondsSinceEpoch, "data": data}));
  }

  /// 返回 (data, isFresh)；无缓存返回 (null, false)
  static (dynamic, bool) read(String key) {
    final raw = _box.get(key);
    if (raw == null) return (null, false);
    try {
      final pack = jsonDecode(raw) as Map<String, dynamic>;
      final fresh = DateTime.now().millisecondsSinceEpoch - (pack["ts"] as int) < _freshTtl.inMilliseconds;
      return (pack["data"], fresh);
    } catch (_) {
      return (null, false);
    }
  }

  /// 网络优先、缓存兜底
  static Future<T> cachedOrNetwork<T>({
    required String key,
    required Future<dynamic> Function() fetch,
    required T Function(dynamic json) parse,
  }) async {
    try {
      final data = await fetch();
      await write(key, data is Map || data is List ? data : data);
      return parse(data);
    } catch (_) {
      final (cached, _) = read(key);
      if (cached != null) return parse(cached);
      rethrow;
    }
  }
}
