import "dart:math" as math;
import "dart:ui" as ui;
import "package:flutter/material.dart";
import "package:flutter_riverpod/flutter_riverpod.dart";
import "package:lottie/lottie.dart";

import "../core/audio/sound_service.dart";
import "../core/settings/settings.dart";
import "../core/theme/app_colors.dart";

/// CppCat · 缅因猫（Maine Coon）形象组件。
///
/// 渲染优先级（PRD §14 缅因猫版 · 2026-09-20 真实照片接入）：
///   1) 显式 imagePath（调用方指定，如圆角全身像 maine_coon_hero.png）
///   2) 真实照片 assets/images/cat_mascot/maine_coon.webp（主人提供的缅因猫，蓝白融合版）
///   3) 照片缺失 → 内置 CustomPainter 缅因猫（同形象，零资源也能跑）
///   4) 任何加载失败都不崩溃（errorBuilder 兜底）
///
/// 状态动效由 MaineCoonAssistant 用补间动画实现（呼吸/倾斜/摇晃/弹跳），
/// 代替 Lottie；「减少动效」开启时全部退化为静态照片。
/// 深色模式自动加青蓝色发光边缘，浅色模式加柔和蓝色微光（PRD §14.3）。
enum CatMood { happy, thinking, confused, cheer, celebrate, comfort, sleeping, loading }

/// 缅因猫主体：图片优先，兜底 CustomPainter，可加发光。
class CppCatMascot extends ConsumerWidget {
  const CppCatMascot({
    super.key,
    this.mood = CatMood.happy,
    this.size = 64,
    this.glow = true,
    this.imagePath,
    this.fit = BoxFit.cover,
  });

  final CatMood mood;
  final double size;
  final bool glow;

  /// 显式图片路径（如 assets/images/cat_mascot/maine_coon.png）。
  /// 提供时优先于 <mood>.webp 的自动命名；找不到则回退自动命名 → CustomPainter。
  final String? imagePath;
  final BoxFit fit;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final dark = Theme.of(context).brightness == Brightness.dark;

    final Widget painter = _MaineCoon(mood: mood, size: size);
    // 默认加载主人提供的真实缅因猫照片（蓝白融合版）；未提供 imagePath 时即为全 App 默认形象
    final String asset = imagePath ?? "assets/images/cat_mascot/maine_coon.webp";
    final Widget body = settings.reduceMotion
        ? painter
        : Image.asset(
            asset,
            width: size,
            height: size,
            fit: fit,
            frameBuilder: (_, child, __, ___) => child,
            errorBuilder: (_, __, ___) =>
                imagePath == null ? painter : _MaineCoon(mood: mood, size: size),
          );

    if (!glow) return body;
    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: (dark ? AppColors.cyan : AppColors.blue).withValues(alpha: dark ? 0.45 : 0.25),
            blurRadius: dark ? 16 : 10,
            spreadRadius: 0,
          ),
        ],
      ),
      child: ClipOval(child: body),
    );
  }
}

/// 加载动画：优先 Lottie（尾巴摆动 / 眨眼 / 敲键盘），兜底静态缅因猫。
class CatLoader extends ConsumerWidget {
  const CatLoader({super.key, this.size = 72});
  final double size;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(settingsProvider).reduceMotion) {
      return CppCatMascot(mood: CatMood.loading, size: size);
    }
    return Lottie.asset(
      "assets/cat/loading.json",
      width: size,
      height: size,
      errorBuilder: (_, __, ___) => CppCatMascot(mood: CatMood.loading, size: size),
    );
  }
}

/// 猫咪对话气泡（蓝白渐变 + 小尾巴，PRD §14.2）。
class CatBubble extends StatelessWidget {
  const CatBubble({super.key, required this.text, this.mood = CatMood.happy, this.catSize = 48});

  final String text;
  final CatMood mood;
  final double catSize;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        CppCatMascot(mood: mood, size: catSize, glow: false),
        const SizedBox(width: 8),
        Flexible(
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: dark
                    ? [const Color(0x661E3A8A), const Color(0xFF1E293B)]
                    : [const Color(0xFFDBEAFE), const Color(0xFFEFF6FF)],
              ),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(16),
                bottomRight: Radius.circular(16),
                bottomLeft: Radius.circular(4),
              ),
              border: Border.all(color: dark ? const Color(0x553B82F6) : const Color(0xFFBFDBFE)),
            ),
            child: Text(
              text,
              style: TextStyle(
                fontSize: 12,
                height: 1.6,
                color: dark ? const Color(0xFFBFDBFE) : const Color(0xFF1E3A8A),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// 缅因猫助手（可交互版）：图片资源 + 状态→表情映射 + 点击弹跳气泡 + 蓝光融合。
///
/// 用法：
/// ```dart
/// MaineCoonAssistant(
///   status: AssistantStatus.celebrate,   // 编译成功 / 答对
///   imagePath: "assets/images/cat_mascot/maine_coon.png",
///   defaultTip: "点我看看提示喵~",
/// )
/// ```
/// 点击猫咪 → 弹出带弹跳动画的提示气泡；再次点击 / 点气泡外关闭。
///
/// **音效**（Phase 7 新增，见 core/audio/sound_service.dart）：
/// * 点击猫咪播放 `tap`；
/// * `status` 发生跃迁时播放对应音效（成功/AC/失败/思考），
///   相同状态重复传入不重复播放（避免重建时噪音）。
class MaineCoonAssistant extends ConsumerStatefulWidget {
  const MaineCoonAssistant({
    super.key,
    this.status = AssistantStatus.idle,
    this.imagePath,
    this.tip,
    this.size = 64,
    this.sound = true,
  });

  /// 业务状态（编译中/成功/失败/加载等），自动映射到猫咪表情
  final AssistantStatus status;
  final String? imagePath;
  final String? tip;
  final double size;

  /// 是否允许状态跃迁时发声。列表/网格里批量渲染的场景可置 false，
  /// 避免多只猫咪同时开口。
  final bool sound;

  @override
  ConsumerState<MaineCoonAssistant> createState() => _MaineCoonAssistantState();
}

/// 业务状态 → 猫咪表情（缅因猫 8 表情）
enum AssistantStatus {
  idle, // 待机
  thinking, // 编译中 / 思考
  success, // 编译成功 / AC（竖大拇指）
  celebrate, // 庆祝
  fail, // 编译失败（眉头微皱，拍肩安慰）
  loading, // 加载
  sleeping, // 睡觉
}

extension AssistantStatusX on AssistantStatus {
  CatMood get mood => switch (this) {
        AssistantStatus.idle => CatMood.happy,
        AssistantStatus.thinking => CatMood.thinking,
        AssistantStatus.success => CatMood.cheer,
        AssistantStatus.celebrate => CatMood.celebrate,
        AssistantStatus.fail => CatMood.comfort,
        AssistantStatus.loading => CatMood.loading,
        AssistantStatus.sleeping => CatMood.sleeping,
      };

  String get defaultTip => switch (this) {
        AssistantStatus.idle => "主人好喵~ 有不懂的点我看看提示~",
        AssistantStatus.thinking => "沙箱编译中… 稍等一下喵~",
        AssistantStatus.success => "编译通过！给你竖个大拇指 👍",
        AssistantStatus.celebrate => "太棒了！AC 了喵~ 🎉",
        AssistantStatus.fail => "别灰心，拍拍肩膀~ 看下报错再试一次？",
        AssistantStatus.loading => "正在加载… 尾巴摇一摇~",
        AssistantStatus.sleeping => "呼… 我在小憩，轻点戳我~",
      };

  /// 该状态**跃迁到**时应播放的音效；null 表示不发声。
  ///
  /// 刻意不给 idle / loading / sleeping 配声音：这些状态在滚动、
  /// 重建、进场时高频出现，一响就变噪音。
  CppSound? get sound => switch (this) {
        AssistantStatus.thinking => CppSound.thinking,
        AssistantStatus.success => CppSound.success,
        AssistantStatus.celebrate => CppSound.celebrate,
        AssistantStatus.fail => CppSound.fail,
        _ => null,
      };
}

class _MaineCoonAssistantState extends ConsumerState<MaineCoonAssistant>
    with SingleTickerProviderStateMixin {
  bool _showTip = false;
  late final AnimationController _bounce = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 500),
  );

  @override
  void didUpdateWidget(covariant MaineCoonAssistant oldWidget) {
    super.didUpdateWidget(oldWidget);
    // status 跃迁才发声（同状态重复传入不响），避免父级重建造成噪音。
    if (oldWidget.status != widget.status && widget.sound) {
      final s = widget.status.sound;
      if (s != null) ref.read(soundServiceProvider).play(s);
    }
  }

  @override
  void dispose() {
    _bounce.dispose();
    super.dispose();
  }

  void _toggleTip() {
    setState(() => _showTip = !_showTip);
    if (_showTip) {
      ref.read(soundServiceProvider).play(CppSound.tap);
      _bounce
        ..reset()
        ..forward();
    }
  }

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final tip = widget.tip ?? widget.status.defaultTip;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // 提示气泡（弹跳动画）
        AnimatedBuilder(
          animation: _bounce,
          builder: (_, child) => AnimatedOpacity(
            opacity: _showTip ? 1 : 0,
            duration: const Duration(milliseconds: 180),
            child: AnimatedScale(
              scale: _showTip ? 1 : 0.6,
              duration: const Duration(milliseconds: 180),
              child: Transform.translate(
                offset: Offset(0, _showTip ? 0 : 6),
                child: child,
              ),
            ),
          ),
          child: Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            constraints: const BoxConstraints(maxWidth: 220),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: dark
                    ? [const Color(0xCC1E3A8A), const Color(0xFF1E293B)]
                    : [const Color(0xFFDBEAFE), const Color(0xFFEFF6FF)],
              ),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: dark ? const Color(0x663B82F6) : const Color(0xFFBFDBFE)),
              boxShadow: [
                BoxShadow(
                  color: (dark ? AppColors.cyan : AppColors.blue).withValues(alpha: 0.18),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Text(
              tip,
              style: TextStyle(
                fontSize: 12,
                height: 1.5,
                color: dark ? const Color(0xFFBFDBFE) : const Color(0xFF1E3A8A),
              ),
            ),
          ),
        ),
        // 猫咪（点击弹跳 + 蓝光融合）
        GestureDetector(
          onTap: _toggleTip,
          child: ScaleTransition(
            scale: TweenSequence<double>([
              TweenSequenceItem(tween: Tween(begin: 1.0, end: 1.12).chain(CurveTween(curve: Curves.easeOut)), weight: 50),
              TweenSequenceItem(tween: Tween(begin: 1.12, end: 1.0).chain(CurveTween(curve: Curves.easeIn)), weight: 50),
            ]).animate(_bounce),
            child: CppCatMascot(
              mood: widget.status.mood,
              size: widget.size,
              glow: true,
              imagePath: widget.imagePath,
            ),
          ),
        ),
      ],
    );
  }
}

/// ============ 兜底：内置缅因猫 CustomPainter（与 web 演示版同形象） ============
class _MaineCoon extends StatelessWidget {
  const _MaineCoon({required this.mood, required this.size});
  final CatMood mood;
  final double size;

  @override
  Widget build(BuildContext context) =>
      CustomPaint(size: Size.square(size), painter: _MaineCoonPainter(mood));
}

class _MaineCoonPainter extends CustomPainter {
  _MaineCoonPainter(this.mood);
  final CatMood mood;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 80;
    final ink = Paint()
      ..color = const Color(0xFF0F172A)
      ..strokeWidth = 2.4 * s
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    final fur = Paint()
      ..shader = ui.Gradient.linear(
        Offset(0, 20 * s),
        Offset(0, 70 * s),
        [const Color(0xFFCBD5E1), const Color(0xFF93C5FD), const Color(0xFF60A5FA)],
      );
    final chest = Paint()
      ..shader = ui.Gradient.radial(Offset(40 * s, 52 * s), 18 * s,
          [Colors.white, const Color(0xFFDBEAFE)]);
    final pink = Paint()..color = const Color(0xFFFBCFE8);
    final tuft = Paint()
      ..color = const Color(0xFF475569)
      ..strokeWidth = 1.5 * s
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    final blush = Paint()..color = const Color(0xFF93C5FD).withValues(alpha: 0.5);
    final wh = Paint()
      ..color = const Color(0xFF94A3B8)
      ..strokeWidth = 1 * s
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // 蓬松尾巴
    final tail = Path()
      ..moveTo(62 * s, 58 * s)
      ..quadraticBezierTo(80 * s, 66 * s, 75 * s, 42 * s)
      ..quadraticBezierTo(72 * s, 33 * s, 64 * s, 38 * s);
    canvas.drawPath(
        tail,
        Paint()
          ..color = const Color(0xFF60A5FA)
          ..strokeWidth = 9 * s
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke);
    fur.style = PaintingStyle.fill;

    // 耳朵 + 粉内耳
    canvas.drawPath(Path()..moveTo(17 * s, 28 * s)..lineTo(11 * s, 7 * s)..lineTo(34 * s, 19 * s)..close(), fur);
    canvas.drawPath(Path()..moveTo(63 * s, 28 * s)..lineTo(69 * s, 7 * s)..lineTo(46 * s, 19 * s)..close(), fur);
    canvas.drawPath(Path()..moveTo(21 * s, 24 * s)..lineTo(18 * s, 12 * s)..lineTo(30 * s, 19 * s)..close(), pink);
    canvas.drawPath(Path()..moveTo(59 * s, 24 * s)..lineTo(62 * s, 12 * s)..lineTo(50 * s, 19 * s)..close(), pink);
    // 猞猁耳尖（聪明毛）
    canvas.drawLine(Offset(11 * s, 7 * s), Offset(8 * s, 1 * s), tuft);
    canvas.drawLine(Offset(15 * s, 9 * s), Offset(14 * s, 3 * s), tuft);
    canvas.drawLine(Offset(69 * s, 7 * s), Offset(72 * s, 1 * s), tuft);
    canvas.drawLine(Offset(65 * s, 9 * s), Offset(66 * s, 3 * s), tuft);

    // 蓬松头部
    canvas.drawOval(Rect.fromCenter(center: Offset(40 * s, 43 * s), width: 56 * s, height: 50 * s), fur);
    // 脸颊蓬松毛
    canvas.drawPath(Path()..moveTo(13 * s, 40 * s)..lineTo(6 * s, 43 * s)..lineTo(13 * s, 47 * s)..close(), fur);
    canvas.drawPath(Path()..moveTo(13 * s, 52 * s)..lineTo(6 * s, 54 * s)..lineTo(13 * s, 58 * s)..close(), fur);
    canvas.drawPath(Path()..moveTo(67 * s, 40 * s)..lineTo(74 * s, 43 * s)..lineTo(67 * s, 47 * s)..close(), fur);
    canvas.drawPath(Path()..moveTo(67 * s, 52 * s)..lineTo(74 * s, 54 * s)..lineTo(67 * s, 58 * s)..close(), fur);
    // 白色胸前毛
    canvas.drawOval(Rect.fromCenter(center: Offset(40 * s, 58 * s), width: 34 * s, height: 30 * s), chest);
    // 腮红
    canvas.drawCircle(Offset(27 * s, 48 * s), 3.4 * s, blush);
    canvas.drawCircle(Offset(53 * s, 48 * s), 3.4 * s, blush);

    _drawEyes(canvas, s, ink);
    _drawGlasses(canvas, s);
    // 鼻子
    canvas.drawPath(Path()..moveTo(37 * s, 48 * s)..lineTo(43 * s, 48 * s)..lineTo(40 * s, 51.4 * s)..close(),
        Paint()..color = const Color(0xFFF472B6));
    _drawMouth(canvas, s, ink);
    // 胡须
    canvas.drawLine(Offset(22 * s, 47 * s), Offset(12 * s, 45 * s), wh);
    canvas.drawLine(Offset(22 * s, 51 * s), Offset(12 * s, 52 * s), wh);
    canvas.drawLine(Offset(58 * s, 47 * s), Offset(68 * s, 45 * s), wh);
    canvas.drawLine(Offset(58 * s, 51 * s), Offset(68 * s, 52 * s), wh);
  }

  void _drawEyes(Canvas c, double s, Paint ink) {
    switch (mood) {
      case CatMood.happy:
      case CatMood.cheer:
      case CatMood.celebrate:
        c.drawArc(Rect.fromCircle(center: Offset(31 * s, 40 * s), radius: 4.5 * s), 3.8, 5.6, false, ink);
        c.drawArc(Rect.fromCircle(center: Offset(49 * s, 40 * s), radius: 4.5 * s), 3.8, 5.6, false, ink);
      case CatMood.comfort:
        c.drawArc(Rect.fromCircle(center: Offset(31 * s, 40 * s), radius: 4.5 * s), 3.4, 2.9, false, ink);
        c.drawArc(Rect.fromCircle(center: Offset(49 * s, 40 * s), radius: 4.5 * s), 3.4, 2.9, false, ink);
      case CatMood.sleeping:
        c.drawLine(Offset(27 * s, 40 * s), Offset(35 * s, 40 * s), ink);
        c.drawLine(Offset(45 * s, 40 * s), Offset(53 * s, 40 * s), ink);
        _drawText(c, "Z", 60 * s, 18 * s, 14 * s, AppColors.blue);
      case CatMood.confused:
        c.drawCircle(Offset(31 * s, 40 * s), 3 * s, Paint()..color = const Color(0xFF0F172A));
        _drawText(c, "?", 45 * s, 44 * s, 14 * s, const Color(0xFF0F172A));
      default: // thinking / loading：大圆蓝眼睛 + 高光
        final eyeW = Paint()..color = const Color(0xFFEFF6FF);
        final eyeB = Paint()..color = AppColors.blue;
        final hi = Paint()..color = Colors.white;
        for (final cx in [31.0, 49.0]) {
          c.drawCircle(Offset(cx * s, 40 * s), 6.4 * s, eyeW);
          c.drawCircle(Offset(cx * s, 40 * s), 4.4 * s, eyeB);
          c.drawCircle(Offset((cx + 1.6) * s, 38.2 * s), 1.8 * s, hi);
        }
    }
  }

  void _drawGlasses(Canvas c, double s) {
    final glass = Paint()
      ..color = AppColors.blue.withValues(alpha: 0.75)
      ..strokeWidth = 2 * s
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(24.5 * s, 34 * s, 14 * s, 12 * s), Radius.circular(5 * s)), glass);
    c.drawRRect(RRect.fromRectAndRadius(Rect.fromLTWH(41.5 * s, 34 * s, 14 * s, 12 * s), Radius.circular(5 * s)), glass);
    c.drawLine(Offset(38.5 * s, 40 * s), Offset(41.5 * s, 40 * s), glass);
    c.drawLine(Offset(24.5 * s, 38 * s), Offset(19.5 * s, 36 * s), glass);
    c.drawLine(Offset(55.5 * s, 38 * s), Offset(60.5 * s, 36 * s), glass);
  }

  void _drawMouth(Canvas c, double s, Paint ink) {
    switch (mood) {
      case CatMood.cheer:
      case CatMood.celebrate:
        c.drawArc(Rect.fromCircle(center: Offset(40 * s, 49 * s), radius: 6 * s), 0.2, 2.7, false, ink);
      case CatMood.comfort:
        c.drawArc(Rect.fromCircle(center: Offset(40 * s, 51 * s), radius: 4 * s), 3.6, 5.8, false, ink);
      case CatMood.sleeping:
        c.drawCircle(Offset(40 * s, 51 * s), 2 * s, Paint()..color = const Color(0xFF0F172A)..style = PaintingStyle.stroke..strokeWidth = 1.8 * s);
      case CatMood.confused:
        c.drawArc(Rect.fromCircle(center: Offset(40 * s, 53 * s), radius: 4 * s), 3.6, 5.8, false, ink);
      case CatMood.happy:
      default:
        c.drawArc(Rect.fromCircle(center: Offset(40 * s, 50 * s), radius: 4 * s), 0.4, 2.4, false, ink);
    }
  }

  void _drawText(Canvas c, String t, double x, double y, double fs, Color col) {
    final tp = TextPainter(
      text: TextSpan(text: t, style: TextStyle(fontSize: fs, fontWeight: FontWeight.bold, color: col)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(c, Offset(x, y - fs * 0.7));
  }

  @override
  bool shouldRepaint(_MaineCoonPainter old) => old.mood != mood;
}
